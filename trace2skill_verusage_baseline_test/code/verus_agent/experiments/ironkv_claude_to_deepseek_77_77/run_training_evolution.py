#!/usr/bin/env python3
"""Run Claude-trace -> DeepSeek Trace2Skill-style success evolution.

Phase 1 performs exactly one non-retried DeepSeek request per complete training
trajectory and emits upstream-compatible Success Memory records. Phase 2 passes
the 77 records to Trace2Skill's original SuccessParallelSkillEvolver hierarchy,
with spreadsheet wording minimally adapted to the Verus domain. No abstraction
or de-specialization post-pass is applied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from openai import OpenAI

from analysis.parse_success_analysis_outputs import parse_items
from skill_evolver.parallel_success_evolving_agent import SuccessParallelSkillEvolver
from react_agent.models import OpenAIClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = Path(__file__).resolve().parent
SPLIT_ROOT = EXPERIMENT_ROOT / "split"
TRAIN_MANIFEST = SPLIT_ROOT / "train_trajectories.jsonl"
PROMPT_ROOT = EXPERIMENT_ROOT / "prompts"
SUCCESS_SYSTEM_PROMPT = PROMPT_ROOT / "success_analysis_system.txt"
SUCCESS_USER_PROMPT = PROMPT_ROOT / "success_analysis_user.txt"
NEUTRAL_SEED = (
    PROJECT_ROOT / "verus_agent/skill_evolution/neutral_seed/verus-proof-repair"
)
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env.deepseek"
DEFAULT_OUTPUT_ROOT = (
    PROJECT_ROOT / "outputs/ironkv_claude_to_deepseek_trace2skill_train77_v1"
)
DEFAULT_TEMPERATURE = 0.2
DEFAULT_ANALYSIS_MAX_TOKENS = 4096
DEFAULT_EVOLUTION_MAX_TOKENS = 8192
DEFAULT_ANALYSIS_WORKERS = 2
DEFAULT_EVOLUTION_WORKERS = 2
DEFAULT_TIMEOUT = 900.0

LOG = logging.getLogger("ironkv_trace2skill_training")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, value: dict[str, Any], lock: threading.Lock) -> None:
    line = json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def nonempty_env_value(
    cli_value: Any,
    process_name: str,
    file_values: dict[str, Any],
    default: Any = None,
) -> Any:
    if cli_value not in (None, ""):
        return cli_value
    process_value = os.environ.get(process_name)
    if process_value not in (None, ""):
        return process_value
    file_value = file_values.get(process_name)
    if file_value not in (None, ""):
        return file_value
    return default


def load_config(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    env_file = args.env_file.resolve()
    values = dict(dotenv_values(env_file)) if env_file.is_file() else {}
    secret = str(
        nonempty_env_value(None, "DEEPSEEK_API_KEY", values, "")
    ).strip()
    base_url = str(
        nonempty_env_value(args.base_url, "DEEPSEEK_BASE_URL", values, "")
    ).strip()
    model = str(
        nonempty_env_value(args.model, "DEEPSEEK_MODEL", values, "")
    ).strip()
    if not secret:
        raise ValueError("DEEPSEEK_API_KEY is empty or missing")
    if not base_url:
        raise ValueError("DEEPSEEK_BASE_URL is empty or missing")
    if not model:
        raise ValueError("DEEPSEEK_MODEL is empty or missing")
    if not 0 <= args.temperature <= 2:
        raise ValueError("temperature must be between 0 and 2")
    for label, value in (
        ("analysis_max_tokens", args.analysis_max_tokens),
        ("evolution_max_tokens", args.evolution_max_tokens),
        ("analysis_workers", args.analysis_workers),
        ("evolution_workers", args.evolution_workers),
    ):
        if value <= 0:
            raise ValueError(f"{label} must be positive")
    return (
        {
            "api_key_env_var": "DEEPSEEK_API_KEY",
            "api_key_configured": True,
            "base_url": base_url,
            "model": model,
            "temperature": args.temperature,
            "analysis_max_tokens": args.analysis_max_tokens,
            "evolution_max_tokens": args.evolution_max_tokens,
            "analysis_workers": args.analysis_workers,
            "evolution_workers": args.evolution_workers,
            "timeout_seconds": args.timeout,
            "sdk_max_retries": 0,
            "thinking_enabled": True,
            "reasoning_effort": "high",
        },
        secret,
    )


def sanitize(text: str, secret: str) -> str:
    return text.replace(secret, "[REDACTED]") if secret else text


def credential_audit(root: Path, secret: str) -> dict[str, Any]:
    hits: list[str] = []
    if secret:
        marker = secret.encode("utf-8")
        for path in sorted(root.rglob("*")):
            if path.is_file() and marker in path.read_bytes():
                hits.append(str(path.relative_to(root)))
    return {"credential_value_absent": not hits, "files_with_credential": hits}


def expected_manifest(config: dict[str, Any]) -> dict[str, Any]:
    train_rows = load_jsonl(TRAIN_MANIFEST)
    return {
        "experiment": "ironkv_claude_teacher_to_deepseek_trace2skill_train77",
        "protocol": "Trace2Skill success analysis -> MAP -> hierarchical REDUCE -> TRANSLATE -> APPLY -> VALIDATE",
        "created_at": utc_now(),
        "status": "prepared",
        "train_manifest": str(TRAIN_MANIFEST.resolve()),
        "train_manifest_sha256": sha256_file(TRAIN_MANIFEST),
        "train_count": len(train_rows),
        "heldout_inputs_used": False,
        "teacher": "claude-sonnet-4.5 successful trajectories",
        "student_and_evolution_model": config["model"],
        "skill_mode": "creation_from_neutral_llm-parametric-style_seed",
        "post_consolidation_despecialization": False,
        "configuration": config,
        "analysis": {
            "one_complete_trajectory_per_request": True,
            "max_success_memory_items": 3,
            "automatic_http_retries": 0,
        },
        "evolution": {
            "upstream_class": "SuccessParallelSkillEvolver",
            "batch_size": 1,
            "merge_batch_size": 5,
            "max_merge_levels": 5,
            "max_skill_lines": 500,
            "max_references": 5,
            "max_verification_rounds": 3,
            "patch_pipeline": "json",
            "translation_skipped": False,
            "json_format_self_fix": True,
            "continuation_and_format_fix_are_counted_as_new_requests": True,
        },
    }


def prepare_output(output_root: Path, config: dict[str, Any], resume: bool) -> None:
    manifest_path = output_root / "run_manifest.json"
    if output_root.exists():
        if not resume:
            raise FileExistsError(
                f"output root already exists; use --resume for this exact run: {output_root}"
            )
        if not manifest_path.is_file():
            raise ValueError("resume output has no run_manifest.json")
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        if current.get("train_manifest_sha256") != sha256_file(TRAIN_MANIFEST):
            raise ValueError("resume train manifest hash mismatch")
        if current.get("configuration") != config:
            raise ValueError("resume configuration mismatch")
        return

    if len(load_jsonl(TRAIN_MANIFEST)) != 77:
        raise ValueError("frozen train manifest must contain exactly 77 tasks")
    output_root.mkdir(parents=True)
    (output_root / "configuration").mkdir()
    shutil.copy2(TRAIN_MANIFEST, output_root / "configuration/train_trajectories.snapshot.jsonl")
    shutil.copy2(SPLIT_ROOT / "split_manifest.json", output_root / "configuration/split_manifest.snapshot.json")
    shutil.copy2(SPLIT_ROOT / "leakage_audit.json", output_root / "configuration/leakage_audit.snapshot.json")
    shutil.copy2(SUCCESS_SYSTEM_PROMPT, output_root / "configuration/success_analysis_system.txt")
    shutil.copy2(SUCCESS_USER_PROMPT, output_root / "configuration/success_analysis_user.txt")
    write_json(manifest_path, expected_manifest(config))


def validate_success_items(items: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not 1 <= len(items) <= 3:
        errors.append(f"expected 1..3 success memories, found {len(items)}")
    for index, item in enumerate(items, start=1):
        for field in ("title", "description", "content"):
            if not str(item.get(field, "")).strip():
                errors.append(f"item {index} has empty {field}")
    return not errors, errors


class RequestLedger:
    def __init__(self, path: Path, secret: str) -> None:
        self.path = path
        self.secret = secret
        self.lock = threading.Lock()
        self.counter_lock = threading.Lock()
        self.counter = len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0

    def next_index(self) -> int:
        with self.counter_lock:
            self.counter += 1
            return self.counter

    def record(self, event: dict[str, Any]) -> None:
        safe = json.loads(sanitize(json.dumps(event), self.secret))
        append_jsonl(self.path, safe, self.lock)


def response_usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    completion_details = getattr(usage, "completion_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
    }


def analyze_one(
    row: dict[str, Any],
    output_root: Path,
    config: dict[str, Any],
    secret: str,
    ledger: RequestLedger,
) -> tuple[str, bool, str]:
    task_id = row["task_id"]
    task_dir = output_root / "success_analysis" / task_id
    task_dir.mkdir(parents=True, exist_ok=False)
    trajectory_path = Path(row["trajectory_path"])
    raw_bytes = trajectory_path.read_bytes()
    if sha256_bytes(raw_bytes) != row["trajectory_sha256"]:
        raise ValueError(f"trajectory hash changed before request: {task_id}")
    raw_log = raw_bytes.decode("utf-8", errors="replace")
    system_prompt = SUCCESS_SYSTEM_PROMPT.read_text(encoding="utf-8")
    user_template = SUCCESS_USER_PROMPT.read_text(encoding="utf-8")
    if user_template.count("{agent_log}") != 1:
        raise ValueError("success user template must contain {agent_log} exactly once")
    user_prompt = user_template.replace("{agent_log}", raw_log)
    request_index = ledger.next_index()
    request_manifest = {
        "request_index": request_index,
        "phase": "success_analysis",
        "task_id": task_id,
        "trajectory_path": str(trajectory_path),
        "trajectory_sha256": row["trajectory_sha256"],
        "trajectory_bytes": len(raw_bytes),
        "trajectory_lines": row["trajectory_lines"],
        "complete_trajectory_included": True,
        "trajectory_template_occurrences": 1,
        "system_prompt_chars": len(system_prompt),
        "user_prompt_chars": len(user_prompt),
        "model": config["model"],
        "base_url": config["base_url"],
        "temperature": config["temperature"],
        "max_output_tokens": config["analysis_max_tokens"],
        "api_key_env_var": config["api_key_env_var"],
        "api_key_configured": True,
        "sdk_max_retries": 0,
        "thinking_enabled": True,
        "reasoning_effort": "high",
        "started_at": utc_now(),
    }
    write_json(task_dir / "request_manifest.json", request_manifest)
    (task_dir / "system_prompt.txt").write_text(system_prompt, encoding="utf-8")
    (task_dir / "user_prompt.txt").write_text(user_prompt, encoding="utf-8")
    started = time.monotonic()
    event = {
        "request_index": request_index,
        "phase": "success_analysis",
        "task_id": task_id,
        "started_at": request_manifest["started_at"],
        "sdk_max_retries": 0,
    }
    try:
        client = OpenAI(
            api_key=secret,
            base_url=config["base_url"],
            timeout=config["timeout_seconds"],
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config["temperature"],
            max_tokens=config["analysis_max_tokens"],
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        raw_response = response.model_dump(mode="json")
        write_json(task_dir / "raw_response.json", raw_response)
        response_text = response.choices[0].message.content or ""
        (task_dir / "response_text.md").write_text(response_text, encoding="utf-8")
        usage = response_usage(response)
        write_json(task_dir / "usage.json", usage)
        items = parse_items(response_text)
        valid, validation_errors = validate_success_items(items)
        write_json(
            task_dir / "validation.json",
            {"valid": valid, "errors": validation_errors, "item_count": len(items)},
        )
        if valid:
            write_json(
                task_dir / "record.json",
                {
                    "instance_id": task_id,
                    "source_file": trajectory_path.name,
                    "items": items,
                },
            )
        else:
            write_json(
                task_dir / "error.json",
                {"type": "response_validation_error", "errors": validation_errors},
            )
        event.update(
            {
                "status": "success" if valid else "invalid_response",
                "model_returned": getattr(response, "model", None),
                **usage,
            }
        )
        return task_id, valid, "ok" if valid else "; ".join(validation_errors)
    except Exception as exc:
        safe_error = sanitize(str(exc), secret)
        write_json(
            task_dir / "error.json",
            {"type": "api_or_transport_error", "error": safe_error},
        )
        event.update({"status": "error", "error": safe_error})
        return task_id, False, safe_error
    finally:
        event["latency_seconds"] = round(time.monotonic() - started, 6)
        ledger.record(event)


def analysis_status(output_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid: list[str] = []
    invalid: list[str] = []
    pending: list[str] = []
    for row in rows:
        task_dir = output_root / "success_analysis" / row["task_id"]
        validation_path = task_dir / "validation.json"
        if validation_path.is_file():
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            (valid if validation.get("valid") else invalid).append(row["task_id"])
        elif (task_dir / "error.json").is_file():
            invalid.append(row["task_id"])
        else:
            pending.append(row["task_id"])
    return {
        "total": len(rows),
        "valid": len(valid),
        "invalid": len(invalid),
        "pending": len(pending),
        "valid_task_ids": valid,
        "invalid_task_ids": invalid,
        "pending_task_ids": pending,
        "updated_at": utc_now(),
    }


def run_analysis(
    output_root: Path,
    config: dict[str, Any],
    secret: str,
    max_new: int | None,
) -> dict[str, Any]:
    rows = load_jsonl(TRAIN_MANIFEST)
    status = analysis_status(output_root, rows)
    if status["invalid"]:
        LOG.error("Existing invalid analysis records block automatic retry: %d", status["invalid"])
        write_json(output_root / "analysis_summary.json", status)
        return status
    pending_ids = set(status["pending_task_ids"])
    pending_rows = [row for row in rows if row["task_id"] in pending_ids]
    if max_new is not None:
        pending_rows = pending_rows[:max_new]
    ledger = RequestLedger(output_root / "api_requests.jsonl", secret)
    LOG.info(
        "Success analysis: total=%d valid=%d pending_now=%d workers=%d",
        len(rows), status["valid"], len(pending_rows), config["analysis_workers"],
    )
    if pending_rows:
        with ThreadPoolExecutor(max_workers=config["analysis_workers"]) as executor:
            futures = {
                executor.submit(analyze_one, row, output_root, config, secret, ledger): row["task_id"]
                for row in pending_rows
            }
            for future in as_completed(futures):
                task_id, valid, message = future.result()
                LOG.info("analysis task=%s valid=%s result=%s", task_id, valid, message)
                write_json(output_root / "analysis_summary.json", analysis_status(output_root, rows))
    final = analysis_status(output_root, rows)
    write_json(output_root / "analysis_summary.json", final)
    return final


def native_verus_map_prompt(text: str) -> str:
    """Apply domain-only substitutions to the upstream success MAP prompt."""
    replacements = {
        "spreadsheet skill folder": "Verus proof-repair skill folder",
        "spreadsheet\nskill folder": "Verus proof-repair\nskill folder",
        "- **recalc.py** — helper script (protected, never modify)\n- **LICENSE.txt** — license file (protected, never modify)": (
            "- **scripts/** — optional deterministic proof-support tools\n"
            "- **assets/** — optional static resources"
        ),
        "exact API pattern": "exact Verus proof pattern",
        "exact API": "exact Verus proof construct",
        "Read back the edited range and confirm the values before saving": (
            "Run Verus after the proof edit and confirm the resulting obligation or success"
        ),
        "formula-validation-patterns.md": "proof-validation-patterns.md",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


class PersistentAuditedClient(OpenAIClient):
    def __init__(self, *, secret: str, ledger: RequestLedger, **kwargs: Any) -> None:
        self._secret = secret
        self._ledger = ledger
        super().__init__(api_key=secret, use_cache=False, retry_times=(), **kwargs)
        self._client.close()
        client_kwargs: dict[str, Any] = {
            "api_key": secret,
            "timeout": kwargs.get("timeout", DEFAULT_TIMEOUT),
            "max_retries": 0,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = OpenAI(**client_kwargs)
        self._async_client_kwargs = dict(client_kwargs)

    def _send_request_with_retry(self, messages: list[dict], config: dict):
        request_index = self._ledger.next_index()
        started = time.monotonic()
        event: dict[str, Any] = {
            "request_index": request_index,
            "phase": "skill_evolution",
            "started_at": utc_now(),
            "message_count": len(messages),
            "sdk_max_retries": 0,
            "wrapper_retry_attempts": 0,
        }
        try:
            response = self._client.chat.completions.create(
                model=self.model, messages=messages, **config
            )
            event.update(
                {
                    "status": "success",
                    "model_returned": getattr(response, "model", None),
                    **response_usage(response),
                }
            )
            return response
        except Exception as exc:
            safe_error = sanitize(str(exc), self._secret)
            event.update({"status": "error", "error": safe_error})
            raise RuntimeError(safe_error) from None
        finally:
            event["latency_seconds"] = round(time.monotonic() - started, 6)
            self._ledger.record(event)


class NativeStyleVerusSuccessEvolver(SuccessParallelSkillEvolver):
    """Upstream success hierarchy with only spreadsheet->Verus wording changes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._map_system_prompt = native_verus_map_prompt(self._map_system_prompt)
        self._map_patterns_system_prompt = native_verus_map_prompt(
            self._map_patterns_system_prompt
        )


def collect_records(output_root: Path) -> list[dict[str, Any]]:
    rows = load_jsonl(TRAIN_MANIFEST)
    records: list[dict[str, Any]] = []
    for row in rows:
        path = output_root / "success_analysis" / row["task_id"] / "record.json"
        if not path.is_file():
            raise ValueError(f"missing valid success record: {row['task_id']}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if len(records) != 77:
        raise ValueError(f"expected 77 success records, found {len(records)}")
    return records


def run_evolution(
    output_root: Path, config: dict[str, Any], secret: str
) -> None:
    evolution_root = output_root / "evolution"
    completion = evolution_root / "evolution_summary.json"
    if completion.is_file():
        LOG.info("Evolution already completed; refusing to run it twice")
        return
    if evolution_root.exists():
        raise FileExistsError(
            "partial evolution directory exists; refusing an automatic paid rerun"
        )
    skill_dir = evolution_root / "skill/verus-proof-repair"
    intermediates = evolution_root / "intermediates"
    skill_dir.parent.mkdir(parents=True)
    shutil.copytree(NEUTRAL_SEED, skill_dir)
    intermediates.mkdir(parents=True)
    records = collect_records(output_root)
    write_json(evolution_root / "input/success_records.json", records)
    write_json(
        evolution_root / "input/input_audit.json",
        {
            "record_count": len(records),
            "success_memory_count": sum(len(record["items"]) for record in records),
            "train_manifest_sha256": sha256_file(TRAIN_MANIFEST),
            "heldout_inputs_used": False,
        },
    )
    ledger = RequestLedger(output_root / "api_requests.jsonl", secret)
    client = PersistentAuditedClient(
        secret=secret,
        ledger=ledger,
        model=config["model"],
        base_url=config["base_url"],
        generation_config={
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        },
        timeout=config["timeout_seconds"],
    )
    import skill_evolver.skill_evolving_agent as sequential_module

    quick_validate = os.environ.get("SKILL_CREATOR_VALIDATE_SCRIPT")
    if quick_validate:
        sequential_module.QUICK_VALIDATE_SCRIPT = Path(quick_validate)
    evolver = NativeStyleVerusSuccessEvolver(
        client=client,
        skill_dir=skill_dir,
        batch_size=1,
        merge_batch_size=5,
        max_workers=config["evolution_workers"],
        max_merge_levels=5,
        temperature=config["temperature"],
        max_tokens=config["evolution_max_tokens"],
        verbose=True,
        dry_run=False,
        output_dir=intermediates,
        parse_failure_dir=evolution_root / "parse_failures",
        max_skill_lines=500,
        max_references=5,
        max_verification_rounds=3,
        skip_translation=False,
        patch_pipeline="json",
        enable_json_format_self_fix=True,
    )
    configuration = evolution_root / "configuration"
    configuration.mkdir(parents=True)
    (configuration / "map_system_prompt.txt").write_text(
        evolver._map_system_prompt, encoding="utf-8"
    )
    (configuration / "merge_system_prompt.txt").write_text(
        evolver._merge_system_prompt, encoding="utf-8"
    )
    (configuration / "apply_system_prompt.txt").write_text(
        evolver._apply_system_prompt, encoding="utf-8"
    )
    (configuration / "translation_system_prompt.txt").write_text(
        evolver._translation_system_prompt, encoding="utf-8"
    )
    write_json(
        evolution_root / "evolution_manifest.json",
        {
            "status": "running",
            "started_at": utc_now(),
            "upstream_class": "SuccessParallelSkillEvolver",
            "domain_adaptation": "spreadsheet terminology replaced with Verus terminology only",
            "additional_despecialization": False,
            "seed": str(NEUTRAL_SEED.resolve()),
            "seed_sha256": sha256_tree(NEUTRAL_SEED),
            "record_count": len(records),
            "configuration": config,
        },
    )
    try:
        result = evolver.run(records, input_mode="records")
        if not result.get("edits"):
            raise RuntimeError("evolver produced no applied skill edits")
        summary = {
            "status": "completed",
            "completed_at": utc_now(),
            "map_patch_count": len(result.get("patches", [])),
            "applied_file_edit_count": len(result.get("edits", [])),
            "reasoning": result.get("reasoning", ""),
            "changelog": result.get("changelog", []),
            "estimated_upstream_llm_calls": result.get("total_llm_calls"),
            "skill_sha256": sha256_tree(skill_dir),
        }
        write_json(completion, summary)
        manifest_path = evolution_root / "evolution_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({"status": "completed", "completed_at": utc_now()})
        write_json(manifest_path, manifest)
    except Exception as exc:
        safe_error = sanitize(str(exc), secret)
        write_json(
            evolution_root / "error.json",
            {"status": "error", "occurred_at": utc_now(), "error": safe_error},
        )
        manifest_path = evolution_root / "evolution_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({"status": "error", "completed_at": utc_now()})
        write_json(manifest_path, manifest)
        raise


def update_run_manifest(output_root: Path, **values: Any) -> None:
    path = output_root / "run_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.update(values)
    write_json(path, manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("analyze", "evolve", "all"), default="all")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--analysis-max-tokens", type=int, default=DEFAULT_ANALYSIS_MAX_TOKENS)
    parser.add_argument("--evolution-max-tokens", type=int, default=DEFAULT_EVOLUTION_MAX_TOKENS)
    parser.add_argument("--analysis-workers", type=int, default=DEFAULT_ANALYSIS_WORKERS)
    parser.add_argument("--evolution-workers", type=int, default=DEFAULT_EVOLUTION_WORKERS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-new", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    config, secret = load_config(args)
    output_root = args.output_root.resolve()
    prepare_output(output_root, config, args.resume)
    if args.prepare_only:
        audit = credential_audit(output_root, secret)
        write_json(output_root / "credential_audit.json", audit)
        if not audit["credential_value_absent"]:
            raise RuntimeError("credential leakage audit failed")
        LOG.info("Prepared offline run at %s", output_root)
        return 0
    try:
        if args.phase in {"analyze", "all"}:
            status = run_analysis(output_root, config, secret, args.max_new)
            if status["invalid"]:
                update_run_manifest(output_root, status="blocked_invalid_analysis")
                return 2
            if args.phase == "all" and status["valid"] != 77:
                update_run_manifest(output_root, status="analysis_incomplete")
                return 3
        if args.phase in {"evolve", "all"}:
            status = analysis_status(output_root, load_jsonl(TRAIN_MANIFEST))
            if status["valid"] != 77 or status["invalid"]:
                raise ValueError("evolution requires exactly 77 valid success records")
            update_run_manifest(output_root, status="evolution_running")
            run_evolution(output_root, config, secret)
            update_run_manifest(output_root, status="completed", completed_at=utc_now())
    except Exception as exc:
        safe_error = sanitize(str(exc), secret)
        write_json(
            output_root / "error.json",
            {"status": "error", "occurred_at": utc_now(), "error": safe_error},
        )
        update_run_manifest(output_root, status="error", completed_at=utc_now())
        LOG.error("%s", safe_error)
        return 1
    finally:
        audit = credential_audit(output_root, secret)
        write_json(output_root / "credential_audit.json", audit)
        if not audit["credential_value_absent"]:
            LOG.error("credential leakage audit failed")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
