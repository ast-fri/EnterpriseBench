"""
Batch Task Evaluator for EnterpriseBench
=========================================
Runs the ReAct agent (graph.py) against every task in
Task_Generation/tasks.json, and scores each run by comparing the tool
calls the agent actually issued against the ground-truth tool calls
recorded in that task's `subtasks`.
"""

import asyncio
import json
import os
import sys
import importlib.util
import inspect
from langchain_core.messages import HumanMessage, SystemMessage

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from graph import build_react_agent_graph, AgentState, get_base_prompt, extract_tool_calls_from_trajectory


DEFAULT_MAX_STEPS = 15
EVALUATE_DIR = Path(__file__).resolve().parent
ENTERPRISE_BENCH_ROOT = EVALUATE_DIR.parent
TASKS_FILE = ENTERPRISE_BENCH_ROOT / "Task_Generation" / "tasks.json"
TOOLS_MODULE_PATH = ENTERPRISE_BENCH_ROOT / "Task_Generation" / "utils" / "tools.py"
TOOLS_SCHEMA_FILE = ENTERPRISE_BENCH_ROOT / "Task_Generation" / "utils" / "tools.json"


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    PURPLE = '\033[95m'
    END = '\033[0m'


class ToolWrapper(BaseTool):
    """Wrapper class for EnterpriseBench tools - LangChain compatible"""

    name: str
    description: str
    invoke_fn: Callable = Field(exclude=True)  # Exclude from pydantic serialization
    args_schema: Optional[Type[BaseModel]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        name: str,
        description: str,
        invoke_fn: Callable,
        args_schema: Dict[str, Any],
        **kwargs
    ):
        if isinstance(args_schema, dict) and args_schema:
            pydantic_schema = self._create_pydantic_schema(name, args_schema)
        else:
            pydantic_schema = None

        super().__init__(
            name=name,
            description=description,
            invoke_fn=invoke_fn,
            args_schema=pydantic_schema,
            **kwargs
        )
        self.metadata = {}

    def _create_pydantic_schema(self, tool_name: str, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Convert dict schema ({"properties": ..., "required": [...]}) to Pydantic BaseModel.

        The underlying Tools methods pull every argument via `arguments.get(key, default)`,
        so nothing actually needs to be present at call time - marking a field pydantic-required
        would make the LLM's partial tool calls raise ValidationError and crash the run. Instead,
        every field stays optional and "required" is only surfaced as a hint in its description.
        """
        from pydantic import create_model

        properties = schema_dict.get("properties", {})
        required_fields = schema_dict.get("required", [])

        fields = {}
        for field_name, field_info in properties.items():
            field_type = self._get_python_type(field_info.get("type", "string"))
            field_description = field_info.get("description", "")
            if field_name in required_fields:
                field_description = f"[REQUIRED] {field_description}"
            default = field_info.get("default", None)
            fields[field_name] = (Optional[field_type], Field(default, description=field_description))

        if fields:
            return create_model(f"{tool_name}Schema", **fields)
        return None

    def _get_python_type(self, json_type: str) -> type:
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(json_type, str)

    def _run(self, **kwargs) -> str:
        try:
            return self.invoke_fn(**kwargs)
        except Exception as e:
            return f"Error executing {self.name}: {str(e)}"

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)

    def __call__(self, **kwargs):
        return self._run(**kwargs)


def _load_tools_class():
    """Load the EnterpriseBench Tools class directly from Task_Generation/utils/tools.py"""
    spec = importlib.util.spec_from_file_location("eb_tools_module", TOOLS_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Tools


def _load_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """Load tools.json (name/description/args_schema per field) and convert each entry's
    args_schema into a JSON-schema-like {"properties": ..., "required": [...]} dict."""
    with open(TOOLS_SCHEMA_FILE, "r") as f:
        raw_tools = json.load(f)

    schemas = {}
    for entry in raw_tools:
        name = entry.get("name")
        properties = {}
        required = []
        for field_name, field_info in entry.get("args_schema", {}).items():
            properties[field_name] = {
                "type": field_info.get("type", "string"),
                "description": field_info.get("description", "")
            }
            if field_info.get("required"):
                required.append(field_name)

        schemas[name] = {
            "description": entry.get("description", f"EnterpriseBench tool: {name}"),
            "args_schema": {"properties": properties, "required": required}
        }
    return schemas


def discover_data_files(tools_instance) -> List[str]:
    """Find every JSON data file a Tools method can write to, by reading each method's
    `json_path` default parameter value. Derived from tools.py itself (not hardcoded)
    so newly added tools/data files are picked up automatically."""
    paths = set()
    for _name, method in inspect.getmembers(tools_instance, predicate=inspect.ismethod):
        try:
            sig = inspect.signature(method)
        except (TypeError, ValueError):
            continue
        param = sig.parameters.get("json_path")
        if param is not None and isinstance(param.default, str) and param.default:
            paths.add(param.default)
    return sorted(paths)


def snapshot_data_files(paths: List[str]) -> Dict[str, Optional[str]]:
    """Read the current contents of every tracked data file into memory, so they can be
    restored after a task runs. `None` means the file didn't exist yet at snapshot time."""
    snapshot = {}
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                snapshot[path] = f.read()
        else:
            snapshot[path] = None
    return snapshot


def restore_data_files(snapshot: Dict[str, Optional[str]]) -> None:
    """Write every tracked data file back to its snapshotted content, undoing whatever
    the task that just ran mutated - so the next task starts from the same pristine
    state as the very first one, regardless of what earlier tasks wrote."""
    for path, content in snapshot.items():
        if content is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        with open(path, "w") as f:
            f.write(content)


class EnterpriseBenchConnector:
    """Connector for EnterpriseBench tools"""

    def __init__(self):
        self.tools_instance = None
        self.tools: List[ToolWrapper] = []
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        self.data_files: List[str] = []

    def connect(self) -> bool:
        """Instantiate the Tools class and load tool metadata"""
        try:
            Tools = _load_tools_class()
            self.tools_instance = Tools()
            self.tool_schemas = _load_tool_schemas()

            print(f"✅ Connected to EnterpriseBench")
            print(f"   • Tools class instantiated from {TOOLS_MODULE_PATH}")
            print(f"   • Loaded metadata for {len(self.tool_schemas)} tools from {TOOLS_SCHEMA_FILE}")
            return True

        except Exception as e:
            print(f"❌ Failed to connect to EnterpriseBench: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_tools(self) -> List[ToolWrapper]:
        """Wrap every tool documented in tools.json that exists as a method on Tools"""
        if not self.tools_instance:
            raise RuntimeError("Must call connect() first!")

        print(f"\n🔧 Loading EnterpriseBench tools...")
        for method_name, schema_info in self.tool_schemas.items():
            method = getattr(self.tools_instance, method_name, None)
            if method is None or not inspect.ismethod(method):
                print(f"   ⚠️  Skipped {method_name}: no matching Tools method")
                continue

            tool = self._wrap_tool_method(method_name, method, schema_info)
            if tool:
                self.tools.append(tool)
                print(f"   • Loaded: {method_name}")

        print(f"✅ Loaded {len(self.tools)} EnterpriseBench tools")

        self.data_files = discover_data_files(self.tools_instance)
        print(f"📂 Discovered {len(self.data_files)} mutable data files for state restore")

        return self.tools

    def _wrap_tool_method(self, method_name: str, method: Callable, schema_info: Dict[str, Any]) -> Optional[ToolWrapper]:
        try:
            description = schema_info["description"].strip()
            args_schema = schema_info["args_schema"]

            def executor(**kwargs) -> str:
                try:
                    # Drop unset optional args so the Tools methods' own
                    # `arguments.get(key, default)` fallbacks kick in, instead of
                    # receiving an explicit `None` for every field the LLM omitted.
                    call_args = {k: v for k, v in kwargs.items() if v is not None}
                    result = method(arguments=call_args)
                    if isinstance(result, list):
                        return "No results found" if len(result) == 0 else str(result)
                    return str(result)
                except Exception as e:
                    return f"Error: {str(e)}"

            tool = ToolWrapper(
                name=method_name,
                description=description,
                invoke_fn=executor,
                args_schema=args_schema
            )
            tool.metadata = {"env": "enterprise_bench", "original_name": method_name}
            return tool

        except Exception as e:
            print(f"⚠️  Failed to wrap tool {method_name}: {e}")
            return None


def _values_match(expected_val: Any, actual_val: Any) -> bool:
    if expected_val is None or actual_val is None:
        return expected_val == actual_val
    return str(expected_val).strip().casefold() == str(actual_val).strip().casefold()


def _call_matches(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    """An actual tool call matches an expected one if the tool name matches and every
    expected argument value is present (order-independent) among the actual arguments."""
    if expected["tool_name"] != actual["tool_name"]:
        return False
    expected_args = expected.get("tool_arguments") or {}
    actual_args = actual.get("tool_arguments") or {}
    for key, value in expected_args.items():
        if key in actual_args:
            if not _values_match(value, actual_args[key]):
                return False
        elif value not in actual_args.values():
            return False
    return True


def get_expected_tool_calls(task: dict) -> List[Dict[str, Any]]:
    """Flatten a task's subtasks into an ordered list of {tool_name, tool_arguments}."""
    expected = []
    for subtask in task.get("subtasks", []):
        for tool_call in subtask.get("tools", []):
            names = tool_call.get("tool_name", [])
            name = names[0] if isinstance(names, list) and names else names
            expected.append({
                "tool_name": name,
                "tool_arguments": tool_call.get("tool_arguments", {})
            })
    return expected


def evaluate_task(task: dict, trajectory: list, final_answer: str) -> Dict[str, Any]:
    """Score a completed run against the task's ground-truth tool calls."""
    expected_calls = get_expected_tool_calls(task)
    actual_calls = extract_tool_calls_from_trajectory(trajectory)

    remaining_actual = list(actual_calls)
    matched = 0
    for expected in expected_calls:
        for i, actual in enumerate(remaining_actual):
            if _call_matches(expected, actual):
                matched += 1
                remaining_actual.pop(i)
                break

    recall = matched / len(expected_calls) if expected_calls else 1.0
    precision = matched / len(actual_calls) if actual_calls else (1.0 if not expected_calls else 0.0)

    ground_truth = task.get("ground_truth", {}) or {}
    haystack = json.dumps(actual_calls, default=str) + " " + str(final_answer)
    ground_truth_hits = {
        key: str(value).casefold() in haystack.casefold()
        for key, value in ground_truth.items()
    }
    ground_truth_match = all(ground_truth_hits.values()) if ground_truth_hits else None

    return {
        "expected_tool_calls": expected_calls,
        "actual_tool_calls": actual_calls,
        "matched_tool_calls": matched,
        "tool_call_recall": recall,
        "tool_call_precision": precision,
        "ground_truth_hits": ground_truth_hits,
        "ground_truth_match": ground_truth_match,
        "task_success": recall == 1.0
    }


def _format_task_result(result: dict) -> Dict[str, Any]:
    """Convert a raw run_task_batch() result into the JSON-serializable shape we persist."""
    task_data = {
        "task_index": result["task_index"],
        "emp_id": result.get("emp_id", ""),
        "query": result["query"],
        "ground_truth": result.get("ground_truth", {}),
        "max_steps": result.get("max_steps", DEFAULT_MAX_STEPS),
        "status": result["status"],
        "final_answer": result.get("final_answer", ""),
        "trajectory_length": result.get("trajectory_length", 0),
        "evaluation": result.get("evaluation", {}),
        "error": result.get("error", None),
        "trajectory": []
    }

    for step in result.get("trajectory", []):
        if hasattr(step, 'dict'):
            task_data["trajectory"].append(step.dict())
        elif isinstance(step, dict):
            task_data["trajectory"].append(step)

    return task_data


def jsonl_path_for_batch(batch_id: str) -> str:
    os.makedirs("trajectories", exist_ok=True)
    return os.path.join("trajectories", f"eval_results_{batch_id}.jsonl")


def append_task_result(result: dict, batch_id: str) -> str:
    """Append a single task's formatted result as one line - O(1) per task, no rewrite
    of everything that ran before it. Safe to tail/inspect while the batch is still running."""
    filepath = jsonl_path_for_batch(batch_id)
    with open(filepath, "a") as f:
        f.write(json.dumps(_format_task_result(result)) + "\n")
        f.flush()
    return filepath


def write_summary_file(all_results: list, batch_id: str):
    """Write the final aggregate summary (+ all formatted tasks) to a single pretty JSON file.
    Called once at the end of the batch; per-task progress already lives in the .jsonl file."""
    filepath = os.path.join("trajectories", f"eval_results_{batch_id}.json")
    formatted_results = [_format_task_result(r) for r in all_results]

    successful = [r for r in all_results if r["status"] == "success"]
    task_successes = sum(1 for r in successful if r.get("evaluation", {}).get("task_success"))
    avg_recall = (
        sum(r.get("evaluation", {}).get("tool_call_recall", 0) for r in successful) / len(successful)
        if successful else 0.0
    )
    avg_precision = (
        sum(r.get("evaluation", {}).get("tool_call_precision", 0) for r in successful) / len(successful)
        if successful else 0.0
    )

    batch_data = {
        "batch_id": batch_id,
        "timestamp": datetime.now().isoformat(),
        "default_max_steps": DEFAULT_MAX_STEPS,
        "total_tasks": len(all_results),
        "successful_runs": len(successful),
        "failed_runs": len(all_results) - len(successful),
        "task_success_count": task_successes,
        "task_success_rate": task_successes / len(all_results) if all_results else 0.0,
        "avg_tool_call_recall": avg_recall,
        "avg_tool_call_precision": avg_precision,
        "tasks": formatted_results
    }

    with open(filepath, "w") as f:
        json.dump(batch_data, f, indent=2)

    print(f"\n{Colors.GREEN}📁 Final summary saved to: {filepath}{Colors.END}")
    return filepath


async def run_task_batch(task: dict, graph, config: dict, task_index: int, total_tasks: int, tools: list):
    """Execute a single EnterpriseBench task and score the resulting trajectory"""
    query = task.get("task", "")
    emp_id = task.get("emp_id", "")
    expected_calls = get_expected_tool_calls(task)
    max_steps = task.get("max_steps", max(DEFAULT_MAX_STEPS, len(expected_calls) * 4 + 4))

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}📋 TASK {task_index}/{total_tasks} (emp_id={emp_id}){Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}Query: {Colors.END}{query}")
    print(f"{Colors.YELLOW}Max Steps: {Colors.END}{max_steps}")
    print(f"{Colors.YELLOW}Expected tool calls: {Colors.END}{len(expected_calls)}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")

    task_config = {
        "configurable": {
            "thread_id": f"batch_task_{task_index}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        }
    }

    system_prompt_msg = SystemMessage(content=get_base_prompt(tools))

    current_state = AgentState(
        messages=[system_prompt_msg, HumanMessage(content=query)],
        trajectory=[],
        current_step=0,
        max_steps=max_steps,
        task_completed=False,
        current_query=query,
        final_answer="",
        needs_clarification=False,
        clarification_question="",
        enable_clarification=False,
        subtasks_identified=[],
        subtasks_completed=[],
        pending_subtasks=[]
    )

    try:
        final_state = None
        async for event in graph.astream(input=current_state, config=task_config):
            for node_name, node_output in event.items():
                final_state = node_output

        if final_state:
            final_answer = final_state.final_answer if hasattr(final_state, 'final_answer') else final_state.get('final_answer', '')
            trajectory = final_state.trajectory if hasattr(final_state, 'trajectory') else final_state.get('trajectory', [])

            evaluation = evaluate_task(task, trajectory, final_answer)

            if final_answer:
                print(f"\n{Colors.GREEN}🎯 ANSWER:{Colors.END}")
                print(f"{Colors.GREEN}{final_answer}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ No final answer provided{Colors.END}")

            status_color = Colors.GREEN if evaluation["task_success"] else Colors.YELLOW
            print(f"{status_color}📊 Tool-call recall: {evaluation['tool_call_recall']:.2f} "
                  f"| precision: {evaluation['tool_call_precision']:.2f} "
                  f"| success: {evaluation['task_success']}{Colors.END}")
            print(f"{Colors.GREEN}✅ Task {task_index} completed - {len(trajectory)}/{max_steps} steps used{Colors.END}")

            return {
                "task_index": task_index,
                "emp_id": emp_id,
                "query": query,
                "ground_truth": task.get("ground_truth", {}),
                "max_steps": max_steps,
                "status": "success",
                "final_answer": final_answer,
                "trajectory_length": len(trajectory),
                "trajectory": trajectory,
                "evaluation": evaluation
            }
        else:
            print(f"{Colors.RED}❌ FAILED: No output from graph{Colors.END}")
            return {
                "task_index": task_index,
                "emp_id": emp_id,
                "query": query,
                "ground_truth": task.get("ground_truth", {}),
                "max_steps": max_steps,
                "status": "failed",
                "error": "No output from graph",
                "trajectory": []
            }

    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return {
            "task_index": task_index,
            "emp_id": emp_id,
            "query": query,
            "ground_truth": task.get("ground_truth", {}),
            "max_steps": max_steps,
            "status": "error",
            "error": str(e),
            "trajectory": []
        }


async def main():
    """Main batch evaluation entrypoint"""
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 🤖 EnterpriseBench Task Evaluator                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"{Colors.YELLOW}⚠️ Ignoring non-integer argument: {sys.argv[1]}{Colors.END}")

    print(f"{Colors.CYAN}Configuration:{Colors.END}")
    print(f"  Default max_steps: {DEFAULT_MAX_STEPS}")
    print(f"  Tasks file: {TASKS_FILE}")

    if not TASKS_FILE.exists():
        print(f"\n{Colors.RED}❌ ERROR: {TASKS_FILE} not found{Colors.END}")
        return

    try:
        with open(TASKS_FILE, 'r') as f:
            tasks = json.load(f)
        print(f"\n{Colors.GREEN}✅ Loaded {len(tasks)} tasks from {TASKS_FILE}{Colors.END}")
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}❌ ERROR: Invalid JSON in {TASKS_FILE}: {e}{Colors.END}")
        return

    if not tasks:
        print(f"{Colors.YELLOW}⚠️ No tasks found in {TASKS_FILE}{Colors.END}")
        return

    if limit:
        tasks = tasks[:limit]
        print(f"{Colors.YELLOW}Limiting run to first {limit} tasks{Colors.END}")

    print(f"\n{Colors.CYAN}🔗 Connecting to EnterpriseBench...{Colors.END}")
    connector = EnterpriseBenchConnector()

    if not connector.connect():
        print(f"{Colors.RED}❌ Failed to connect to EnterpriseBench{Colors.END}")
        return

    tools = connector.load_tools()
    if not tools:
        print(f"{Colors.YELLOW}⚠️ No tools loaded from EnterpriseBench{Colors.END}")

    print(f"\n{Colors.GREEN}✅ Building ReAct agent with {len(tools)} EnterpriseBench tools{Colors.END}")
    graph = build_react_agent_graph(tools, enable_clarification=False)

    batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    graph_config = {"configurable": {"thread_id": f"batch_{batch_id}"}}

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}🚀 STARTING BATCH EVALUATION ({len(tasks)} tasks){Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")

    jsonl_filepath = jsonl_path_for_batch(batch_id)
    print(f"{Colors.PURPLE}📝 Incrementally appending each task's result to: {jsonl_filepath}{Colors.END}")

    data_snapshot = snapshot_data_files(connector.data_files)
    print(f"{Colors.PURPLE}💾 Snapshotted {len(data_snapshot)} data files - "
          f"restoring them to this state after every task{Colors.END}")

    results = []
    for i, task in enumerate(tasks, 1):
        try:
            result = await run_task_batch(task, graph, graph_config, i, len(tasks), tools)
        finally:
            # Always restore, even if the task raised, so one crashed run can't leak
            # mutated state into every task that runs after it.
            restore_data_files(data_snapshot)
        results.append(result)
        append_task_result(result, batch_id)

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}📊 BATCH EVALUATION SUMMARY{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")

    successful = [r for r in results if r['status'] == 'success']
    task_successes = sum(1 for r in successful if r.get("evaluation", {}).get("task_success"))

    print(f"{Colors.GREEN}✅ Runs completed: {len(successful)}/{len(results)}{Colors.END}")
    print(f"{Colors.RED}❌ Runs failed: {len(results) - len(successful)}/{len(results)}{Colors.END}")
    print(f"{Colors.GREEN}🎯 Task success rate: {task_successes}/{len(results)}"
          f" ({(task_successes/len(results)*100 if results else 0):.1f}%){Colors.END}")

    for result in results:
        evaluation = result.get("evaluation", {})
        success = evaluation.get("task_success")
        status_color = Colors.GREEN if success else (Colors.RED if result['status'] != 'success' else Colors.YELLOW)
        status_icon = "✅" if success else ("❌" if result['status'] != 'success' else "⚠️")
        print(f"\n{status_color}{status_icon} Task {result['task_index']} (emp_id={result.get('emp_id')}): "
              f"{result['query'][:60]}...{Colors.END}")
        if result['status'] == 'success':
            print(f"   Tool-call recall: {evaluation.get('tool_call_recall', 0):.2f} "
                  f"| precision: {evaluation.get('tool_call_precision', 0):.2f}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")

    summary_filepath = write_summary_file(results, batch_id)
    print(f"{Colors.GREEN}📁 Per-task incremental log: {jsonl_filepath}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}📁 Final summary file: {summary_filepath}{Colors.END}")


if __name__ == "__main__":
    print("🚀 Starting EnterpriseBench Task Evaluator...")
    asyncio.run(main())
