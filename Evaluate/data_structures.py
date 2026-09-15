

"""
Core data structures for Agentic GRPO training.

Trajectory format (mirrors example):
  - Assistant turns: plain prose reasoning + JSON array tool call
        [{"name": "toolName", "args": {...}}]
  - System turns:   observation injected by executor
        ["Function Call {'name': ..., 'args': ...} Succeeded. Result: {...}"]
        ["Function Call {'name': ..., 'args': ...} Failed during execution. Error: {...}"]
  - Final turn:     assistant prose ending with <TASK_FINISHED>

is_trainable flag:
  True  → model-generated tokens (reasoning + tool calls + final answer)
  False → system prompts, user query, observations (environment outputs)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import json
import re


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ToolExecutionStatus(Enum):
    SUCCESS       = "success"
    INVALID_ARGS  = "invalid_args"
    TIMEOUT       = "timeout"
    RUNTIME_ERROR = "runtime_error"
    TOOL_NOT_FOUND = "tool_not_found"


# ---------------------------------------------------------------------------
# Tool execution primitives
# ---------------------------------------------------------------------------

@dataclass
class ExecutedToolCall:
    tool_name:        str
    args:             Dict[str, Any]
    status:           str          # stringified ToolExecutionStatus
    output:           str
    error_message:    Optional[str] = None
    execution_time_ms: float = 0.0
    source_segment_index: Optional[int] = None
    planner_turn_index: Optional[int] = None
    call_id: Optional[str] = None
    executed_code: Optional[str] = None


@dataclass
class ToolExecutionResult:
    """
    Result of a single tool execution.

    Attribution:
      - INVALID_ARGS / TOOL_NOT_FOUND → model's fault → penalise
      - TIMEOUT / RUNTIME_ERROR       → environment issue → do not penalise
    """
    status:           ToolExecutionStatus
    output:           str
    execution_time_ms: float
    error_message:    Optional[str] = None

    def should_penalize_model(self) -> bool:
        return self.status in (
            ToolExecutionStatus.INVALID_ARGS,
            ToolExecutionStatus.TOOL_NOT_FOUND,
        )


# ---------------------------------------------------------------------------
# Trajectory segments
# ---------------------------------------------------------------------------

@dataclass
class TrajectorySegment:
    """
    One segment of a trajectory.

    segment_type values
    -------------------
    'system'              – planner system prompt (not trainable)
    'user'                – user query (not trainable)
    'thought_and_action'  – assistant turn: prose + optional tool-call array (TRAINABLE)
    'observation'         – system-injected tool result (not trainable)

    Invariant: observation / user / system segments must never be trainable.
    """
    text:         str
    is_trainable: bool
    segment_type: str
    token_count:  int = 0   # filled in by tokenizer during collation

    _NON_TRAINABLE_TYPES = frozenset({"observation", "user", "system"})

    def __post_init__(self):
        if self.segment_type in self._NON_TRAINABLE_TYPES and self.is_trainable:
            raise ValueError(
                f"segment_type '{self.segment_type}' must have is_trainable=False. "
                "Training on environment outputs causes hallucination."
            )


@dataclass
class PlannerTurn:
    """Exact prompt/response pair produced by the trainable AgentFlow planner."""

    prompt: str
    response: str
    turn_index: int


# ---------------------------------------------------------------------------
# JSON extraction helper (brace-matching)
# ---------------------------------------------------------------------------

def _extract_json_with_brace_matching(text: str, start_pos: int) -> Tuple[str, int]:
    """
    Extract a complete JSON object/array using brace/bracket counting.
    Returns (json_string, end_pos) or ("", -1) on failure.
    """
    if start_pos >= len(text) or text[start_pos] not in ('{', '['):
        return "", -1

    open_ch  = text[start_pos]
    close_ch = '}' if open_ch == '{' else ']'
    depth    = 0
    in_str   = False
    escape   = False

    for i in range(start_pos, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start_pos: i + 1], i + 1

    return "", -1


# ---------------------------------------------------------------------------
# Completed trajectory
# ---------------------------------------------------------------------------

@dataclass
class CompletedTrajectory:
    """
    A complete multi-turn trajectory ready for reward assignment and training.

    Termination reasons
    -------------------
    'success'                – <TASK_FINISHED> found in last assistant turn
    'no_tool_call'           – assistant produced neither a tool call nor TASK_FINISHED
    'invalid_tool_call_json' – tool-call array was malformed JSON
    'invalid_action'         – tool name missing or null
    'invalid_args'           – args was not a dict
    'invalid_code_action'    - malformed or unsupported Python tool action
    'max_turns_reached'      – loop hit max_turns without finishing
    'generation_error'       – LLM threw an exception
    'exception'              – outer catch-all in batch runner
    'unknown'                – default / uninitialised
    """

    query_id:          str
    segments:          List[TrajectorySegment]
    reward:            Optional[float] = None
    advantage:         Optional[float] = None

    # Metadata
    num_tool_calls:    int   = 0
    total_tokens:      int   = 0
    generation_time_ms: float = 0.0
    termination_reason: str  = "unknown"

    # Lazy cache
    _full_text:        Optional[str] = field(default=None, repr=False)
    _trainable_text:   Optional[str] = field(default=None, repr=False)
    executed_tool_calls: List[ExecutedToolCall] = field(default_factory=list)
    planner_turns: List[PlannerTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def full_text(self) -> str:
        if self._full_text is None:
            self._full_text = "".join(s.text for s in self.segments)
        return self._full_text

    @property
    def trainable_text(self) -> str:
        if self._trainable_text is None:
            self._trainable_text = "".join(
                s.text for s in self.segments if s.is_trainable
            )
        return self._trainable_text

    # ------------------------------------------------------------------
    # Tool-call extraction from 'thought_and_action' segments
    # ------------------------------------------------------------------

    def _extract_tool_calls_from_segment(
        self, segment: TrajectorySegment
    ) -> List[Tuple[str, str]]:
        """
        Extract (tool_name, args_json) pairs from the JSON-array tool call
        embedded in an assistant segment.

        Expected pattern inside the text:
            [{"name": "toolName", "args": {...}}]
        """
        text = segment.text
        results: List[Tuple[str, str]] = []

        artist_match = re.search(r"<tool>\s*(.*?)\s*</tool>", text, re.DOTALL | re.IGNORECASE)
        if artist_match:
            try:
                payload = json.loads(artist_match.group(1).strip())
                if isinstance(payload, list) and payload:
                    payload = payload[0]
                if isinstance(payload, dict):
                    name = str(
                        payload.get("name")
                        or payload.get("tool_name")
                        or payload.get("tool")
                        or ""
                    ).strip()
                    args = payload.get("args", payload.get("arguments", {}))
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            pass
                    if name and isinstance(args, dict):
                        return [(name, json.dumps(args))]
            except (json.JSONDecodeError, TypeError):
                pass

        # Find the opening bracket of a top-level JSON array
        for i, ch in enumerate(text):
            if ch == '[':
                arr_str, _ = _extract_json_with_brace_matching(text, i)
                if not arr_str:
                    continue
                try:
                    calls = json.loads(arr_str)
                    if not isinstance(calls, list):
                        continue
                    for call in calls:
                        if isinstance(call, dict):
                            name = str(call.get("name", "")).strip()
                            args = call.get("args", {})
                            if name:
                                results.append((name, json.dumps(args)))
                    if results:
                        break   # stop after first valid array
                except (json.JSONDecodeError, TypeError):
                    continue

        return results

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    _VALID_SEGMENT_TYPES = frozenset({
        "system", "user", "thought_and_action", "observation",
        # legacy names kept for backward compat
        "thought", "action", "final_answer", "malformed_output",
    })

    _VALID_TERMINATION_REASONS = frozenset({
        "success", "no_tool_call", "invalid_tool_call_json",
        "invalid_action", "invalid_args", "invalid_code_action", "max_turns_reached",
        "generation_error", "exception", "unknown",
        "codeact_correction_budget", "codeact_local_budget", "codeact_binding_error",
        # legacy
        "max_turns", "context_overflow", "malformed_output",
    })

    def validate_structure(self) -> Tuple[bool, str]:
        """Validate trajectory structure (before reward assignment)."""
        if not self.query_id:
            return False, "Missing query_id"
        if not self.segments:
            return False, "Empty trajectory"
        if not any(s.is_trainable for s in self.segments):
            return False, "No trainable segments"
        for seg in self.segments:
            if seg.segment_type not in self._VALID_SEGMENT_TYPES:
                return False, f"Invalid segment_type: '{seg.segment_type}'"
        if (self.termination_reason not in self._VALID_TERMINATION_REASONS
                and not self.termination_reason.startswith("tool_")):
            return False, f"Invalid termination_reason: '{self.termination_reason}'"

        # Loop detection: 3+ consecutive identical tool calls
        if self.num_tool_calls >= 3:
            if self.executed_tool_calls:
                call_signatures = [
                    f"{call.tool_name}::{json.dumps(call.args, sort_keys=True, default=str)}"
                    for call in self.executed_tool_calls
                ]
            else:
                action_segs = [
                    s for s in self.segments if s.segment_type == "thought_and_action"
                ]
                call_signatures = []
                for seg in action_segs:
                    for name, args in self._extract_tool_calls_from_segment(seg):
                        call_signatures.append(f"{name}::{args}")

            for i in range(len(call_signatures) - 2):
                if call_signatures[i] == call_signatures[i+1] == call_signatures[i+2]:
                    return False, (
                        f"Infinite loop: '{call_signatures[i]}' repeated 3× consecutively"
                    )

        return True, ""

    def validate_for_training(self) -> Tuple[bool, str]:
        """Validate structure AND reward assignment."""
        ok, msg = self.validate_structure()
        if not ok:
            return False, msg
        if self.reward is None:
            return False, "Reward not assigned"
        return True, ""

    def validate(self) -> Tuple[bool, str]:
        """Alias for validate_for_training (backward compat)."""
        return self.validate_for_training()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def has_successful_completion(self) -> bool:
        return self.termination_reason == "success"

    def has_final_answer(self) -> bool:
        """True if any assistant segment contains a supported completion marker."""
        return any(
            "<TASK_FINISHED>" in s.text
            or bool(re.search(r"<answer>\s*.*?\s*</answer>", s.text, re.DOTALL | re.IGNORECASE))
            for s in self.segments
            if s.segment_type == "thought_and_action"
        )

    def get_final_answer(self) -> Optional[str]:
        """
        Return the text of the last assistant segment that contains
        a supported completion marker, stripped of the marker itself.
        """
        for seg in reversed(self.segments):
            if seg.segment_type != "thought_and_action":
                continue
            if "<TASK_FINISHED>" in seg.text:
                return seg.text.replace("<TASK_FINISHED>", "").strip()
            answer_match = re.search(r"<answer>\s*(.*?)\s*</answer>", seg.text, re.DOTALL | re.IGNORECASE)
            if answer_match:
                return answer_match.group(1).strip()
        return None

    def get_action_sequence(self) -> List[str]:
        """Ordered list of tool names called in this trajectory."""
        names: List[str] = []
        for seg in self.segments:
            if seg.segment_type == "thought_and_action":
                for name, _ in self._extract_tool_calls_from_segment(seg):
                    names.append(name)
        return names

    def count_segment_tokens(self, tokenizer: Any) -> None:
        """Populate token_count for all segments."""
        for seg in self.segments:
            if seg.token_count == 0:
                seg.token_count = len(
                    tokenizer.encode(seg.text, add_special_tokens=False)
                )

    def get_stats(self) -> Dict[str, Any]:
        trainable_tok = sum(s.token_count for s in self.segments if s.is_trainable)
        total_tok     = sum(s.token_count for s in self.segments)
        seg_counts: Dict[str, int] = {}
        for s in self.segments:
            seg_counts[s.segment_type] = seg_counts.get(s.segment_type, 0) + 1
        return {
            "query_id":         self.query_id,
            "num_segments":     len(self.segments),
            "segment_counts":   seg_counts,
            "num_tool_calls":   self.num_tool_calls,
            "total_tokens":     total_tok,
            "trainable_tokens": trainable_tok,
            "trainable_ratio":  trainable_tok / max(total_tok, 1),
            "generation_time_ms": self.generation_time_ms,
            "termination_reason": self.termination_reason,
            "reward":           self.reward,
            "advantage":        self.advantage,
        }

    def summary(self) -> str:
        action_seq = self.get_action_sequence()
        final      = self.get_final_answer()
        lines = [
            f"Trajectory {self.query_id}:",
            f"  Status      : {self.termination_reason}",
            f"  Tools used  : {' -> '.join(action_seq) if action_seq else 'None'}",
            f"  Final answer: {(final[:100] + '...') if final else 'None'}",
            f"  Reward      : {self.reward:.3f if self.reward is not None else 'Not assigned'}",
            f"  Tokens      : {self.total_tokens} "
            f"({sum(1 for s in self.segments if s.is_trainable)} trainable segments)",
        ]
        return "\n".join(lines)
