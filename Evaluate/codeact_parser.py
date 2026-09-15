"""Incremental Python tool actions without exec/eval or an unrestricted interpreter."""

from __future__ import annotations

import ast
import io
import json
import operator
import re
import tokenize
from copy import deepcopy
from typing import Any


class CodeActError(ValueError):
    pass


def response_boundary(text: str) -> int | None:
    """Find the first complete block, ignoring closing tags in Python strings/comments."""
    opening = re.match(r"\s*<(code|answer)\s*>", text, re.IGNORECASE)
    if not opening:
        return None
    tag = opening.group(1).lower()
    body = text[opening.end():]
    closing = list(re.finditer(rf"</{tag}\s*>", body, re.IGNORECASE))
    if not closing:
        return None
    if tag == "answer":
        return opening.end() + closing[0].end()

    offsets = [0]
    for line in body.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def offset(position):
        row, column = position
        return offsets[min(row - 1, len(offsets) - 1)] + column

    protected = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(body).readline):
            if token.type in (tokenize.STRING, tokenize.COMMENT):
                protected.append((offset(token.start), offset(token.end)))
    except tokenize.TokenError as exc:
        if "multi-line string" in exc.args[0]:
            protected.append((offset(exc.args[1]), len(body)))
    except (IndentationError, SyntaxError):
        # A malformed program still needs to stop at its real closing tag.
        pass
    for match in closing:
        if not any(start <= match.start() < end for start, end in protected):
            return opening.end() + match.end()
    return None


def truncate_response(text: str) -> str:
    """Discard overgeneration without rewriting Python or fabricating observations."""
    boundary = response_boundary(text)
    return text[:boundary] if boundary is not None else text


def parse_response(text: str) -> tuple[str, ast.Module | None]:
    """Require exactly one code block or a terminal answer, without mixed actions."""
    answer = re.fullmatch(r"\s*<answer\s*>(.*?)</answer\s*>\s*", text, re.DOTALL | re.IGNORECASE)
    if answer and answer.group(1).strip() and not re.search(r"</?(?:code|answer)\s*>", answer.group(1), re.IGNORECASE):
        return answer.group(1).strip(), None
    match = re.fullmatch(r"\s*<code\s*>\s*(.*?)\s*</code\s*>\s*", text, re.DOTALL | re.IGNORECASE)
    if not match or not match.group(1).strip():
        raise CodeActError("Return one <code>Python statements</code> or one <answer>...</answer>.")
    source = match.group(1)
    if len(source) > 32_768:
        raise CodeActError("Code block is too large.")
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise CodeActError(f"Invalid Python syntax: {exc}") from exc
    if sum(1 for _ in ast.walk(tree)) > 2048:
        raise CodeActError("Code block is too complex.")
    return source, tree


def format_valid(text: str) -> bool:
    try:
        _, tree = parse_response(text)
        if tree is None:
            return True
        validate_tree(tree)
        return any(isinstance(node, ast.Call) for node in ast.walk(tree))
    except CodeActError:
        return False


def validate_tree(tree: ast.Module) -> None:
    # A small Python subset keeps model-generated code away from Python objects,
    # files, imports, unbounded loops, and arbitrary function execution.
    allowed = (
        ast.Module, ast.Assign, ast.Expr, ast.If, ast.Pass,
        ast.Name, ast.Load, ast.Store, ast.Constant, ast.Dict, ast.List, ast.Tuple,
        ast.Subscript, ast.Slice, ast.Call, ast.keyword, ast.UnaryOp,
        ast.USub, ast.UAdd, ast.Not, ast.Compare, ast.Eq, ast.NotEq, ast.Lt,
        ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
        ast.BoolOp, ast.And, ast.Or, ast.IfExp,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise CodeActError(f"Unsupported Python construct: {type(node).__name__}.")
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise CodeActError("Assign to one variable, not attributes, unpacking, or indexed values.")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise CodeActError("Dunder names are not permitted.")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.args:
                raise CodeActError("Use direct tool names with keyword arguments only.")
            names = [keyword.arg for keyword in node.keywords if keyword.arg is not None]
            if len(names) != len(set(names)):
                raise CodeActError("Duplicate tool argument.")
            if any(isinstance(child, ast.Call) for keyword in node.keywords for child in ast.walk(keyword.value)):
                raise CodeActError("Put dependent tool calls in separate assignments.")


def decode_output(output: Any) -> Any:
    """Preserve native data; decode JSON/Python literal data, never executable text."""
    if not isinstance(output, str):
        return deepcopy(output)
    try:
        return json.loads(output)
    except (ValueError, TypeError):
        pass
    # Enterprise tools also serialize dictionaries using str(dict).
    try:
        value = ast.literal_eval(output)
        json.dumps(value, allow_nan=False)
        return value
    except (ValueError, SyntaxError, TypeError, RecursionError, OverflowError):
        return output


class CodeActSession:
    """Per-trajectory bindings; stop before dispatching the first selected tool."""

    def __init__(self, tool_names):
        self.tool_names = set(tool_names)
        self.variables: dict[str, Any] = {}

    def parse_turn(self, text: str) -> dict[str, Any]:
        try:
            _, tree = parse_response(text)
            if tree is None:
                return {"finished": True}
            validate_tree(tree)
            variables = dict(self.variables)
            action = self._statements(tree.body, variables)
            if action is None:
                raise CodeActError("No tool call selected. Emit an action or a final answer.")
            self.variables = variables
            return action
        except (CodeActError, KeyError, IndexError, TypeError, ValueError, RecursionError) as exc:
            return {"error_reason": "invalid_code_action", "error": str(exc)}

    def _statements(self, statements, variables):
        for statement in statements:
            if isinstance(statement, ast.If):
                body = statement.body if self._value(statement.test, variables) else statement.orelse
                action = self._statements(body, variables)
                if action is not None:
                    return action
                continue
            if isinstance(statement, ast.Pass):
                continue
            target = statement.targets[0].id if isinstance(statement, ast.Assign) else None
            if target in self.tool_names:
                raise CodeActError("A variable cannot shadow an available tool name.")
            value = statement.value
            if isinstance(value, ast.Call):
                name = value.func.id
                if name not in self.tool_names:
                    raise CodeActError(f"Unknown tool: {name}.")
                args = {}
                for keyword in value.keywords:
                    argument = self._value(keyword.value, variables)
                    expanded = argument if keyword.arg is None else {keyword.arg: argument}
                    if not isinstance(expanded, dict) or not all(isinstance(key, str) for key in expanded):
                        raise CodeActError("Expanded **arguments must be a dictionary with string keys.")
                    duplicates = args.keys() & expanded.keys()
                    if duplicates:
                        raise CodeActError(f"Duplicate tool arguments: {sorted(duplicates)}.")
                    args.update(expanded)
                json.dumps(args, allow_nan=False)
                return {"finished": False, "tool_name": name, "tool_args": args, "bind_variable": target}
            result = self._value(value, variables)
            if target is not None:
                variables[target] = result
        return None

    def _value(self, node, variables):
        if isinstance(node, ast.Constant):
            if type(node.value) not in (str, int, float, bool, type(None)):
                raise CodeActError("Only JSON-compatible literal values are supported.")
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise CodeActError(f"Variable {node.id!r} has no value. Use a completed tool result or define it first.")
            return variables[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self._value(item, variables) for item in node.elts]
        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                raise CodeActError("Dictionary unpacking is not supported.")
            return {self._value(key, variables): self._value(value, variables) for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            return self._value(node.value, variables)[self._value(node.slice, variables)]
        if isinstance(node, ast.Slice):
            return slice(*(self._value(value, variables) if value is not None else None for value in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.UnaryOp):
            fn = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}[type(node.op)]
            return fn(self._value(node.operand, variables))
        if isinstance(node, ast.Compare):
            functions = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                         ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
                         ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
                         ast.Is: operator.is_, ast.IsNot: operator.is_not}
            left = self._value(node.left, variables)
            for op, right_node in zip(node.ops, node.comparators):
                right = self._value(right_node, variables)
                if not functions[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            for child in node.values:
                result = self._value(child, variables)
                if isinstance(node.op, ast.And) and not result:
                    return result
                if isinstance(node.op, ast.Or) and result:
                    return result
            return result
        if isinstance(node, ast.IfExp):
            return self._value(node.body if self._value(node.test, variables) else node.orelse, variables)
        raise CodeActError("Tool calls must be standalone statements or assigned directly to a variable.")

    def bind_result(self, action, output, success: bool) -> Any:
        target = action.get("bind_variable")
        value = decode_output(output)
        if target:
            if success:
                self.variables[target] = value
            else:
                # Never retain a stale success value after a failed reassignment.
                self.variables.pop(target, None)
        return value
