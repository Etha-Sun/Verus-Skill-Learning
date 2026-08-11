from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from skillopt_verusage.budget_guard import (
    SharedBudgetGuard,
    estimate_flash_cost,
    estimate_flash_request_upper_bound,
)


BEGIN = "<BEGIN_SKILLOPT_VERUSAGE_SKILL"
END = "<END_SKILLOPT_VERUSAGE_SKILL>"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _usage_dict(usage: Any) -> dict[str, int]:
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    hit = int(getattr(usage, "prompt_cache_hit_tokens", 0) or 0)
    miss_value = getattr(usage, "prompt_cache_miss_tokens", None)
    miss = int(miss_value if miss_value is not None else max(0, prompt - hit))
    details = getattr(usage, "completion_tokens_details", None)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
        "total_tokens": int(getattr(usage, "total_tokens", prompt + completion) or 0),
        "reasoning_tokens": int(getattr(details, "reasoning_tokens", 0) or 0),
    }


class SkillAwareDeepSeekLLM:
    """Drop-in VeruSAGE LLM with exact skill injection and request accounting."""

    def __init__(
        self,
        config,
        logger,
        *,
        skill_text: str,
        calls_path: Path,
        request_cap: int = 512,
        action_output_tokens: int = 32768,
        reasoning_output_tokens: int = 32768,
        retry_action_output_tokens: int = 262144,
        retry_reasoning_output_tokens: int = 262144,
        max_action_output_tokens: int = 384000,
        max_reasoning_output_tokens: int = 384000,
        request_timeout_seconds: int = 1800,
        budget_state_path: Path | None = None,
        budget_approval_limit_usd: float = 20.0,
        budget_prior_spend_usd: float = 0.0,
        budget_optimizer_reserve_usd: float = 1.0,
        budget_request_reserve_usd: float = 0.3,
        client: Any | None = None,
    ):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if client is None and not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")
        self.config = config
        self.logger = logger
        self.skill_text = skill_text
        self.skill_sha256 = _sha256_text(self.skill_text)
        self.calls_path = Path(calls_path)
        self.request_cap = int(request_cap)
        self.action_output_tokens = int(action_output_tokens)
        self.reasoning_output_tokens = int(reasoning_output_tokens)
        self.retry_action_output_tokens = int(retry_action_output_tokens)
        self.retry_reasoning_output_tokens = int(retry_reasoning_output_tokens)
        self.max_action_output_tokens = int(max_action_output_tokens)
        self.max_reasoning_output_tokens = int(max_reasoning_output_tokens)
        self.request_timeout_seconds = int(request_timeout_seconds)
        self.request_count = 0
        self.budget_guard = (
            SharedBudgetGuard(
                budget_state_path,
                approval_limit_usd=budget_approval_limit_usd,
                prior_spend_usd=budget_prior_spend_usd,
                optimizer_reserve_usd=budget_optimizer_reserve_usd,
                request_reserve_usd=budget_request_reserve_usd,
            )
            if budget_state_path is not None
            else None
        )
        self.client = client or OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            max_retries=0,
            timeout=self.request_timeout_seconds,
        )

    @property
    def skill_block(self) -> str:
        separator = "" if self.skill_text.endswith("\n") else "\n"
        return (
            f'{BEGIN} sha256="{self.skill_sha256}">\n'
            f"{self.skill_text}{separator}{END}"
        )

    def _inject(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = [dict(message) for message in messages]
        for message in result:
            if message.get("role") == "system":
                content = str(message.get("content") or "")
                if BEGIN not in content:
                    message["content"] = f"{content.rstrip()}\n\n{self.skill_block}"
                return result
        result.insert(0, {"role": "system", "content": self.skill_block})
        return result

    def _call(
        self,
        *,
        engine: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        answer_num: int,
        temperature: float,
        json_mode: bool,
        timeout: float,
    ) -> list[str]:
        injected = self._inject(messages)
        requested_tokens = max(1, int(max_tokens))
        thinking = requested_tokens >= 8192
        budgets = (
            [
                self.reasoning_output_tokens,
                self.retry_reasoning_output_tokens,
                self.max_reasoning_output_tokens,
            ]
            if thinking
            else [
                self.action_output_tokens,
                self.retry_action_output_tokens,
                self.max_action_output_tokens,
            ]
        )
        answers: list[str] = []
        for sample_index in range(max(1, int(answer_num))):
            last_error: Exception | None = None
            sample_accepted = False
            for retry, effective_tokens in enumerate(budgets):
                response_issue: str | None = None
                for transport_retry in range(2):
                    if self.request_count >= self.request_cap:
                        raise RuntimeError("REQUEST_BUDGET_EXCEEDED")
                    reserve_usd = estimate_flash_request_upper_bound(
                        effective_tokens
                    )
                    reservation_id = (
                        self.budget_guard.reserve(reserve_usd)
                        if self.budget_guard
                        else None
                    )
                    self.request_count += 1
                    call_index = self.request_count
                    started = time.monotonic()
                    try:
                        kwargs: dict[str, Any] = {
                            "model": engine,
                            "messages": injected,
                            "max_tokens": effective_tokens,
                            "timeout": max(
                                float(timeout), self.request_timeout_seconds
                            ),
                            "extra_body": {
                                "thinking": {
                                    "type": "enabled" if thinking else "disabled"
                                },
                            },
                        }
                        if thinking:
                            kwargs["extra_body"]["reasoning_effort"] = "high"
                        else:
                            kwargs["temperature"] = temperature
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}
                        response = self.client.chat.completions.create(**kwargs)
                        choices = list(getattr(response, "choices", None) or [])
                        if not choices:
                            raise RuntimeError("provider returned no choices")
                        usage = _usage_dict(getattr(response, "usage", None))
                        if self.budget_guard and reservation_id:
                            self.budget_guard.settle(
                                reservation_id,
                                cost_usd=estimate_flash_cost(usage),
                                usage=usage,
                            )
                            reservation_id = None
                        response_texts = [
                            str(choice.message.content or "") for choice in choices
                        ]
                        finish_reasons = [
                            str(getattr(choice, "finish_reason", "") or "")
                            for choice in choices
                        ]
                        response_issue = None
                        if any(reason == "length" for reason in finish_reasons):
                            response_issue = "finish_reason_length"
                        elif not any(text.strip() for text in response_texts):
                            response_issue = "empty_content"
                        elif any(
                            reason not in {"", "stop"}
                            for reason in finish_reasons
                        ):
                            response_issue = "non_stop_finish_reason"
                        accepted = response_issue is None
                        _append_jsonl(
                            self.calls_path,
                            {
                                "call_index": call_index,
                                "sample_index": sample_index,
                                "requested_answer_num": int(answer_num),
                                "retry_index": retry,
                                "transport_retry_index": transport_retry,
                                "model": engine,
                                "mode": "thinking" if thinking else "nonthinking",
                                "requested_max_tokens": requested_tokens,
                                "effective_max_tokens": effective_tokens,
                                "effective_timeout_seconds": max(
                                    float(timeout), self.request_timeout_seconds
                                ),
                                "budget_reserve_usd": reserve_usd,
                                "skill_sha256": self.skill_sha256,
                                "system_message_sha256": _sha256_text(
                                    str(injected[0].get("content") or "")
                                ),
                                "messages": injected,
                                "responses": response_texts,
                                "reasoning_content": [
                                    str(
                                        getattr(
                                            choice.message,
                                            "reasoning_content",
                                            "",
                                        )
                                        or ""
                                    )
                                    for choice in choices
                                ],
                                "finish_reasons": finish_reasons,
                                "response_issue": response_issue,
                                "accepted": accepted,
                                "usage": usage,
                                "estimated_cost_usd": estimate_flash_cost(usage),
                                "wall_seconds": time.monotonic() - started,
                                "error": None,
                            },
                        )
                        if accepted:
                            answers.append(response_texts[0])
                            sample_accepted = True
                            break
                        last_error = RuntimeError(response_issue)
                    except Exception as error:  # provider errors remain auditable
                        response_issue = "provider_error"
                        last_error = error
                        if self.budget_guard and reservation_id:
                            self.budget_guard.settle(
                                reservation_id,
                                cost_usd=None,
                                usage=None,
                            )
                            reservation_id = None
                        _append_jsonl(
                            self.calls_path,
                            {
                                "call_index": call_index,
                                "sample_index": sample_index,
                                "requested_answer_num": int(answer_num),
                                "retry_index": retry,
                                "transport_retry_index": transport_retry,
                                "model": engine,
                                "mode": "thinking" if thinking else "nonthinking",
                                "requested_max_tokens": requested_tokens,
                                "effective_max_tokens": effective_tokens,
                                "effective_timeout_seconds": max(
                                    float(timeout), self.request_timeout_seconds
                                ),
                                "budget_reserve_usd": reserve_usd,
                                "skill_sha256": self.skill_sha256,
                                "system_message_sha256": _sha256_text(
                                    str(injected[0].get("content") or "")
                                ),
                                "messages": injected,
                                "responses": [],
                                "reasoning_content": [],
                                "finish_reasons": [],
                                "response_issue": response_issue,
                                "accepted": False,
                                "usage": _usage_dict(None),
                                "estimated_cost_usd": None,
                                "wall_seconds": time.monotonic() - started,
                                "error": f"{type(error).__name__}: {error}",
                            },
                        )
                    if response_issue == "finish_reason_length":
                        break
                    if transport_retry == 0:
                        time.sleep(1)
                if sample_accepted:
                    break
                if response_issue != "finish_reason_length":
                    break
                if retry < len(budgets) - 1:
                    time.sleep(1)
            if not sample_accepted:
                raise RuntimeError(f"DeepSeek request failed: {last_error}")
        return answers

    def infer_llm(
        self,
        engine,
        instruction,
        exemplars,
        query,
        system_info=None,
        answer_num=1,
        max_tokens=8192,
        temp=1.0,
        json=False,
        return_msg=False,
        verbose=False,
        timeout=100,
    ):
        del verbose
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": system_info or "You are a helpful AI assistant.",
            }
        ]
        if instruction is not None:
            messages.extend(
                [
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": "OK, I'm ready to help."},
                ]
            )
        for exemplar in exemplars or []:
            messages.extend(
                [
                    {"role": "user", "content": exemplar["query"]},
                    {"role": "assistant", "content": exemplar["answer"]},
                ]
            )
        messages.append({"role": "user", "content": query})
        answers = self._call(
            engine=engine,
            messages=messages,
            max_tokens=max_tokens,
            answer_num=answer_num,
            temperature=temp,
            json_mode=json,
            timeout=timeout,
        )
        return (answers, self._inject(messages)) if return_msg else answers

    def infer_llm_with_history(
        self,
        engine,
        history,
        query,
        answer_num=1,
        max_tokens=2048,
        temp=0.7,
        json=False,
        return_msg=False,
        verbose=False,
    ):
        del verbose
        messages = [dict(message) for message in history]
        messages.append({"role": "user", "content": query})
        answers = self._call(
            engine=engine,
            messages=messages,
            max_tokens=max_tokens,
            answer_num=answer_num,
            temperature=temp,
            json_mode=json,
            timeout=100,
        )
        return (answers, self._inject(messages)) if return_msg else answers
