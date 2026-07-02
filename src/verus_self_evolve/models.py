from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Attempt:
    index: int
    target_error: str
    action: str
    input_tokens: int
    output_tokens: int
    accepted: bool

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Trace:
    model: str
    batch: str
    project: str
    file: str
    status: str
    csv_total_tokens: int
    time_seconds: float
    lemmas: tuple[str, ...]
    recursive_functions: tuple[str, ...]
    opaque_functions: tuple[str, ...]
    attempts: tuple[Attempt, ...]
    log_path: str

    @property
    def log_total_tokens(self) -> int:
        return sum(attempt.total_tokens for attempt in self.attempts)

    @property
    def effective_total_tokens(self) -> int:
        return max(self.csv_total_tokens, self.log_total_tokens)

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"

    @property
    def action_sequence(self) -> tuple[str, ...]:
        return tuple(attempt.action for attempt in self.attempts if attempt.action)


@dataclass(frozen=True)
class CandidateRule:
    rule_id: str
    level: str
    threshold: int
    project: str
    motif: str
    repeated_error: str
    repeated_action: str
    prefer_actions: tuple[str, ...]
    support_traces: int
    evidence: str

