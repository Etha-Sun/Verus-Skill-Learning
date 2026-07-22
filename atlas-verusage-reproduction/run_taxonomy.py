from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from verus_self_evolve.data_layout import validate_output_path
from vendor.atlas.config import PipelineConfig, resolve_output_dir
from vendor.atlas.pipeline.check import TaxonomyChecker
from vendor.atlas.pipeline.dedup import CrossCategoryDeduplicator
from vendor.atlas.pipeline.generator import CategoryGenerator
from vendor.atlas.pipeline import pipeline as pipeline_module
from vendor.atlas.pipeline.pipeline import TaxonomyPipeline
from vendor.atlas.pipeline.prompts import DEFAULT_ROLE_DEFINITIONS
from vendor.atlas.pipeline.structure import TraceStructureExtractor
from vendor.atlas.pipeline.validate import CrossCategoryValidator
from vendor.atlas.traces.loader import load_traces
from vendor.atlas.utils import save_json


class CodexCLIClient:
    def __init__(
        self,
        model: str,
        reasoning_effort: str,
        log_dir: Path,
        timeout: int,
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.log_dir = log_dir
        self.timeout = timeout
        self.call_index = 0
        self.last_response = ""
        self.lock = threading.Lock()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def chat(self, prompt: str, system: str = "") -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        with self.lock:
            self.call_index += 1
            call_id = f"call_{self.call_index:02d}"
            with tempfile.NamedTemporaryFile(
                prefix=f"atlas_{call_id}_",
                suffix=".txt",
                dir="/tmp",
                delete=False,
            ) as handle:
                output_path = Path(handle.name)
            command = [
                "codex",
                "exec",
                "--model",
                self.model,
                "-c",
                f'model_reasoning_effort="{self.reasoning_effort}"',
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--color",
                "never",
                "-C",
                "/tmp",
                "--output-last-message",
                str(output_path),
                "-",
            ]
            try:
                result = subprocess.run(
                    command,
                    input=full_prompt,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout,
                    check=False,
                )
                response = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            except subprocess.TimeoutExpired as error:
                result = error
                response = "{}"
            finally:
                output_path.unlink(missing_ok=True)

            self.last_response = response

            stdout = getattr(result, "stdout", "") or ""
            stderr = getattr(result, "stderr", "") or ""
            return_code = getattr(result, "returncode", None)
            record = {
                "call_id": call_id,
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "prompt_chars": len(full_prompt),
                "prompt_sha256": hashlib.sha256(full_prompt.encode()).hexdigest(),
                "return_code": return_code,
                "response_chars": len(response),
                "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
            }
            (self.log_dir / f"{call_id}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (self.log_dir / f"{call_id}.response.txt").write_text(response, encoding="utf-8")
            (self.log_dir / f"{call_id}.stderr.txt").write_text(
                stdout + "\n" + stderr,
                encoding="utf-8",
            )
            if return_code != 0 or not response.strip():
                return "{}"
            return response


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resume_after_step3(
    pipeline: TaxonomyPipeline,
    traces: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    pipeline.domain_info = load_json(out_dir / "step1_domain_info.json")
    pipeline.structure_info = load_json(out_dir / "step2_structure_info.json")
    normalize_discovered_roles(pipeline.structure_info)
    pipeline._save_step("step2_structure_info", pipeline.structure_info)
    pipeline.trace_signals = load_json(out_dir / "step2_5_trace_signals.json")
    a_codes = load_json(out_dir / "step3_a_codes.json")["codes"]

    b_codes = CategoryGenerator(
        pipeline.client,
        pipeline.config,
        "B",
        pipeline.domain_info,
        pipeline.structure_info,
    ).generate(traces, {"category_a": a_codes})
    pipeline._save_step("step4_b_codes", {"codes": b_codes})

    c_codes = CategoryGenerator(
        pipeline.client,
        pipeline.config,
        "C",
        pipeline.domain_info,
        pipeline.structure_info,
    ).generate(traces, {"category_a": a_codes, "category_b": b_codes})
    pipeline._save_step("step5_c_codes", {"codes": c_codes})

    dedup_result = CrossCategoryDeduplicator(pipeline.client).deduplicate(
        a_codes,
        b_codes,
        c_codes,
    )
    pipeline._save_step("step6_dedup", dedup_result)
    if pipeline.config.max_codes > 0:
        total = sum(
            len(dedup_result.get(key, []))
            for key in ("category_a", "category_b", "category_c")
        )
        if total > pipeline.config.max_codes:
            dedup_result = pipeline._cap_codes(dedup_result, pipeline.config.max_codes)
            pipeline._save_step("step6_5_capped", dedup_result)

    validated = CrossCategoryValidator(
        pipeline.client,
        pipeline.structure_info,
    ).validate(
        dedup_result.get("category_a", []),
        dedup_result.get("category_b", []),
        dedup_result.get("category_c", []),
    )
    pipeline._save_step("step7_validated", validated)

    final = TaxonomyChecker(
        pipeline.client,
        pipeline.structure_info,
        pipeline.domain_info,
    ).check_and_fix(
        validated.get("category_a", []),
        validated.get("category_b", []),
        validated.get("category_c", []),
    )
    pipeline._save_step("step8_final", final)
    taxonomy = pipeline._build_taxonomy(final, len(traces))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json(taxonomy, out_dir / f"taxonomy_{timestamp}.json")
    save_json(taxonomy, out_dir / "taxonomy.json")
    pipeline._print_summary(taxonomy)
    return taxonomy


def canonical_role(value: str) -> str:
    text = value.lower()
    if any(token in text for token in ("coordinator", "orchestrat", "controller", "router")):
        return "coordinator"
    if any(token in text for token in ("checker", "verifier", "validator", "reviewer")):
        return "checker"
    if any(token in text for token in ("refiner", "repair", "specialist")):
        return "refiner"
    if any(token in text for token in ("solver", "reasoner", "generator")):
        return "solver"
    return "refiner"


def canonical_role_for_agent(agent: str, value: str) -> str:
    if agent == "Agent_RepairOrchestrator":
        return "coordinator"
    if agent.endswith("ErrorAgent") or agent == "Agent_LoopNoDecAgent":
        return "refiner"
    return canonical_role(value)


def normalize_discovered_roles(structure: dict) -> None:
    discovered = structure.get("discovered_agents", {})
    agent_to_role = {
        agent: canonical_role_for_agent(agent, role)
        for agent, role in discovered.get("agent_to_role", {}).items()
    }
    role_details: dict[str, dict] = {}
    for agent, role in agent_to_role.items():
        defaults = DEFAULT_ROLE_DEFINITIONS.get(role, {})
        bucket = role_details.setdefault(
            role,
            {
                "agents": [],
                "definition": defaults.get("definition", f"Agent with the {role} role."),
                "purpose": defaults.get("purpose", f"Perform {role} work."),
            },
        )
        bucket["agents"].append(agent)
    discovered["agent_to_role"] = agent_to_role
    discovered["role_details"] = role_details
    structure["discovered_agents"] = discovered


class CanonicalRoleTraceStructureExtractor(TraceStructureExtractor):
    def extract(self, traces: list[dict]) -> dict:
        result = super().extract(traces)
        normalize_discovered_roles(result)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the vendored ATLAS taxonomy pipeline")
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--transport", choices=("codex-cli", "openai"), default="codex-cli")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-codes", type=int, default=24)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--resume-after-step3", action="store_true")
    args = parser.parse_args()
    args.out = validate_output_path(args.out)

    config = PipelineConfig(
        model=args.model,
        timeout=args.timeout,
        max_workers=args.max_workers,
        max_codes=args.max_codes,
        traces_for_analysis=20,
        traces_per_agent=50,
        enable_parallel=True,
        save_intermediate_steps=True,
    )
    traces = load_traces(args.traces, verbose=True)
    if not traces:
        raise ValueError(f"no ATLAS traces loaded from {args.traces}")
    if args.transport == "codex-cli":
        os.environ.setdefault("OPENAI_API_KEY", "codex-cli-transport-unused")
    pipeline_module.TraceStructureExtractor = CanonicalRoleTraceStructureExtractor
    pipeline = TaxonomyPipeline(config=config, output_dir=resolve_output_dir(args.out))
    if args.transport == "codex-cli":
        client = CodexCLIClient(
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            log_dir=args.out / "codex_calls",
            timeout=args.timeout,
        )
        if args.resume_after_step3:
            existing = sorted((args.out / "codex_calls").glob("call_*.json"))
            client.call_index = len(existing)
        pipeline.client = client
    taxonomy = (
        resume_after_step3(pipeline, traces, args.out)
        if args.resume_after_step3
        else pipeline.run(traces)
    )
    summary = {
        "source": str(args.traces),
        "model": args.model,
        "transport": args.transport,
        "reasoning_effort": args.reasoning_effort,
        "counts": taxonomy.get("metadata", {}).get("counts", {}),
        "taxonomy": str(args.out / "taxonomy.json"),
    }
    (args.out / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
