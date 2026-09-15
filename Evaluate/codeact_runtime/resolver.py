"""Bounded AST evaluation that yields before dispatching the first selected tool."""

import ast
import hashlib
import json
import operator
import re
from copy import deepcopy

from .protocol import parse_program
from .state import SessionState, check_value, preview
from .types import (FinalAnswer, LocalResult, ResolutionFailure, ResolverError,
                    RuntimeLimits, ToolCallReady)

HELPERS = {"len": len, "str": str, "int": int, "float": float, "bool": bool,
           "abs": abs, "round": round}
RESERVED = set(HELPERS) | {"print"}
BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
COMPARISONS = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
               ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
               ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
               ast.Is: operator.is_, ast.IsNot: operator.is_not}


class CodeActResolver:
    def __init__(self, tool_names, limits=None, session_id="trajectory"):
        self.tool_names = frozenset(tool_names)
        if self.tool_names & RESERVED:
            raise ValueError(f"Tool names conflict with local helpers: {sorted(self.tool_names & RESERVED)}")
        self.limits = limits or RuntimeLimits()
        self.state = SessionState(self.limits)
        self.session_id = session_id

    @property
    def variables(self):
        return self.state.variables

    def resolve(self, text, source_segment_index=0, planner_turn_index=0):
        self.operations = 0
        self.node = None
        self.stdout = ""
        self.changed = set()
        self.executed = []
        self.dependencies = set()
        self.segment_index = source_segment_index
        self.turn_index = planner_turn_index
        try:
            self.source, tree = parse_program(text, self.limits.max_depth)
            if tree is None:
                return FinalAnswer(self.source)
            self.working = deepcopy(self.state.variables)
            self.sources = deepcopy(self.state.provenance)
            event = self._statements(tree.body)
            self.state.commit(self.working, self.sources)
            return event or LocalResult(tuple(sorted(self.changed)),
                                        {name: preview(self.working[name]) for name in sorted(self.changed)},
                                        self.stdout)
        except ResolutionFailure as exc:
            return self._error(exc.kind, str(exc), exc.format_valid)
        except (KeyError, IndexError, TypeError, ValueError, ArithmeticError) as exc:
            return self._error(type(exc).__name__, str(exc), True)
        except RecursionError:
            return self._error("resource_limit", "Nesting limit exceeded.", False)

    def _error(self, kind, message, format_valid):
        return ResolverError(kind, message[:1000], getattr(self.node, "lineno", None),
                             getattr(self.node, "col_offset", None), format_valid)

    def _tick(self, node):
        self.node = node
        self.operations += 1
        if self.operations > self.limits.max_operations:
            raise ResolutionFailure("Local execution budget exhausted.", "resource_limit")

    def _name(self, name, assignment=False):
        if name.startswith("__") or (assignment and name in self.tool_names | RESERVED):
            raise ResolutionFailure(f"Reserved name: {name!r}.")

    def _statements(self, statements):
        for statement in statements:
            self._tick(statement)
            if isinstance(statement, ast.If):
                selected = bool(self._value(statement.test))
                self.executed.append(f"# Selected {'true' if selected else 'false'} branch: {ast.unparse(statement.test)}")
                event = self._statements(statement.body if selected else statement.orelse)
                if event:
                    return event
                continue
            if isinstance(statement, ast.Pass):
                self.executed.append("pass")
                continue
            target = None
            if isinstance(statement, ast.Assign):
                if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                    raise ResolutionFailure("Assign to one variable, not attributes, indexing or unpacking.")
                target = statement.targets[0].id
                self._name(target, assignment=True)
            elif not isinstance(statement, ast.Expr):
                raise ResolutionFailure(f"Unsupported Python statement: {type(statement).__name__}.")
            value = statement.value
            self.dependencies = set()
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in self.tool_names:
                if value.args:
                    raise ResolutionFailure("Tool calls require keyword arguments; positional order is not inferred.")
                args = self._kwargs(value.keywords)
                self._json_arguments(args)
                self.executed.append(ast.get_source_segment(self.source, statement) or ast.unparse(statement))
                call_id = f"{self.session_id}_turn_{self.turn_index}_segment_{self.segment_index}"
                return ToolCallReady(value.func.id, deepcopy(args), target, self.segment_index,
                                     self.turn_index, call_id, "\n".join(self.executed), self.stdout)
            result = self._value(value)
            if target is not None:
                self.working[target] = result
                self.sources[target] = {"origin": "derived" if self.dependencies else "model_literal",
                                        "dependencies": sorted(self.dependencies),
                                        "planner_turn_index": self.turn_index}
                self.changed.add(target)
            self.executed.append(ast.get_source_segment(self.source, statement) or ast.unparse(statement))
        return None

    def _json_arguments(self, args):
        pending = [args]
        while pending:
            value = pending.pop()
            if type(value) is dict:
                if not all(type(key) is str for key in value):
                    raise ResolutionFailure("Tool argument objects require string keys.")
                pending.extend(value.values())
            elif type(value) is list:
                pending.extend(value)
            elif type(value) is tuple:
                raise ResolutionFailure("Convert tuples to list literals before passing them to a tool.")
        json.dumps(args, allow_nan=False)

    def _kwargs(self, keywords):
        args = {}
        for keyword in keywords:
            value = self._value(keyword.value)
            expanded = value if keyword.arg is None else {keyword.arg: value}
            if type(expanded) is not dict or not all(type(key) is str for key in expanded):
                raise ResolutionFailure("Expanded **arguments must be a dictionary with string keys.")
            duplicates = args.keys() & expanded.keys()
            if duplicates:
                raise ResolutionFailure(f"Duplicate arguments: {sorted(duplicates)}.")
            args.update(expanded)
        return args

    def _value(self, node):
        self._tick(node)
        result = self._evaluate(node)
        if not isinstance(result, slice):
            check_value(result, self.limits)
        return result

    def _evaluate(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            self._name(node.id)
            if node.id not in self.working:
                raise ResolutionFailure(f"Variable {node.id!r} is unbound. Use a real prior result or define it first.", "missing_name", True)
            self.dependencies.add(node.id)
            return self.working[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self._value(item) for item in node.elts]
            return tuple(values) if isinstance(node, ast.Tuple) else values
        if isinstance(node, ast.Dict):
            result = {}
            for key, value in zip(node.keys, node.values):
                if key is None:
                    raise ResolutionFailure("Dictionary unpacking is not supported; expand **fields in a tool call.")
                result[self._value(key)] = self._value(value)
            return result
        if isinstance(node, ast.Subscript):
            value, key = self._value(node.value), self._value(node.slice)
            if type(value) is dict and key not in value:
                raise ResolutionFailure(f"Missing key {preview(key, 80)}; available keys: {preview(list(value), 400)}.", "missing_key", True)
            return value[key]
        if isinstance(node, ast.Slice):
            return slice(*(self._value(part) if part is not None else None for part in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.UnaryOp):
            fn = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}.get(type(node.op))
            if fn is not None:
                return fn(self._value(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
            left, right = self._value(node.left), self._value(node.right)
            self._check_binary(node.op, left, right)
            return BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.Compare):
            left = self._value(node.left)
            for op, other in zip(node.ops, node.comparators):
                right = self._value(other)
                if not COMPARISONS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            for child in node.values:
                result = self._value(child)
                if isinstance(node.op, ast.And) and not result or isinstance(node.op, ast.Or) and result:
                    return result
            return result
        if isinstance(node, ast.IfExp):
            return self._value(node.body if self._value(node.test) else node.orelse)
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant):
                    parts.append(self._value(part))
                else:
                    value = self._value(part.value)
                    if part.conversion not in (-1, 115, 114, 97):
                        raise ResolutionFailure("Unsupported f-string conversion.")
                    if part.conversion != -1:
                        value = {115: str, 114: repr, 97: ascii}[part.conversion](value)
                    spec = self._value(part.format_spec) if part.format_spec else ""
                    if len(spec) > 64 or any(int(number) > 4096 for number in re.findall(r"\d+", spec)):
                        raise ResolutionFailure("F-string format width/precision limit exceeded.", "resource_limit")
                    parts.append(format(value, spec))
                if sum(map(len, parts)) > self.limits.max_string_chars:
                    raise ResolutionFailure("F-string output limit exceeded.", "resource_limit")
            return "".join(parts)
        if isinstance(node, ast.Call):
            return self._pure_call(node)
        raise ResolutionFailure(f"Unsupported Python expression: {type(node).__name__}.")

    def _check_binary(self, op, left, right):
        sequence_types = (str, list, tuple)
        if isinstance(op, ast.Mod) and type(left) is str:
            raise ResolutionFailure("Use bounded f-strings rather than %-string formatting.")
        if isinstance(op, ast.Mult):
            sequence, count = (left, right) if type(left) in sequence_types else (right, left)
            if type(sequence) in sequence_types and type(count) in (int, bool):
                maximum = self.limits.max_string_chars if type(sequence) is str else self.limits.max_container_items
                if len(sequence) * max(0, count) > maximum:
                    raise ResolutionFailure("Sequence repetition limit exceeded.", "resource_limit")
        if isinstance(op, ast.Add) and type(left) in sequence_types and type(right) is type(left):
            maximum = self.limits.max_string_chars if type(left) is str else self.limits.max_container_items
            if len(left) + len(right) > maximum:
                raise ResolutionFailure("Sequence concatenation limit exceeded.", "resource_limit")

    def _pure_call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            receiver = self._value(node.func.value)
            if type(receiver) is not dict or node.keywords or not 1 <= len(node.args) <= 2:
                raise ResolutionFailure("Only dict.get(key[, default]) is supported.")
            return receiver.get(*(self._value(arg) for arg in node.args))
        if not isinstance(node.func, ast.Name):
            raise ResolutionFailure("Arbitrary methods and attribute access are not supported.")
        name = node.func.id
        if name in self.tool_names:
            raise ResolutionFailure("Nested tool calls are not supported. Use separate assignments.")
        if name not in RESERVED:
            raise ResolutionFailure(f"Unknown tool or unsupported helper: {name!r}.")
        args = [self._value(arg) for arg in node.args]
        kwargs = self._kwargs(node.keywords)
        if name == "print":
            if set(kwargs) - {"sep", "end"}:
                raise ResolutionFailure("print supports only sep and end, not files or other options.")
            sep, end = kwargs.get("sep", " "), kwargs.get("end", "\n")
            sep, end = " " if sep is None else sep, "\n" if end is None else end
            if type(sep) is not str or type(end) is not str:
                raise TypeError("print sep and end must be strings or None")
            parts = [str(arg) for arg in args]
            size = sum(map(len, parts)) + len(sep) * max(0, len(parts) - 1) + len(end)
            if len(self.stdout) + size > self.limits.max_stdout_chars:
                raise ResolutionFailure("Captured stdout limit exceeded. Print a smaller slice.", "resource_limit")
            text = sep.join(parts) + end
            self.stdout += text
            return None
        if name == "round" and len(args) > 1 and type(args[1]) is int and abs(args[1]) > 4096:
            raise ResolutionFailure("round precision limit exceeded.", "resource_limit")
        if name == "round" and type(kwargs.get("ndigits")) is int and abs(kwargs["ndigits"]) > 4096:
            raise ResolutionFailure("round precision limit exceeded.", "resource_limit")
        return HELPERS[name](*args, **kwargs)

    def bind_result(self, action, output, success, status=""):
        return self.state.bind_result(action, output, success, status)

    def clear(self):
        self.state.clear()
        self.working = {}
        self.sources = {}
        self.executed = []
        self.dependencies = set()
        self.stdout = ""

    @staticmethod
    def event_record(event, text, source_segment_index):
        record = {"kind": event.kind, "format_valid": event.format_valid,
                  "source_segment_index": source_segment_index,
                  "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                  "planner_text": text}
        if isinstance(event, ResolverError):
            record.update(error_kind=event.error_kind, message=event.message,
                          line=event.line, column=event.column)
        elif isinstance(event, ToolCallReady):
            record.update(call_id=event.call_id, tool_name=event.tool_name, args=event.args,
                          bind_variable=event.bind_variable, executed_code=event.executed_code,
                          stdout=event.stdout)
        elif isinstance(event, LocalResult):
            record.update(changed_names=list(event.changed_names), previews=dict(event.previews),
                          stdout=event.stdout)
        elif isinstance(event, FinalAnswer):
            record.update(text=event.text)
        return record
