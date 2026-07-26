from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .events import EventLog
from .redaction import redact, redact_text


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.6-27b"
SOLVER_TEMPERATURE = 0.2
META_TEMPERATURE = 0.7
PREFLIGHT_TEMPERATURE = 0.0


class OpenRouterError(RuntimeError):
    def __init__(self, category: str, status: int | None, message: str):
        super().__init__(message)
        self.category = category
        self.status = status


def classify_status(status: int | None) -> str:
    if status in {401, 403}:
        return "authentication"
    if status == 402:
        return "no_credit"
    if status == 429:
        return "rate_limit"
    if status is not None and status >= 500:
        return "provider_transient"
    if status is not None and status >= 400:
        return "provider_request"
    return "network_or_unknown"


def normalized_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    completion_details = usage.get("completion_tokens_details")
    if not isinstance(completion_details, dict):
        completion_details = {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "cached_prompt_tokens": usage.get("cached_tokens")
        or usage.get("cached_prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": usage.get("reasoning_tokens")
        or completion_details.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cost": usage.get("cost"),
        "available": bool(usage),
    }


def _error_message(body: bytes, secret: str) -> str:
    text = body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            text = str(error.get("message") or error.get("code") or "provider error")
        elif error is not None:
            text = str(error)
    return redact_text(text, (secret,))


def _append_provider_io(
    path: Path,
    *,
    direction: str,
    request_id: str,
    payload: dict[str, Any],
    secret: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "direction": direction,
        "request_id": request_id,
        "payload": redact(payload, (secret,)),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


@dataclass
class OpenRouterClient:
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 300.0
    transport: Callable[[urllib.request.Request, float], bytes] | None = None

    def _credential(self) -> str:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise OpenRouterError(
                "credential_missing",
                None,
                "OPENROUTER_API_KEY is not present in the process environment",
            )
        return key

    def _send(self, request: urllib.request.Request) -> bytes:
        if self.transport is not None:
            return self.transport(request, self.timeout_seconds)
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            secret = self._credential()
            body = exc.read()
            raise OpenRouterError(
                classify_status(exc.code),
                exc.code,
                _error_message(body, secret),
            ) from None
        except urllib.error.URLError as exc:
            raise OpenRouterError(
                "network_or_unknown",
                None,
                redact_text(str(exc.reason), (self._credential(),)),
            ) from None

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        event_log: EventLog,
        provider_io_path: Path | None = None,
        temperature: float = SOLVER_TEMPERATURE,
        top_p: float = 1.0,
        max_tokens: int = 8,
        reasoning_effort: str = "high",
    ) -> dict[str, Any]:
        secret = self._credential()
        request_id = f"openrouter-{uuid.uuid4().hex}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "reasoning": {
                "effort": reasoning_effort,
                "exclude": False,
            },
        }
        event_log.append(
            actor="qwen",
            event_type="model_request",
            request_id=request_id,
            data={
                "transport": "openrouter",
                "url": OPENROUTER_URL,
                "headers": {
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
                "payload": payload,
            },
        )
        if provider_io_path is not None:
            _append_provider_io(
                provider_io_path,
                direction="request",
                request_id=request_id,
                payload={
                    "url": OPENROUTER_URL,
                    "headers": {
                        "Authorization": f"Bearer {secret}",
                        "Content-Type": "application/json",
                    },
                    "body": payload,
                },
                secret=secret,
            )
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            body = self._send(request)
            response = json.loads(body.decode("utf-8"))
        except OpenRouterError as exc:
            event_log.append(
                actor="qwen",
                event_type="model_response",
                request_id=request_id,
                payload_complete=False,
                data={
                    "transport": "openrouter",
                    "error_category": exc.category,
                    "status": exc.status,
                    "message": redact_text(str(exc), (secret,)),
                    "latency_seconds": time.monotonic() - started,
                    "usage": normalized_usage({}),
                },
            )
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            event_log.append(
                actor="qwen",
                event_type="model_response",
                request_id=request_id,
                payload_complete=False,
                data={
                    "transport": "openrouter",
                    "error_category": "malformed_response",
                    "message": type(exc).__name__,
                    "latency_seconds": time.monotonic() - started,
                    "usage": normalized_usage({}),
                },
            )
            raise OpenRouterError(
                "malformed_response", None, "OpenRouter returned invalid JSON"
            ) from None

        returned_model = response.get("model")
        if provider_io_path is not None:
            _append_provider_io(
                provider_io_path,
                direction="response",
                request_id=request_id,
                payload=response,
                secret=secret,
            )
        choices = response.get("choices")
        choice = choices[0] if isinstance(choices, list) and choices else {}
        message = choice.get("message") if isinstance(choice, dict) else {}
        if not isinstance(message, dict):
            message = {}
        complete = bool(returned_model and choices and message)
        event_log.append(
            actor="qwen",
            event_type="model_response",
            request_id=request_id,
            payload_complete=complete,
            data=redact(
                {
                    "transport": "openrouter",
                    "requested_model": self.model,
                    "returned_model": returned_model,
                    "finish_reason": choice.get("finish_reason")
                    if isinstance(choice, dict)
                    else None,
                    "message": message,
                    "usage": normalized_usage(response),
                    "latency_seconds": time.monotonic() - started,
                    "provider_response_id": response.get("id"),
                    "provider_response": response,
                },
                (secret,),
            ),
        )
        if returned_model != self.model:
            raise OpenRouterError(
                "model_mismatch",
                None,
                f"requested model {self.model!r}, received {returned_model!r}",
            )
        if not complete:
            raise OpenRouterError(
                "malformed_response", None, "OpenRouter response lacks model or choice"
            )
        return {
            "request_id": request_id,
            "model": returned_model,
            "message": message,
            "finish_reason": choice.get("finish_reason"),
            "usage": normalized_usage(response),
        }


def run_preflight(out_dir: Path, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    secret = os.environ.get("OPENROUTER_API_KEY", "")
    log = EventLog(out_dir / "agent_events.jsonl", "openrouter-preflight", (secret,))
    client = OpenRouterClient(model=model)
    result = client.complete(
        messages=[{"role": "user", "content": "Reply with exactly READY."}],
        event_log=log,
        provider_io_path=out_dir / "provider_io.jsonl",
        temperature=PREFLIGHT_TEMPERATURE,
        top_p=1.0,
        max_tokens=8,
    )
    summary = {
        "status": "COMPLETE",
        "requested_model": model,
        "returned_model": result["model"],
        "credential_env": "OPENROUTER_API_KEY",
        "credential_present": True,
        "usage": result["usage"],
        "finish_reason": result["finish_reason"],
    }
    (out_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
