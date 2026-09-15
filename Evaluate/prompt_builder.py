


"""
PromptBuilder - Builds system prompts matching the new trajectory format.

Trajectory format contract
--------------------------
Assistant turns contain:
  1. Free-form reasoning prose.
  2. (Optional) A single JSON *array* containing the tool call(s):
         [{"name": "toolName", "args": {"param": "value"}}]
  3. If the task is complete, the turn ends with:
         <TASK_FINISHED>

System turns contain the executor-injected observation:
  ["Function Call {'name': '...', 'args': {...}} Succeeded. Result: {...}"]
  ["Function Call {'name': '...', 'args': {...}} Failed during execution. Error: {...}"]

No XML action tags (<think>, <tool_call>, etc.) are used.
"""

import json
import os
from typing import Any, Dict, List, Union


class PromptBuilder:
    """
    Builds planner system prompts for the new trajectory format.

    Tool schema formats accepted
    ----------------------------
    - List[Dict]  with keys 'name', 'description', 'parameters'  (OpenAI-style)
    - Dict[str, Dict] mapping name → {description, args_schema}
    - List[str]   of bare tool names (minimal descriptions)
    """

    def __init__(
        self,
        tool_methods: Union[List[Dict[str, Any]], Dict[str, Any], List[str]],
    ):
        self.tool_methods = self._normalize_tools(tool_methods)

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def _normalize_tools(self, raw: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        if isinstance(raw, dict):
            for name, info in raw.items():
                entry: Dict[str, Any] = {"name": name}
                if isinstance(info, dict):
                    entry["description"] = info.get("description", f"Tool: {name}")
                    entry["args_schema"]  = info.get("args_schema", info.get("parameters", {}))
                else:
                    entry["description"] = str(info) if info else f"Tool: {name}"
                    entry["args_schema"]  = {}
                normalized.append(entry)

        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    if "name" not in item:
                        continue
                    # OpenAI-style: parameters.properties → args_schema
                    params = item.get("parameters", {})
                    if isinstance(params, dict):
                        args_schema = params.get("properties", params)
                        required    = params.get("required", [])
                        # Annotate each property with required flag
                        for pname, pinfo in args_schema.items():
                            if isinstance(pinfo, dict):
                                pinfo["required"] = pname in required
                    else:
                        args_schema = {}
                    normalized.append({
                        "name":        item["name"],
                        "description": item.get("description", f"Tool: {item['name']}"),
                        "args_schema": args_schema,
                    })
                elif isinstance(item, str):
                    normalized.append({
                        "name":        item,
                        "description": f"Tool: {item}",
                        "args_schema": {},
                    })
                else:
                    normalized.append({
                        "name":        str(item),
                        "description": "No description",
                        "args_schema": {},
                    })
        else:
            normalized.append({
                "name":        str(raw),
                "description": "No description",
                "args_schema": {},
            })

        return normalized

    # ------------------------------------------------------------------
    # Main prompt builder
    # ------------------------------------------------------------------

    def build_react_prompt(self) -> str:
        """
        Build the system prompt that governs the new trajectory format.

        Key conventions enforced
        ------------------------
        • Reasoning is plain prose (no XML tags).
        • Tool calls are a JSON array: [{"name": "...", "args": {...}}]
        • Observations arrive as system messages; the model never writes them.
        • Task completion is signalled by appending <TASK_FINISHED> to the
          final assistant turn.
        • At most ONE tool call per turn.
        """
        lines = [
            "You are an Enterprise Agent with access to APIs exposed as tools.",
            "",
            "═" * 60,
            "AVAILABLE TOOLS",
            "═" * 60,
            "",
        ]

        for i, tool in enumerate(self.tool_methods, 1):
            name   = tool.get("name", "unknown")
            desc   = tool.get("description", "")
            schema = tool.get("args_schema", {})

            lines.append(f"{i}. {name}")
            lines.append(f"   {desc}")

            if schema:
                lines.append("   Parameters:")
                for pname, pinfo in schema.items():
                    if isinstance(pinfo, dict):
                        ptype   = pinfo.get("type", "any")
                        pdesc   = pinfo.get("description", "")
                        req     = pinfo.get("required", False)
                        req_str = " [required]" if req else " [optional]"
                        lines.append(f"     • {pname} ({ptype}{req_str}): {pdesc}")
                    else:
                        lines.append(f"     • {pname}: {pinfo}")
            lines.append("")

        lines += [
            "═" * 60,
            "RESPONSE FORMAT — follow exactly, in order, every turn",
            "═" * 60,
            "",
            "1.  Write your reasoning as free-form prose.",
            "",
            "2.  If you need to call a tool, emit a JSON array on its own",
            "    line (at most ONE call per turn):",
            "",
            '    [{"name": "toolName", "args": {"param1": value1, "param2": value2}}]',
            "",
            "    Argument rules:",
            "    • \"args\" must be a JSON object — never a string or list.",
            "    • Every key must match the tool's declared parameter name exactly.",
            "    • String values use double quotes; numbers/booleans are unquoted.",
            "    • Omit optional parameters you don't need; never pass null.",
            "",
            "3.  The executor will inject the result as a system message:",
            "    [\"Function Call {'name': '...', 'args': {...}} Succeeded. Result: {...}\"]",
            "    or",
            "    [\"Function Call {'name': '...', 'args': {...}} Failed during execution."
            " Error: {...}\"]",
            "",
            "4.  After receiving the observation, write your next reasoning",
            "    step and optionally call another tool (repeat steps 1-3).",
            "",
            "5.  When the task is fully complete, write your final prose",
            "    explanation and append <TASK_FINISHED> on the same turn.",
            "    Do NOT call any tool in the same turn as <TASK_FINISHED>.",
            "",
            "═" * 60,
            "RULES",
            "═" * 60,
            "",
            "• Never emit XML tags such as <think>, <tool_call>, <observe>, etc.",
            "• Never emit more than one JSON tool-call array per turn.",
            "• Never fabricate tool results — wait for the executor observation.",
            "• If a tool fails, reason about the error and try an alternative",
            "  (e.g., press the brake before starting the engine).",
            "• If no tool is needed, answer directly and append <TASK_FINISHED>.",
            "• Your answer must be grounded in the actual tool observations.",
            "",
            "═" * 60,
            "EXAMPLES",
            "═" * 60,
            "",
            "─── Example 1: single tool call ───",
            "",
            "User: Lock all car doors.",
            "",
            "Assistant:",
            "I will lock all car doors now.",
            "",
            '[{"name": "lockDoors", "args": {"unlock": false,'
            ' "door": ["driver", "passenger", "rear_left", "rear_right"]}}]',
            "",
            "System (executor):",
            '[\"Function Call {\'name\': \'lockDoors\', \'args\': {\'unlock\': False,'
            " 'door': ('driver', 'passenger', 'rear_left', 'rear_right')}}"
            " Succeeded. Result: {'lockStatus': 'locked', 'remainingUnlockedDoors': 0}\"]",
            "",
            "Assistant:",
            "All car doors are now locked. <TASK_FINISHED>",
            "",
            "─── Example 2: multi-turn with error recovery ───",
            "",
            "User: Start the engine in START mode.",
            "",
            "Assistant:",
            "I will start the engine in START mode.",
            "",
            '[{"name": "startEngine", "args": {"ignitionMode": "START"}}]',
            "",
            "System (executor):",
            '[\"Function Call {\'name\': \'startEngine\', \'args\': {\'ignitionMode\': \'START\'}}'
            " Failed during execution. Error: {'error': 'Brake pedal needs to be pressed"
            " when starting the engine.'}\"]",
            "",
            "Assistant:",
            "The engine requires the brake pedal to be pressed first. I will press it now.",
            "",
            '[{"name": "pressBrakePedal", "args": {"pedalPosition": 1.0}}]',
            "",
            "System (executor):",
            '[\"Function Call {\'name\': \'pressBrakePedal\', \'args\': {\'pedalPosition\': 1.0}}'
            " Succeeded. Result: {'brakePedalStatus': 'pressed', 'brakePedalForce': 1000.0}\"]",
            "",
            "Assistant:",
            "Brake pedal is pressed. Retrying engine start.",
            "",
            '[{"name": "startEngine", "args": {"ignitionMode": "START"}}]',
            "",
            "System (executor):",
            '[\"Function Call {\'name\': \'startEngine\', \'args\': {\'ignitionMode\': \'START\'}}'
            " Succeeded. Result: {'engineState': 'running', 'fuelLevel': 15.5,"
            " 'batteryVoltage': 12.8}\"]",
            "",
            "Assistant:",
            "The engine is now running. You are primed to set off! <TASK_FINISHED>",
            "",
        ]

        return "\n".join(lines)

    def build_prompt(
        self,
        prompt_mode: str = "default",
        prompt_template_path: str | None = None,
        codeact_runtime: str = "legacy",
    ) -> str:
        """Build either the default ReAct prompt or an external ARTIST prompt."""
        mode = (prompt_mode or "default").strip().lower()
        if mode in {"default", "react_json", "custom_react_json"}:
            return self.build_react_prompt()
        if mode == "artist":
            return self.build_artist_prompt(prompt_template_path)
        if mode == "codeact":
            from codeact_runtime import prompt_path
            path = prompt_template_path or prompt_path(codeact_runtime)
            return self.build_artist_prompt(path)
        raise ValueError(f"Unsupported prompt_mode: {prompt_mode!r}")

    def build_artist_prompt(self, prompt_template_path: str | None) -> str:
        """Load the exact ARTIST prompt template and inject the tool catalog."""
        if not prompt_template_path:
            raise ValueError("ARTIST prompt mode requires a prompt_template_path")
        if not os.path.exists(prompt_template_path):
            raise FileNotFoundError(
                f"ARTIST prompt template not found: {prompt_template_path}"
            )
        with open(prompt_template_path, "r") as handle:
            template = handle.read()
        full_tools = []
        for tool in self.tool_methods:
            full_tools.append(
                {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "args_schema": tool.get("args_schema", {}),
                }
            )
        tool_block = json.dumps(full_tools, indent=2, ensure_ascii=True)
        return template.replace("{tools}", tool_block)

    # ------------------------------------------------------------------
    # Compact / utility variants
    # ------------------------------------------------------------------

    def build_compact_prompt(self) -> str:
        """Minimal prompt for tight-context scenarios."""
        names = ", ".join(t.get("name", "?") for t in self.tool_methods)
        return (
            f"Tools: {names}\n\n"
            "Format:\n"
            "  <reasoning prose>\n"
            '  [{"name": "toolName", "args": {"arg": "value"}}]   ← omit if no tool needed\n'
            "  <reasoning prose after observation>\n"
            "  … repeat …\n"
            "  <final prose> <TASK_FINISHED>"
        )

    def build_tool_list_only(self) -> str:
        """Return just the formatted tool list."""
        lines: List[str] = []
        for t in self.tool_methods:
            name   = t.get("name", "?")
            desc   = t.get("description", "")
            schema = t.get("args_schema", {})
            entry  = f"• {name}: {desc}"
            if schema:
                args_list = []
                for pname, pinfo in schema.items():
                    req = (pinfo.get("required", False)
                           if isinstance(pinfo, dict) else False)
                    args_list.append(f"{pname}{'*' if req else ''}")
                entry += f"  [{', '.join(args_list)}]"
            lines.append(entry)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_tool_count(self) -> int:
        return len(self.tool_methods)

    def get_tool_names(self) -> List[str]:
        return [t.get("name", "?") for t in self.tool_methods]
