"""Reuse legacy response boundaries without legacy whole-tree execution checks."""

import ast
import os

from codeact_parser import CodeActError, parse_response, response_boundary, truncate_response

from .types import ResolutionFailure


def prompt_path(runtime="legacy"):
    if runtime not in {"legacy", "resolver_v2"}:
        raise ValueError(f"Unsupported CODEACT_RUNTIME: {runtime!r}")
    filename = "codeact_resolver_v2_prompt.txt" if runtime == "resolver_v2" else "codeact_tool_calling_prompt.txt"
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", filename)


def parse_program(text, max_depth=64):
    try:
        source, tree = parse_response(text)
    except CodeActError as exc:
        raise ResolutionFailure(str(exc), "protocol_or_syntax") from exc
    if tree is not None:
        pending = [(tree, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > max_depth:
                raise ResolutionFailure("AST nesting limit exceeded.", "resource_limit")
            pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return source, tree
