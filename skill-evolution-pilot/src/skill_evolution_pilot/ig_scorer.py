from __future__ import annotations

import json
import math
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from .workspace import sha256_file


def _external_output(path: Path) -> Path:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    path = path.resolve()
    if path == root or root not in path.parents:
        raise ValueError("InfoGain output must be below VERUS_SKILL_RUN_ROOT")
    if path.exists():
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _run(command: list[str], timeout_seconds: int = 120) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "wall_seconds": time.monotonic() - started,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def prepare_reference_manifest(
    *,
    tasks_path: Path,
    output_path: Path,
    verus_bin: Path,
    lynette_bin: Path,
) -> dict[str, Any]:
    output_path = _external_output(output_path)
    tasks = _jsonl(tasks_path)
    if len(tasks) != 4:
        raise ValueError("InfoGain pilot requires exactly four tasks")
    rows = []
    for task in tasks:
        source = Path(task["source"]).resolve()
        if sha256_file(source) != task["source_sha256"]:
            raise ValueError(f"source hash changed for {task['task_id']}")
        project_root = source.parent.parent
        historical_candidates = sorted(
            path.resolve()
            for path in project_root.glob(f"**/{source.name}")
            if path.resolve() != source
            and "unverified" not in path.relative_to(project_root).parts
        )
        h0_candidate = Path(task["h0_run_dir"]) / "workspace" / "candidate.rs"
        candidates = []
        if h0_candidate.is_file():
            candidates.append(h0_candidate.resolve())
        candidates.extend(
            candidate
            for candidate in historical_candidates
            if candidate not in candidates
        )
        screened = []
        selected: tuple[Path, dict[str, Any], dict[str, Any]] | None = None
        for candidate in candidates:
            verus = _run([str(verus_bin.resolve()), str(candidate)])
            lynette = _run(
                [
                    str(lynette_bin.resolve()),
                    "compare",
                    "-t",
                    str(source),
                    str(candidate),
                ]
            )
            valid = verus["returncode"] == 0 and lynette["returncode"] == 0
            screened.append(
                {
                    "candidate": str(candidate),
                    "candidate_sha256": sha256_file(candidate),
                    "verus_returncode": verus["returncode"],
                    "lynette_returncode": lynette["returncode"],
                    "valid": valid,
                }
            )
            if valid:
                selected = (candidate, verus, lynette)
                break
        if selected is None:
            raise ValueError(f"no current-valid reference found for {task['task_id']}")
        reference, verus, lynette = selected
        row = {
            "task_id": task["task_id"],
            "source": str(source),
            "source_sha256": sha256_file(source),
            "reference": str(reference),
            "reference_sha256": sha256_file(reference),
            "reference_bytes": reference.stat().st_size,
            "verus": verus,
            "lynette": lynette,
            "screened_candidates": screened,
            "valid": verus["returncode"] == 0 and lynette["returncode"] == 0,
        }
        rows.append(row)
    manifest = {
        "schema_version": "1",
        "selection_rule": (
            "current H0 final candidate first, then lexicographically sorted "
            "same-name historical candidates outside unverified*; select the "
            "first that passes current Verus and Lynette"
        ),
        "reference_visibility": "evaluator_only",
        "rows": rows,
        "valid": all(row["valid"] for row in rows),
    }
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


class VllmPromptScorer:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        model: str = "qwen35-27b",
        timeout_seconds: float = 1800.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            request, timeout=self.timeout_seconds
        ) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("vLLM returned a non-object response")
        return value

    def tokenize(self, text: str) -> dict[str, Any]:
        return self._post(
            "/tokenize",
            {"model": self.model, "prompt": text},
        )

    def score(
        self,
        *,
        context: str,
        target: str,
        token_output: Path,
    ) -> dict[str, Any]:
        context_tokens = self.tokenize(context)["tokens"]
        full_text = context + target
        full_tokenized = self.tokenize(full_text)
        full_tokens = full_tokenized["tokens"]
        if full_tokens[: len(context_tokens)] != context_tokens:
            raise ValueError("context tokenization is not a prefix of context+target")
        target_start = len(context_tokens)
        if target_start >= len(full_tokens):
            raise ValueError("teacher-forced target has no tokens")
        max_model_len = int(full_tokenized["max_model_len"])
        if len(full_tokens) + 1 > max_model_len:
            raise ValueError(
                f"exact sequence exceeds context: {len(full_tokens) + 1} > "
                f"{max_model_len}"
            )
        response = self._post(
            "/v1/completions",
            {
                "model": self.model,
                "prompt": full_text,
                "max_tokens": 1,
                "temperature": 0,
                "prompt_logprobs": 1,
            },
        )
        if response.get("model") != self.model:
            raise RuntimeError(f"vLLM model mismatch: {response.get('model')}")
        choice = response["choices"][0]
        prompt_logprobs = choice["prompt_logprobs"]
        if len(prompt_logprobs) != len(full_tokens):
            raise RuntimeError("prompt logprob/token length mismatch")
        token_output.parent.mkdir(parents=True, exist_ok=True)
        total = 0.0
        count = 0
        with token_output.open("w", encoding="utf-8") as handle:
            for position in range(target_start, len(full_tokens)):
                token_id = int(full_tokens[position])
                entry = prompt_logprobs[position]
                value = entry.get(str(token_id)) if isinstance(entry, dict) else None
                if not isinstance(value, dict) or not isinstance(
                    value.get("logprob"), (int, float)
                ):
                    raise RuntimeError(
                        f"actual target token missing at position {position}"
                    )
                logprob = float(value["logprob"])
                total += logprob
                count += 1
                handle.write(
                    json.dumps(
                        {
                            "target_offset": count - 1,
                            "prompt_position": position,
                            "token_id": token_id,
                            "decoded_token": value.get("decoded_token"),
                            "logprob": logprob,
                            "prob": math.exp(logprob),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return {
            "model": self.model,
            "exact_teacher_forcing": True,
            "truncated": False,
            "context_tokens": len(context_tokens),
            "target_tokens": count,
            "sequence_tokens": len(full_tokens),
            "max_model_len": max_model_len,
            "sum_logprob_nats": total,
            "avg_logprob_nats": total / count,
            "token_rows": str(token_output.resolve()),
            "token_rows_sha256": sha256_file(token_output),
        }


def proof_context(source: str, summary: str | None) -> str:
    summary_block = (
        "\nProof-repair rationale:\n" + summary.strip() + "\n"
        if summary and summary.strip()
        else ""
    )
    return (
        "Complete the following unfinished Verus source file.\n"
        "Return the complete repaired Verus source and nothing else.\n"
        "Unfinished source:\n<BEGIN_UNFINISHED_VERUS>\n"
        + source
        + "\n<END_UNFINISHED_VERUS>\n"
        + summary_block
        + "<BEGIN_COMPLETE_VERUS>\n"
    )


def run_scorer_gate(
    *,
    reference_manifest_path: Path,
    out_dir: Path,
    scorer: VllmPromptScorer | None = None,
) -> dict[str, Any]:
    out_dir = _external_output(out_dir)
    out_dir.mkdir()
    manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("valid"):
        raise ValueError("reference manifest is not valid")
    scorer = scorer or VllmPromptScorer()
    rows = []
    for task in manifest["rows"]:
        source = Path(task["source"]).read_text(encoding="utf-8")
        target = Path(task["reference"]).read_text(encoding="utf-8")
        scores = []
        for repeat in (1, 2):
            score = scorer.score(
                context=proof_context(source, None),
                target=target,
                token_output=out_dir
                / "tokens"
                / f"{task['task_id']}-baseline-repeat-{repeat}.jsonl",
            )
            scores.append(score)
        delta = scores[1]["sum_logprob_nats"] - scores[0]["sum_logprob_nats"]
        rows.append(
            {
                "task_id": task["task_id"],
                "repeat_1": scores[0],
                "repeat_2": scores[1],
                "repeat_delta_nats": delta,
                "reproducible": abs(delta) <= 1e-6,
            }
        )
    summary = {
        "schema_version": "1",
        "reference_manifest": str(reference_manifest_path.resolve()),
        "model": scorer.model,
        "baseline_rows": rows,
        "all_exact": all(
            row["repeat_1"]["exact_teacher_forcing"]
            and row["repeat_2"]["exact_teacher_forcing"]
            for row in rows
        ),
        "all_fit_context": all(
            not row["repeat_1"]["truncated"] and not row["repeat_2"]["truncated"]
            for row in rows
        ),
        "all_reproducible": all(row["reproducible"] for row in rows),
    }
    summary["valid"] = bool(
        summary["all_exact"]
        and summary["all_fit_context"]
        and summary["all_reproducible"]
    )
    (out_dir / "gate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def score_information_gain_round(
    *,
    reference_manifest_path: Path,
    gate_summary_path: Path,
    meta_output_path: Path,
    jobs_path: Path,
    out_dir: Path,
    scorer: VllmPromptScorer | None = None,
) -> dict[str, Any]:
    out_dir = _external_output(out_dir)
    out_dir.mkdir()
    manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
    gate = json.loads(gate_summary_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_output_path.read_text(encoding="utf-8"))
    if not gate.get("valid"):
        raise ValueError("InfoGain scorer gate is not valid")
    if meta.get("objective") != "information_gain":
        raise ValueError("meta output is not for information_gain")
    scorer = scorer or VllmPromptScorer()
    task_by_id = {row["task_id"]: row for row in manifest["rows"]}
    baseline_by_id = {
        row["task_id"]: row["repeat_1"] for row in gate["baseline_rows"]
    }
    skill_by_id = {skill["skill_id"]: skill for skill in meta["skills"]}
    rows = []
    for job in _jsonl(jobs_path):
        result_dir = Path(job["out_dir"])
        result = json.loads(
            (result_dir / "result.json").read_text(encoding="utf-8")
        )
        if not result.get("fidelity", {}).get("f3"):
            raise ValueError(f"non-F3 InfoGain trajectory: {result_dir}")
        task = task_by_id[job["task_id"]]
        source = Path(task["source"]).read_text(encoding="utf-8")
        target = Path(task["reference"]).read_text(encoding="utf-8")
        skill = skill_by_id[job["skill_id"]]
        post = (result_dir / "last_message.txt").read_text(encoding="utf-8")
        condition_scores = {}
        for phase, summary in (("pre", skill["content"]), ("post", post)):
            score = scorer.score(
                context=proof_context(source, summary),
                target=target,
                token_output=out_dir
                / "tokens"
                / f"{job['skill_id']}--{job['task_id']}--{phase}.jsonl",
            )
            baseline = baseline_by_id[job["task_id"]]
            delta_nats = score["sum_logprob_nats"] - baseline["sum_logprob_nats"]
            condition_scores[phase] = {
                **score,
                "ig_nats": delta_nats,
                "ig_bits": delta_nats / math.log(2),
                "ig_bits_per_target_token": delta_nats
                / math.log(2)
                / score["target_tokens"],
            }
        rows.append(
            {
                "task_id": job["task_id"],
                "skill_id": job["skill_id"],
                "skill_profile": job["skill_profile"],
                "solver_status": result["status"],
                "pre": condition_scores["pre"],
                "post": condition_scores["post"],
            }
        )
    aggregates = {}
    for skill_id in skill_by_id:
        selected = [row for row in rows if row["skill_id"] == skill_id]
        aggregates[skill_id] = {
            "runs": len(selected),
            "mean_ig_pre_bits": sum(row["pre"]["ig_bits"] for row in selected)
            / len(selected),
            "mean_ig_post_bits": sum(row["post"]["ig_bits"] for row in selected)
            / len(selected),
            "mean_ig_pre_bits_per_token": sum(
                row["pre"]["ig_bits_per_target_token"] for row in selected
            )
            / len(selected),
            "mean_ig_post_bits_per_token": sum(
                row["post"]["ig_bits_per_target_token"] for row in selected
            )
            / len(selected),
        }
    summary = {
        "schema_version": "1",
        "objective": "information_gain",
        "model": scorer.model,
        "run_count": len(rows),
        "all_exact": all(
            row[phase]["exact_teacher_forcing"]
            for row in rows
            for phase in ("pre", "post")
        ),
        "aggregates": aggregates,
        "rows": rows,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
