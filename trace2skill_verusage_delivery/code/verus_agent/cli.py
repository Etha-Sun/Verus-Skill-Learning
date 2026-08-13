from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agent import VerusProofAgent
from .client import FixedGenerationClient
from .docs import VerusDocumentation
from .usage_client import UsageTrackingOpenAIClient
from .workspace import prepare_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Trace2Skill ReAct on one Verus proof task")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--verus-bin", type=Path, required=True)
    parser.add_argument("--lynette-bin", type=Path, required=True)
    parser.add_argument("--guide-snapshot", type=Path, required=True)
    parser.add_argument("--vstd-root", type=Path, required=True)
    parser.add_argument("--model", default="qwen35-27b")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument(
        "--api-key-env-var",
        default=None,
        help="Read the credential from this environment variable instead of a CLI value",
    )
    parser.add_argument("--deepseek-thinking", action="store_true")
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--max-no-progress-turns", type=int, default=10)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--skill-dir", type=Path, default=PROJECT_ROOT / "verus_agent" / "skills" / "verus-proof-repair")
    parser.add_argument("--no-skill", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = prepare_workspace(args.input, args.work_dir)
    workspace.verus_bin = workspace._require_executable(args.verus_bin, "Verus")
    workspace.lynette_bin = workspace._require_executable(args.lynette_bin, "Lynette")
    documentation = VerusDocumentation(args.guide_snapshot, args.vstd_root)
    api_key = args.api_key
    if args.api_key_env_var:
        api_key = os.getenv(args.api_key_env_var, "").strip()
        if not api_key:
            raise ValueError(
                f"API credential is missing from environment variable {args.api_key_env_var}"
            )
    generation_config = {
        "max_tokens": args.max_output_tokens,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    }
    if args.deepseek_thinking:
        generation_config = {
            "max_tokens": args.max_output_tokens,
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
    transport_client = UsageTrackingOpenAIClient(
        model=args.model,
        api_key=api_key,
        base_url=args.base_url,
        use_cache=False,
        retry_times=(),
        generation_config=generation_config,
    )
    client = transport_client if args.deepseek_thinking else FixedGenerationClient(
        transport_client, temperature=args.temperature, max_output_tokens=args.max_output_tokens
    )
    runner = VerusProofAgent(
        client=client,
        workspace=workspace,
        documentation=documentation,
        skill_dir=None if args.no_skill else args.skill_dir,
        max_turns=args.max_turns,
        max_steps_without_material_progress=args.max_no_progress_turns,
        verbose=not args.quiet,
    )
    result = runner.run()
    usage = transport_client.usage_summary(include_requests=True)
    usage_summary = transport_client.usage_summary(include_requests=False)
    steps = result.agent_result.steps
    trace = {
        "schema_version": "1",
        "total_turns": result.agent_result.total_turns,
        "step_count": len(steps),
        "tool_action_count": sum(step.action is not None for step in steps),
        "format_error_count": sum(step.is_format_error for step in steps),
        "completion_signal_count": sum(step.is_final for step in steps),
        "steps": [
            {
                "turn": step.turn,
                "response": step.thought,
                "action": (
                    {"name": step.action.name, "arguments": step.action.arguments}
                    if step.action is not None
                    else None
                ),
                "observation": step.observation,
                "is_format_error": step.is_format_error,
                "is_final": step.is_final,
            }
            for step in steps
        ],
    }
    (workspace.root / "agent_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (workspace.root / "usage.json").write_text(
        json.dumps(usage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    payload = {
        "success": result.success,
        "turns": result.agent_result.total_turns,
        "error": None if result.success else result.agent_result.error,
        "agent_termination": {
            "success": result.agent_result.success,
            "error": result.agent_result.error,
        },
        "validation": result.validation,
        "reference_reads": result.reference_reads,
        "loop_control": result.loop_control,
        "tool_action_count": trace["tool_action_count"],
        "format_error_count": trace["format_error_count"],
        "completion_signal_count": trace["completion_signal_count"],
        "usage": usage_summary,
    }
    (workspace.root / "run_result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
