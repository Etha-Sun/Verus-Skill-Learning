"""Aggregate-only held-out gate shared by all skill construction methods."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class GateConfig:
    """Promotion policy; ``enabled=False`` exactly preserves direct merging."""

    enabled: bool = False
    expected_task_count: int | None = None
    success_weight: float = 0.70
    token_weight: float = 0.15
    wall_time_weight: float = 0.15
    primary_uncached_token_component_weight: float = 0.60
    reasoning_token_component_weight: float = 0.40
    max_total_token_increase_success_gain: float = 0.20
    max_wall_time_increase_success_gain: float = 0.20
    max_total_token_increase_equal_success: float = 0.10
    max_wall_time_increase_equal_success: float = 0.10
    max_total_token_ratio_to_m_core_equal_success: float = 1.10
    max_total_token_ratio_to_m_core_success_gain: float = 1.20
    min_common_solved_count: int = 3
    min_token_gain: float = 0.15
    min_wall_time_gain: float = 0.10
    min_efficiency_gain: float = 0.05
    relative_gain_clip: float = 1.0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "GateConfig":
        value = value or {}
        enabled = value.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("held_out_gate.enabled must be true or false")
        expected = value.get("expected_task_count")
        if expected is not None and (not isinstance(expected, int) or expected <= 0):
            raise ValueError("held_out_gate.expected_task_count must be a positive integer")
        defaults = cls()
        kwargs: dict[str, Any] = {
            "enabled": enabled,
            "expected_task_count": expected,
        }
        float_fields = (
            "success_weight",
            "token_weight",
            "wall_time_weight",
            "primary_uncached_token_component_weight",
            "reasoning_token_component_weight",
            "max_total_token_increase_success_gain",
            "max_wall_time_increase_success_gain",
            "max_total_token_increase_equal_success",
            "max_wall_time_increase_equal_success",
            "max_total_token_ratio_to_m_core_equal_success",
            "max_total_token_ratio_to_m_core_success_gain",
            "min_token_gain",
            "min_wall_time_gain",
            "min_efficiency_gain",
            "relative_gain_clip",
        )
        for name in float_fields:
            raw = value.get(name, getattr(defaults, name))
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"held_out_gate.{name} must be numeric")
            kwargs[name] = float(raw)
        common = value.get("min_common_solved_count", defaults.min_common_solved_count)
        if not isinstance(common, int) or isinstance(common, bool) or common <= 0:
            raise ValueError("held_out_gate.min_common_solved_count must be a positive integer")
        kwargs["min_common_solved_count"] = common
        config = cls(**kwargs)
        config.validate()
        return config

    def validate(self) -> None:
        if self.expected_task_count is not None and self.expected_task_count <= 0:
            raise ValueError("expected_task_count must be positive")
        weights = (self.success_weight, self.token_weight, self.wall_time_weight)
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("success/token/wall-time weights must be nonnegative and sum to 1")
        if self.token_weight + self.wall_time_weight <= 0:
            raise ValueError("token_weight + wall_time_weight must be positive")
        token_weights = (
            self.primary_uncached_token_component_weight,
            self.reasoning_token_component_weight,
        )
        if any(weight < 0 for weight in token_weights) or abs(sum(token_weights) - 1.0) > 1e-9:
            raise ValueError("primary-uncached/reasoning token component weights must sum to 1")
        nonnegative = (
            self.max_total_token_increase_success_gain,
            self.max_wall_time_increase_success_gain,
            self.max_total_token_increase_equal_success,
            self.max_wall_time_increase_equal_success,
            self.min_token_gain,
            self.min_wall_time_gain,
            self.min_efficiency_gain,
        )
        if any(value < 0 for value in nonnegative):
            raise ValueError("gate caps and materiality thresholds must be nonnegative")
        cumulative_ratios = (
            self.max_total_token_ratio_to_m_core_equal_success,
            self.max_total_token_ratio_to_m_core_success_gain,
        )
        if any(value < 1 for value in cumulative_ratios):
            raise ValueError("M-core cumulative token ratios must be at least 1")
        if (
            self.max_total_token_ratio_to_m_core_equal_success
            > self.max_total_token_ratio_to_m_core_success_gain
        ):
            raise ValueError("equal-success M-core ratio cannot exceed success-gain ratio")
        if self.min_common_solved_count <= 0:
            raise ValueError("min_common_solved_count must be positive")
        if self.relative_gain_clip <= 0:
            raise ValueError("relative_gain_clip must be positive")


@dataclass(frozen=True)
class CandidateSnapshot:
    """One method-specific update materialized as a complete runnable skill."""

    candidate_id: str
    skill_dir: Path
    construction_method: str
    unit_type: str
    train_provenance_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskEvaluation:
    """Private host-side task metrics used only for paired efficiency."""

    task_id: str
    success: bool
    primary_uncached_tokens: int
    total_tokens: int
    reasoning_tokens: int
    wall_time_seconds: float

    def validate(self) -> None:
        if not self.task_id:
            raise ValueError("task evaluation requires a non-empty task_id")
        if (
            self.primary_uncached_tokens < 0
            or self.total_tokens < 0
            or self.reasoning_tokens < 0
        ):
            raise ValueError("task token counts must be nonnegative")
        if self.primary_uncached_tokens > self.total_tokens:
            raise ValueError("task primary uncached tokens cannot exceed provider total tokens")
        if self.reasoning_tokens > self.total_tokens:
            raise ValueError("task reasoning tokens cannot exceed provider total tokens")
        if self.wall_time_seconds < 0:
            raise ValueError("task wall time must be nonnegative")


@dataclass(frozen=True)
class AggregateEvaluation:
    """Host-side evaluation; task rows never leave the gate controller."""

    success_count: int
    task_count: int
    timeout_count: int = 0
    primary_uncached_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_cost_usd: float | None = None
    wall_time_seconds: float | None = None
    coverage_complete: bool = False
    fidelity_complete: bool = False
    safety_complete: bool = False
    unsafe_regression_count: int = 0
    contract_violation_count: int = 0
    task_metrics: tuple[TaskEvaluation, ...] = field(default_factory=tuple, repr=False)

    def validate(self) -> None:
        if self.task_count <= 0:
            raise ValueError("aggregate task_count must be positive")
        if not 0 <= self.success_count <= self.task_count:
            raise ValueError("aggregate success_count is outside [0, task_count]")
        if not 0 <= self.timeout_count <= self.task_count:
            raise ValueError("aggregate timeout_count is outside [0, task_count]")
        for name in ("primary_uncached_tokens", "total_tokens", "reasoning_tokens"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"aggregate {name} must be nonnegative")
        if self.wall_time_seconds is not None and self.wall_time_seconds < 0:
            raise ValueError("aggregate wall_time_seconds must be nonnegative")
        if self.unsafe_regression_count < 0 or self.contract_violation_count < 0:
            raise ValueError("aggregate veto counts must be nonnegative")
        if (
            self.primary_uncached_tokens is not None
            and self.total_tokens is not None
            and self.primary_uncached_tokens > self.total_tokens
        ):
            raise ValueError("aggregate primary uncached tokens cannot exceed provider total")
        if (
            self.reasoning_tokens is not None
            and self.total_tokens is not None
            and self.reasoning_tokens > self.total_tokens
        ):
            raise ValueError("aggregate reasoning tokens cannot exceed provider total")
        for name in ("coverage_complete", "fidelity_complete", "safety_complete"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"aggregate {name} must be boolean")
        if self.task_metrics:
            if len(self.task_metrics) != self.task_count:
                raise ValueError("task_metrics count does not match aggregate task_count")
            ids = [task.task_id for task in self.task_metrics]
            if len(ids) != len(set(ids)):
                raise ValueError("task_metrics task_id values must be unique")
            for task in self.task_metrics:
                task.validate()
            if sum(task.success for task in self.task_metrics) != self.success_count:
                raise ValueError("task_metrics success count does not match aggregate")
            if (
                sum(task.primary_uncached_tokens for task in self.task_metrics)
                != self.primary_uncached_tokens
            ):
                raise ValueError("task_metrics primary uncached tokens do not match aggregate")
            if sum(task.total_tokens for task in self.task_metrics) != self.total_tokens:
                raise ValueError("task_metrics total tokens do not match aggregate")
            if sum(task.reasoning_tokens for task in self.task_metrics) != self.reasoning_tokens:
                raise ValueError("task_metrics reasoning tokens do not match aggregate")

    def history_summary(self) -> dict[str, Any]:
        """Return aggregate-only fields; never serialize task IDs into gate history."""
        return {
            "success_count": self.success_count,
            "task_count": self.task_count,
            "timeout_count": self.timeout_count,
            "primary_uncached_tokens": self.primary_uncached_tokens,
            "total_tokens": self.total_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_cost_usd": self.total_cost_usd,
            "wall_time_seconds": self.wall_time_seconds,
            "coverage_complete": self.coverage_complete,
            "fidelity_complete": self.fidelity_complete,
            "safety_complete": self.safety_complete,
            "unsafe_regression_count": self.unsafe_regression_count,
            "contract_violation_count": self.contract_violation_count,
        }


class AggregateEvaluator(Protocol):
    def evaluate(self, skill_dir: Path, label: str) -> AggregateEvaluation:
        """Evaluate one immutable skill snapshot for the host-side gate."""


@dataclass(frozen=True)
class PromotionResult:
    accepted: bool
    reason: str
    incumbent_hash: str
    candidate_hash: str
    next_snapshot: CandidateSnapshot
    incumbent_evaluation: AggregateEvaluation | None
    candidate_evaluation: AggregateEvaluation | None
    comparison: dict[str, Any] | None = None


def hash_skill_tree(skill_dir: Path) -> str:
    """Hash one regular-file-only skill tree without following symlinks."""
    root = skill_dir.resolve()
    if not root.is_dir() or not (root / "SKILL.md").is_file():
        raise ValueError(f"invalid skill snapshot: {skill_dir}")
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file() or path.is_symlink())
    if not files:
        raise ValueError(f"empty skill snapshot: {skill_dir}")
    for path in files:
        if path.is_symlink():
            raise ValueError(f"skill snapshots may not contain symlinks: {path}")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


class CommandAggregateEvaluator:
    """Run an actor command and read a compact aggregate summary.

    ``argv`` is an argument vector, never a shell string. The placeholders
    ``{skill_dir}``, ``{output_dir}``, and ``{label}`` are expanded per run.
    Full actor logs stay below ``output_root``. Per-task metrics are retained
    privately for paired comparison; the controller publishes aggregates only.
    """

    def __init__(
        self,
        argv: Sequence[str],
        output_root: Path,
        summary_relative_path: str = "summary.json",
        timeout_seconds: int | None = None,
        resume_argv: Sequence[str] | None = None,
    ) -> None:
        if not argv:
            raise ValueError("evaluator argv must not be empty")
        self.argv = tuple(argv)
        self.output_root = output_root.resolve()
        self.summary_relative_path = summary_relative_path
        self.timeout_seconds = timeout_seconds
        self.resume_argv = tuple(resume_argv) if resume_argv is not None else None

    @staticmethod
    def _first(mapping: Mapping[str, Any], names: Sequence[str]) -> Any:
        for name in names:
            if name in mapping:
                return mapping[name]
        return None

    @classmethod
    def _usage(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        usage = payload.get("usage")
        return usage if isinstance(usage, Mapping) else payload

    @classmethod
    def _primary_uncached_tokens(cls, usage: Mapping[str, Any]) -> int | None:
        direct = cls._first(
            usage,
            (
                "primary_uncached_tokens",
                "uncached_tokens",
                "provider_primary_uncached_tokens",
            ),
        )
        if direct is not None:
            return int(direct)
        uncached_input = cls._first(
            usage,
            (
                "cache_miss_input_tokens",
                "uncached_input_tokens",
                "input_cache_miss_tokens",
                "cache_miss_tokens",
            ),
        )
        output = cls._first(usage, ("output_tokens", "provider_output_tokens"))
        if uncached_input is None or output is None:
            return None
        return int(uncached_input) + int(output)

    @staticmethod
    def _elapsed_seconds(payload: Mapping[str, Any]) -> float | None:
        for name in ("wall_time_seconds", "elapsed_seconds", "duration_seconds"):
            if name in payload:
                return float(payload[name])
        started = payload.get("started_at")
        finished = payload.get("finished_at")
        if not isinstance(started, str) or not isinstance(finished, str):
            return None
        start_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
        finish_time = datetime.fromisoformat(finished.replace("Z", "+00:00"))
        return (finish_time - start_time).total_seconds()

    @classmethod
    def _task_evaluations(cls, payload: Mapping[str, Any]) -> tuple[TaskEvaluation, ...]:
        raw_tasks = payload.get("tasks")
        if raw_tasks is None:
            return ()
        if not isinstance(raw_tasks, list):
            raise ValueError("actor summary tasks must be a JSON array")
        tasks: list[TaskEvaluation] = []
        for raw_task in raw_tasks:
            if not isinstance(raw_task, Mapping):
                raise ValueError("actor summary task entries must be JSON objects")
            usage = cls._usage(raw_task)
            primary_uncached_tokens = cls._primary_uncached_tokens(usage)
            total_tokens = cls._first(usage, ("total_tokens", "provider_total_tokens"))
            reasoning_tokens = cls._first(
                usage, ("reasoning_tokens", "provider_reasoning_tokens")
            )
            elapsed = cls._elapsed_seconds(raw_task)
            if (
                primary_uncached_tokens is None
                or total_tokens is None
                or reasoning_tokens is None
                or elapsed is None
            ):
                # Preserve the aggregate summary so the controller can emit a
                # deterministic missing-metrics rejection instead of aborting
                # the entire candidate sequence.
                return ()
            task = TaskEvaluation(
                task_id=str(raw_task.get("task_id") or ""),
                success=bool(raw_task.get("success", False)),
                primary_uncached_tokens=int(primary_uncached_tokens),
                total_tokens=int(total_tokens),
                reasoning_tokens=int(reasoning_tokens),
                wall_time_seconds=float(elapsed),
            )
            task.validate()
            tasks.append(task)
        return tuple(tasks)

    @classmethod
    def parse_summary(cls, payload: Mapping[str, Any]) -> AggregateEvaluation:
        """Parse the current Codex actor summary without exposing task rows."""
        task_metrics = cls._task_evaluations(payload)
        usage = cls._usage(payload)
        success_count = cls._first(payload, ("success_count", "successes", "passed"))
        task_count = cls._first(
            payload, ("task_count", "total_tasks", "total", "completed_tasks")
        )
        if success_count is None or task_count is None:
            raise ValueError("actor summary requires success and task counts")
        timeout_count = cls._first(payload, ("timeout_count", "timeouts"))
        if timeout_count is None and isinstance(payload.get("tasks"), list):
            timeout_count = sum(bool(task.get("timed_out")) for task in payload["tasks"])
        primary_uncached_tokens = cls._primary_uncached_tokens(usage)
        total_tokens = cls._optional_int(usage, ("total_tokens", "provider_total_tokens"))
        reasoning_tokens = cls._optional_int(
            usage, ("reasoning_tokens", "provider_reasoning_tokens")
        )
        wall_time = cls._optional_float(payload, ("wall_time_seconds", "elapsed_seconds"))
        if primary_uncached_tokens is None and task_metrics:
            primary_uncached_tokens = sum(
                task.primary_uncached_tokens for task in task_metrics
            )
        if total_tokens is None and task_metrics:
            total_tokens = sum(task.total_tokens for task in task_metrics)
        if reasoning_tokens is None and task_metrics:
            reasoning_tokens = sum(task.reasoning_tokens for task in task_metrics)
        if wall_time is None and task_metrics:
            wall_time = sum(task.wall_time_seconds for task in task_metrics)
        fidelity = payload.get("fidelity")
        evaluation = AggregateEvaluation(
            success_count=int(success_count),
            task_count=int(task_count),
            timeout_count=int(timeout_count or 0),
            primary_uncached_tokens=primary_uncached_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens,
            total_cost_usd=cls._optional_float(
                payload, ("total_cost_usd", "estimated_cost_usd")
            ),
            wall_time_seconds=wall_time,
            coverage_complete=payload.get("coverage_complete") is True,
            fidelity_complete=(
                payload.get("fidelity_complete") is True or fidelity == "V3_AUDITED"
            ),
            safety_complete=(
                payload.get("safety_complete") is True
                or payload.get("safety_audit_complete") is True
            ),
            unsafe_regression_count=int(payload.get("unsafe_regression_count", 0)),
            contract_violation_count=int(payload.get("contract_violation_count", 0)),
            task_metrics=task_metrics,
        )
        evaluation.validate()
        return evaluation

    def evaluate(self, skill_dir: Path, label: str) -> AggregateEvaluation:
        safe_label = "".join(char if char.isalnum() or char in "-_" else "_" for char in label)
        output_dir = self.output_root / safe_label
        summary_path = (output_dir / self.summary_relative_path).resolve()
        if output_dir.resolve() not in summary_path.parents:
            raise ValueError("summary_relative_path escapes evaluator output directory")
        values = {
            "skill_dir": str(skill_dir.resolve()),
            "output_dir": str(output_dir),
            "label": safe_label,
        }
        if not summary_path.is_file():
            if output_dir.exists():
                if self.resume_argv is None:
                    raise FileExistsError(
                        f"incomplete evaluator output requires resume_argv: {output_dir}"
                    )
                argv = self.resume_argv
            else:
                output_dir.mkdir(parents=True)
                argv = self.argv
            command = [
                argument.replace("{skill_dir}", values["skill_dir"])
                .replace("{output_dir}", values["output_dir"])
                .replace("{label}", values["label"])
                for argument in argv
            ]
            subprocess.run(command, check=True, timeout=self.timeout_seconds)
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("actor summary must be a JSON object")
        return self.parse_summary(payload)

    @classmethod
    def _optional_int(cls, payload: Mapping[str, Any], names: Sequence[str]) -> int | None:
        value = cls._first(payload, names)
        return None if value is None else int(value)

    @classmethod
    def _optional_float(cls, payload: Mapping[str, Any], names: Sequence[str]) -> float | None:
        value = cls._first(payload, names)
        return None if value is None else float(value)


class HeldOutGateController:
    """Compare complete snapshots while remaining agnostic to update-unit type."""

    def __init__(
        self,
        config: GateConfig,
        evaluator: AggregateEvaluator | None,
        m_core_snapshot: CandidateSnapshot | None = None,
        history_path: Path | None = None,
        evaluation_cache_path: Path | None = None,
    ) -> None:
        config.validate()
        if config.enabled and evaluator is None:
            raise ValueError("an aggregate evaluator is required when held-out gate is enabled")
        if config.enabled and m_core_snapshot is None:
            raise ValueError("the frozen M-core snapshot is required when the gate is enabled")
        self.config = config
        self.evaluator = evaluator
        self.m_core_snapshot = m_core_snapshot
        self.m_core_hash = (
            hash_skill_tree(m_core_snapshot.skill_dir) if m_core_snapshot is not None else None
        )
        self.history_path = history_path
        self.evaluation_cache_path = evaluation_cache_path
        self._history = self._load_history()
        self._evaluation_cache = self._load_evaluation_cache()

    def _load_history(self) -> list[dict[str, Any]]:
        if self.history_path is None or not self.history_path.exists():
            return []
        payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        decisions = payload.get("decisions") if isinstance(payload, dict) else None
        if not isinstance(decisions, list) or not all(isinstance(row, dict) for row in decisions):
            raise ValueError("gate history must contain a decisions array")
        return list(decisions)

    @staticmethod
    def _evaluation_to_private_json(evaluation: AggregateEvaluation) -> dict[str, Any]:
        value = evaluation.history_summary()
        value["task_metrics"] = [
            {
                "task_id": task.task_id,
                "success": task.success,
                "primary_uncached_tokens": task.primary_uncached_tokens,
                "total_tokens": task.total_tokens,
                "reasoning_tokens": task.reasoning_tokens,
                "wall_time_seconds": task.wall_time_seconds,
            }
            for task in evaluation.task_metrics
        ]
        return value

    @staticmethod
    def _evaluation_from_private_json(value: Mapping[str, Any]) -> AggregateEvaluation:
        raw_tasks = value.get("task_metrics", [])
        if not isinstance(raw_tasks, list):
            raise ValueError("private evaluation cache task_metrics must be an array")
        tasks = tuple(
            TaskEvaluation(
                task_id=str(task["task_id"]),
                success=bool(task["success"]),
                primary_uncached_tokens=int(task["primary_uncached_tokens"]),
                total_tokens=int(task["total_tokens"]),
                reasoning_tokens=int(task["reasoning_tokens"]),
                wall_time_seconds=float(task["wall_time_seconds"]),
            )
            for task in raw_tasks
        )
        evaluation = AggregateEvaluation(
            success_count=int(value["success_count"]),
            task_count=int(value["task_count"]),
            timeout_count=int(value.get("timeout_count", 0)),
            primary_uncached_tokens=value.get("primary_uncached_tokens"),
            total_tokens=value.get("total_tokens"),
            reasoning_tokens=value.get("reasoning_tokens"),
            total_cost_usd=value.get("total_cost_usd"),
            wall_time_seconds=value.get("wall_time_seconds"),
            coverage_complete=value.get("coverage_complete") is True,
            fidelity_complete=value.get("fidelity_complete") is True,
            safety_complete=value.get("safety_complete") is True,
            unsafe_regression_count=int(value.get("unsafe_regression_count", 0)),
            contract_violation_count=int(value.get("contract_violation_count", 0)),
            task_metrics=tasks,
        )
        evaluation.validate()
        return evaluation

    def _load_evaluation_cache(self) -> dict[str, AggregateEvaluation]:
        if self.evaluation_cache_path is None or not self.evaluation_cache_path.exists():
            return {}
        payload = json.loads(self.evaluation_cache_path.read_text(encoding="utf-8"))
        snapshots = payload.get("snapshots") if isinstance(payload, dict) else None
        if not isinstance(snapshots, dict):
            raise ValueError("private evaluation cache must contain a snapshots object")
        return {
            snapshot_hash: self._evaluation_from_private_json(value)
            for snapshot_hash, value in snapshots.items()
        }

    def _save_evaluation_cache(self) -> None:
        if self.evaluation_cache_path is None:
            return
        self.evaluation_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.evaluation_cache_path.with_suffix(
            self.evaluation_cache_path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                {
                    "privacy": "host-private; contains held-out task IDs",
                    "snapshots": {
                        key: self._evaluation_to_private_json(value)
                        for key, value in sorted(self._evaluation_cache.items())
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.evaluation_cache_path)

    def evaluate_m_core(self) -> AggregateEvaluation:
        """Evaluate and cache the common baseline before candidate construction."""
        if not self.config.enabled:
            raise ValueError("M-core evaluation requires an enabled gate")
        assert self.m_core_snapshot is not None and self.m_core_hash is not None
        return self._evaluate_cached(
            self.m_core_snapshot, self.m_core_hash, "m-core__baseline"
        )

    def promote(
        self,
        incumbent: CandidateSnapshot,
        candidate: CandidateSnapshot,
    ) -> PromotionResult:
        incumbent_hash = hash_skill_tree(incumbent.skill_dir)
        candidate_hash = hash_skill_tree(candidate.skill_dir)

        incumbent_eval: AggregateEvaluation | None = None
        candidate_eval: AggregateEvaluation | None = None
        comparison: dict[str, Any] | None = None
        if not self.config.enabled:
            accepted = True
            reason = "gate_disabled_direct_merge"
        elif incumbent_hash == candidate_hash:
            accepted = False
            reason = "identical_snapshot_no_improvement"
        else:
            assert self.m_core_snapshot is not None and self.m_core_hash is not None
            m_core_eval = self.evaluate_m_core()
            incumbent_eval = self._evaluate_cached(
                incumbent, incumbent_hash, f"{candidate.candidate_id}__incumbent"
            )
            candidate_eval = self._evaluate_cached(
                candidate, candidate_hash, f"{candidate.candidate_id}__candidate"
            )
            self._validate_pair(m_core_eval, incumbent_eval)
            self._validate_pair(incumbent_eval, candidate_eval)
            accepted, reason, comparison = self._decide(
                m_core_eval, incumbent_eval, candidate_eval
            )

        result = PromotionResult(
            accepted=accepted,
            reason=reason,
            incumbent_hash=incumbent_hash,
            candidate_hash=candidate_hash,
            next_snapshot=candidate if accepted else incumbent,
            incumbent_evaluation=self._aggregate_only(incumbent_eval),
            candidate_evaluation=self._aggregate_only(candidate_eval),
            comparison=comparison,
        )
        self._record(candidate, result)
        return result

    def resume_promotion(
        self,
        incumbent: CandidateSnapshot,
        candidate: CandidateSnapshot,
    ) -> PromotionResult | None:
        """Restore one exact prior decision without evaluating or recording it again."""
        incumbent_hash = hash_skill_tree(incumbent.skill_dir)
        candidate_hash = hash_skill_tree(candidate.skill_dir)
        matches = [
            row
            for row in self._history
            if row.get("candidate_id") == candidate.candidate_id
            and row.get("incumbent_hash") == incumbent_hash
            and row.get("candidate_hash") == candidate_hash
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise ValueError(
                f"gate history contains duplicate decisions for {candidate.candidate_id}"
            )
        row = matches[0]
        if (
            row.get("construction_method") != candidate.construction_method
            or row.get("unit_type") != candidate.unit_type
            or tuple(row.get("train_provenance_ids", []))
            != candidate.train_provenance_ids
            or row.get("gate_enabled") is not self.config.enabled
            or row.get("m_core_hash") != self.m_core_hash
        ):
            raise ValueError(
                f"gate history metadata mismatch for {candidate.candidate_id}"
            )
        accepted = row.get("accepted")
        reason = row.get("reason")
        if not isinstance(accepted, bool) or not isinstance(reason, str):
            raise ValueError(f"invalid gate history decision for {candidate.candidate_id}")
        incumbent_evaluation = self._aggregate_only(
            self._evaluation_cache.get(incumbent_hash)
        )
        candidate_evaluation = self._aggregate_only(
            self._evaluation_cache.get(candidate_hash)
        )
        if self.config.enabled and incumbent_hash != candidate_hash:
            if incumbent_evaluation is None or candidate_evaluation is None:
                raise ValueError(
                    f"private evaluation cache is incomplete for {candidate.candidate_id}"
                )
        comparison = row.get("comparison")
        if comparison is not None and not isinstance(comparison, dict):
            raise ValueError(f"invalid gate comparison for {candidate.candidate_id}")
        return PromotionResult(
            accepted=accepted,
            reason=reason,
            incumbent_hash=incumbent_hash,
            candidate_hash=candidate_hash,
            next_snapshot=candidate if accepted else incumbent,
            incumbent_evaluation=incumbent_evaluation,
            candidate_evaluation=candidate_evaluation,
            comparison=comparison,
        )

    def _validate_pair(
        self,
        incumbent: AggregateEvaluation,
        candidate: AggregateEvaluation,
    ) -> None:
        incumbent.validate()
        candidate.validate()
        if incumbent.task_count != candidate.task_count:
            raise ValueError("incumbent and candidate were not evaluated on equal task counts")
        expected = self.config.expected_task_count
        if expected is not None and incumbent.task_count != expected:
            raise ValueError(
                f"held-out task count mismatch: expected {expected}, got {incumbent.task_count}"
            )
        if incumbent.task_metrics and candidate.task_metrics:
            incumbent_ids = {task.task_id for task in incumbent.task_metrics}
            candidate_ids = {task.task_id for task in candidate.task_metrics}
            if incumbent_ids != candidate_ids:
                raise ValueError("incumbent and candidate task metric IDs differ")

    def _evaluate_cached(
        self,
        snapshot: CandidateSnapshot,
        snapshot_hash: str,
        label: str,
    ) -> AggregateEvaluation:
        cached = self._evaluation_cache.get(snapshot_hash)
        if cached is not None:
            return cached
        assert self.evaluator is not None
        evaluation = self.evaluator.evaluate(snapshot.skill_dir, label)
        evaluation.validate()
        self._evaluation_cache[snapshot_hash] = evaluation
        self._save_evaluation_cache()
        return evaluation

    @staticmethod
    def _aggregate_only(evaluation: AggregateEvaluation | None) -> AggregateEvaluation | None:
        if evaluation is None:
            return None
        return AggregateEvaluation(
            success_count=evaluation.success_count,
            task_count=evaluation.task_count,
            timeout_count=evaluation.timeout_count,
            primary_uncached_tokens=evaluation.primary_uncached_tokens,
            total_tokens=evaluation.total_tokens,
            reasoning_tokens=evaluation.reasoning_tokens,
            total_cost_usd=evaluation.total_cost_usd,
            wall_time_seconds=evaluation.wall_time_seconds,
            coverage_complete=evaluation.coverage_complete,
            fidelity_complete=evaluation.fidelity_complete,
            safety_complete=evaluation.safety_complete,
            unsafe_regression_count=evaluation.unsafe_regression_count,
            contract_violation_count=evaluation.contract_violation_count,
        )

    @staticmethod
    def _increase_ratio(candidate: float, incumbent: float) -> float | None:
        if incumbent == 0:
            return 0.0 if candidate == 0 else None
        return (candidate - incumbent) / incumbent

    @staticmethod
    def _clipped_relative_gain(incumbent: float, candidate: float, clip: float) -> float:
        if incumbent == 0:
            return 0.0 if candidate == 0 else -clip
        return max(-clip, min(clip, (incumbent - candidate) / incumbent))

    @staticmethod
    def _has_efficiency_metrics(evaluation: AggregateEvaluation) -> bool:
        return (
            evaluation.primary_uncached_tokens is not None
            and evaluation.total_tokens is not None
            and evaluation.reasoning_tokens is not None
            and evaluation.wall_time_seconds is not None
            and len(evaluation.task_metrics) == evaluation.task_count
        )

    @staticmethod
    def _hard_veto(evaluation: AggregateEvaluation) -> str | None:
        if not evaluation.coverage_complete:
            return "incomplete_coverage"
        if not evaluation.fidelity_complete:
            return "incomplete_fidelity"
        if not evaluation.safety_complete:
            return "incomplete_safety_audit"
        if evaluation.unsafe_regression_count:
            return "unsafe_regression"
        if evaluation.contract_violation_count:
            return "contract_violation"
        return None

    @staticmethod
    def _paired_transition_counts(
        incumbent: AggregateEvaluation,
        candidate: AggregateEvaluation,
    ) -> dict[str, int] | None:
        if not incumbent.task_metrics or not candidate.task_metrics:
            return None
        candidate_by_id = {task.task_id: task for task in candidate.task_metrics}
        counts = {"0_to_0": 0, "0_to_1": 0, "1_to_0": 0, "1_to_1": 0}
        for old in incumbent.task_metrics:
            new = candidate_by_id[old.task_id]
            key = f"{int(old.success)}_to_{int(new.success)}"
            counts[key] += 1
        return counts

    @staticmethod
    def _ratio(value: float, baseline: float) -> float | None:
        if baseline == 0:
            return 1.0 if value == 0 else None
        return value / baseline

    def _decide(
        self,
        m_core: AggregateEvaluation,
        incumbent: AggregateEvaluation,
        candidate: AggregateEvaluation,
    ) -> tuple[bool, str, dict[str, Any]]:
        success_delta = candidate.success_count - incumbent.success_count
        comparison: dict[str, Any] = {
            "success_delta": success_delta,
            "success_delta_from_m_core": candidate.success_count - m_core.success_count,
            "paired_transitions": self._paired_transition_counts(incumbent, candidate),
            "common_solved_count": None,
            "total_token_increase_ratio": None,
            "primary_uncached_token_increase_ratio": None,
            "estimated_cost_increase_ratio": None,
            "wall_time_increase_ratio": None,
            "total_token_ratio_to_m_core": None,
            "m_core_total_token_ratio_cap": None,
            "m_core_total_token_cap_passed": False,
            "paired_median_total_token_gain": None,
            "paired_median_primary_uncached_token_gain": None,
            "paired_median_reasoning_token_gain": None,
            "token_gain": None,
            "paired_median_wall_time_gain": None,
            "efficiency_gain": None,
        }

        for role, evaluation in (
            ("m_core", m_core),
            ("incumbent", incumbent),
            ("candidate", candidate),
        ):
            veto = self._hard_veto(evaluation)
            if veto is not None:
                return False, f"{role}_{veto}", comparison
        if success_delta < 0:
            return False, "success_regression", comparison
        if candidate.success_count < m_core.success_count:
            return False, "success_below_m_core", comparison
        if any(
            not self._has_efficiency_metrics(evaluation)
            for evaluation in (m_core, incumbent, candidate)
        ):
            return False, "missing_required_efficiency_metrics", comparison

        assert m_core.total_tokens is not None
        assert incumbent.primary_uncached_tokens is not None
        assert candidate.primary_uncached_tokens is not None
        assert incumbent.total_tokens is not None and candidate.total_tokens is not None
        assert incumbent.wall_time_seconds is not None
        assert candidate.wall_time_seconds is not None
        total_increase = self._increase_ratio(candidate.total_tokens, incumbent.total_tokens)
        primary_uncached_increase = self._increase_ratio(
            candidate.primary_uncached_tokens, incumbent.primary_uncached_tokens
        )
        time_increase = self._increase_ratio(
            candidate.wall_time_seconds, incumbent.wall_time_seconds
        )
        cost_increase = None
        if incumbent.total_cost_usd is not None and candidate.total_cost_usd is not None:
            cost_increase = self._increase_ratio(
                candidate.total_cost_usd, incumbent.total_cost_usd
            )
        m_core_total_ratio = self._ratio(candidate.total_tokens, m_core.total_tokens)
        if candidate.success_count == m_core.success_count:
            m_core_ratio_cap = self.config.max_total_token_ratio_to_m_core_equal_success
        else:
            m_core_ratio_cap = self.config.max_total_token_ratio_to_m_core_success_gain
        m_core_cap_passed = (
            m_core_total_ratio is not None and m_core_total_ratio <= m_core_ratio_cap
        )
        comparison["total_token_increase_ratio"] = total_increase
        comparison["primary_uncached_token_increase_ratio"] = primary_uncached_increase
        comparison["estimated_cost_increase_ratio"] = cost_increase
        comparison["wall_time_increase_ratio"] = time_increase
        comparison["total_token_ratio_to_m_core"] = m_core_total_ratio
        comparison["m_core_total_token_ratio_cap"] = m_core_ratio_cap
        comparison["m_core_total_token_cap_passed"] = m_core_cap_passed

        if success_delta > 0:
            local_caps_passed = (
                total_increase is not None
                and time_increase is not None
                and total_increase <= self.config.max_total_token_increase_success_gain
                and time_increase <= self.config.max_wall_time_increase_success_gain
            )
            comparison["total_token_cap"] = self.config.max_total_token_increase_success_gain
            comparison["wall_time_cap"] = self.config.max_wall_time_increase_success_gain
            comparison["local_resource_caps_passed"] = local_caps_passed
            comparison["resource_caps_passed"] = local_caps_passed and m_core_cap_passed
            if not local_caps_passed:
                return False, "success_gain_resource_cap_exceeded", comparison
            if m_core_cap_passed:
                return True, "success_gain_within_resource_caps", comparison
            return False, "success_gain_m_core_token_cap_exceeded", comparison

        candidate_by_id = {task.task_id: task for task in candidate.task_metrics}
        common = [
            (task, candidate_by_id[task.task_id])
            for task in incumbent.task_metrics
            if task.success and candidate_by_id[task.task_id].success
        ]
        comparison["common_solved_count"] = len(common)
        comparison["total_token_cap"] = self.config.max_total_token_increase_equal_success
        comparison["wall_time_cap"] = self.config.max_wall_time_increase_equal_success
        local_caps_passed = (
            total_increase is not None
            and time_increase is not None
            and total_increase <= self.config.max_total_token_increase_equal_success
            and time_increase <= self.config.max_wall_time_increase_equal_success
        )
        comparison["local_resource_caps_passed"] = local_caps_passed
        comparison["resource_caps_passed"] = local_caps_passed and m_core_cap_passed
        if not local_caps_passed:
            return False, "equal_success_resource_cap_exceeded", comparison
        if not m_core_cap_passed:
            return False, "equal_success_m_core_token_cap_exceeded", comparison
        if len(common) < self.config.min_common_solved_count:
            comparison["min_common_solved_count"] = self.config.min_common_solved_count
            return False, "equal_success_insufficient_common_solved", comparison

        clip = self.config.relative_gain_clip
        total_gain = median(
            self._clipped_relative_gain(old.total_tokens, new.total_tokens, clip)
            for old, new in common
        )
        primary_uncached_gain = median(
            self._clipped_relative_gain(
                old.primary_uncached_tokens, new.primary_uncached_tokens, clip
            )
            for old, new in common
        )
        reasoning_gain = median(
            self._clipped_relative_gain(old.reasoning_tokens, new.reasoning_tokens, clip)
            for old, new in common
        )
        time_gain = median(
            self._clipped_relative_gain(old.wall_time_seconds, new.wall_time_seconds, clip)
            for old, new in common
        )
        token_gain = (
            self.config.primary_uncached_token_component_weight * primary_uncached_gain
            + self.config.reasoning_token_component_weight * reasoning_gain
        )
        secondary_weight = self.config.token_weight + self.config.wall_time_weight
        efficiency_gain = (
            self.config.token_weight / secondary_weight * token_gain
            + self.config.wall_time_weight / secondary_weight * time_gain
        )
        token_material = token_gain >= self.config.min_token_gain
        time_material = time_gain >= self.config.min_wall_time_gain
        efficiency_material = efficiency_gain >= self.config.min_efficiency_gain
        comparison.update(
            {
                "paired_median_total_token_gain": total_gain,
                "paired_median_primary_uncached_token_gain": primary_uncached_gain,
                "paired_median_reasoning_token_gain": reasoning_gain,
                "token_gain": token_gain,
                "paired_median_wall_time_gain": time_gain,
                "efficiency_gain": efficiency_gain,
                "min_token_gain": self.config.min_token_gain,
                "min_wall_time_gain": self.config.min_wall_time_gain,
                "min_efficiency_gain": self.config.min_efficiency_gain,
                "token_material": token_material,
                "wall_time_material": time_material,
                "efficiency_material": efficiency_material,
            }
        )
        if efficiency_material and (token_material or time_material):
            return True, "equal_success_material_efficiency_gain", comparison
        return False, "equal_success_no_material_efficiency_gain", comparison

    def _record(self, candidate: CandidateSnapshot, result: PromotionResult) -> None:
        row = {
            "candidate_id": candidate.candidate_id,
            "construction_method": candidate.construction_method,
            "unit_type": candidate.unit_type,
            "train_provenance_ids": list(candidate.train_provenance_ids),
            "gate_enabled": self.config.enabled,
            "accepted": result.accepted,
            "reason": result.reason,
            "m_core_hash": self.m_core_hash,
            "incumbent_hash": result.incumbent_hash,
            "candidate_hash": result.candidate_hash,
            "incumbent_aggregate": (
                result.incumbent_evaluation.history_summary()
                if result.incumbent_evaluation
                else None
            ),
            "candidate_aggregate": (
                result.candidate_evaluation.history_summary()
                if result.candidate_evaluation
                else None
            ),
            "comparison": result.comparison,
        }
        self._history.append(row)
        if self.history_path is not None:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.history_path.with_suffix(self.history_path.suffix + ".tmp")
            temporary.write_text(
                json.dumps({"decisions": self._history}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.history_path)
