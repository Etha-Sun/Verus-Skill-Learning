#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_TASKS = 20
OUTCOME_COLORS = ("#D3A095", "#5C8F83")
TOKEN_COLORS = ("#F7F3EC", "#B7CEC7", "#356F78")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_label(key: str) -> str:
    lower = key.lower()
    if "trace2skill" in lower or re.search(r"(^|[_-])trace([_-]|$)", lower):
        return "Trace2Skill"
    for token, label in (("blank", "Blank"), ("s1", "S1"), ("s2", "S2")):
        if re.search(rf"(^|[_-]){token}([_-]|$)", lower):
            return label
    return re.sub(r"[_-](?:budget)?\d+(?:s)?$", "", key).replace("_", " ")


def _arm_rank(label: str) -> tuple[int, str]:
    order = {"Blank": 0, "S1": 1, "S2": 2, "Trace2Skill": 3}
    return order.get(label, 99), label


def _common_budget(keys: list[str]) -> str | None:
    budgets = []
    for key in keys:
        match = re.search(r"(?:budget|_)(\d+)(?:s)?(?:[_-]|$)", key.lower())
        budgets.append(match.group(1) if match else None)
    return budgets[0] if budgets[0] and len(set(budgets)) == 1 else None


def _resolve_run_dir(input_dir: Path, raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_dir():
        return path
    sibling = input_dir.parent / path.name
    return sibling if sibling.is_dir() else None


def _load_matrix(input_dir: Path) -> dict[str, Any] | None:
    candidates = []
    for path in sorted(input_dir.glob("*matrix.json")):
        document = _read_json(path)
        if (
            isinstance(document, dict)
            and isinstance(document.get("tasks"), list)
            and isinstance(document.get("run_order"), list)
        ):
            candidates.append((path, document))
    if not candidates:
        return None
    if len(candidates) != 1:
        names = ", ".join(path.name for path, _ in candidates)
        raise ValueError(f"multiple comparison matrices found: {names}")

    matrix_path, document = candidates[0]
    run_order = document["run_order"]
    if len(run_order) < 3:
        raise ValueError("comparison matrix contains fewer than three runs")
    selected = run_order[-3:]
    labels = [_arm_label(key) for key in selected]
    if len(set(labels)) != 3:
        raise ValueError(f"last three matrix runs do not identify three arms: {selected}")

    raw_tasks = document["tasks"]
    if len(raw_tasks) != EXPECTED_TASKS:
        raise ValueError(f"expected {EXPECTED_TASKS} tasks, found {len(raw_tasks)}")
    tasks = []
    for task in raw_tasks:
        runs = task.get("runs") or {}
        if any(key not in runs for key in selected):
            raise ValueError(f"task {task.get('task_id')} is missing a selected arm")
        tasks.append(
            {
                "name": task.get("problem_name") or task.get("task_id"),
                "id": task["task_id"],
                "arms": {
                    key: {
                        "solved": bool(runs[key]["solved"]),
                        "total_tokens": int(runs[key]["total_tokens"]),
                    }
                    for key in selected
                },
            }
        )

    run_dirs = []
    models = set()
    for key in selected:
        raw_path = (document.get("run_dirs") or {}).get(key)
        run_dir = _resolve_run_dir(input_dir, raw_path) if raw_path else None
        run_dirs.append(str(run_dir or raw_path or key))
        if run_dir and (run_dir / "summary.json").is_file():
            models.add(str(_read_json(run_dir / "summary.json").get("model")))
    model = models.pop() if len(models) == 1 else input_dir.name
    complete_scope = all(
        "unretained_total_tokens" in task["runs"][key]
        for task in raw_tasks
        for key in selected
    )
    return {
        "source": str(matrix_path),
        "model": model,
        "budget_seconds": _common_budget(selected),
        "token_scope": (
            "complete bridge ledger (input + output, including retries and archived attempts)"
            if complete_scope
            else "reported input + output tokens"
        ),
        "arms": [
            {"key": key, "label": label, "run_dir": run_dir}
            for key, label, run_dir in zip(selected, labels, run_dirs)
        ],
        "tasks": tasks,
    }


def _ledger_tokens(run_dir: Path, task_ids: list[str]) -> dict[str, int] | None:
    path = run_dir / "bridge_calls.jsonl"
    if not path.is_file():
        return None
    totals = {task_id: 0 for task_id in task_ids}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        record = json.loads(line)
        ledger_task = str(record.get("task_id") or "")
        matches = [task_id for task_id in task_ids if f"--{task_id}--" in ledger_task]
        if len(matches) != 1:
            raise ValueError(f"cannot map ledger task key: {ledger_task}")
        for attempt in record.get("attempts") or []:
            usage = attempt.get("usage") or {}
            totals[matches[0]] += int(usage.get("prompt_tokens", 0) or 0)
            totals[matches[0]] += int(usage.get("completion_tokens", 0) or 0)
    return totals


def _load_run_dir(run_dir: Path) -> dict[str, Any]:
    summary = _read_json(run_dir / "summary.json")
    rows = _read_json(run_dir / "per_task.json")
    if summary.get("status") != "complete":
        raise ValueError(f"run is not complete: {run_dir}")
    if len(rows) != EXPECTED_TASKS or int(summary.get("test_n", 0)) != EXPECTED_TASKS:
        raise ValueError(f"run must contain exactly {EXPECTED_TASKS} tasks: {run_dir}")
    ids = [str(row["id"]) for row in rows]
    if len(set(ids)) != EXPECTED_TASKS:
        raise ValueError(f"duplicate task ids in {run_dir}")
    complete_tokens = _ledger_tokens(run_dir, ids)
    task_rows = {}
    for row in rows:
        task_id = str(row["id"])
        usage = row.get("usage") or {}
        task_rows[task_id] = {
            "name": str(row["task_id"]),
            "solved": bool(row["proof_solved"]),
            "total_tokens": (
                complete_tokens[task_id]
                if complete_tokens is not None
                else int(usage.get("prompt_tokens", 0) or 0)
                + int(usage.get("completion_tokens", 0) or 0)
            ),
        }
    if complete_tokens is not None:
        expected = summary.get("usage") or {}
        expected_total = int(expected.get("prompt_tokens", 0) or 0) + int(
            expected.get("completion_tokens", 0) or 0
        )
        if sum(complete_tokens.values()) != expected_total:
            raise ValueError(f"complete ledger does not reconcile with summary: {run_dir}")
    return {
        "run_dir": str(run_dir),
        "model": str(summary.get("model") or "unknown model"),
        "label": _arm_label(run_dir.name),
        "task_order": ids,
        "tasks": task_rows,
        "complete_ledger": complete_tokens is not None,
    }


def _load_child_runs(input_dir: Path) -> dict[str, Any]:
    run_dirs = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_dir()
        and (path / "summary.json").is_file()
        and (path / "per_task.json").is_file()
    )
    if len(run_dirs) != 3:
        raise ValueError(
            "input folder needs one comparison *matrix.json or exactly three child run folders"
        )
    loaded = sorted((_load_run_dir(path) for path in run_dirs), key=lambda row: _arm_rank(row["label"]))
    if len({row["label"] for row in loaded}) != 3:
        raise ValueError("child run folder names do not identify three distinct arms")
    if len({row["model"] for row in loaded}) != 1:
        raise ValueError("the three runs use different models")
    first_ids = loaded[0]["task_order"]
    if any(set(row["task_order"]) != set(first_ids) for row in loaded[1:]):
        raise ValueError("the three runs do not contain the same task ids")

    tasks = []
    for task_id in first_ids:
        names = {row["tasks"][task_id]["name"] for row in loaded}
        if len(names) != 1:
            raise ValueError(f"task name differs across arms: {task_id}")
        tasks.append(
            {
                "name": names.pop(),
                "id": task_id,
                "arms": {
                    row["label"]: {
                        "solved": row["tasks"][task_id]["solved"],
                        "total_tokens": row["tasks"][task_id]["total_tokens"],
                    }
                    for row in loaded
                },
            }
        )
    budget = _common_budget([Path(row["run_dir"]).name for row in loaded])
    return {
        "source": str(input_dir),
        "model": loaded[0]["model"],
        "budget_seconds": budget,
        "token_scope": (
            "complete bridge ledger (input + output, including retries and archived attempts)"
            if all(row["complete_ledger"] for row in loaded)
            else "reported per-task input + output tokens"
        ),
        "arms": [
            {"key": row["label"], "label": row["label"], "run_dir": row["run_dir"]}
            for row in loaded
        ],
        "tasks": tasks,
    }


def load_dataset(input_dir: Path) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        raise ValueError(f"input folder does not exist: {input_dir}")
    return _load_matrix(input_dir) or _load_child_runs(input_dir)


def _style() -> dict[str, Any]:
    return {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.06,
        "savefig.dpi": 220,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "font.size": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 7.2,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }


def _matrix(dataset: dict[str, Any], field: str) -> list[list[Any]]:
    return [
        [task["arms"][arm["key"]][field] for arm in dataset["arms"]]
        for task in dataset["tasks"]
    ]


def _column_labels(dataset: dict[str, Any]) -> list[str]:
    outcome = _matrix(dataset, "solved")
    return [
        f"{arm['label']}\n{sum(int(row[index]) for row in outcome)}/{len(outcome)} pass"
        for index, arm in enumerate(dataset["arms"])
    ]


def _format_tokens(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(value)


def _display_model(model: str) -> str:
    match = re.fullmatch(r"qwen(\d)(\d)-(\d+)b-(bf16)", model.lower())
    if match:
        return f"Qwen{match.group(1)}.{match.group(2)}-{match.group(3)}B {match.group(4).upper()}"
    return model


def _configure_axis(ax: Any, dataset: dict[str, Any]) -> None:
    ax.set_xticks(range(3), _column_labels(dataset))
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=8)
    ax.set_yticks(range(EXPECTED_TASKS), [task["name"] for task in dataset["tasks"]])
    ax.tick_params(axis="y", length=0, pad=7)
    ax.set_xticks([0.5, 1.5], minor=True)
    ax.set_yticks([index + 0.5 for index in range(EXPECTED_TASKS - 1)], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _title(dataset: dict[str, Any], suffix: str) -> tuple[str, str]:
    budget = (
        f" · {dataset['budget_seconds']} s per task" if dataset["budget_seconds"] else ""
    )
    return (
        f"{_display_model(dataset['model'])}: {suffix}",
        f"Fixed test-{EXPECTED_TASKS}{budget}",
    )


def _save_outcome_heatmap(dataset: dict[str, Any], path: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    values = [[int(value) for value in row] for row in _matrix(dataset, "solved")]
    with plt.style.context(_style()):
        fig, ax = plt.subplots(figsize=(19.0, 10.8))
        fig.subplots_adjust(left=0.76, right=0.96, top=0.86, bottom=0.06)
        image = ax.imshow(
            values,
            cmap=ListedColormap(OUTCOME_COLORS),
            norm=BoundaryNorm((-0.5, 0.5, 1.5), 2),
            aspect="auto",
        )
        image.set_clim(-0.5, 1.5)
        _configure_axis(ax, dataset)
        for y, row in enumerate(values):
            for x, value in enumerate(row):
                ax.text(
                    x,
                    y,
                    "PASS" if value else "FAIL",
                    ha="center",
                    va="center",
                    color="white" if value else "#482B27",
                    fontsize=8.2,
                    fontweight="bold",
                )
        title, subtitle = _title(dataset, "per-task outcomes")
        fig.suptitle(title, x=0.31, y=0.965, ha="left", fontsize=14, fontweight="bold")
        fig.text(0.31, 0.925, subtitle + " · independently verified proof outcome", color="#5F6368")
        fig.savefig(path)
        plt.close(fig)


def _save_token_heatmap(dataset: dict[str, Any], path: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.ticker import FuncFormatter

    values = _matrix(dataset, "total_tokens")
    maximum = max(value for row in values for value in row)
    norm = Normalize(vmin=0, vmax=maximum)
    cmap = LinearSegmentedColormap.from_list("token_cost", TOKEN_COLORS)
    with plt.style.context(_style()):
        fig, ax = plt.subplots(figsize=(19.0, 10.8))
        fig.subplots_adjust(left=0.76, right=0.93, top=0.86, bottom=0.08)
        image = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto")
        _configure_axis(ax, dataset)
        for y, row in enumerate(values):
            for x, value in enumerate(row):
                ax.text(
                    x,
                    y,
                    _format_tokens(value),
                    ha="center",
                    va="center",
                    color="white" if norm(value) >= 0.58 else "#273436",
                    fontsize=8.0,
                    fontweight="bold",
                )
        colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.045)
        colorbar.set_label("Total tokens per task")
        colorbar.ax.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _: _format_tokens(int(value)))
        )
        colorbar.outline.set_linewidth(0.5)
        title, subtitle = _title(dataset, "per-task token cost")
        fig.suptitle(title, x=0.31, y=0.965, ha="left", fontsize=14, fontweight="bold")
        fig.text(0.31, 0.925, subtitle + f" · {dataset['token_scope']}", color="#5F6368")
        fig.savefig(path)
        plt.close(fig)


def _write_csv(dataset: dict[str, Any], path: Path) -> None:
    fields = ["problem_name", "task_id"]
    for arm in dataset["arms"]:
        fields.extend((f"{arm['key']}_solved", f"{arm['key']}_total_tokens"))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task in dataset["tasks"]:
            row: dict[str, Any] = {"problem_name": task["name"], "task_id": task["id"]}
            for arm in dataset["arms"]:
                result = task["arms"][arm["key"]]
                row[f"{arm['key']}_solved"] = result["solved"]
                row[f"{arm['key']}_total_tokens"] = result["total_tokens"]
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot pass/fail and token-cost heatmaps for a three-arm test-20 folder."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="default: INPUT_DIR/figures/three_arm_heatmaps",
    )
    args = parser.parse_args()
    dataset = load_dataset(args.input_dir)
    output_dir = (args.output_dir or args.input_dir / "figures" / "three_arm_heatmaps").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    outcome_path = output_dir / "pass_fail_heatmap.png"
    token_path = output_dir / "token_cost_heatmap.png"
    csv_path = output_dir / "heatmap_data.csv"
    _save_outcome_heatmap(dataset, outcome_path)
    _save_token_heatmap(dataset, token_path)
    _write_csv(dataset, csv_path)
    print(
        json.dumps(
            {
                "source": dataset["source"],
                "model": dataset["model"],
                "tasks": len(dataset["tasks"]),
                "arms": [arm["label"] for arm in dataset["arms"]],
                "pass_fail_png": str(outcome_path),
                "token_cost_png": str(token_path),
                "data_csv": str(csv_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
