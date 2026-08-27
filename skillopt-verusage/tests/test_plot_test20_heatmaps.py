import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "plot_test20_heatmaps.py"
    spec = importlib.util.spec_from_file_location("plot_test20_heatmaps", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_matrix_input_selects_latest_three_arms(tmp_path: Path) -> None:
    tasks = []
    run_order = ["blank_600", "s2_600", "trace_600", "blank_1200", "s2_1200", "trace_1200"]
    for index in range(20):
        tasks.append(
            {
                "problem_name": f"problem_{index}",
                "task_id": f"id{index}",
                "runs": {
                    key: {
                        "solved": key == "s2_1200" and index == 0,
                        "total_tokens": 1000 + index,
                        "unretained_total_tokens": 10,
                    }
                    for key in run_order
                },
            }
        )
    (tmp_path / "comparison_matrix.json").write_text(
        json.dumps({"run_order": run_order, "tasks": tasks}), encoding="utf-8"
    )

    dataset = _module().load_dataset(tmp_path)

    assert [arm["label"] for arm in dataset["arms"]] == ["Blank", "S2", "Trace2Skill"]
    assert dataset["budget_seconds"] == "1200"
    assert dataset["tasks"][0]["arms"]["s2_1200"]["solved"] is True
    assert "complete bridge ledger" in dataset["token_scope"]


def test_child_run_input_requires_same_complete_test20(tmp_path: Path) -> None:
    for label in ("blank", "s2", "trace2skill"):
        run_dir = tmp_path / f"model-budget1200-{label}"
        run_dir.mkdir()
        rows = [
            {
                "id": f"id{index}",
                "task_id": f"problem_{index}",
                "proof_solved": label == "s2" and index == 0,
                "usage": {"prompt_tokens": 100 + index, "completion_tokens": 10},
            }
            for index in range(20)
        ]
        (run_dir / "per_task.json").write_text(json.dumps(rows), encoding="utf-8")
        (run_dir / "summary.json").write_text(
            json.dumps({"status": "complete", "model": "model", "test_n": 20}),
            encoding="utf-8",
        )

    dataset = _module().load_dataset(tmp_path)

    assert [arm["label"] for arm in dataset["arms"]] == ["Blank", "S2", "Trace2Skill"]
    assert dataset["tasks"][0]["arms"]["S2"]["total_tokens"] == 110


def test_child_run_input_rejects_incomplete_run(tmp_path: Path) -> None:
    for label in ("blank", "s2", "trace2skill"):
        run_dir = tmp_path / label
        run_dir.mkdir()
        (run_dir / "per_task.json").write_text("[]", encoding="utf-8")
        (run_dir / "summary.json").write_text(
            json.dumps({"status": "running", "model": "model", "test_n": 20}),
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="not complete"):
        _module().load_dataset(tmp_path)
