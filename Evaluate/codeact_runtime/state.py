"""Bounded working values and immutable records of actual tool observations."""

import ast
import json
import math
from copy import deepcopy
from dataclasses import dataclass

from .types import ResolutionFailure, RuntimeLimits


def check_value(value, limits: RuntimeLimits, *, max_bytes=None):
    remaining = limits.max_state_bytes if max_bytes is None else max_bytes
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > limits.max_depth:
            raise ResolutionFailure("Value nesting limit exceeded.", "resource_limit")
        kind = type(item)
        remaining -= 32
        if kind is str:
            if len(item) > limits.max_string_chars:
                raise ResolutionFailure("String size limit exceeded.", "resource_limit")
            remaining -= len(item.encode("utf-8"))
        elif kind is int:
            if item.bit_length() > limits.max_integer_bits:
                raise ResolutionFailure("Integer size limit exceeded.", "resource_limit")
            remaining -= item.bit_length() // 8
        elif kind is float:
            if not math.isfinite(item):
                raise ResolutionFailure("Non-finite numbers are not supported.", "value_error", True)
        elif kind in (dict, list, tuple):
            if len(item) > limits.max_container_items:
                raise ResolutionFailure("Container size limit exceeded.", "resource_limit")
            values = list(item.keys()) + list(item.values()) if kind is dict else item
            pending.extend((child, depth + 1) for child in values)
        elif kind not in (bool, type(None)):
            raise ResolutionFailure(f"Unsupported value type: {kind.__name__}.")
        if remaining < 0:
            raise ResolutionFailure("Binding memory limit exceeded.", "resource_limit")


def decode_observation(output, limits):
    if type(output) is str:
        if len(output) > limits.max_observation_chars:
            raise ResolutionFailure("Tool observation exceeds runtime capacity.", "resource_limit")
        try:
            value = json.loads(output)
        except (ValueError, TypeError):
            # Bound the literal tree before decoding legacy str(dict) outputs.
            try:
                tree = ast.parse(output, mode="eval")
                if sum(1 for _ in ast.walk(tree)) > limits.max_container_items:
                    raise ResolutionFailure("Observation literal is too complex.", "resource_limit")
                value = ast.literal_eval(tree)
            except (SyntaxError, ValueError, TypeError):
                value = output
    else:
        value = output
    check_value(value, limits)
    return deepcopy(value)


def preview(value, max_chars=400):
    # Values are already bounded and contain no application objects/custom repr.
    text = repr(value)
    return text if len(text) <= max_chars else text[:max_chars] + " ... [preview truncated]"


@dataclass(frozen=True)
class ObservationRecord:
    call_id: str
    tool_name: str
    args_json: str
    status: str
    raw_output: str


class SessionState:
    def __init__(self, limits):
        self.limits = limits
        self.variables = {}
        self.provenance = {}
        self.observations = []
        self.observation_chars = 0

    def commit(self, variables, provenance):
        check_value(variables, self.limits)
        self.variables = deepcopy(variables)
        self.provenance = deepcopy(provenance)

    def bind_result(self, action, output, success, status=""):
        target = action.bind_variable
        if target:
            self.variables.pop(target, None)
            self.provenance.pop(target, None)
        if type(output) is not str:
            check_value(output, self.limits)
        raw = output if type(output) is str else json.dumps(output, ensure_ascii=True, allow_nan=False)
        if len(raw) > self.limits.max_observation_chars:
            raise ResolutionFailure("Tool observation exceeds runtime capacity.", "resource_limit")
        if self.observation_chars + len(raw) > self.limits.max_state_bytes:
            raise ResolutionFailure("Observation history limit exceeded.", "resource_limit")
        self.observations.append(ObservationRecord(
            action.call_id, action.tool_name, json.dumps(action.args, allow_nan=False),
            status or ("success" if success else "error"), raw,
        ))
        self.observation_chars += len(raw)
        value = decode_observation(output, self.limits)
        if success and target:
            candidate = dict(self.variables, **{target: value})
            check_value(candidate, self.limits)
            self.variables = candidate
            self.provenance[target] = {"origin": "tool_result", "call_id": action.call_id}
        return value

    def clear(self):
        self.variables.clear()
        self.provenance.clear()
        self.observations.clear()
        self.observation_chars = 0
