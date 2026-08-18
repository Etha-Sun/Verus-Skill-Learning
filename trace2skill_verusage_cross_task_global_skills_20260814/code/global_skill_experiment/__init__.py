"""Cross-task Trace2Skill construction and held-out promotion utilities."""

from .gate import (
    AggregateEvaluation,
    CandidateSnapshot,
    CommandAggregateEvaluator,
    GateConfig,
    HeldOutGateController,
    PromotionResult,
    TaskEvaluation,
)

__all__ = [
    "AggregateEvaluation",
    "CandidateSnapshot",
    "CommandAggregateEvaluator",
    "GateConfig",
    "HeldOutGateController",
    "PromotionResult",
    "TaskEvaluation",
]
