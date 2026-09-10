#!/usr/bin/env python3
"""Select a high-quality, test-aware EnterpriseBench training subset."""

from __future__ import annotations

import argparse
import copy
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_ROOT = Path("/home/fripl/vharsh/research/EnterpriseBench")
DEFAULT_CANDIDATES = DEFAULT_ROOT / "new_training_tasks.json"
DEFAULT_TEST = DEFAULT_ROOT / "Task_Generation/tasks.json"
DEFAULT_TOOLS = DEFAULT_ROOT / "Task_Generation/utils/tools.json"
DEFAULT_OUTPUT = DEFAULT_ROOT / "selected_training_tasks_2000.json"
DEFAULT_REPORT = DEFAULT_ROOT / "selected_training_tasks_2000_report.json"

TEST_TOOL_FLOOR = 8
NON_TEST_TOOL_FLOOR = 5
MAX_TASKS_PER_SOURCE = 2
LENGTH_PROPORTIONS = {1: 0.325, 2: 0.500, 3: 0.175}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--test-tasks", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--tools", type=Path, default=DEFAULT_TOOLS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--size", type=int, default=2000)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def source_id(task: Dict[str, Any]) -> str:
    return (
        task.get("meta", {}).get("trajectory_id")
        or task.get("prerequisite_context", {}).get("workflow_id")
        or task["task_id"]
    )


def canonical_call(name: str, arguments: Dict[str, Any]) -> Tuple[str, str]:
    return (
        name,
        json.dumps(
            arguments,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        ),
    )


def test_calls(task: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    calls: List[Tuple[str, Dict[str, Any]]] = []
    for message in task.get("messages", []):
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"__raw__": arguments}
            if name and name != "llm":
                calls.append((name, arguments))
    return calls


def task_calls(task: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    return [
        (checkpoint["tool"], checkpoint.get("input_bindings") or {})
        for checkpoint in task.get("reward_checkpoints", [])
    ]


def sanitize_user_id(task: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = copy.deepcopy(task)
    for step in sanitized.get("chain_of_thought", []):
        inputs = step.get("inputs")
        if isinstance(inputs, dict):
            inputs.pop("userId", None)
    for checkpoint in sanitized.get("reward_checkpoints", []):
        bindings = checkpoint.get("input_bindings")
        if isinstance(bindings, dict):
            bindings.pop("userId", None)
    return sanitized


def validate_candidate(
    task: Dict[str, Any],
    tool_schemas: Dict[str, Dict[str, Any]],
) -> List[str]:
    reasons: List[str] = []
    checkpoints = task.get("reward_checkpoints", [])
    chain = task.get("chain_of_thought", [])
    sequence = tuple(item.get("tool") for item in checkpoints)

    if "target record" in task.get("instruction", "").lower():
        reasons.append("generic_target_record_instruction")
    if not task.get("instruction", "").strip():
        reasons.append("empty_instruction")
    if not checkpoints:
        reasons.append("no_reward_checkpoints")
    if len(chain) != len(checkpoints):
        reasons.append("chain_checkpoint_length_mismatch")
    if tuple(item.get("tool") for item in chain) != sequence:
        reasons.append("chain_checkpoint_sequence_mismatch")
    if tuple(
        task.get("ground_truth", {}).get("expected_tool_sequence", [])
    ) != sequence:
        reasons.append("ground_truth_sequence_mismatch")
    if set(task.get("required_tools", [])) != set(sequence):
        reasons.append("required_tools_mismatch")
    if any(step.get("success") is not True for step in chain):
        reasons.append("unsuccessful_gold_step")

    for checkpoint in checkpoints:
        tool_name = checkpoint.get("tool")
        definition = tool_schemas.get(tool_name)
        if definition is None:
            reasons.append(f"unknown_tool:{tool_name}")
            continue
        bindings = set((checkpoint.get("input_bindings") or {}).keys())
        argument_schema = definition.get("args_schema") or {}
        required = {
            name
            for name, spec in argument_schema.items()
            if isinstance(spec, dict) and spec.get("required") is True
        }
        missing = sorted(required - bindings)
        unknown = sorted(bindings - set(argument_schema))
        if missing:
            reasons.append(
                f"missing_required:{tool_name}:{','.join(missing)}"
            )
        if unknown:
            reasons.append(f"unknown_args:{tool_name}:{','.join(unknown)}")
    return reasons


def has_state_dependency(task: Dict[str, Any]) -> bool:
    for checkpoint in task.get("reward_checkpoints", []):
        state = checkpoint.get("state_tracking") or {}
        if (
            state.get("has_state_requirements")
            or state.get("state_dependencies")
            or state.get("state_to_retain")
        ):
            return True
    return False


def has_checkpoint_validation(task: Dict[str, Any]) -> bool:
    return any(
        checkpoint.get("success_validation")
        or checkpoint.get("expected_output_fields")
        or checkpoint.get("expected_output_parsed")
        or checkpoint.get("expected_effects")
        for checkpoint in task.get("reward_checkpoints", [])
    )


def missing_observation_count(task: Dict[str, Any]) -> int:
    return sum(
        not step.get("observed_output")
        for step in task.get("chain_of_thought", [])
    )


def capped_ratio(numerator: int, denominator: int, cap: float = 4.0) -> float:
    if numerator <= 0:
        return 0.0
    return min(cap, numerator / max(denominator, 1))


def selection_stats(
    tasks: Sequence[Dict[str, Any]],
    catalog: Iterable[str],
) -> Dict[str, Any]:
    tools = Counter()
    first_tools = Counter()
    transitions = Counter()
    lengths = Counter()
    sources = Counter()
    instructions = Counter()
    action_signatures = Counter()

    for task in tasks:
        calls = task_calls(task)
        names = [name for name, _ in calls]
        tools.update(names)
        if names:
            first_tools[names[0]] += 1
        transitions.update(zip(names, names[1:]))
        lengths[len(names)] += 1
        sources[source_id(task)] += 1
        instructions[task.get("instruction", "")] += 1
        action_signatures.update(canonical_call(*call) for call in calls)

    catalog = list(catalog)
    counts = sorted(tools.get(name, 0) for name in catalog)
    total = sum(counts)
    gini = 0.0
    if counts and total:
        size = len(counts)
        gini = sum(
            (2 * index - size - 1) * value
            for index, value in enumerate(counts, 1)
        ) / (size * total)

    return {
        "tasks": len(tasks),
        "gold_calls": sum(tools.values()),
        "mean_steps": (
            sum(length * count for length, count in lengths.items())
            / max(len(tasks), 1)
        ),
        "step_distribution": dict(sorted(lengths.items())),
        "covered_tools": len(tools),
        "uncovered_tools": sorted(set(catalog) - set(tools)),
        "tool_counts": dict(tools.most_common()),
        "first_tool_counts": dict(first_tools.most_common()),
        "unique_transitions": len(transitions),
        "source_trajectories": len(sources),
        "source_multiplicity": dict(sorted(Counter(sources.values()).items())),
        "duplicate_instruction_copies": sum(
            count - 1 for count in instructions.values() if count > 1
        ),
        "unique_action_signatures": len(action_signatures),
        "tool_frequency_gini": gini,
        "state_dependency_tasks": sum(has_state_dependency(task) for task in tasks),
        "checkpoint_validation_tasks": sum(
            has_checkpoint_validation(task) for task in tasks
        ),
        "missing_observations": sum(
            missing_observation_count(task) for task in tasks
        ),
    }


def select_tasks(
    candidates: Sequence[Dict[str, Any]],
    test_tasks: Sequence[Dict[str, Any]],
    tool_schemas: Dict[str, Dict[str, Any]],
    target_size: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    test_tool_counts = Counter()
    test_first_counts = Counter()
    test_transition_counts = Counter()
    test_action_signatures = set()
    test_trajectory_signatures = set()

    for task in test_tasks:
        calls = test_calls(task)
        names = [name for name, _ in calls]
        test_tool_counts.update(names)
        if names:
            test_first_counts[names[0]] += 1
        test_transition_counts.update(zip(names, names[1:]))
        signatures = tuple(canonical_call(*call) for call in calls)
        test_action_signatures.update(signatures)
        test_trajectory_signatures.add(signatures)

    rejection_counts = Counter()
    valid: List[Dict[str, Any]] = []
    for original in candidates:
        task = sanitize_user_id(original)
        reasons = validate_candidate(task, tool_schemas)
        if reasons:
            rejection_counts.update(set(reasons))
            continue
        signature = tuple(canonical_call(*call) for call in task_calls(task))
        if signature in test_trajectory_signatures:
            rejection_counts["exact_test_trajectory_overlap"] += 1
            continue
        if any(item in test_action_signatures for item in signature):
            rejection_counts["exact_test_action_overlap"] += 1
            continue
        valid.append(task)

    if len(valid) < target_size:
        raise RuntimeError(
            f"Only {len(valid)} valid candidates remain for {target_size} slots"
        )

    pool_tool_counts = Counter()
    pool_first_counts = Counter()
    pool_transition_counts = Counter()
    for task in valid:
        names = [name for name, _ in task_calls(task)]
        pool_tool_counts.update(names)
        if names:
            pool_first_counts[names[0]] += 1
        pool_transition_counts.update(zip(names, names[1:]))

    expected_calls = target_size * 2
    test_call_total = max(sum(test_tool_counts.values()), 1)
    tool_targets: Dict[str, int] = {
        name: min(
            pool_tool_counts[name],
            TEST_TOOL_FLOOR if test_tool_counts[name] else NON_TEST_TOOL_FLOOR,
        )
        for name in tool_schemas
    }
    remaining_target_calls = max(
        0,
        expected_calls - sum(tool_targets.values()),
    )
    # Candidate availability is much lower than the raw test demand for some
    # important tools. Redistribute that unreachable mass across other tools
    # that are present in the test set instead of over-selecting non-test tools.
    for _ in range(remaining_target_calls):
        available = [
            name
            for name in test_tool_counts
            if tool_targets[name] < pool_tool_counts[name]
        ]
        if not available:
            break
        name = max(
            available,
            key=lambda item: (
                test_tool_counts[item] / (tool_targets[item] + 1),
                item,
            ),
        )
        tool_targets[name] += 1

    test_first_total = max(sum(test_first_counts.values()), 1)
    first_targets = {
        name: min(
            pool_first_counts[name],
            max(
                TEST_TOOL_FLOOR,
                round(target_size * test_first_counts[name] / test_first_total),
            ),
        )
        for name in test_first_counts
    }

    test_transition_total = max(sum(test_transition_counts.values()), 1)
    transition_targets = {
        pair: min(
            pool_transition_counts[pair],
            max(
                2,
                round(
                    target_size
                    * test_transition_counts[pair]
                    / test_transition_total
                ),
            ),
        )
        for pair in test_transition_counts
        if pool_transition_counts[pair]
    }

    static_scores: Dict[str, float] = {}
    task_features: Dict[str, Dict[str, Any]] = {}
    for task in valid:
        calls = task_calls(task)
        names = [name for name, _ in calls]
        transitions = list(zip(names, names[1:]))
        actions = [canonical_call(*call) for call in calls]
        score = 2.0 * len(calls)
        score += min(len(task.get("instruction", "")) / 1000.0, 1.5)
        score += 0.75 if missing_observation_count(task) == 0 else 0.0
        score += 1.5 if has_state_dependency(task) else 0.0
        score += 0.5 if has_checkpoint_validation(task) else 0.0
        score += 2.5 * sum(
            capped_ratio(test_tool_counts[name], pool_tool_counts[name])
            for name in names
        )
        if names:
            score += 2.0 * capped_ratio(
                test_first_counts[names[0]],
                pool_first_counts[names[0]],
            )
        score += 4.0 * sum(
            capped_ratio(
                test_transition_counts[pair],
                pool_transition_counts[pair],
            )
            for pair in transitions
        )
        score -= 2.0 * sum(name not in test_tool_counts for name in names)
        task_id = task["task_id"]
        static_scores[task_id] = score
        task_features[task_id] = {
            "source": source_id(task),
            "names": names,
            "first": names[0] if names else None,
            "transitions": transitions,
            "actions": actions,
            "instruction": task.get("instruction", ""),
        }

    selected: List[Dict[str, Any]] = []
    selected_ids = set()
    selected_instructions = set()
    source_counts = Counter()
    tool_counts = Counter()
    first_counts = Counter()
    transition_counts = Counter()
    action_counts = Counter()
    length_targets = {
        1: round(target_size * LENGTH_PROPORTIONS[1]),
        2: round(target_size * LENGTH_PROPORTIONS[2]),
    }
    length_targets[3] = target_size - sum(length_targets.values())
    length_counts = Counter()

    while len(selected) < target_size:
        best_task = None
        best_key = None
        for task in valid:
            task_id = task["task_id"]
            if task_id in selected_ids:
                continue
            features = task_features[task_id]
            task_length = len(features["names"])
            if length_counts[task_length] >= length_targets.get(task_length, 0):
                continue
            if source_counts[features["source"]] >= MAX_TASKS_PER_SOURCE:
                continue
            if features["instruction"] in selected_instructions:
                continue

            score = static_scores[task_id]
            score += 15.0 if source_counts[features["source"]] == 0 else -5.0

            for name in features["names"]:
                target = tool_targets.get(name, 0)
                if target and tool_counts[name] < target:
                    score += 5.0 * (target - tool_counts[name]) / target
                elif target:
                    score -= (
                        8.0
                        * (tool_counts[name] - target + 1)
                        / max(target, NON_TEST_TOOL_FLOOR)
                    )

            first = features["first"]
            first_target = first_targets.get(first, 0)
            if first_target and first_counts[first] < first_target:
                score += 4.0 * (first_target - first_counts[first]) / first_target

            for pair in features["transitions"]:
                target = transition_targets.get(pair, 0)
                if target and transition_counts[pair] < target:
                    score += 6.0 * (target - transition_counts[pair]) / target

            score -= 0.35 * sum(
                math.log1p(action_counts[action])
                for action in features["actions"]
            )
            key = (score, task_id)
            if best_key is None or key > best_key:
                best_key = key
                best_task = task

        if best_task is None:
            raise RuntimeError(
                "Selection constraints exhausted at "
                f"{len(selected)}/{target_size} tasks"
            )

        selected.append(best_task)
        task_id = best_task["task_id"]
        features = task_features[task_id]
        selected_ids.add(task_id)
        selected_instructions.add(features["instruction"])
        source_counts[features["source"]] += 1
        length_counts[len(features["names"])] += 1
        tool_counts.update(features["names"])
        if features["first"]:
            first_counts[features["first"]] += 1
        transition_counts.update(features["transitions"])
        action_counts.update(features["actions"])

    selected.sort(key=lambda task: task["task_id"])
    selected_action_signatures = {
        canonical_call(*call)
        for task in selected
        for call in task_calls(task)
    }
    selected_trajectory_signatures = {
        tuple(canonical_call(*call) for call in task_calls(task))
        for task in selected
    }
    report = {
        "selection_policy": {
            "target_size": target_size,
            "removed_argument": "userId",
            "hard_filters": [
                "non-generic instruction",
                "known tools",
                "all required arguments present",
                "no unsupported arguments after userId cleanup",
                "successful structurally aligned gold trajectory",
                "no exact test action overlap",
                "no exact test trajectory overlap",
            ],
            "max_tasks_per_source_trajectory": MAX_TASKS_PER_SOURCE,
            "length_targets": length_targets,
            "tool_targets": tool_targets,
            "ranking_signals": [
                "test tool distribution",
                "test first-tool distribution",
                "test transition distribution",
                "trajectory length",
                "source diversity",
                "state dependencies",
                "checkpoint validation",
                "observed outputs",
                "action-signature diversity",
            ],
        },
        "candidate_counts": {
            "input": len(candidates),
            "valid_after_filters": len(valid),
            "rejections": dict(rejection_counts.most_common()),
        },
        "leakage_checks": {
            "exact_test_action_overlap": len(
                selected_action_signatures & test_action_signatures
            ),
            "exact_test_trajectory_overlap": len(
                selected_trajectory_signatures & test_trajectory_signatures
            ),
        },
        "selected": selection_stats(selected, tool_schemas),
        "test": {
            "tasks": len(test_tasks),
            "tool_counts": dict(test_tool_counts.most_common()),
            "first_tool_counts": dict(test_first_counts.most_common()),
            "unique_transitions": len(test_transition_counts),
        },
    }
    return selected, report


def main() -> None:
    args = parse_args()
    candidates = load_json(args.candidates)
    test_tasks = load_json(args.test_tasks)
    tool_definitions = load_json(args.tools)
    tool_schemas = {item["name"]: item for item in tool_definitions}

    selected, report = select_tasks(
        candidates,
        test_tasks,
        tool_schemas,
        args.size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(selected, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    with args.report.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"Selected {len(selected)} tasks -> {args.output}")
    print(f"Audit report -> {args.report}")
    print(json.dumps(report["selected"], indent=2))


if __name__ == "__main__":
    main()
