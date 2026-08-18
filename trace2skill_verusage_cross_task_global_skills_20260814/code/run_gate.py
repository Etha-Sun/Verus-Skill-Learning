#!/usr/bin/env python3
"""Promote a predeclared sequence of complete skill snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from global_skill_experiment.gate import (
    CandidateSnapshot,
    CommandAggregateEvaluator,
    GateConfig,
    HeldOutGateController,
)


def _snapshot(value: dict[str, Any]) -> CandidateSnapshot:
    return CandidateSnapshot(
        candidate_id=str(value["candidate_id"]),
        skill_dir=Path(value["skill_dir"]),
        construction_method=str(value["construction_method"]),
        unit_type=str(value["unit_type"]),
        train_provenance_ids=tuple(map(str, value.get("train_provenance_ids", []))),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.config.read_text(encoding="utf-8"))
    gate_config = GateConfig.from_mapping(payload.get("held_out_gate"))

    evaluator = None
    if gate_config.enabled:
        evaluator_config = payload["evaluator"]
        evaluator = CommandAggregateEvaluator(
            argv=evaluator_config["argv"],
            output_root=Path(evaluator_config["output_root"]),
            summary_relative_path=evaluator_config.get("summary_relative_path", "summary.json"),
            timeout_seconds=evaluator_config.get("timeout_seconds"),
        )
    incumbent = _snapshot(payload["incumbent"])
    controller = HeldOutGateController(
        gate_config,
        evaluator,
        m_core_snapshot=incumbent if gate_config.enabled else None,
        history_path=Path(payload["history_path"]),
        evaluation_cache_path=(
            Path(payload["evaluation_cache_path"])
            if payload.get("evaluation_cache_path")
            else None
        ),
    )
    for candidate_payload in payload["candidates"]:
        result = controller.promote(incumbent, _snapshot(candidate_payload))
        incumbent = result.next_snapshot
        print(
            f"{candidate_payload['candidate_id']}\t"
            f"{'ACCEPT' if result.accepted else 'REJECT'}\t{result.reason}",
            flush=True,
        )
    print(f"FINAL\t{incumbent.candidate_id}\t{incumbent.skill_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
