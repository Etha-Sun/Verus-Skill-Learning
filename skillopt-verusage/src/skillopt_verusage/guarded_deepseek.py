"""Guarded, replay-safe native Responses transport for campaign teachers/optimizers."""
from __future__ import annotations

import errno
import hashlib
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Any

from skillopt_verusage.budget_guard import SharedBudgetGuard
from skillopt_verusage.budget_guard import estimate_deepseek_cost
from skillopt_verusage.codex_deepseek_bridge import BridgeConfig, forward_native_responses
from skillopt_verusage.text_context import context_admission


STORAGE_RESERVE_BYTES = 1 << 30


def check_storage(directory: Path) -> None:
    if shutil.disk_usage(directory).free < STORAGE_RESERVE_BYTES:
        raise OSError(errno.ENOSPC, "Provider evidence requires 1 GiB of free storage")
    with tempfile.TemporaryFile(dir=directory) as probe:
        probe.write(b"\0")
        probe.flush()
        os.fsync(probe.fileno())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


class BudgetMux:
    """Reserve global/method/phase caps before a request; rollback only unsent work."""

    def __init__(self, guards: list[SharedBudgetGuard], request_bound: float | None = None):
        self.guards = guards
        self.request_bound = request_bound

    def reserve(self, amount_usd: float) -> str:
        if self.request_bound is not None:
            amount_usd = self.request_bound
        reservations = []
        try:
            for guard in self.guards:
                if guard._update(lambda state: state["uncertain_requests"]):
                    raise RuntimeError("Unknown provider cost: prohibit automatic paid retry")
                reservations.append(guard.reserve(amount_usd, wait_timeout_seconds=0))
        except Exception:
            for guard, reservation in zip(self.guards, reservations):
                # No network request has been made: a cancellation is not a refund.
                guard._update(lambda state, key=reservation: state["reservations"].pop(key))
            raise
        return json.dumps(reservations)

    def settle(self, reservation_id: str, *, cost_usd, usage) -> None:
        for guard, reservation in zip(self.guards, json.loads(reservation_id)):
            guard.settle(reservation, cost_usd=cost_usd, usage=usage)


def response_text(body: bytes) -> str:
    if body.lstrip().startswith(b"{"):
        value = json.loads(body)
        response = value.get("response", value)
    else:
        events = [json.loads(line[5:].strip()) for line in body.decode().splitlines()
                  if line.startswith("data:") and line[5:].strip() not in {"", "[DONE]"}]
        response = next(row["response"] for row in reversed(events)
                        if row.get("type") == "response.completed")
    return "".join(part["text"] for item in response.get("output", [])
                   if item.get("type") == "message" for part in item.get("content", [])
                   if part.get("type") == "output_text")


class GuardedDeepSeek:
    def __init__(self, *, root: Path, api_key: str, guards: list[SharedBudgetGuard],
                 ledger: Path, output_cap: int = 16384, tokenizer_path=None, tokenizer_sha256=None):
        self.root = root
        self.api_key = api_key
        self.guards = guards
        self.ledger = ledger
        self.output_cap = output_cap
        self.tokenizer_path = tokenizer_path
        self.tokenizer_sha256 = tokenizer_sha256
        self.lock = threading.Lock()
        self.slots = threading.Semaphore(2)
        self.errors: list[str] = []

    def payload(self, *, system, user, cap=None, effort="high", response_schema=None):
        payload = {"model": "deepseek-v4-pro", "instructions": system,
                   "input": [{"role": "user", "content": [{"type": "input_text", "text": user}]}],
                   "reasoning": {"effort": effort}, "max_output_tokens": cap or self.output_cap,
                   "text": {"format": {"type": "json_object"}},
                   "stream": False}
        if response_schema is not None:
            payload["text"]["format"] = {"type":"json_schema","name":"campaign_cards",
                                          "schema":response_schema}
        return payload

    def admit(self, **kwargs):
        return context_admission(self.payload(**kwargs),tokenizer_path=self.tokenizer_path,
                                 expected_sha256=self.tokenizer_sha256)

    def _persist_error(self, directory, error, *, upstream_dispatched):
        evidence = {"type": type(error).__name__, "message": str(error),
                    "upstream_dispatched": upstream_dispatched}
        if isinstance(error, IncompleteRead) and error.partial:
            try:
                (directory / "response.partial.raw").write_bytes(error.partial)
                evidence.update(partial_body_sha256=hashlib.sha256(error.partial).hexdigest(),
                                partial_body_bytes=len(error.partial))
            except Exception:
                pass
        try:
            write_json(directory / "error.json", evidence)
        except Exception:
            # Evidence storage may be the original failure; never mask it or clear the latch.
            pass

    def call(self, *, system: str, user: str, name: str, cap: int | None = None,
             effort: str = "high", response_schema: dict | None = None) -> tuple[str, dict]:
        payload = self.payload(system=system,user=user,cap=cap,effort=effort,response_schema=response_schema)
        admission = context_admission(payload,tokenizer_path=self.tokenizer_path,expected_sha256=self.tokenizer_sha256)
        serialized = json.dumps(payload, ensure_ascii=False).encode()
        digest = hashlib.sha256(serialized).hexdigest()
        directory = self.root / name / digest
        with self.lock:
            if self.errors:
                raise RuntimeError("Prior client failure: stop new calls pending audit")
            try:
                directory.mkdir(parents=True, exist_ok=True)
                stored = directory / "validated.json"
                if stored.exists():
                    value = json.loads(stored.read_text())
                    return value["text"], value["usage"]
                if (directory / "started.json").exists():
                    raise RuntimeError(f"Previous attempt unresolved; no paid automatic replay: {name}")
                check_storage(directory)
                write_json(directory / "request.json", payload)
                write_json(directory / "context_admission.json", admission)
                write_json(directory / "started.json", {"request_sha256": digest})
            except Exception as error:
                self.errors.append(f"{name}: {type(error).__name__}")
                self._persist_error(directory, error, upstream_dispatched=False)
                raise
        with self.slots:
            with self.lock:
                if self.errors:
                    try:
                        write_json(directory/'error.json',{'type':'PriorClientFailure',
                                   'message':'Queued request cancelled before upstream dispatch',
                                   'upstream_dispatched':False})
                    except Exception:
                        pass
                    raise RuntimeError('Prior client failure: queued request cancelled without an API call')
                try:
                    check_storage(directory)
                except Exception as error:
                    self.errors.append(f"{name}: {type(error).__name__}")
                    self._persist_error(directory, error, upstream_dispatched=False)
                    raise
            # Direct calls contain text only. UTF-8 JSON bytes bound text tokens;
            # add 8192 tokens for framing and reserve at peak prices, never cache rates.
            bound = estimate_deepseek_cost({"prompt_cache_miss_tokens": len(serialized)+8192,
                        "completion_tokens":payload["max_output_tokens"]},
                        "deepseek-v4-pro", price_band="peak")
            config = BridgeConfig(model="deepseek-v4-pro", upstream_base_url="https://api.deepseek.com",
                                  api_key=self.api_key, ledger_path=self.ledger,
                                  max_output_tokens=payload["max_output_tokens"],
                                  retry_output_tokens=payload["max_output_tokens"],
                                  request_timeout_seconds=1800, native_responses=True,
                                  expected_upstream_model="deepseek-v4-pro", pricing_profile="deepseek-current",
                                  budget_guard=BudgetMux(self.guards, request_bound=bound))
            try:
                body, _, record = forward_native_responses(config, payload, task_id=name)
                (directory / "response.raw").write_bytes(body)
                text = response_text(body)
                usage = record["attempts"][0]["usage"]
                if usage["prompt_tokens"] + payload["max_output_tokens"] > 1048576:
                    raise ValueError("Observed context exceeds frozen contract")
                write_json(stored, {"text": text, "usage": usage, "record": record})
                return text, usage
            except Exception as error:
                with self.lock:
                    self.errors.append(f"{name}: {type(error).__name__}")
                self._persist_error(directory, error, upstream_dispatched=True)
                raise

    def optimizer(self, *, system, user, stage="optimizer", max_completion_tokens=16384,
                  retries=3, **kwargs):
        # Native algorithm retries are not authority to silently pay for another attempt.
        fingerprint = hashlib.sha256((system + user).encode()).hexdigest()
        try:
            text, usage = self.call(system=system, user=user, name=stage + "/" + fingerprint,
                             cap=min(max_completion_tokens, self.output_cap))
            value = json.loads(text)
            required = "patch" if stage=="analyst" else "selected_indices" if stage=="ranking" else "edits"
            if not isinstance(value,dict) or required not in value:
                raise ValueError("Native optimizer response schema mismatch: " + stage)
        except Exception:
            with self.lock:
                self.errors.append("Native optimizer failure: " + stage)
            raise
        return text,usage
