from __future__ import annotations

import json

from skillopt.gradient.reflect import fmt_minibatch_trajectories
from skillopt.optimizer.slow_update import _trajectory_path, format_comparison_text


def _write_conversation(predictions, task_id: str, size: int) -> None:
    task_dir = predictions / task_id
    task_dir.mkdir()
    (task_dir / "conversation.json").write_text(
        json.dumps([{"role": "assistant", "content": task_id * size}]),
        encoding="utf-8",
    )


def test_three_longest_trajectories_are_replaced_by_read_only_paths(
    tmp_path, monkeypatch
) -> None:
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    for task_id, size in (("short", 1), ("long_a", 20), ("long_b", 30), ("long_c", 40)):
        _write_conversation(predictions, task_id, size)

    monkeypatch.setenv("CODEX_WORKING_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("SKILLOPT_PATH_REFERENCES", "1")
    items = [
        {"id": task_id, "task_description": task_id, "task_type": "test"}
        for task_id in ("short", "long_a", "long_b", "long_c")
    ]

    rendered = fmt_minibatch_trajectories(items, str(predictions))

    assert "Read every referenced file before analyzing the minibatch" in rendered
    assert "[assistant] short" in rendered
    for task_id in ("long_a", "long_b", "long_c"):
        assert f"[assistant] {task_id}" not in rendered
        assert f"`predictions/{task_id}/conversation.json`" in rendered
    assert "`predictions/short/conversation.json`" not in rendered


def _pair(task_id: str, trajectory_size: int, category: str = "persistent_fail") -> dict:
    return {
        "id": task_id,
        "task": task_id,
        "category": category,
        "prev": {
            "hard": int(category == "stable_success"),
            "soft": float(category == "stable_success"),
            "predicted_answer": "N/A",
            "fail_reason": "",
        },
        "curr": {
            "hard": int(category == "stable_success"),
            "soft": float(category == "stable_success"),
            "predicted_answer": "N/A",
            "fail_reason": "",
        },
        "prev_trajectory": f"prev-{task_id}-" + "p" * trajectory_size,
        "curr_trajectory": f"curr-{task_id}-" + "c" * trajectory_size,
        "prev_trajectory_path": f"prev/{task_id}/conversation.json",
        "curr_trajectory_path": f"curr/{task_id}/conversation.json",
    }


def test_only_three_longest_trajectory_pairs_use_paths(monkeypatch) -> None:
    monkeypatch.setenv("SKILLOPT_PATH_REFERENCES", "1")
    pairs = [
        _pair("short", 10),
        _pair("medium", 20),
        _pair("long", 30),
        _pair("longest", 40),
        _pair("stable", 100, category="stable_success"),
    ]

    text = format_comparison_text(pairs)

    assert pairs[0]["prev_trajectory"] in text
    assert pairs[0]["curr_trajectory"] in text
    for pair in pairs[1:4]:
        assert f"`{pair['prev_trajectory_path']}`" in text
        assert f"`{pair['curr_trajectory_path']}`" in text
        assert pair["prev_trajectory"] not in text
        assert pair["curr_trajectory"] not in text
    assert pairs[4]["prev_trajectory_path"] not in text
    assert pairs[4]["prev_trajectory"] not in text


def test_trajectory_path_is_relative_to_codex_working_directory(
    tmp_path, monkeypatch
) -> None:
    rollout_dir = tmp_path / "slow_update" / "rollout_prev"
    monkeypatch.setenv("CODEX_WORKING_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("SKILLOPT_PATH_REFERENCES", "1")

    path = _trajectory_path(str(rollout_dir), "task-id")

    assert path == "slow_update/rollout_prev/predictions/task-id/conversation.json"


def test_api_optimizer_keeps_trajectories_inline(tmp_path, monkeypatch) -> None:
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    for task_id, size in (("a", 10), ("b", 20), ("c", 30), ("d", 40)):
        _write_conversation(predictions, task_id, size)
    monkeypatch.delenv("SKILLOPT_PATH_REFERENCES", raising=False)
    monkeypatch.setenv("CODEX_WORKING_DIRECTORY", str(tmp_path))

    items = [
        {"id": task_id, "task_description": task_id, "task_type": "test"}
        for task_id in ("a", "b", "c", "d")
    ]
    rendered = fmt_minibatch_trajectories(items, str(predictions))
    comparison = format_comparison_text(
        [_pair("short", 10), _pair("medium", 20), _pair("long", 30)]
    )

    assert "read-only file" not in rendered
    assert "read-only file" not in comparison
    for task_id in ("a", "b", "c", "d"):
        assert f"[assistant] {task_id}" in rendered
