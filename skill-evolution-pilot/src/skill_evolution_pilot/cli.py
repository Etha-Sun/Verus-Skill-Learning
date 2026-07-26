from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .codex_adapter import normalize_codex_jsonl
from .batch_runner import (
    freeze_four_task_set,
    prepare_h0_jobs,
    prepare_skill_jobs,
    run_batch,
)
from .codex_runner import run_codex_smoke
from .events import EventLog, audit_events, load_events
from .meta_agent import reaudit_token_meta_agent, run_token_meta_agent
from .openrouter_adapter import DEFAULT_MODEL, run_preflight
from .redaction import secret_match_count
from .token_ledger import aggregate_ledgers, build_run_ledger, write_ledger
from .token_compare import write_token_comparison
from .token_matrix import write_token_matrix_summary


def model_free_smoke(out_dir: Path) -> dict[str, object]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    fake_secret = "canary-secret-value"
    events_path = out_dir / "agent_events.jsonl"
    log = EventLog(events_path, "model-free-smoke", (fake_secret,))
    log.append(
        actor="qwen",
        event_type="model_request",
        request_id="r1",
        data={
            "headers": {"Authorization": f"Bearer {fake_secret}"},
            "messages": [{"role": "user", "content": fake_secret}],
        },
    )
    log.append(
        actor="qwen",
        event_type="model_response",
        request_id="r1",
        data={
            "message": {"role": "assistant", "content": "edit candidate"},
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "reasoning_tokens": None,
            },
        },
    )
    log.append(
        actor="host",
        event_type="tool_call",
        tool_call_id="t1",
        candidate_sha256="a" * 64,
        data={"command": "verus candidate.rs"},
    )
    log.append(
        actor="host",
        event_type="tool_result",
        tool_call_id="t1",
        candidate_sha256="a" * 64,
        data={"exit_code": 0, "output": "1 verified, 0 errors"},
    )
    log.append(
        actor="verus",
        event_type="verifier",
        candidate_sha256="a" * 64,
        data={"passed": True},
    )
    rows, parse_errors = load_events(events_path)
    audit = audit_events(rows, parse_errors)
    audit["secret_match_count"] = secret_match_count(out_dir, (fake_secret,))
    audit["valid"] = bool(
        audit["valid_f3_event_stream"] and audit["secret_match_count"] == 0
    )
    (out_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(prog="skill-evolution-pilot")
    commands = parser.add_subparsers(dest="command", required=True)
    model_free = commands.add_parser("model-free-smoke")
    model_free.add_argument("--out-dir", type=Path)
    normalize = commands.add_parser("normalize-codex")
    normalize.add_argument("--raw-events", type=Path, required=True)
    normalize.add_argument("--normalized-events", type=Path, required=True)
    normalize.add_argument("--run-id", required=True)
    normalize.add_argument("--candidate", type=Path)
    codex_smoke = commands.add_parser("codex-smoke")
    codex_smoke.add_argument("--source", type=Path, required=True)
    codex_smoke.add_argument("--out-dir", type=Path, required=True)
    codex_smoke.add_argument("--codex-bin", type=Path, required=True)
    codex_smoke.add_argument("--verus-bin", type=Path, required=True)
    codex_smoke.add_argument("--lynette-bin", type=Path, required=True)
    codex_smoke.add_argument("--model", default="gpt-5.6-sol")
    codex_smoke.add_argument("--reasoning-effort", default="high")
    codex_smoke.add_argument("--reasoning-summary", default="detailed")
    codex_smoke.add_argument(
        "--show-raw-agent-reasoning",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    codex_smoke.add_argument("--timeout-seconds", type=int, default=600)
    preflight = commands.add_parser("openrouter-preflight")
    preflight.add_argument("--out-dir", type=Path, required=True)
    preflight.add_argument("--model", default=DEFAULT_MODEL)
    ledger = commands.add_parser("token-ledger")
    ledger.add_argument("--run-dir", type=Path, required=True)
    ledger.add_argument("--output", type=Path, required=True)
    aggregate = commands.add_parser("token-aggregate")
    aggregate.add_argument("--run-dir", type=Path, action="append", required=True)
    aggregate.add_argument("--output", type=Path, required=True)
    prepare_batch = commands.add_parser("prepare-h0-batch")
    prepare_batch.add_argument("--baseline-jobs", type=Path, required=True)
    prepare_batch.add_argument("--out-root", type=Path, required=True)
    prepare_batch.add_argument("--output", type=Path, required=True)
    prepare_batch.add_argument("--run-suffix", required=True)
    batch = commands.add_parser("run-codex-batch")
    batch.add_argument("--jobs", type=Path, required=True)
    batch.add_argument("--summary", type=Path, required=True)
    batch.add_argument("--codex-bin", type=Path, required=True)
    batch.add_argument("--verus-bin", type=Path, required=True)
    batch.add_argument("--lynette-bin", type=Path, required=True)
    batch.add_argument("--max-workers", type=int, default=3)
    batch.add_argument("--timeout-seconds", type=int, default=600)
    token_meta = commands.add_parser("token-meta-agent")
    token_meta.add_argument("--h0-run-dir", type=Path, action="append", required=True)
    token_meta.add_argument("--out-dir", type=Path, required=True)
    token_meta.add_argument("--codex-bin", type=Path, required=True)
    token_meta.add_argument("--current-meta-skill", type=Path, required=True)
    token_meta.add_argument("--model", default="gpt-5.6-sol")
    token_meta.add_argument("--reasoning-effort", default="high")
    token_meta.add_argument("--timeout-seconds", type=int, default=600)
    prepare_skills = commands.add_parser("prepare-skill-batch")
    prepare_skills.add_argument("--task-jobs", type=Path, required=True)
    prepare_skills.add_argument("--meta-output", type=Path, required=True)
    prepare_skills.add_argument("--out-root", type=Path, required=True)
    prepare_skills.add_argument("--output", type=Path, required=True)
    prepare_skills.add_argument("--iteration", required=True)
    prepare_skills.add_argument("--task-id", action="append")
    reaudit_meta = commands.add_parser("reaudit-token-meta")
    reaudit_meta.add_argument("--run-dir", type=Path, required=True)
    compare_tokens = commands.add_parser("token-compare")
    compare_tokens.add_argument("--baseline-run-dir", type=Path, required=True)
    compare_tokens.add_argument(
        "--candidate-run-dir", type=Path, action="append", required=True
    )
    compare_tokens.add_argument("--output", type=Path, required=True)
    freeze_tasks = commands.add_parser("freeze-four-task-set")
    freeze_tasks.add_argument("--three-h0-jobs", type=Path, required=True)
    freeze_tasks.add_argument("--fourth-task-id", required=True)
    freeze_tasks.add_argument("--fourth-source", type=Path, required=True)
    freeze_tasks.add_argument("--fourth-run-dir", type=Path, required=True)
    freeze_tasks.add_argument("--output", type=Path, required=True)
    freeze_tasks.add_argument(
        "--require-fourth-unsolved",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    matrix_summary = commands.add_parser("token-matrix-summary")
    matrix_summary.add_argument("--frozen-tasks", type=Path, required=True)
    matrix_summary.add_argument("--skill-jobs", type=Path, required=True)
    matrix_summary.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "model-free-smoke":
        if args.out_dir is None:
            with tempfile.TemporaryDirectory() as tmp:
                result = model_free_smoke(Path(tmp))
        else:
            result = model_free_smoke(args.out_dir)
    elif args.command == "normalize-codex":
        result = normalize_codex_jsonl(
            raw_path=args.raw_events,
            normalized_path=args.normalized_events,
            run_id=args.run_id,
            candidate_path=args.candidate,
        )
    elif args.command == "codex-smoke":
        result = run_codex_smoke(
            source=args.source,
            out_dir=args.out_dir,
            codex_bin=args.codex_bin,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            reasoning_summary=args.reasoning_summary,
            show_raw_agent_reasoning=args.show_raw_agent_reasoning,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "openrouter-preflight":
        result = run_preflight(args.out_dir, args.model)
    elif args.command == "token-ledger":
        result = write_ledger(args.run_dir, args.output)
    elif args.command == "token-aggregate":
        ledgers = [build_run_ledger(run_dir) for run_dir in args.run_dir]
        result = aggregate_ledgers(ledgers)
        if args.output.exists():
            raise ValueError(f"output already exists: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    elif args.command == "prepare-h0-batch":
        result = {
            "jobs": prepare_h0_jobs(
                baseline_jobs_path=args.baseline_jobs,
                out_root=args.out_root,
                output_path=args.output,
                run_suffix=args.run_suffix,
            )
        }
    elif args.command == "run-codex-batch":
        result = run_batch(
            jobs_path=args.jobs,
            summary_path=args.summary,
            codex_bin=args.codex_bin,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
            max_workers=args.max_workers,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "token-meta-agent":
        result = run_token_meta_agent(
            out_dir=args.out_dir,
            h0_run_dirs=args.h0_run_dir,
            current_meta_skill=args.current_meta_skill.read_text(encoding="utf-8"),
            codex_bin=args.codex_bin,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "prepare-skill-batch":
        result = {
            "jobs": prepare_skill_jobs(
                task_jobs_path=args.task_jobs,
                meta_output_path=args.meta_output,
                out_root=args.out_root,
                output_path=args.output,
                iteration=args.iteration,
                task_ids=set(args.task_id) if args.task_id else None,
            )
        }
    elif args.command == "reaudit-token-meta":
        result = reaudit_token_meta_agent(args.run_dir)
    elif args.command == "token-compare":
        result = write_token_comparison(
            args.baseline_run_dir,
            args.candidate_run_dir,
            args.output,
        )
    elif args.command == "freeze-four-task-set":
        result = {
            "tasks": freeze_four_task_set(
                three_h0_jobs_path=args.three_h0_jobs,
                fourth_task_id=args.fourth_task_id,
                fourth_source=args.fourth_source,
                fourth_run_dir=args.fourth_run_dir,
                output_path=args.output,
                require_fourth_unsolved=args.require_fourth_unsolved,
            )
        }
    else:
        result = write_token_matrix_summary(
            frozen_tasks_path=args.frozen_tasks,
            skill_jobs_path=args.skill_jobs,
            output_path=args.output,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
