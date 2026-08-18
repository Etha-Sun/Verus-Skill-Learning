from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from verus_agent.codex_harness.upstream_skillopt.budget_guard import (
    SharedBudgetGuard,
    estimate_deepseek_cost,
    estimate_deepseek_request_upper_bound,
)


def _append_jsonl(path: Path | None, row: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    return "\n".join(
        str(part.get("text") or part.get("output") or "")
        for part in content
        if isinstance(part, dict)
        and part.get("type")
        in {"input_text", "output_text", "text", "function_call_output"}
    )


def translate_responses_request(
    payload: dict[str, Any],
    *,
    model: str,
    max_output_tokens: int,
    allowed_tool_names: frozenset[str] | None = None,
    reasoning_by_call: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Translate the subset of Responses used by Codex into Chat Completions."""
    messages: list[dict[str, Any]] = []
    instructions = str(payload.get("instructions") or "").strip()
    if instructions:
        messages.append({"role": "system", "content": instructions})

    pending_calls: list[dict[str, Any]] = []

    def flush_calls() -> None:
        if pending_calls:
            assistant: dict[str, Any] = {
                "role": "assistant",
                "content": None,
                "tool_calls": list(pending_calls),
            }
            if reasoning_by_call:
                reasoning = next(
                    (
                        reasoning_by_call.get(str(call.get("id") or ""), "")
                        for call in pending_calls
                        if reasoning_by_call.get(str(call.get("id") or ""), "")
                    ),
                    "",
                )
                if reasoning:
                    assistant["reasoning_content"] = reasoning
            messages.append(assistant)
            pending_calls.clear()

    for item in payload.get("input") or []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "message")
        if item_type == "function_call":
            pending_calls.append(
                {
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(item.get("name") or ""),
                        "arguments": str(item.get("arguments") or "{}"),
                    },
                }
            )
            continue
        flush_calls()
        if item_type == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(item.get("call_id") or ""),
                    "content": _content_text(item.get("output")),
                }
            )
            continue
        if item_type in {"reasoning", "computer_call", "computer_call_output"}:
            continue
        role = str(item.get("role") or "user")
        if role == "developer":
            role = "system"
        messages.append({"role": role, "content": _content_text(item.get("content"))})
    flush_calls()

    tool_types: dict[str, str] = {}
    tools: list[dict[str, Any]] = []
    for tool in payload.get("tools") or []:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "")
        if not name:
            continue
        original_type = str(tool.get("type") or "function")
        if original_type != "function":
            continue
        if allowed_tool_names is not None and name not in allowed_tool_names:
            continue
        tool_types[name] = original_type
        parameters = tool.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
                "additionalProperties": False,
            }
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(tool.get("description") or ""),
                    "parameters": parameters,
                },
            }
        )

    request: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": int(payload.get("max_output_tokens") or max_output_tokens),
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    }
    if tools:
        request["tools"] = tools
        request["tool_choice"] = "auto"
        request["parallel_tool_calls"] = bool(payload.get("parallel_tool_calls", True))
    return request, tool_types


def _usage(raw: Any) -> dict[str, int]:
    value = raw if isinstance(raw, dict) else {}
    prompt = int(value.get("prompt_tokens", 0) or 0)
    completion = int(value.get("completion_tokens", 0) or 0)
    hit = int(value.get("prompt_cache_hit_tokens", 0) or 0)
    miss = int(value.get("prompt_cache_miss_tokens", max(0, prompt - hit)) or 0)
    completion_details = value.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
        "reasoning_tokens": int(completion_details.get("reasoning_tokens", 0) or 0),
        "total_tokens": int(value.get("total_tokens", prompt + completion) or 0),
    }


def responses_sse_events(
    chat_payload: dict[str, Any],
    *,
    request_model: str,
) -> list[dict[str, Any]]:
    choices = list(chat_payload.get("choices") or [])
    if not choices:
        raise RuntimeError("DeepSeek returned no choices")
    choice = choices[0]
    message = choice.get("message") or {}
    text = str(message.get("content") or "")
    tool_calls = list(message.get("tool_calls") or [])
    usage = _usage(chat_payload.get("usage"))
    response_id = f"resp_bridge_{uuid.uuid4().hex}"
    created_at = int(time.time())
    output: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    sequence = 0

    def emit(event_type: str, **values: Any) -> None:
        nonlocal sequence
        events.append({"type": event_type, "sequence_number": sequence, **values})
        sequence += 1

    response_base = {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": "in_progress",
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "max_output_tokens": None,
        "model": str(chat_payload.get("model") or request_model),
        "output": [],
        "parallel_tool_calls": True,
        "previous_response_id": None,
        "reasoning": None,
        "temperature": None,
        "text": {"format": {"type": "text"}},
        "tool_choice": "auto",
        "tools": [],
        "top_p": None,
        "truncation": "disabled",
        "usage": None,
        "user": None,
        "metadata": {},
    }
    emit("response.created", response=dict(response_base))
    emit("response.in_progress", response=dict(response_base))

    if text:
        item_id = f"msg_{uuid.uuid4().hex}"
        added = {
            "id": item_id,
            "type": "message",
            "status": "in_progress",
            "content": [],
            "role": "assistant",
        }
        output_index = len(output)
        emit("response.output_item.added", output_index=output_index, item=added)
        emit(
            "response.content_part.added",
            item_id=item_id,
            output_index=output_index,
            content_index=0,
            part={"type": "output_text", "text": "", "annotations": [], "logprobs": []},
        )
        emit(
            "response.output_text.delta",
            item_id=item_id,
            output_index=output_index,
            content_index=0,
            delta=text,
            logprobs=[],
        )
        part = {"type": "output_text", "text": text, "annotations": [], "logprobs": []}
        emit(
            "response.output_text.done",
            item_id=item_id,
            output_index=output_index,
            content_index=0,
            text=text,
            logprobs=[],
        )
        emit(
            "response.content_part.done",
            item_id=item_id,
            output_index=output_index,
            content_index=0,
            part=part,
        )
        completed = {
            "id": item_id,
            "type": "message",
            "status": "completed",
            "content": [part],
            "role": "assistant",
        }
        emit("response.output_item.done", output_index=output_index, item=completed)
        output.append(completed)

    for raw_call in tool_calls:
        function = raw_call.get("function") or {}
        call_id = str(raw_call.get("id") or f"call_{uuid.uuid4().hex}")
        name = str(function.get("name") or "")
        arguments = str(function.get("arguments") or "{}")
        item_id = f"fc_{uuid.uuid4().hex}"
        output_index = len(output)
        added = {
            "type": "function_call",
            "id": item_id,
            "status": "in_progress",
            "call_id": call_id,
            "name": name,
            "arguments": "",
        }
        emit("response.output_item.added", output_index=output_index, item=added)
        emit(
            "response.function_call_arguments.delta",
            item_id=item_id,
            output_index=output_index,
            delta=arguments,
        )
        emit(
            "response.function_call_arguments.done",
            item_id=item_id,
            output_index=output_index,
            arguments=arguments,
        )
        completed = {**added, "status": "completed", "arguments": arguments}
        emit("response.output_item.done", output_index=output_index, item=completed)
        output.append(completed)

    response_usage = {
        "input_tokens": usage["prompt_tokens"],
        "input_tokens_details": {"cached_tokens": usage["prompt_cache_hit_tokens"]},
        "output_tokens": usage["completion_tokens"],
        "output_tokens_details": {"reasoning_tokens": usage["reasoning_tokens"]},
        "total_tokens": usage["total_tokens"],
    }
    completed_response = {
        **response_base,
        "status": "completed",
        "output": output,
        "usage": response_usage,
    }
    emit("response.completed", response=completed_response)
    return events


@dataclass
class BridgeConfig:
    model: str
    upstream_base_url: str
    api_key: str
    ledger_path: Path | None
    max_output_tokens: int
    retry_output_tokens: int
    request_timeout_seconds: int
    native_responses: bool = False
    model_catalog: bytes | None = None
    budget_guard: SharedBudgetGuard | None = None
    fake_reply: str | None = None
    fake_tool_name: str | None = None
    fake_tool_arguments: str = "{}"
    allowed_tool_names: frozenset[str] = frozenset({"exec_command", "write_stdin"})
    reasoning_by_call: dict[str, str] = field(default_factory=dict)
    state_lock: threading.Lock = field(default_factory=threading.Lock)
    config_sha256: str | None = None
    ledger_lock: threading.Lock = field(default_factory=threading.Lock)
    instance_id: str | None = None


def _native_response_usage(
    body: bytes,
) -> tuple[dict[str, int] | None, str | None, str | None]:
    """Extract final usage/model/status without changing a native Responses body."""
    final_response: dict[str, Any] | None = None
    decoded = body.decode("utf-8", errors="replace")
    for line in decoded.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if event.get("type") in {"response.completed", "response.incomplete"}:
            response = event.get("response")
            if isinstance(response, dict):
                final_response = response
    if final_response is None:
        try:
            candidate = json.loads(decoded)
        except json.JSONDecodeError:
            candidate = None
        if isinstance(candidate, dict):
            final_response = candidate.get("response", candidate)
    if not isinstance(final_response, dict):
        return None, None, None
    raw = final_response.get("usage")
    if not isinstance(raw, dict):
        return None, str(final_response.get("model") or "") or None, str(
            final_response.get("status") or ""
        ) or None
    input_tokens = int(raw.get("input_tokens", 0) or 0)
    input_details = raw.get("input_tokens_details") or {}
    output_tokens = int(raw.get("output_tokens", 0) or 0)
    output_details = raw.get("output_tokens_details") or {}
    hit = int(input_details.get("cached_tokens", 0) or 0)
    usage = {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": max(0, input_tokens - hit),
        "reasoning_tokens": int(output_details.get("reasoning_tokens", 0) or 0),
        "total_tokens": int(raw.get("total_tokens", input_tokens + output_tokens) or 0),
    }
    return (
        usage,
        str(final_response.get("model") or "") or None,
        str(final_response.get("status") or "") or None,
    )


def forward_native_responses(
    config: BridgeConfig,
    payload: dict[str, Any],
    *,
    task_id: str | None = None,
) -> tuple[bytes, str, dict[str, Any]]:
    """Pass a Codex Responses request through unchanged except for frozen model id."""
    request_payload = dict(payload)
    request_payload["model"] = config.model
    started = time.monotonic()
    usage: dict[str, int] | None = None
    upstream_model: str | None = None
    response_status: str | None = None
    error_text: str | None = None
    content_type = "text/event-stream"
    body = b""
    requested_output_tokens = int(
        request_payload.get("max_output_tokens") or config.max_output_tokens
    )
    reserve = estimate_deepseek_request_upper_bound(
        requested_output_tokens, config.model
    )
    reservation_id = (
        config.budget_guard.reserve(reserve) if config.budget_guard else None
    )
    try:
        request = Request(
            config.upstream_base_url.rstrip("/") + "/responses",
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=config.request_timeout_seconds) as response:
            content_type = response.headers.get_content_type()
            body = response.read()
        usage, upstream_model, response_status = _native_response_usage(body)
        if config.budget_guard and reservation_id:
            config.budget_guard.settle(
                reservation_id,
                cost_usd=(
                    estimate_deepseek_cost(usage, config.model) if usage else None
                ),
                usage=usage,
            )
            reservation_id = None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:2000]
        error_text = f"DeepSeek HTTP {error.code}: {detail}"
        raise RuntimeError(error_text) from error
    except URLError as error:
        error_text = f"DeepSeek transport error: {error.reason}"
        raise RuntimeError(error_text) from error
    except Exception as error:
        error_text = f"{type(error).__name__}: {error}"
        raise
    finally:
        if config.budget_guard and reservation_id:
            config.budget_guard.settle(
                reservation_id, cost_usd=None, usage=None
            )
            reservation_id = None
        phase = task_id.split("--", 1)[0] if task_id and "--" in task_id else None
        attempt = {
            "retry_index": 0,
            "max_tokens": request_payload.get("max_output_tokens"),
            "finish_reason": response_status,
            "usage": usage,
            "estimated_cost_usd": (
                estimate_deepseek_cost(usage, config.model) if usage else None
            ),
            "error": error_text,
        }
        record = {
            "request_id": uuid.uuid4().hex,
            "task_id": task_id,
            "phase": phase,
            "model": config.model,
            "upstream_model": upstream_model,
            "bridge_config_sha256": config.config_sha256,
            "protocol": "native_responses_passthrough",
            "input_items": len(payload.get("input") or []),
            "tool_count": len(payload.get("tools") or []),
            "attempts": [attempt],
            "wall_seconds": time.monotonic() - started,
        }
        with config.ledger_lock:
            _append_jsonl(config.ledger_path, record)
    return body, content_type, record


def _post_chat(config: BridgeConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if config.fake_reply is not None:
        has_tool_result = any(
            message.get("role") == "tool" for message in payload.get("messages") or []
        )
        if config.fake_tool_name and not has_tool_result:
            return {
                "id": "chatcmpl-fake-tool",
                "model": config.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_fake_1",
                                    "type": "function",
                                    "function": {
                                        "name": config.fake_tool_name,
                                        "arguments": config.fake_tool_arguments,
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        return {
            "id": "chatcmpl-fake",
            "model": config.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": config.fake_reply},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    request = Request(
        config.upstream_base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config.request_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"DeepSeek HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"DeepSeek transport error: {error.reason}") from error


def forward_responses(
    config: BridgeConfig,
    payload: dict[str, Any],
    *,
    task_id: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with config.state_lock:
        chat_request, _ = translate_responses_request(
            payload,
            model=config.model,
            max_output_tokens=config.max_output_tokens,
            allowed_tool_names=config.allowed_tool_names,
            reasoning_by_call=dict(config.reasoning_by_call),
        )
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    requested_budgets = [config.max_output_tokens, config.retry_output_tokens]
    final_payload: dict[str, Any] | None = None
    for retry_index, output_tokens in enumerate(dict.fromkeys(requested_budgets)):
        chat_request["max_tokens"] = output_tokens
        reserve = estimate_deepseek_request_upper_bound(output_tokens, config.model)
        reservation_id = config.budget_guard.reserve(reserve) if config.budget_guard else None
        try:
            candidate = _post_chat(config, chat_request)
            usage = _usage(candidate.get("usage"))
            if config.budget_guard and reservation_id:
                config.budget_guard.settle(
                    reservation_id,
                    cost_usd=estimate_deepseek_cost(usage, config.model),
                    usage=usage,
                )
                reservation_id = None
            finish_reason = str(
                ((candidate.get("choices") or [{}])[0]).get("finish_reason") or ""
            )
            attempts.append(
                {
                    "retry_index": retry_index,
                    "max_tokens": output_tokens,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "estimated_cost_usd": estimate_deepseek_cost(usage, config.model),
                    "error": None,
                }
            )
            if finish_reason != "length":
                final_payload = candidate
                break
        except Exception as error:
            if config.budget_guard and reservation_id:
                config.budget_guard.settle(reservation_id, cost_usd=None, usage=None)
                reservation_id = None
            attempts.append(
                {
                    "retry_index": retry_index,
                    "max_tokens": output_tokens,
                    "finish_reason": None,
                    "usage": None,
                    "estimated_cost_usd": None,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            if retry_index + 1 >= len(requested_budgets):
                raise
            time.sleep(1)
    if final_payload is None:
        raise RuntimeError("DeepSeek response remained truncated after expanded retry")
    message = ((final_payload.get("choices") or [{}])[0]).get("message") or {}
    reasoning_content = str(message.get("reasoning_content") or "")
    if reasoning_content:
        with config.state_lock:
            for tool_call in message.get("tool_calls") or []:
                call_id = str(tool_call.get("id") or "")
                if call_id:
                    config.reasoning_by_call[call_id] = reasoning_content
    events = responses_sse_events(final_payload, request_model=config.model)
    record = {
        "request_id": uuid.uuid4().hex,
        "task_id": task_id,
        "model": config.model,
        "bridge_config_sha256": config.config_sha256,
        "input_items": len(payload.get("input") or []),
        "input_item_types": [
            str(item.get("type") or "message")
            for item in payload.get("input") or []
            if isinstance(item, dict)
        ],
        "tool_count": len(payload.get("tools") or []),
        "tools": [
            {
                "name": str(tool.get("name") or ""),
                "type": str(tool.get("type") or ""),
                "parameter_keys": sorted(
                    str(key)
                    for key in ((tool.get("parameters") or {}).get("properties") or {})
                ),
            }
            for tool in payload.get("tools") or []
            if isinstance(tool, dict)
        ],
        "attempts": attempts,
        "wall_seconds": time.monotonic() - started,
    }
    with config.ledger_lock:
        _append_jsonl(config.ledger_path, record)
    return events, record


def make_handler(config: BridgeConfig):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CodexDeepSeekBridge/1"

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def _json_error(self, status: int, message: str) -> None:
            body = json.dumps({"error": {"message": message}}).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            request_path = self.path.split("?", 1)[0].rstrip("/")
            if request_path.endswith("/models") and config.model_catalog is not None:
                body = config.model_catalog
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if request_path not in {"", "/health"}:
                self._json_error(404, "not found")
                return
            body = json.dumps(
                {
                    "status": "ok",
                    "model": config.model,
                    "instance_id": config.instance_id,
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            request_path = self.path.split("?", 1)[0].rstrip("/")
            task_id: str | None = None
            if request_path.startswith("/tasks/") and request_path.endswith(
                "/v1/responses"
            ):
                task_id = request_path[len("/tasks/") : -len("/v1/responses")]
                if not task_id or "/" in task_id or task_id in {".", ".."}:
                    self._json_error(400, "unsafe task id")
                    return
            elif request_path != "/v1/responses":
                self._json_error(404, "only /v1/responses is supported")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if config.native_responses:
                    body, content_type, _ = forward_native_responses(
                        config, payload, task_id=task_id
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                    self.wfile.flush()
                    return
                events, _ = forward_responses(config, payload, task_id=task_id)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for event in events:
                    event_type = str(event["type"])
                    data = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
                    self.wfile.write(f"event: {event_type}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception as error:
                self._json_error(502, f"{type(error).__name__}: {error}")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--upstream-base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--ledger-path", type=Path)
    parser.add_argument("--max-output-tokens", type=int, default=32768)
    parser.add_argument("--retry-output-tokens", type=int, default=131072)
    parser.add_argument("--request-timeout-seconds", type=int, default=1800)
    parser.add_argument(
        "--native-responses",
        action="store_true",
        help="transparently forward Codex Responses requests to DeepSeek /responses",
    )
    parser.add_argument("--budget-state-path", type=Path)
    parser.add_argument("--approval-limit-usd", type=float, default=20.0)
    parser.add_argument("--prior-spend-usd", type=float, default=0.0)
    parser.add_argument("--request-reserve-usd", type=float, default=0.25)
    parser.add_argument("--fake-reply")
    parser.add_argument("--fake-tool-name")
    parser.add_argument("--fake-tool-arguments", default="{}")
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--instance-id")
    parser.add_argument("--model-catalog-path", type=Path)
    parser.add_argument(
        "--allowed-tool",
        action="append",
        default=None,
        help="Codex function tool exposed to DeepSeek (repeatable)",
    )
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key and args.fake_reply is None:
        raise RuntimeError(f"{args.api_key_env} is not set")
    budget_guard = (
        SharedBudgetGuard(
            args.budget_state_path,
            approval_limit_usd=args.approval_limit_usd,
            prior_spend_usd=args.prior_spend_usd,
            optimizer_reserve_usd=0.0,
            request_reserve_usd=args.request_reserve_usd,
        )
        if args.budget_state_path
        else None
    )
    model_catalog: bytes | None = None
    model_catalog_sha256: str | None = None
    if args.model_catalog_path:
        model_catalog = args.model_catalog_path.read_bytes()
        catalog = json.loads(model_catalog.decode("utf-8"))
        slugs = {
            str(entry.get("slug") or "")
            for entry in catalog.get("models") or []
            if isinstance(entry, dict)
        }
        if args.model not in slugs:
            raise ValueError(f"model catalog does not contain {args.model}")
        model_catalog_sha256 = hashlib.sha256(model_catalog).hexdigest()
    config = BridgeConfig(
        model=args.model,
        upstream_base_url=args.upstream_base_url,
        api_key=api_key,
        ledger_path=args.ledger_path,
        max_output_tokens=args.max_output_tokens,
        retry_output_tokens=args.retry_output_tokens,
        request_timeout_seconds=args.request_timeout_seconds,
        native_responses=args.native_responses,
        model_catalog=model_catalog,
        budget_guard=budget_guard,
        fake_reply=args.fake_reply,
        fake_tool_name=args.fake_tool_name,
        fake_tool_arguments=args.fake_tool_arguments,
        allowed_tool_names=frozenset(
            args.allowed_tool or ["exec_command", "write_stdin"]
        ),
        instance_id=args.instance_id or uuid.uuid4().hex,
    )
    public_manifest = {
        "schema_version": "1",
        "model": config.model,
        "upstream_base_url": config.upstream_base_url,
        "max_output_tokens": config.max_output_tokens,
        "retry_output_tokens": config.retry_output_tokens,
        "request_timeout_seconds": config.request_timeout_seconds,
        "native_responses": config.native_responses,
        "model_catalog_sha256": model_catalog_sha256,
        "protocol": (
            "native_responses_passthrough"
            if config.native_responses
            else "responses_to_chat_completions"
        ),
        "allowed_tool_names": (
            None if config.native_responses else sorted(config.allowed_tool_names)
        ),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "instance_id": config.instance_id,
        "fake_mode": config.fake_reply is not None,
        "shared_budget_guard_enabled": config.budget_guard is not None,
        "approval_limit_usd": (
            config.budget_guard.approval_limit_usd
            if config.budget_guard is not None
            else None
        ),
        "prior_spend_usd": (
            config.budget_guard.prior_spend_usd
            if config.budget_guard is not None
            else None
        ),
        "request_reserve_usd": (
            config.budget_guard.request_reserve_usd
            if config.budget_guard is not None
            else None
        ),
    }
    config.config_sha256 = _sha256_json(public_manifest)
    public_manifest["config_sha256"] = config.config_sha256
    server = ThreadingHTTPServer((args.host, args.port), make_handler(config))
    if args.manifest_path:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(public_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"BRIDGE_READY http://{args.host}:{server.server_port}/v1 "
        f"model={args.model} config_sha256={config.config_sha256}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
