"""Outcome-aware, resumable memory extraction for shared train trajectories."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from openai import OpenAI

from .shared_train import assert_below, canonical_sha256, sha256_file, write_json, write_jsonl


SUCCESS_ITEM_RE = re.compile(
    r"^#+\s+Success Memory Item\s+(\d+)\s*$", re.MULTILINE
)
FAILURE_ITEM_RE = re.compile(
    r"^#\s+(Failure Cause Item|Failure Memory Item)\s+(\d+)\s*\n"
    r"(.*?)(?=\n#\s+(?:Failure Cause Item|Failure Memory Item)\s+\d+|\Z)",
    re.MULTILINE | re.DOTALL,
)
SECTION_RE = re.compile(r"^#+\s+(Title|Description|Content)\s*$", re.MULTILINE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_response_wrappers(text: str) -> str:
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = re.sub(r"^```\w*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped


def sections(body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(body))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        found[match.group(1)] = body[match.end() : end].strip().rstrip("-_*").strip()
    return found


def parse_success_items(text: str) -> list[dict[str, Any]]:
    text = strip_response_wrappers(text)
    matches = list(SUCCESS_ITEM_RE.finditer(text))
    parsed: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        values = sections(text[match.end() : end])
        parsed.append(
            {
                "type": "success_memory",
                "number": int(match.group(1)),
                "title": values.get("Title", ""),
                "description": values.get("Description", ""),
                "content": values.get("Content", ""),
            }
        )
    return parsed


def parse_failure_items(text: str) -> list[dict[str, Any]]:
    text = strip_response_wrappers(text)
    parsed: list[dict[str, Any]] = []
    for match in FAILURE_ITEM_RE.finditer(text):
        values = sections(match.group(3))
        parsed.append(
            {
                "type": (
                    "failure_cause"
                    if match.group(1) == "Failure Cause Item"
                    else "failure_memory"
                ),
                "number": int(match.group(2)),
                "title": values.get("Title", ""),
                "description": values.get("Description", ""),
                "content": values.get("Content", ""),
            }
        )
    return parsed


def validate_items(route: str, items: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    counts = Counter(item.get("type") for item in items)
    if route == "success":
        if not 1 <= counts["success_memory"] <= 3 or len(items) != counts["success_memory"]:
            errors.append("success output must contain 1..3 Success Memory Items only")
    elif route == "failure":
        if counts["failure_cause"] < 1:
            errors.append("failure output must contain at least one Failure Cause Item")
        if not 1 <= counts["failure_memory"] <= 3:
            errors.append("failure output must contain 1..3 Failure Memory Items")
        if len(items) != counts["failure_cause"] + counts["failure_memory"]:
            errors.append("failure output contains an unsupported item type")
    else:
        errors.append(f"unsupported memory route: {route}")
    for index, item in enumerate(items, start=1):
        required = ("description", "content")
        if item.get("type") != "failure_cause":
            required = ("title", *required)
        for field in required:
            if not str(item.get(field, "")).strip():
                errors.append(f"item {index} has empty {field}")
    return errors


def response_usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "reasoning_tokens": getattr(details, "reasoning_tokens", None),
    }


def load_records(materialized_root: Path) -> list[dict[str, Any]]:
    manifest = json.loads((materialized_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("train_count") != 40:
        raise ValueError("shared train materialization is not a complete 40-task input")
    records_path = materialized_root / "records.jsonl"
    if sha256_file(records_path) != manifest.get("records_jsonl_sha256"):
        raise ValueError("materialized records hash mismatch")
    rows = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != 40:
        raise ValueError("materialized records must contain exactly 40 tasks")
    return rows


def load_config(
    env_file: Path,
    model: str | None,
    base_url: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
    workers: int,
) -> tuple[dict[str, Any], str]:
    values = dict(dotenv_values(env_file)) if env_file.is_file() else {}
    secret = str(os.environ.get("DEEPSEEK_API_KEY") or values.get("DEEPSEEK_API_KEY") or "").strip()
    selected_model = str(model or os.environ.get("DEEPSEEK_MODEL") or values.get("DEEPSEEK_MODEL") or "").strip()
    selected_base = str(base_url or os.environ.get("DEEPSEEK_BASE_URL") or values.get("DEEPSEEK_BASE_URL") or "").strip()
    if not secret or not selected_model or not selected_base:
        raise ValueError("DEEPSEEK_API_KEY, DEEPSEEK_MODEL, and DEEPSEEK_BASE_URL are required")
    if not 0 <= temperature <= 2 or max_tokens <= 0 or timeout <= 0 or workers <= 0:
        raise ValueError("invalid extraction configuration")
    return (
        {
            "api_key_env_var": "DEEPSEEK_API_KEY",
            "api_key_configured": True,
            "model": selected_model,
            "base_url": selected_base,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "timeout_seconds": timeout,
            "workers": workers,
            "sdk_max_retries": 0,
            "thinking_enabled": True,
            "reasoning_effort": "high",
        },
        secret,
    )


class Ledger:
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

    def append(self, event: dict[str, Any]) -> None:
        safe = json.loads(json.dumps(event).replace(self.secret, "[REDACTED]"))
        line = json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n"
        with self.lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()


def prepare(
    materialized_root: Path,
    output_root: Path,
    run_root: Path,
    prompt_root: Path,
    config: dict[str, Any],
    resume: bool,
) -> None:
    assert_below(output_root, run_root)
    input_manifest = materialized_root / "manifest.json"
    prompt_files = {
        route: {
            kind: prompt_root / f"{route}_{kind}.txt"
            for kind in ("system", "user")
        }
        for route in ("success", "failure")
    }
    expected = {
        "materialized_input_manifest_sha256": sha256_file(input_manifest),
        "configuration": config,
        "prompt_hashes": {
            route: {kind: sha256_file(path) for kind, path in files.items()}
            for route, files in prompt_files.items()
        },
    }
    manifest_path = output_root / "run_manifest.json"
    if output_root.exists():
        if not resume:
            raise FileExistsError(f"memory output exists; use --resume: {output_root}")
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if current.get(key) != value:
                raise ValueError(f"resume mismatch: {key}")
        return
    output_root.mkdir(parents=True)
    configuration = output_root / "configuration"
    configuration.mkdir()
    for route, files in prompt_files.items():
        for kind, path in files.items():
            (configuration / f"{route}_{kind}.txt").write_bytes(path.read_bytes())
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "created_at": utc_now(),
            "status": "prepared",
            "train_count": 40,
            "one_complete_trajectory_per_request": True,
            "candidate_code_sent_to_analyzer": False,
            "automatic_http_retries": 0,
            **expected,
        },
    )


def analyze_one(
    row: dict[str, Any],
    materialized_root: Path,
    output_root: Path,
    prompt_root: Path,
    config: dict[str, Any],
    secret: str,
    ledger: Ledger,
) -> tuple[str, bool, str]:
    task_id = row["task_id"]
    route = row["memory_route"]
    task_root = output_root / "by_task" / task_id
    task_root.mkdir(parents=True, exist_ok=False)
    trajectory = materialized_root / row["artifacts"]["trajectory"]["materialized_path"]
    if sha256_file(trajectory) != row["artifacts"]["trajectory"]["sha256"]:
        raise ValueError(f"trajectory hash mismatch before request: {task_id}")
    raw_log = trajectory.read_text(encoding="utf-8", errors="replace")
    system_prompt = (prompt_root / f"{route}_system.txt").read_text(encoding="utf-8")
    template = (prompt_root / f"{route}_user.txt").read_text(encoding="utf-8")
    if template.count("{agent_log}") != 1:
        raise ValueError(f"{route} user prompt must contain one agent_log placeholder")
    user_prompt = template.replace("{agent_log}", raw_log)
    request_index = ledger.next_index()
    started_at = utc_now()
    write_json(
        task_root / "request_manifest.json",
        {
            "request_index": request_index,
            "task_id": task_id,
            "memory_route": route,
            "claude_outcome_raw": row["claude_outcome_raw"],
            "trajectory_sha256": row["artifacts"]["trajectory"]["sha256"],
            "trajectory_bytes": row["artifacts"]["trajectory"]["size_bytes"],
            "trajectory_lines": row["artifacts"]["trajectory"]["line_count"],
            "complete_trajectory_included": True,
            "candidate_code_included": False,
            "system_prompt_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
            "user_template_sha256": sha256_file(prompt_root / f"{route}_user.txt"),
            "model": config["model"],
            "base_url": config["base_url"],
            "temperature": config["temperature"],
            "max_output_tokens": config["max_output_tokens"],
            "started_at": started_at,
        },
    )
    event: dict[str, Any] = {
        "request_index": request_index,
        "task_id": task_id,
        "memory_route": route,
        "started_at": started_at,
    }
    started = time.monotonic()
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
            max_tokens=config["max_output_tokens"],
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        write_json(task_root / "raw_response.json", response.model_dump(mode="json"))
        response_text = response.choices[0].message.content or ""
        (task_root / "response.md").write_text(response_text, encoding="utf-8")
        items = (
            parse_success_items(response_text)
            if route == "success"
            else parse_failure_items(response_text)
        )
        errors = validate_items(route, items)
        usage = response_usage(response)
        write_json(task_root / "usage.json", usage)
        write_json(task_root / "validation.json", {"valid": not errors, "errors": errors, "item_count": len(items)})
        if not errors:
            write_json(
                task_root / "record.json",
                {
                    "instance_id": task_id,
                    "source_file": "trajectory.log",
                    "record_source": "success" if route == "success" else "error",
                    "items": items,
                    "provenance": {
                        "project_code": row["project_code"],
                        "claude_outcome_raw": row["claude_outcome_raw"],
                        "memory_route": route,
                        "trajectory_sha256": row["artifacts"]["trajectory"]["sha256"],
                        "response_sha256": hashlib.sha256(response_text.encode()).hexdigest(),
                    },
                },
            )
        event.update({"status": "success" if not errors else "invalid_response", **usage})
        return task_id, not errors, "ok" if not errors else "; ".join(errors)
    except Exception as exc:
        safe_error = str(exc).replace(secret, "[REDACTED]")
        write_json(task_root / "error.json", {"type": "api_or_transport_error", "error": safe_error})
        event.update({"status": "error", "error": safe_error})
        return task_id, False, safe_error
    finally:
        event["latency_seconds"] = round(time.monotonic() - started, 6)
        ledger.append(event)


def status(rows: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    valid: list[str] = []
    invalid: list[str] = []
    pending: list[str] = []
    for row in rows:
        task_root = output_root / "by_task" / row["task_id"]
        validation_path = task_root / "validation.json"
        if validation_path.is_file():
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            (valid if validation.get("valid") is True else invalid).append(row["task_id"])
        elif (task_root / "error.json").is_file():
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


def freeze_memory_set(rows: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    success_records: list[dict[str, Any]] = []
    failure_records: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    for row in rows:
        record_path = output_root / "by_task" / row["task_id"] / "record.json"
        if not record_path.is_file():
            raise ValueError(f"missing valid memory record: {row['task_id']}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        expected = row["artifacts"]["trajectory"]["sha256"]
        if record.get("provenance", {}).get("trajectory_sha256") != expected:
            raise ValueError(f"memory provenance mismatch: {row['task_id']}")
        target = success_records if row["memory_route"] == "success" else failure_records
        target.append(record)
        provenance_rows.append(
            {
                "order": row["order"],
                "task_id": row["task_id"],
                "memory_route": row["memory_route"],
                "claude_outcome_raw": row["claude_outcome_raw"],
                "trajectory_sha256": expected,
                "record_sha256": canonical_sha256(record),
                "item_hashes": [canonical_sha256(item) for item in record["items"]],
            }
        )
    # Match the baseline normalize_mixed_records contract: error records first,
    # then success records. All organizers consume this exact frozen list.
    combined = failure_records + success_records
    write_json(output_root / "success_records.json", success_records)
    write_json(output_root / "failure_records.json", failure_records)
    write_json(output_root / "combined_records.json", combined)
    write_jsonl(output_root / "memory_provenance.jsonl", provenance_rows)
    frozen = {
        "status": "complete",
        "record_count": len(combined),
        "success_record_count": len(success_records),
        "failure_record_count": len(failure_records),
        "memory_item_count": sum(len(record["items"]) for record in combined),
        "shared_memory_set_sha256": canonical_sha256(combined),
        "memory_provenance_sha256": canonical_sha256(provenance_rows),
        "combined_records_file_sha256": sha256_file(output_root / "combined_records.json"),
    }
    write_json(output_root / "frozen_memory_set.json", frozen)
    manifest_path = output_root / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({**frozen, "completed_at": utc_now()})
    write_json(manifest_path, manifest)
    return frozen


def run(
    materialized_root: Path,
    output_root: Path,
    run_root: Path,
    prompt_root: Path,
    config: dict[str, Any],
    secret: str,
    resume: bool,
    max_new: int | None,
) -> dict[str, Any]:
    rows = load_records(materialized_root)
    prepare(materialized_root, output_root, run_root, prompt_root, config, resume)
    current = status(rows, output_root)
    if current["invalid"]:
        write_json(output_root / "analysis_status.json", current)
        return current
    pending = [row for row in rows if row["task_id"] in set(current["pending_task_ids"])]
    if max_new is not None:
        pending = pending[:max_new]
    ledger = Ledger(output_root / "api_requests.jsonl", secret)
    with ThreadPoolExecutor(max_workers=config["workers"]) as executor:
        futures = {
            executor.submit(
                analyze_one,
                row,
                materialized_root,
                output_root,
                prompt_root,
                config,
                secret,
                ledger,
            ): row["task_id"]
            for row in pending
        }
        for future in as_completed(futures):
            task_id, valid, message = future.result()
            print(f"task={task_id} valid={valid} result={message}", flush=True)
            write_json(output_root / "analysis_status.json", status(rows, output_root))
    final = status(rows, output_root)
    write_json(output_root / "analysis_status.json", final)
    if final["valid"] == 40 and not final["invalid"]:
        final["frozen_memory_set"] = freeze_memory_set(rows, output_root)
    return final


def credential_audit(root: Path, secret: str) -> dict[str, Any]:
    hits: list[str] = []
    marker = secret.encode("utf-8")
    for path in sorted(root.rglob("*")):
        if path.is_file() and marker in path.read_bytes():
            hits.append(str(path.relative_to(root)))
    result = {"credential_value_absent": not hits, "files_with_credential": hits}
    write_json(root / "credential_audit.json", result)
    return result
