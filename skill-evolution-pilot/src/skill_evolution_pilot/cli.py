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
from .ig_scorer import (
    prepare_reference_manifest,
    run_scorer_gate,
    score_information_gain_round,
)
from .meta_agent import (
    reaudit_token_meta_agent,
    run_information_gain_meta_agent,
    run_small_model_meta_agent,
    run_token_meta_agent,
)
from .openrouter_adapter import DEFAULT_MODEL, run_preflight
from .qwen_runner import run_qwen_agentic_smoke
from .qwen_batch import prepare_qwen_jobs, run_qwen_batch
from .redaction import secret_match_count
from .token_ledger import aggregate_ledgers, build_run_ledger, write_ledger
from .token_compare import write_token_comparison
from .token_matrix import write_token_matrix_summary
from .verusage_transcript import render_verusage_transcript


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
    render_log = commands.add_parser("render-verusage-log")
    render_log.add_argument("--run-dir", type=Path, required=True)
    render_log.add_argument("--output", type=Path, required=True)
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
    qwen_smoke = commands.add_parser("qwen-agentic-smoke")
    qwen_smoke.add_argument("--source", type=Path, required=True)
    qwen_smoke.add_argument("--out-dir", type=Path, required=True)
    qwen_smoke.add_argument("--verus-bin", type=Path, required=True)
    qwen_smoke.add_argument("--lynette-bin", type=Path, required=True)
    qwen_smoke.add_argument("--model", default=DEFAULT_MODEL)
    qwen_smoke.add_argument("--max-iters", type=int, default=6)
    qwen_smoke.add_argument("--max-tokens", type=int, default=8192)
    qwen_smoke.add_argument("--skill-file", type=Path)
    qwen_smoke.add_argument("--provider-timeout-seconds", type=float, default=180.0)
    prepare_qwen = commands.add_parser("prepare-qwen-batch")
    prepare_qwen.add_argument("--tasks", type=Path, required=True)
    prepare_qwen.add_argument("--out-root", type=Path, required=True)
    prepare_qwen.add_argument("--output", type=Path, required=True)
    prepare_qwen.add_argument("--meta-output", type=Path)
    qwen_batch = commands.add_parser("run-qwen-batch")
    qwen_batch.add_argument("--jobs", type=Path, required=True)
    qwen_batch.add_argument("--summary", type=Path, required=True)
    qwen_batch.add_argument("--verus-bin", type=Path, required=True)
    qwen_batch.add_argument("--lynette-bin", type=Path, required=True)
    qwen_batch.add_argument("--model", default=DEFAULT_MODEL)
    qwen_batch.add_argument("--max-workers", type=int, default=4)
    qwen_batch.add_argument("--max-iters", type=int, default=10)
    qwen_batch.add_argument("--max-tokens", type=int, default=8192)
    qwen_batch.add_argument("--transport-attempts", type=int, default=2)
    qwen_batch.add_argument("--provider-timeout-seconds", type=float, default=180.0)
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
    token_current = token_meta.add_mutually_exclusive_group(required=True)
    token_current.add_argument("--current-meta-skill", type=Path)
    token_current.add_argument("--current-meta-output", type=Path)
    token_meta.add_argument("--prior-run-dir", type=Path, action="append", default=[])
    token_meta.add_argument("--prior-meta-output", type=Path)
    token_meta.add_argument("--prior-summary", type=Path)
    token_meta.add_argument("--design-brief", type=Path)
    token_meta.add_argument("--forbidden-term", action="append", default=[])
    token_meta.add_argument("--model", default="gpt-5.6-sol")
    token_meta.add_argument("--reasoning-effort", default="high")
    token_meta.add_argument("--timeout-seconds", type=int, default=600)
    small_meta = commands.add_parser("small-model-meta-agent")
    small_meta.add_argument("--h0-run-dir", type=Path, action="append", required=True)
    small_meta.add_argument("--out-dir", type=Path, required=True)
    small_meta.add_argument("--codex-bin", type=Path, required=True)
    small_current = small_meta.add_mutually_exclusive_group(required=True)
    small_current.add_argument("--current-meta-skill", type=Path)
    small_current.add_argument("--current-meta-output", type=Path)
    small_meta.add_argument(
        "--baseline-run-dir", type=Path, action="append", default=[]
    )
    small_meta.add_argument("--prior-run-dir", type=Path, action="append", default=[])
    small_meta.add_argument("--prior-meta-output", type=Path)
    small_meta.add_argument("--prior-summary", type=Path)
    small_meta.add_argument("--forbidden-term", action="append", default=[])
    small_meta.add_argument("--model", default="gpt-5.6-sol")
    small_meta.add_argument("--reasoning-effort", default="high")
    small_meta.add_argument("--timeout-seconds", type=int, default=600)
    ig_meta = commands.add_parser("information-gain-meta-agent")
    ig_meta.add_argument("--h0-run-dir", type=Path, action="append", required=True)
    ig_meta.add_argument("--out-dir", type=Path, required=True)
    ig_meta.add_argument("--codex-bin", type=Path, required=True)
    ig_current = ig_meta.add_mutually_exclusive_group(required=True)
    ig_current.add_argument("--current-meta-skill", type=Path)
    ig_current.add_argument("--current-meta-output", type=Path)
    ig_meta.add_argument("--prior-run-dir", type=Path, action="append", default=[])
    ig_meta.add_argument("--prior-meta-output", type=Path)
    ig_meta.add_argument("--prior-summary", type=Path)
    ig_meta.add_argument("--forbidden-term", action="append", default=[])
    ig_meta.add_argument("--model", default="gpt-5.6-sol")
    ig_meta.add_argument("--reasoning-effort", default="high")
    ig_meta.add_argument("--timeout-seconds", type=int, default=600)
    ig_references = commands.add_parser("prepare-ig-references")
    ig_references.add_argument("--tasks", type=Path, required=True)
    ig_references.add_argument("--output", type=Path, required=True)
    ig_references.add_argument("--verus-bin", type=Path, required=True)
    ig_references.add_argument("--lynette-bin", type=Path, required=True)
    ig_gate = commands.add_parser("run-ig-scorer-gate")
    ig_gate.add_argument("--reference-manifest", type=Path, required=True)
    ig_gate.add_argument("--out-dir", type=Path, required=True)
    ig_score = commands.add_parser("score-ig-round")
    ig_score.add_argument("--reference-manifest", type=Path, required=True)
    ig_score.add_argument("--gate-summary", type=Path, required=True)
    ig_score.add_argument("--meta-output", type=Path, required=True)
    ig_score.add_argument("--jobs", type=Path, required=True)
    ig_score.add_argument("--out-dir", type=Path, required=True)
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
    elif args.command == "render-verusage-log":
        result = render_verusage_transcript(
            run_dir=args.run_dir,
            output_path=args.output,
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
    elif args.command == "qwen-agentic-smoke":
        result = run_qwen_agentic_smoke(
            source=args.source,
            out_dir=args.out_dir,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
            model=args.model,
            max_iters=args.max_iters,
            max_tokens=args.max_tokens,
            skill_text=(
                args.skill_file.read_text(encoding="utf-8")
                if args.skill_file is not None
                else None
            ),
            provider_timeout_seconds=args.provider_timeout_seconds,
        )
    elif args.command == "prepare-qwen-batch":
        result = {
            "jobs": prepare_qwen_jobs(
                tasks_path=args.tasks,
                out_root=args.out_root,
                output_path=args.output,
                meta_output_path=args.meta_output,
            )
        }
    elif args.command == "run-qwen-batch":
        result = run_qwen_batch(
            jobs_path=args.jobs,
            summary_path=args.summary,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
            model=args.model,
            max_workers=args.max_workers,
            max_iters=args.max_iters,
            max_tokens=args.max_tokens,
            transport_attempts=args.transport_attempts,
            provider_timeout_seconds=args.provider_timeout_seconds,
        )
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
        current_meta_skill = (
            args.current_meta_skill.read_text(encoding="utf-8")
            if args.current_meta_skill is not None
            else json.loads(
                args.current_meta_output.read_text(encoding="utf-8")
            )["revised_meta_skill"]
        )
        result = run_token_meta_agent(
            out_dir=args.out_dir,
            h0_run_dirs=args.h0_run_dir,
            current_meta_skill=current_meta_skill,
            codex_bin=args.codex_bin,
            prior_run_dirs=args.prior_run_dir,
            prior_meta_output_path=args.prior_meta_output,
            prior_summary_path=args.prior_summary,
            design_brief_path=args.design_brief,
            forbidden_terms=args.forbidden_term,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "small-model-meta-agent":
        current_meta_skill = (
            args.current_meta_skill.read_text(encoding="utf-8")
            if args.current_meta_skill is not None
            else json.loads(
                args.current_meta_output.read_text(encoding="utf-8")
            )["revised_meta_skill"]
        )
        result = run_small_model_meta_agent(
            out_dir=args.out_dir,
            h0_run_dirs=args.h0_run_dir,
            current_meta_skill=current_meta_skill,
            codex_bin=args.codex_bin,
            baseline_run_dirs=args.baseline_run_dir,
            prior_run_dirs=args.prior_run_dir,
            prior_meta_output_path=args.prior_meta_output,
            prior_summary_path=args.prior_summary,
            forbidden_terms=args.forbidden_term,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "information-gain-meta-agent":
        current_meta_skill = (
            args.current_meta_skill.read_text(encoding="utf-8")
            if args.current_meta_skill is not None
            else json.loads(
                args.current_meta_output.read_text(encoding="utf-8")
            )["revised_meta_skill"]
        )
        result = run_information_gain_meta_agent(
            out_dir=args.out_dir,
            h0_run_dirs=args.h0_run_dir,
            current_meta_skill=current_meta_skill,
            codex_bin=args.codex_bin,
            prior_run_dirs=args.prior_run_dir,
            prior_meta_output_path=args.prior_meta_output,
            prior_summary_path=args.prior_summary,
            forbidden_terms=args.forbidden_term,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "prepare-ig-references":
        result = prepare_reference_manifest(
            tasks_path=args.tasks,
            output_path=args.output,
            verus_bin=args.verus_bin,
            lynette_bin=args.lynette_bin,
        )
    elif args.command == "run-ig-scorer-gate":
        result = run_scorer_gate(
            reference_manifest_path=args.reference_manifest,
            out_dir=args.out_dir,
        )
    elif args.command == "score-ig-round":
        result = score_information_gain_round(
            reference_manifest_path=args.reference_manifest,
            gate_summary_path=args.gate_summary,
            meta_output_path=args.meta_output,
            jobs_path=args.jobs,
            out_dir=args.out_dir,
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
