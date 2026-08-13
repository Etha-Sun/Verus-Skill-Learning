from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


DEEPSEEK_RATES_USD_PER_MILLION = {
    "deepseek-v4-flash": {
        "prompt_cache_hit_tokens": 0.0028,
        "prompt_cache_miss_tokens": 0.14,
        "completion_tokens": 0.28,
    },
    "deepseek-v4-pro": {
        "prompt_cache_hit_tokens": 0.003625,
        "prompt_cache_miss_tokens": 0.435,
        "completion_tokens": 0.87,
    },
}
FLASH_RATES_USD_PER_MILLION = DEEPSEEK_RATES_USD_PER_MILLION[
    "deepseek-v4-flash"
]


def rates_for_model(model: str) -> dict[str, float]:
    try:
        return DEEPSEEK_RATES_USD_PER_MILLION[model]
    except KeyError as error:
        raise ValueError(f"unsupported DeepSeek billing model: {model}") from error


def estimate_deepseek_cost(usage: dict[str, int], model: str) -> float:
    return sum(
        int(usage.get(key, 0) or 0) * rate / 1_000_000
        for key, rate in rates_for_model(model).items()
    )


def estimate_deepseek_request_upper_bound(
    max_completion_tokens: int,
    model: str,
) -> float:
    """Conservative request bound: 1M uncached input plus capped output."""

    return estimate_deepseek_cost(
        {
            "prompt_cache_miss_tokens": 1_000_000,
            "completion_tokens": max_completion_tokens,
        },
        model,
    )


def estimate_flash_cost(usage: dict[str, int]) -> float:
    return estimate_deepseek_cost(usage, "deepseek-v4-flash")


def estimate_flash_request_upper_bound(max_completion_tokens: int) -> float:
    return estimate_deepseek_request_upper_bound(
        max_completion_tokens,
        "deepseek-v4-flash",
    )


class SharedBudgetGuard:
    """Cross-process conservative spend guard for DeepSeek target calls."""

    def __init__(
        self,
        path: Path,
        *,
        approval_limit_usd: float,
        prior_spend_usd: float,
        optimizer_reserve_usd: float,
        request_reserve_usd: float,
    ) -> None:
        self.path = Path(path)
        self.approval_limit_usd = float(approval_limit_usd)
        self.prior_spend_usd = float(prior_spend_usd)
        self.optimizer_reserve_usd = float(optimizer_reserve_usd)
        self.request_reserve_usd = float(request_reserve_usd)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._update(lambda state: state)

    def _initial_state(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "approval_limit_usd": self.approval_limit_usd,
            "prior_spend_usd": self.prior_spend_usd,
            "optimizer_reserve_usd": self.optimizer_reserve_usd,
            "target_spend_usd": 0.0,
            "uncertain_spend_usd": 0.0,
            "settled_requests": 0,
            "uncertain_requests": 0,
            "usage": {
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 0,
                "completion_tokens": 0,
            },
            "reservations": {},
        }

    def _validate(self, state: dict[str, Any]) -> None:
        expected = {
            "approval_limit_usd": self.approval_limit_usd,
            "prior_spend_usd": self.prior_spend_usd,
            "optimizer_reserve_usd": self.optimizer_reserve_usd,
        }
        for key, value in expected.items():
            if abs(float(state.get(key, -1.0)) - value) > 1e-9:
                raise RuntimeError(f"budget state mismatch for {key}")

    def _update(self, transform):
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.seek(0)
            text = handle.read().strip()
            state = json.loads(text) if text else self._initial_state()
            self._validate(state)
            result = transform(state)
            handle.seek(0)
            handle.truncate()
            json.dump(state, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            return result

    def reserve(
        self,
        amount_usd: float | None = None,
        *,
        wait_timeout_seconds: float = 1800,
    ) -> str:
        reservation_id = uuid.uuid4().hex
        reserve_usd = (
            self.request_reserve_usd
            if amount_usd is None
            else max(self.request_reserve_usd, float(amount_usd))
        )
        if reserve_usd <= 0:
            raise ValueError("budget reservation must be positive")

        class CapacityUnavailable(RuntimeError):
            pass

        def apply(state: dict[str, Any]) -> str:
            reserved = sum(float(value) for value in state["reservations"].values())
            committed = (
                float(state["prior_spend_usd"])
                + float(state["optimizer_reserve_usd"])
                + float(state["target_spend_usd"])
                + float(state["uncertain_spend_usd"])
            )
            projected = committed + reserved + reserve_usd
            if projected > float(state["approval_limit_usd"]):
                if committed + reserve_usd <= float(state["approval_limit_usd"]):
                    raise CapacityUnavailable
                raise RuntimeError(
                    "DEEPSEEK_BUDGET_APPROVAL_REQUIRED: "
                    f"projected conservative spend ${projected:.6f} exceeds "
                    f"${state['approval_limit_usd']:.2f}"
                )
            state["reservations"][reservation_id] = reserve_usd
            return reservation_id

        deadline = time.monotonic() + max(0.0, float(wait_timeout_seconds))
        while True:
            try:
                return self._update(apply)
            except CapacityUnavailable:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "DEEPSEEK_BUDGET_CAPACITY_TIMEOUT: "
                        "waiting for in-flight request reservations"
                    ) from None
                time.sleep(0.5)

    def settle(
        self,
        reservation_id: str,
        *,
        cost_usd: float | None,
        usage: dict[str, int] | None,
    ) -> None:
        def apply(state: dict[str, Any]) -> None:
            reserved = float(state["reservations"].pop(reservation_id))
            if cost_usd is None:
                state["uncertain_spend_usd"] += reserved
                state["uncertain_requests"] += 1
                return
            state["target_spend_usd"] += float(cost_usd)
            state["settled_requests"] += 1
            for key in state["usage"]:
                state["usage"][key] += int((usage or {}).get(key, 0) or 0)

        self._update(apply)

    def mark_stale_reservations_uncertain(self) -> float:
        """Conservatively account reservations after all caller processes stop."""

        def apply(state: dict[str, Any]) -> float:
            reservations = state["reservations"]
            amount = sum(float(value) for value in reservations.values())
            state["uncertain_spend_usd"] += amount
            state["uncertain_requests"] += len(reservations)
            reservations.clear()
            return amount

        return float(self._update(apply))
