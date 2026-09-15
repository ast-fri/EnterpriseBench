"""Deterministic resolver contracts; no model or environment dependencies."""

from dataclasses import dataclass, field
import os
import math
from typing import Any

RUNTIME_VERSION = "resolver_v2.0.0"


@dataclass(frozen=True)
class RuntimeLimits:
    max_depth: int = 64
    max_operations: int = 4096
    max_container_items: int = 10000
    max_string_chars: int = 262144
    max_integer_bits: int = 4096
    max_state_bytes: int = 4 * 1024 * 1024
    max_observation_chars: int = 1024 * 1024
    max_stdout_chars: int = 4096
    # Unused by the resolver (pending removal): wall-clock budgets are not
    # deterministic (identical code can pass or fail depending on system
    # load), which conflicts with the resolver's determinism guarantee.
    # max_operations/max_depth/max_container_items already bound work.
    # Kept only so RuntimeLimits.from_env()/serialized configs stay valid.
    max_seconds: float = 1.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if value <= 0 or not math.isfinite(value):
                raise ValueError(f"{name} must be positive")

    @classmethod
    def from_env(cls):
        defaults = cls()
        return cls(**{name: type(value)(os.getenv(f"CODEACT_{name.upper()}", value))
                      for name, value in vars(defaults).items()})


@dataclass(frozen=True)
class ToolCallReady:
    tool_name: str
    args: dict[str, Any]
    bind_variable: str | None
    source_segment_index: int
    planner_turn_index: int
    call_id: str
    executed_code: str
    stdout: str = ""
    kind: str = field(default="tool", init=False)
    format_valid: bool = field(default=True, init=False)

    def as_action(self):
        return {"tool_name": self.tool_name, "tool_args": self.args,
                "bind_variable": self.bind_variable, "finished": False}


@dataclass(frozen=True)
class LocalResult:
    changed_names: tuple[str, ...]
    previews: dict[str, str]
    stdout: str
    kind: str = field(default="local", init=False)
    format_valid: bool = field(default=True, init=False)


@dataclass(frozen=True)
class ResolverError:
    error_kind: str
    message: str
    line: int | None = None
    column: int | None = None
    format_valid: bool = False
    kind: str = field(default="error", init=False)


@dataclass(frozen=True)
class FinalAnswer:
    text: str
    kind: str = field(default="final", init=False)
    format_valid: bool = field(default=True, init=False)


class ResolutionFailure(ValueError):
    def __init__(self, message, kind="unsupported", format_valid=False):
        super().__init__(message)
        self.kind = kind
        self.format_valid = format_valid
