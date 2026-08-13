from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from react_agent import OpenAIClient
from react_agent.models import Message, ModelSettings


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _detail_value(details: Any, name: str) -> int | None:
    if details is None:
        return None
    if isinstance(details, dict):
        return _integer(details.get(name))
    return _integer(getattr(details, name, None))


@dataclass
class TokenUsageLedger:
    requests: list[dict[str, Any]] = field(default_factory=list)

    def record_response(self, response: Any, latency_seconds: float) -> None:
        usage = getattr(response, "usage", None)
        prompt_tokens = _integer(getattr(usage, "prompt_tokens", None))
        completion_tokens = _integer(getattr(usage, "completion_tokens", None))
        total_tokens = _integer(getattr(usage, "total_tokens", None))
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)
        self.requests.append(
            {
                "request_index": len(self.requests) + 1,
                "response_id": getattr(response, "id", None),
                "model": getattr(response, "model", None),
                "created": getattr(response, "created", None),
                "latency_seconds": round(latency_seconds, 6),
                "usage_available": usage is not None,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_prompt_tokens": _detail_value(prompt_details, "cached_tokens"),
                "reasoning_tokens": _detail_value(completion_details, "reasoning_tokens"),
            }
        )

    def summary(self, include_requests: bool = True) -> dict[str, Any]:
        with_usage = [request for request in self.requests if request["usage_available"]]
        latencies = [float(request["latency_seconds"]) for request in self.requests]

        def sum_known(field: str) -> int | None:
            values = [request[field] for request in with_usage if request[field] is not None]
            return sum(values) if values else None

        models = sorted(
            {str(request["model"]) for request in self.requests if request["model"]}
        )
        result: dict[str, Any] = {
            "schema_version": "1",
            "request_count": len(self.requests),
            "requests_with_usage": len(with_usage),
            "usage_complete": bool(self.requests) and len(with_usage) == len(self.requests),
            "models_returned": models,
            "prompt_tokens": sum_known("prompt_tokens"),
            "completion_tokens": sum_known("completion_tokens"),
            "total_tokens": sum_known("total_tokens"),
            "cached_prompt_tokens": sum_known("cached_prompt_tokens"),
            "reasoning_tokens": sum_known("reasoning_tokens"),
            "latency_seconds_total": round(sum(latencies), 6),
            "latency_seconds_mean": (
                round(sum(latencies) / len(latencies), 6) if latencies else None
            ),
            "latency_seconds_max": round(max(latencies), 6) if latencies else None,
        }
        if include_requests:
            result["requests"] = list(self.requests)
        return result


class UsageTrackingOpenAIClient(OpenAIClient):
    """OpenAI-compatible client that retains provider token usage and latency."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.usage_ledger = TokenUsageLedger()

    def chat(
        self,
        messages: list[Message],
        settings: ModelSettings | None = None,
        return_reasoning: bool = False,
    ) -> str | tuple[str, str]:
        openai_messages = [{"role": message.role, "content": message.content} for message in messages]
        config = self.generation_config.copy()
        if settings:
            config.update(settings.to_dict())
        started = time.monotonic()
        response = self._send_request_with_retry(openai_messages, config)
        latency = time.monotonic() - started
        self.usage_ledger.record_response(response, latency)
        reply, reasoning_content = self._parse_response(response)
        return (reply, reasoning_content) if return_reasoning else reply

    def usage_summary(self, include_requests: bool = True) -> dict[str, Any]:
        return self.usage_ledger.summary(include_requests=include_requests)
