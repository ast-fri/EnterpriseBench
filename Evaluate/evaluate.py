"""
LLM-as-judge evaluator for EnterpriseBench trajectories.
=========================================================
Takes the trajectories produced by client.py (Evaluate/trajectories/eval_results_*.json)
and, for each task, asks an LLM judge to score the agent's generated trajectory against
the reference trajectory implied by that task's `subtasks` in Task_Generation/tasks.json.

Rubric/prompt design follows /mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Evaluation/evaluate.py
(1-5 score + feedback, JSON output), but reuses this repo's own model loaders from graph.py
so the judge can be any of local/vllm/azure/bedrock/gemini/takane, not just Azure GPT.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from client import Colors, TASKS_FILE
from graph import (
    LOCAL_MODEL_PATH,
    VLLM_API_KEY,
    VLLM_BASE_URL,
    load_bedrock_model,
    load_gemini_model,
    load_gpt_model,
    load_local_model,
    load_takane_model,
    load_vllm_model,
)

load_dotenv()

EVALUATE_DIR = Path(__file__).resolve().parent
TRAJECTORIES_DIR = EVALUATE_DIR / "trajectories"

# ============================================================
# Hyperparameters
# ============================================================
# How many generated trajectories to send to the judge. Judging is a separate LLM call
# per task on top of generation, so this bounds judge-side cost/latency independently of
# how many tasks client.py actually ran. 0 (or unset) => judge every trajectory found in
# the results file. Override per-run with `python evaluate.py <results_file> <num>`.
NUM_TRAJECTORIES_TO_EVALUATE = int(os.getenv("NUM_TRAJECTORIES_TO_EVALUATE", "0")) or None

# Model used as the judge. Defaults to MODEL_MODE (the same model client.py generated
# with) but can be pointed at a different/stronger judge via JUDGE_MODEL_MODE.
JUDGE_MODEL_MODE = os.getenv("JUDGE_MODEL_MODE", os.getenv("MODEL_MODE", "azure"))

JUDGE_MAX_RETRIES = 5


RUBRIC_PROMPT = """###Task Description:
    An instruction (might include an Input inside it), a query, a trajectory to evaluate, a reference trajectory that gets a score of 5, and a score rubric representing a evaluation criteria are given.
    1. Write a detailed feedback that assesses the quality of the trajectory strictly based on the given score rubric, not evaluating in general.
    2. After writing a feedback, write a score that is either 1 or 2 or 3 or 4 or 5. You should refer to the score rubric.
    3. The output format should be JSON and should only look as follows: {{"Feedback": write a feedback for criteria, "Score": [an integer number between 1 and 5]}} "
    4. Please do not generate any other opening, closing, and explanations.
    5. Only evaluate on common things between generated trajectory and reference trajectory. Don't evaluate on things which are present in reference trajectory but not in generated trajectory.

    ###Instruction:
    Your task is to evaluate the generated answer and reference answer for the following query:
    {query}

    ###Generate trajectory to evaluate:
    {generated_answer}

    ###Reference trajectory (Score 5):
    {reference_answer}

    ###Score Rubrics:
    Score 1: If the generated trajectory is not relevant to the user query and reference trajectory with missing entities.
    Score 2: If the generated trajectory is relevant to user query or contains significant mistakes or misses important entities or if entities present in reference trajectory are not exact match.
    Score 3: If the generated trajectory is relevant to the reference trajectory and trajectorys the query but contains very few mistakes.
    Score 4: If the generated trajectory is relevant to the user query and all the entities are exact match as the reference trajectory along with same intent, but it is not as concise.
    Score 5: If the generated trajectory is relevant to the user query and fully correct according to the reference trajectory.

    ###Feedback:"""


def load_judge_model(mode: str):
    if mode == "azure":
        return load_gpt_model()
    if mode == "takane":
        return load_takane_model()
    if mode == "bedrock":
        return load_bedrock_model()
    if mode == "gemini":
        return load_gemini_model()
    if mode == "vllm":
        llm, _model_name = load_vllm_model(VLLM_BASE_URL, VLLM_API_KEY)
        return llm
    if mode == "local":
        return load_local_model(LOCAL_MODEL_PATH)
    raise ValueError(f"Unknown JUDGE_MODEL_MODE: {mode}. Use one of 'local', 'vllm', 'azure', 'bedrock', 'gemini', 'takane'")


def _extract_judge_json(text: str) -> Dict[str, Any]:
    """Robustly pull {"Feedback": ..., "Score": ...} out of a judge response."""
    if not text:
        return {"Feedback": "", "Score": 0}

    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped[len("```json"):].strip() if stripped.startswith("```json") else stripped[3:].strip()
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    feedback_match = re.search(r'"Feedback"\s*:\s*"(.*?)"\s*,\s*"Score"', stripped, re.DOTALL)
    score_match = re.search(r'"Score"\s*:\s*(\d+)', stripped)
    if feedback_match or score_match:
        return {
            "Feedback": feedback_match.group(1) if feedback_match else "",
            "Score": int(score_match.group(1)) if score_match else 0
        }

    print(f"{Colors.YELLOW}⚠️  Could not parse judge response, defaulting to score 0: {stripped[:200]}{Colors.END}")
    return {"Feedback": stripped, "Score": 0}


def format_reference_trajectory(task: dict) -> str:
    """Build the gold/reference trajectory text from a task's `subtasks` (ground-truth
    tool calls + outputs recorded at task-generation time)."""
    lines = []
    for i, subtask in enumerate(task.get("subtasks", []), 1):
        lines.append(f"Step {i}: {subtask.get('subtask', '')}")
        for tool_call in subtask.get("tools", []):
            names = tool_call.get("tool_name", [])
            name = names[0] if isinstance(names, list) and names else names
            lines.append(f"  Tool: {name}")
            lines.append(f"  Arguments: {json.dumps(tool_call.get('tool_arguments', {}), default=str)}")
            lines.append(f"  Output: {tool_call.get('tool_output')}")
    return "\n".join(lines)


def format_generated_trajectory(trajectory: List[dict]) -> str:
    """Build the generated trajectory text from a run_task_batch() trajectory (as saved
    by client.py - list of {step_type, content, tool_used, tool_input, ...} dicts)."""
    lines = []
    for step in trajectory:
        step_type = step.get("step_type")
        content = step.get("content", "")
        if step_type == "thought":
            lines.append(f"Thought: {content}")
        elif step_type == "action":
            tool_used = step.get("tool_used")
            if tool_used:
                lines.append(f"Action: {tool_used}({json.dumps(step.get('tool_input', {}), default=str)})")
            else:
                lines.append(f"Action (final answer): {content}")
        elif step_type == "observation":
            lines.append(f"Observation: {content}")
    return "\n".join(lines)


class TrajectoryEvaluator:
    """LLM-as-judge: scores one generated trajectory against its reference, 1-5 + feedback."""

    def __init__(self, mode: str = JUDGE_MODEL_MODE):
        self.mode = mode
        print(f"{Colors.CYAN}🧑‍⚖️  Loading judge model ({mode})...{Colors.END}")
        self.llm = load_judge_model(mode)

    def judge(self, query: str, reference: str, generated: str) -> Dict[str, Any]:
        prompt = RUBRIC_PROMPT.format(query=query, generated_answer=generated, reference_answer=reference)

        response_text = ""
        for attempt in range(1, JUDGE_MAX_RETRIES + 1):
            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                response_text = response.content
                break
            except Exception as e:
                wait = 15 * attempt
                print(f"{Colors.YELLOW}⚠️  Judge call failed ({e}); retrying in {wait}s...{Colors.END}")
                time.sleep(wait)

        parsed = _extract_judge_json(response_text)
        return {
            "feedback": parsed.get("Feedback", ""),
            "score": parsed.get("Score", 0)
        }


def find_latest_results_file() -> Optional[Path]:
    candidates = sorted(TRAJECTORIES_DIR.glob("eval_results_*.json"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_tasks_by_index(tasks_file: Path) -> Dict[int, dict]:
    with open(tasks_file, "r") as f:
        tasks = json.load(f)
    # client.py enumerates tasks.json 1-indexed (enumerate(tasks, 1)) - mirror that here
    # so task_index in the results file lines up with the right tasks.json entry.
    return {i: task for i, task in enumerate(tasks, 1)}


def append_judge_result(result: dict, batch_id: str) -> Path:
    os.makedirs(TRAJECTORIES_DIR, exist_ok=True)
    filepath = TRAJECTORIES_DIR / f"judge_results_{batch_id}.jsonl"
    with open(filepath, "a") as f:
        f.write(json.dumps(result) + "\n")
        f.flush()
    return filepath


def write_judge_summary(results: List[dict], batch_id: str) -> Path:
    filepath = TRAJECTORIES_DIR / f"judge_results_{batch_id}.json"
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    summary = {
        "batch_id": batch_id,
        "judge_model_mode": JUDGE_MODEL_MODE,
        "num_evaluated": len(results),
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
        "score_distribution": {s: scores.count(s) for s in sorted(set(scores))},
        "results": results
    }
    with open(filepath, "w") as f:
        json.dump(summary, f, indent=2)
    return filepath


def main():
    results_arg = sys.argv[1] if len(sys.argv) > 1 else None
    num_override = int(sys.argv[2]) if len(sys.argv) > 2 else None

    num_to_evaluate = num_override or NUM_TRAJECTORIES_TO_EVALUATE

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 🧑‍⚖️  EnterpriseBench Trajectory Evaluator (LLM judge)     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    results_path = Path(results_arg) if results_arg else find_latest_results_file()
    if not results_path or not results_path.exists():
        print(f"{Colors.RED}❌ ERROR: no eval_results_*.json file found under {TRAJECTORIES_DIR}. "
              f"Run client.py first, or pass a path explicitly.{Colors.END}")
        return

    batch_id_match = re.search(r"eval_results_(.+)\.json$", results_path.name)
    batch_id = batch_id_match.group(1) if batch_id_match else results_path.stem

    print(f"{Colors.CYAN}Results file: {Colors.END}{results_path}")
    print(f"{Colors.CYAN}Tasks file:   {Colors.END}{TASKS_FILE}")
    print(f"{Colors.CYAN}Judge model:  {Colors.END}{JUDGE_MODEL_MODE}")
    print(f"{Colors.CYAN}Trajectories to evaluate: {Colors.END}{num_to_evaluate if num_to_evaluate else 'ALL'}")

    with open(results_path, "r") as f:
        batch_data = json.load(f)
    generated_tasks = batch_data.get("tasks", [])

    tasks_by_index = load_tasks_by_index(TASKS_FILE)

    # Only trajectories that actually completed successfully have a trajectory to judge.
    candidates = [t for t in generated_tasks if t.get("status") == "success" and t.get("trajectory")]
    skipped = len(generated_tasks) - len(candidates)
    if skipped:
        print(f"{Colors.YELLOW}⚠️  Skipping {skipped} task(s) without a successful trajectory{Colors.END}")

    if num_to_evaluate:
        candidates = candidates[:num_to_evaluate]

    print(f"{Colors.GREEN}✅ Evaluating {len(candidates)} trajectories{Colors.END}\n")

    evaluator = TrajectoryEvaluator(JUDGE_MODEL_MODE)

    judge_filepath = TRAJECTORIES_DIR / f"judge_results_{batch_id}.jsonl"
    print(f"{Colors.PURPLE}📝 Incrementally appending each judged result to: {judge_filepath}{Colors.END}\n")

    results = []
    for i, generated_task in enumerate(candidates, 1):
        task_index = generated_task["task_index"]
        gold_task = tasks_by_index.get(task_index)
        if gold_task is None:
            print(f"{Colors.YELLOW}⚠️  No matching tasks.json entry for task_index={task_index}, skipping{Colors.END}")
            continue

        query = generated_task.get("query", gold_task.get("task", ""))
        reference = format_reference_trajectory(gold_task)
        generated = format_generated_trajectory(generated_task.get("trajectory", []))

        print(f"{Colors.CYAN}[{i}/{len(candidates)}] Judging task {task_index} (emp_id={generated_task.get('emp_id')}){Colors.END}")

        verdict = evaluator.judge(query, reference, generated)
        result = {
            "task_index": task_index,
            "emp_id": generated_task.get("emp_id", ""),
            "query": query,
            "feedback": verdict["feedback"],
            "score": verdict["score"]
        }
        results.append(result)
        append_judge_result(result, batch_id)

        print(f"   Score: {result['score']}/5 - {str(result['feedback'])[:150]}")

    summary_path = write_judge_summary(results, batch_id)

    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}📊 JUDGE SUMMARY{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"{Colors.GREEN}✅ Evaluated: {len(results)} trajectories{Colors.END}")
    print(f"{Colors.GREEN}⭐ Average score: {avg:.2f}/5{Colors.END}")
    print(f"{Colors.GREEN}📁 Per-task incremental log: {judge_filepath}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}📁 Final summary file: {summary_path}{Colors.END}")


if __name__ == "__main__":
    main()
