from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from react_agent import LLMClient, Tool, tool
from react_agent.agent import AgentStep
from react_agent.converter import (
    FORMAT_ERROR_TEMPLATE,
    ParsedAction,
    ParseResult,
    ParseResultType,
    ReActConverter,
    TASK_COMPLETE_SIGNAL,
)
from react_agent.models import Message, ModelSettings

from .workspace import VerusWorkspace, sha256_file


STRICT_ACTION_ERROR = (
    "A Verus proof run cannot finish with a narrative-only response. "
    "Use exactly ACTION: TASK_COMPLETE only after run_verus and run_lynette pass. "
    "Otherwise issue one valid Action tool call. For multiline code, use edit_lines or insert_lines with a JSON array containing one string per physical line.\n\n"
    + FORMAT_ERROR_TEMPLATE
)
PROGRESS_PROTOCOL_PREFIX = "[Host Progress Protocol]"

STRONG_ACTION_ERROR = (
    "Repeated protocol failure: do not answer with analysis alone. Your next response "
    "must be exactly one parseable Action JSON for a registered tool. If you believe "
    "the proof is complete, first use run_verus and run_lynette; only then emit the "
    "standalone completion signal. Never encode multiline code as one JSON string; use edit_lines or insert_lines with a JSON string array.\n\n"
    + FORMAT_ERROR_TEMPLATE
)
_INFORMATION_ACTIONS = {
    "read_file",
    "search_file",
    "explain_verus_diagnostic",
    "search_verus_docs",
    "lookup_vstd_symbol",
    "read_skill_reference",
}
_PROGRESS_EVIDENCE_ACTIONS = _INFORMATION_ACTIONS | {"run_verus"}
_REASONING_NEXT_ACTIONS = {
    "read_skill_reference",
    "read_file",
    "search_file",
    "search_verus_docs",
    "lookup_vstd_symbol",
    "edit_lines",
    "insert_lines",
    "replace_text",
    "run_verus",
}
_FRUITLESS_SEARCH_ACTIONS = {
    "search_file",
    "search_verus_docs",
    "lookup_vstd_symbol",
}
_ERROR_NUMBER_RE = re.compile(r"\b\d+\b")
_SPACE_RE = re.compile(r"\s+")
_VERIFICATION_RESULT_RE = re.compile(
    r"verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors?",
    re.IGNORECASE,
)
_PRIMARY_ERROR_RE = re.compile(r"^\s*error(?:\[[^]]+\])?:\s*(.+)$", re.IGNORECASE)
_OBSERVED_FACT_OVERCLAIM_RE = re.compile(
    r"\b(?:is|are|was|were)\s+(?:false|violated|invalid)\b|"
    # Literal verifier diagnostics such as "cannot prove that ..." and
    # faithful reports such as "did not prove that ..." describe an unproved
    # obligation. Do not treat their embedded ``prove that`` as affirmative.
    r"(?<!cannot )(?<!not )\bproves? that\b|"
    r"\b(?:therefore|likely|suggests?|because)\b|"
    r"\b(?:must|needs? to)\s+(?:be\s+)?(?:update|updated|change|changed|replace|replaced)\b",
    re.IGNORECASE,
)
_HYPOTHESIS_MARKER_RE = re.compile(
    r"\b(?:may|might|could|hypothesis|possibly|appears?|insufficient|unknown|"
    r"needs? (?:to be )?test(?:ed|ing)?)\b",
    re.IGNORECASE,
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_error(text: str) -> str:
    first = text.splitlines()[0] if text else ""
    return _SPACE_RE.sub(" ", _ERROR_NUMBER_RE.sub("#", first.lower())).strip()


def _diagnostic_summary(text: str) -> dict[str, Any]:
    result = _VERIFICATION_RESULT_RE.search(text)
    headlines = []
    for line in text.splitlines():
        match = _PRIMARY_ERROR_RE.match(line)
        if match and not match.group(1).lower().startswith("aborting due to"):
            headlines.append(_SPACE_RE.sub(" ", match.group(1)).strip())
    return {
        "verified_count": int(result.group(1)) if result else None,
        "reported_error_count": int(result.group(2)) if result else None,
        "primary_error_count": len(headlines),
        "primary_error_headlines": headlines,
    }


def _diagnostic_diff(before: str | None, after: str) -> dict[str, Any]:
    previous = _diagnostic_summary(before or "")
    current = _diagnostic_summary(after)
    reasons = []
    before_verified = previous["verified_count"]
    after_verified = current["verified_count"]
    if (
        before_verified is not None
        and after_verified is not None
        and after_verified > before_verified
    ):
        reasons.append("verified_count_increased")
    before_errors = previous["reported_error_count"]
    after_errors = current["reported_error_count"]
    if before_errors is not None and after_errors is not None and after_errors < before_errors:
        reasons.append("reported_error_count_decreased")
    if (
        current["primary_error_count"] > 0
        and current["primary_error_count"] < previous["primary_error_count"]
    ):
        reasons.append("primary_error_count_decreased")
    return {
        "diagnostic_changed": before is not None and before != after,
        "verified_count_before": before_verified,
        "verified_count_after": after_verified,
        "reported_error_count_before": before_errors,
        "reported_error_count_after": after_errors,
        "primary_error_count_before": previous["primary_error_count"],
        "primary_error_count_after": current["primary_error_count"],
        "confirmed_progress": bool(reasons),
        "confirmed_reasons": reasons,
    }


class ExplicitCompletionReActConverter(ReActConverter):
    """Require explicit completion and progressively correct malformed responses."""

    def __init__(
        self,
        *args: Any,
        guard: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.guard = guard
        self.consecutive_format_errors = 0

    def _enforce_progress_action(self, result: ParseResult) -> ParseResult:
        if self.guard is None:
            return result
        attempted_action = None
        if result.type == ParseResultType.TASK_COMPLETE:
            attempted_action = TASK_COMPLETE_SIGNAL
        elif result.type == ParseResultType.ACTION and result.action is not None:
            attempted_action = result.action.name
        if attempted_action is None:
            return result
        message = self.guard.progress_action_requirement_error(attempted_action)
        if message is None:
            return result
        self.consecutive_format_errors += 1
        return ParseResult(
            type=ParseResultType.FORMAT_ERROR,
            error_message=message,
        )

    def _format_error(self) -> ParseResult:
        self.consecutive_format_errors += 1
        return ParseResult(
            type=ParseResultType.FORMAT_ERROR,
            error_message=(
                STRONG_ACTION_ERROR
                if self.consecutive_format_errors >= 3
                else STRICT_ACTION_ERROR
            ),
        )

    def parse_response(self, response: str) -> ParseResult:
        if response.strip() == TASK_COMPLETE_SIGNAL:
            self.consecutive_format_errors = 0
            return self._enforce_progress_action(
                ParseResult(type=ParseResultType.TASK_COMPLETE)
            )
        if TASK_COMPLETE_SIGNAL in response or self.ACTION_MARKER not in response:
            return self._format_error()

        action_text = response.split(self.ACTION_MARKER, 1)[1].lstrip()
        json_start = action_text.find("{")
        if json_start < 0:
            return self._format_error()
        try:
            action_data, _ = json.JSONDecoder().raw_decode(action_text[json_start:])
        except json.JSONDecodeError:
            return self._format_error()
        if (
            not isinstance(action_data, dict)
            or not isinstance(action_data.get("name"), str)
            or not isinstance(action_data.get("arguments", {}), dict)
        ):
            return self._format_error()
        self.consecutive_format_errors = 0
        return self._enforce_progress_action(
            ParseResult(
                type=ParseResultType.ACTION,
                action=ParsedAction(
                    name=action_data["name"],
                    arguments=action_data.get("arguments", {}),
                ),
            )
        )


@dataclass
class VerusLoopGuard:
    """Track semantic progress, intervene softly, and stop only repeated stalls."""

    workspace: VerusWorkspace
    max_consecutive_format_errors: int = 6
    max_premature_completions: int = 6
    max_repeated_tool_failure: int = 4
    max_repeated_action_observation: int = 5
    max_steps_without_material_progress: int = 10
    reasoning_extension_turns: int = 5
    hypothesis_extension_turns: int = 3
    max_reasoning_extensions_per_stage: int = 2
    max_progress_action_enforcements: int = 3
    skill_navigation_enabled: bool = False
    skill_navigation_interval: int = 8
    format_errors: int = 0
    premature_completions: int = 0
    tool_errors: int = 0
    consecutive_format_errors: int = 0
    consecutive_premature_completions: int = 0
    repeated_tool_failure_count: int = 0
    repeated_action_observation_count: int = 0
    information_action_streak: int = 0
    max_information_action_streak: int = 0
    material_progress_events: int = 0
    reasoning_progress_accepted: int = 0
    reasoning_progress_rejected: int = 0
    reasoning_progress_reminders: int = 0
    progress_action_enforcements: int = 0
    pending_progress_action_violations: int = 0
    steps_without_material_progress: int = 0
    max_steps_without_material_progress_seen: int = 0
    max_adaptive_no_progress_limit_seen: int = 0
    edit_verus_cycles: int = 0
    skill_navigation_checkpoints: int = 0
    no_progress_guard_armed: bool = False
    _candidate_changed_since_verus: bool = False
    interventions: list[dict[str, Any]] = field(default_factory=list)
    _pending_interventions: list[str] = field(default_factory=list)
    _last_tool_failure_fingerprint: str | None = None
    _last_action_observation_fingerprint: str | None = None
    _last_candidate_sha256: str = field(init=False)
    _last_verus_fingerprint: str | None = None
    _exploration_nudge_interval: int = field(init=False)
    _next_exploration_nudge: int = field(init=False)
    _next_skill_navigation_checkpoint: int = field(init=False)
    _information_since_skill_read: int = 0
    _fruitless_search_streak: int = 0
    _stage_reasoning_extensions: int = 0
    _stage_reasoning_extension_turns: int = 0
    _mid_progress_reminder_sent: bool = False
    _last_deadline_reminder_limit: int | None = None
    _reasoning_checkpoint_fingerprints: set[str] = field(default_factory=set)
    _progress_evidence_turns_used: set[int] = field(default_factory=set)
    _evidence_observations: dict[int, tuple[str, str, bool]] = field(default_factory=dict)
    _verus_diffs_by_turn: dict[int, dict[str, Any]] = field(default_factory=dict)
    _last_verus_text: str | None = None
    _last_material_progress_step: int = 0
    _required_progress_evidence_turn: int | None = None
    reasoning_progress_events: list[dict[str, Any]] = field(default_factory=list)
    _step_number: int = 0

    def __post_init__(self) -> None:
        self._last_candidate_sha256 = sha256_file(self.workspace.candidate_path)
        line_count = len(
            self.workspace.candidate_path.read_text(encoding="utf-8").splitlines()
        )
        self._exploration_nudge_interval = (
            10 if line_count <= 500 else 16 if line_count <= 1500 else 24
        )
        self._next_exploration_nudge = self._exploration_nudge_interval
        self._next_skill_navigation_checkpoint = self.skill_navigation_interval
        self.max_adaptive_no_progress_limit_seen = self.max_steps_without_material_progress

    def set_initial_diagnostic(self, diagnostic: str) -> None:
        self._last_verus_fingerprint = _sha256_text(diagnostic)
        self._last_verus_text = diagnostic

    def _schedule(self, kind: str, message: str) -> None:
        if message in self._pending_interventions:
            return
        self._pending_interventions.append(message)
        self.interventions.append(
            {"after_step": self._step_number, "kind": kind, "message": message}
        )

    def consume_intervention(self) -> str | None:
        if not self._pending_interventions:
            return None
        messages = list(self._pending_interventions)
        self._pending_interventions.clear()
        return "\n\n".join(messages)

    def _current_stage_evidence_hint(self) -> str:
        eligible_verus_turns = [
            turn
            for turn, (action_name, _observation, is_error) in self._evidence_observations.items()
            if turn >= self._last_material_progress_step
            and action_name == "run_verus"
            and not is_error
        ]
        hint = (
            f"eligible evidence turns for the current proof stage start at "
            f"{self._last_material_progress_step}"
        )
        if eligible_verus_turns:
            latest = max(eligible_verus_turns)
            hint += (
                f"; the latest eligible run_verus Action turn is {latest}. "
                f"If its changed diagnostic supports the checkpoint, cite "
                f"evidence_turns: [{latest}]"
            )
        return hint

    def progress_action_requirement_error(self, attempted_action: str) -> str | None:
        required_turn = self._required_progress_evidence_turn
        if required_turn is None or attempted_action == "record_proof_progress":
            return None
        self.progress_action_enforcements += 1
        self.pending_progress_action_violations += 1
        if self.pending_progress_action_violations >= self.max_progress_action_enforcements:
            raise RuntimeError(
                "Verus loop stopped after ignoring the mandatory evidence-backed "
                f"progress report {self.pending_progress_action_violations} consecutive times"
            )
        return (
            f"{PROGRESS_PROTOCOL_PREFIX} Action {attempted_action!r} was not executed. "
            "An effective edit changed the Verus diagnostic, so the next Action MUST "
            "be record_proof_progress. Cite the diagnostic as "
            f"evidence_turns: [{required_turn}]. Separate observed_fact, a tentative "
            "working_hypothesis, and a concrete next_test; then set next_action to the "
            "exact tool name you intended to use."
        )

    def record_proof_progress(
        self,
        obstacle: str,
        evidence_turns: list,
        observed_fact: str,
        working_hypothesis: str,
        next_test: str,
        next_action: str,
    ) -> str:
        """Grant bounded time for an auditable fact-hypothesis-test checkpoint."""
        try:
            if not self.no_progress_guard_armed:
                raise ValueError(
                    "reasoning progress may be recorded only after an effective "
                    "edit-to-Verus cycle arms the no-progress guard"
                )
            report_fields = {
                "obstacle": obstacle,
                "observed_fact": observed_fact,
                "working_hypothesis": working_hypothesis,
                "next_test": next_test,
            }
            short_fields = [name for name, value in report_fields.items() if len(value.strip()) < 20]
            if short_fields:
                raise ValueError(
                    "obstacle, observed_fact, working_hypothesis, and next_test must "
                    f"each contain at least 20 characters; too short: {short_fields}"
                )
            if _OBSERVED_FACT_OVERCLAIM_RE.search(observed_fact):
                raise ValueError(
                    "observed_fact must contain only directly observed verifier or tool "
                    "facts. A failed proof obligation means unproved, not false or violated; "
                    "move causal claims and proposed repairs to working_hypothesis"
                )
            if not _HYPOTHESIS_MARKER_RE.search(working_hypothesis):
                raise ValueError(
                    "working_hypothesis must be explicitly tentative (for example: may, "
                    "might, could, appears, insufficient, unknown, or needs testing)"
                )
            if next_action not in _REASONING_NEXT_ACTIONS:
                raise ValueError(
                    f"next_action must be one of {sorted(_REASONING_NEXT_ACTIONS)}"
                )
            if (
                not isinstance(evidence_turns, list)
                or not 1 <= len(evidence_turns) <= 2
                or not all(
                    isinstance(turn, int) and not isinstance(turn, bool)
                    for turn in evidence_turns
                )
            ):
                raise ValueError(
                    "evidence_turns must contain one or two integer Action turn IDs"
                )
            cited = sorted(set(evidence_turns))
            if (
                self._required_progress_evidence_turn is not None
                and self._required_progress_evidence_turn not in cited
            ):
                raise ValueError(
                    "the mandatory changed diagnostic must be cited as "
                    f"evidence_turns: [{self._required_progress_evidence_turn}]"
                )
            if self._stage_reasoning_extensions >= self.max_reasoning_extensions_per_stage:
                raise ValueError(
                    "the reasoning-progress extension limit for this proof stage was reached"
                )
            if all(turn in self._progress_evidence_turns_used for turn in cited):
                raise ValueError(
                    "progress evidence was already used in this proof stage; cite at least "
                    "one new eligible evidence turn"
                )
            evidence_sources: list[dict[str, Any]] = []
            verifier_diffs: list[dict[str, Any]] = []
            for turn in cited:
                source = self._evidence_observations.get(turn)
                if source is None:
                    raise ValueError(
                        f"evidence turn {turn} does not exist; "
                        f"{self._current_stage_evidence_hint()}"
                    )
                action_name, observation, is_error = source
                if turn < self._last_material_progress_step:
                    raise ValueError(
                        f"evidence turn {turn} predates the current proof stage; "
                        f"{self._current_stage_evidence_hint()}"
                    )
                if is_error:
                    raise ValueError(f"evidence turn {turn} is a failed tool call")
                if action_name not in _PROGRESS_EVIDENCE_ACTIONS:
                    raise ValueError(
                        f"evidence turn {turn} uses ineligible action {action_name!r}"
                    )
                evidence_sources.append(
                    {
                        "turn": turn,
                        "action": action_name,
                        "observation_sha256": _sha256_text(observation),
                        "observation_chars": len(observation),
                    }
                )
                if turn in self._verus_diffs_by_turn:
                    verifier_diffs.append(
                        {"turn": turn, **self._verus_diffs_by_turn[turn]}
                    )
            fingerprint_text = "\n".join(
                (obstacle, observed_fact, working_hypothesis, next_test)
            )
            fingerprint = _sha256_text(_SPACE_RE.sub(" ", fingerprint_text.lower()).strip())
            if fingerprint in self._reasoning_checkpoint_fingerprints:
                raise ValueError("the same reasoning checkpoint was already recorded")

            confirmed = any(diff["confirmed_progress"] for diff in verifier_diffs)
            progress_kind = (
                "confirmed_verifier_progress" if confirmed else "hypothesis_refinement"
            )
            extension_turns = (
                self.reasoning_extension_turns if confirmed else self.hypothesis_extension_turns
            )
            self._reasoning_checkpoint_fingerprints.add(fingerprint)
            self._progress_evidence_turns_used.update(cited)
            self._stage_reasoning_extensions += 1
            self._stage_reasoning_extension_turns += extension_turns
            self.reasoning_progress_accepted += 1
            adaptive_limit = (
                self.max_steps_without_material_progress
                + self._stage_reasoning_extension_turns
            )
            self.max_adaptive_no_progress_limit_seen = max(
                self.max_adaptive_no_progress_limit_seen, adaptive_limit
            )
            event = {
                "at_step": self._step_number + 1,
                "obstacle": obstacle.strip(),
                "evidence_turns": cited,
                "evidence_sources": evidence_sources,
                "observed_fact": observed_fact.strip(),
                "working_hypothesis": working_hypothesis.strip(),
                "next_test": next_test.strip(),
                "next_action": next_action,
                "progress_kind": progress_kind,
                "verifier_diffs": verifier_diffs,
                "extension_turns": extension_turns,
                "adaptive_limit": adaptive_limit,
            }
            self.reasoning_progress_events.append(event)
            self._required_progress_evidence_turn = None
            self.pending_progress_action_violations = 0
            return (
                f"Reasoning progress accepted as {progress_kind} from cited evidence; "
                f"{extension_turns} bounded turns were added, making the current "
                f"no-material-progress limit {adaptive_limit}. Execute the committed "
                f"next action: {next_action}."
            )
        except ValueError:
            self.reasoning_progress_rejected += 1
            raise

    def premature_completion_message(self, missing: list[str]) -> str:
        base = (
            "[System Check] Completion was rejected. The current candidate still "
            f"requires {', '.join(missing)}. Continue in this same conversation."
        )
        if self.consecutive_premature_completions >= 3:
            return (
                base
                + " Repeated completion claims are not progress. Your next response must "
                "be one concrete Action that gathers missing evidence, edits candidate.rs, "
                "or runs the missing validator."
            )
        return base + " Edit if needed and do not signal completion until both checks pass."

    def _record_material_progress(self) -> None:
        self.material_progress_events += 1
        self.steps_without_material_progress = 0
        self.information_action_streak = 0
        self._information_since_skill_read = 0
        self._fruitless_search_streak = 0
        self._next_exploration_nudge = self._exploration_nudge_interval
        self._next_skill_navigation_checkpoint = self.skill_navigation_interval
        self._stage_reasoning_extensions = 0
        self._stage_reasoning_extension_turns = 0
        self._mid_progress_reminder_sent = False
        self._last_deadline_reminder_limit = None
        self._reasoning_checkpoint_fingerprints.clear()
        self._progress_evidence_turns_used.clear()
        self._last_material_progress_step = self._step_number
        self._last_action_observation_fingerprint = None
        self.repeated_action_observation_count = 0

    def __call__(self, step: AgentStep) -> None:
        self._step_number += 1
        if step.is_format_error:
            if (step.observation or "").startswith(PROGRESS_PROTOCOL_PREFIX):
                return
            self.format_errors += 1
            self.consecutive_format_errors += 1
            if self.consecutive_format_errors >= self.max_consecutive_format_errors:
                raise RuntimeError(
                    "Verus loop stopped after "
                    f"{self.consecutive_format_errors} consecutive responses without "
                    "a parseable Action or exact completion signal"
                )
            return
        self.consecutive_format_errors = 0

        if step.is_final:
            if not self.workspace.validation_status()["complete"]:
                self.premature_completions += 1
                self.consecutive_premature_completions += 1
                if self.consecutive_premature_completions >= 3:
                    self._schedule(
                        "premature_completion",
                        "Do not claim completion again until both validators pass. Choose "
                        "one concrete corrective Action based on the current diagnostic.",
                    )
                if (
                    self.consecutive_premature_completions
                    >= self.max_premature_completions
                ):
                    raise RuntimeError(
                        "Verus loop stopped after "
                        f"{self.consecutive_premature_completions} consecutive premature "
                        "completion signals without current validator passes"
                    )
            else:
                self.consecutive_premature_completions = 0
            return
        self.consecutive_premature_completions = 0

        if step.action is None:
            return
        name = step.action.name
        observation = step.observation or ""
        action_payload = json.dumps(
            {"name": name, "arguments": step.action.arguments},
            ensure_ascii=False,
            sort_keys=True,
        )
        action_observation = _sha256_text(action_payload + "\n" + observation)
        if action_observation == self._last_action_observation_fingerprint:
            self.repeated_action_observation_count += 1
        else:
            self._last_action_observation_fingerprint = action_observation
            self.repeated_action_observation_count = 1
        if self.repeated_action_observation_count == 2:
            self._schedule(
                "repeated_action",
                "The last action and observation repeated without new evidence. Change "
                "the query, inspect a different location, edit the proof, or rerun Verus "
                "only after candidate.rs changes.",
            )
        if (
            self.repeated_action_observation_count
            >= self.max_repeated_action_observation
        ):
            raise RuntimeError(
                "Verus loop stopped after repeating the identical action and observation "
                f"{self.repeated_action_observation_count} times"
            )

        is_tool_error = observation.startswith("Error")
        self._evidence_observations[self._step_number] = (
            name,
            observation,
            is_tool_error,
        )
        if is_tool_error:
            self.tool_errors += 1
            failure = _sha256_text(name + "\n" + _normalized_error(observation))
            if failure == self._last_tool_failure_fingerprint:
                self.repeated_tool_failure_count += 1
            else:
                self._last_tool_failure_fingerprint = failure
                self.repeated_tool_failure_count = 1
            if self.repeated_tool_failure_count == 2:
                self._schedule(
                    "repeated_tool_failure",
                    "The same tool and error class repeated. Re-read that tool's schema "
                    "and use materially different arguments or a different tool.",
                )
            if self.repeated_tool_failure_count >= self.max_repeated_tool_failure:
                raise RuntimeError(
                    "Verus loop stopped after the same tool failure repeated "
                    f"{self.repeated_tool_failure_count} times"
                )
        else:
            self._last_tool_failure_fingerprint = None
            self.repeated_tool_failure_count = 0

        progress_events_before = self.material_progress_events
        completed_edit_verus_cycle = False
        candidate_sha = sha256_file(self.workspace.candidate_path)
        candidate_changed = candidate_sha != self._last_candidate_sha256
        if candidate_changed:
            self._last_candidate_sha256 = candidate_sha
            self._candidate_changed_since_verus = True
            self._record_material_progress()
        elif name == "run_verus":
            verifier_diff = _diagnostic_diff(self._last_verus_text, observation)
            self._verus_diffs_by_turn[self._step_number] = verifier_diff
            self._last_verus_text = observation
            completed_edit_verus_cycle = (
                self._candidate_changed_since_verus and not is_tool_error
            )
            if completed_edit_verus_cycle:
                self._candidate_changed_since_verus = False
                self.edit_verus_cycles += 1
                self.no_progress_guard_armed = True
                self.steps_without_material_progress = 0
            verifier_fingerprint = _sha256_text(observation)
            if verifier_fingerprint != self._last_verus_fingerprint:
                self._last_verus_fingerprint = verifier_fingerprint
                self._record_material_progress()
                if (
                    completed_edit_verus_cycle
                    and not self.workspace.validation_status()["verus_passed"]
                ):
                    self._required_progress_evidence_turn = self._step_number
                    self.pending_progress_action_violations = 0
                if (
                    self.skill_navigation_enabled
                    and not self.workspace.validation_status()["verus_passed"]
                ):
                    self.skill_navigation_checkpoints += 1
                    self._schedule(
                        "skill_navigation_after_diagnostic_change",
                        "[Skill Procedure Check] The Verus diagnostic changed. Return to "
                        "the preloaded root SKILL.md procedure and reclassify the new "
                        "obstacle. Continue from the root when it is sufficient. Only if "
                        "a concrete lower-frequency obstacle directly matches an unread "
                        "card should you consult that one reference. If an already loaded "
                        "card still applies, reuse its Observation without rereading it. "
                        "The authoritative new diagnostic is the Observation from run_verus Action turn "
                        f"{self._step_number}. Before any other Action, report this progress "
                        f"with evidence_turns: [{self._step_number}].",
                    )
        elif name == "run_lynette" and self.workspace.validation_status()[
            "lynette_passed"
        ]:
            self._record_material_progress()

        if name in _INFORMATION_ACTIONS:
            self.information_action_streak += 1
            self.max_information_action_streak = max(
                self.max_information_action_streak, self.information_action_streak
            )
            if name == "read_skill_reference" and not is_tool_error:
                self._information_since_skill_read = 0
                self._fruitless_search_streak = 0
                self._next_skill_navigation_checkpoint = self.skill_navigation_interval
            else:
                self._information_since_skill_read += 1
                if (
                    name in _FRUITLESS_SEARCH_ACTIONS
                    and (is_tool_error or "0 result(s)" in observation)
                ):
                    self._fruitless_search_streak += 1
                else:
                    self._fruitless_search_streak = 0

            if (
                self.skill_navigation_enabled
                and (
                    self._information_since_skill_read
                    >= self._next_skill_navigation_checkpoint
                    or self._fruitless_search_streak >= 2
                )
            ):
                reason = (
                    "repeated empty or failed searches"
                    if self._fruitless_search_streak >= 2
                    else "an extended information-gathering sequence"
                )
                self.skill_navigation_checkpoints += 1
                self._schedule(
                    "skill_navigation_checkpoint",
                    "[Skill Procedure Check] After "
                    f"{reason}, return to the preloaded root SKILL.md procedure and "
                    "reclassify the current obstacle. Use the root's narrowest applicable "
                    "procedure when it is sufficient. If one concrete lower-frequency "
                    "obstacle precisely matches an unread card, consult that single "
                    "reference; otherwise continue with one targeted evidence Action. "
                    "Do not reread an already loaded card.",
                )
                self._fruitless_search_streak = 0
                self._next_skill_navigation_checkpoint = (
                    self._information_since_skill_read + self.skill_navigation_interval
                )

            if self.information_action_streak >= self._next_exploration_nudge:
                self._schedule(
                    "exploration_checkpoint",
                    "Exploration remains allowed, but pause to synthesize what the new "
                    "evidence established. If a proof edit is justified, make it; if not, "
                    "use the next targeted information Action to obtain the specific "
                    "missing fact. After an effective edit-to-Verus cycle, use "
                    "record_proof_progress only for a new fact-hypothesis-test checkpoint "
                    "backed by cited tool turns; ordinary reading is not reasoning progress.",
                )
                self._next_exploration_nudge += self._exploration_nudge_interval
        elif name not in {"replace_text", "run_verus", "run_lynette", "record_proof_progress"}:
            self.information_action_streak = 0

        if self.no_progress_guard_armed:
            if (
                self.material_progress_events == progress_events_before
                and not completed_edit_verus_cycle
            ):
                self.steps_without_material_progress += 1
                self.max_steps_without_material_progress_seen = max(
                    self.max_steps_without_material_progress_seen,
                    self.steps_without_material_progress,
                )
                adaptive_limit = (
                    self.max_steps_without_material_progress
                    + self._stage_reasoning_extension_turns
                )
                self.max_adaptive_no_progress_limit_seen = max(
                    self.max_adaptive_no_progress_limit_seen, adaptive_limit
                )
                midpoint = max(1, self.max_steps_without_material_progress // 2)
                if (
                    not self._mid_progress_reminder_sent
                    and self.steps_without_material_progress >= midpoint
                ):
                    self._mid_progress_reminder_sent = True
                    self.reasoning_progress_reminders += 1
                    self._schedule(
                        "reasoning_progress_midpoint",
                        "[Progress Check "
                        f"{self.steps_without_material_progress}/{adaptive_limit}] If new "
                        "evidence since the last material change identifies a different "
                        "obstacle, rules out a hypothesis, or determines the next edit, "
                        "your next Action MUST be record_proof_progress. Cite one or two "
                        "real evidence turn IDs and use an exact next_action tool name. Otherwise do "
                        "not report; take one targeted Action.",
                    )
                deadline_warning_at = max(midpoint + 1, adaptive_limit - 2)
                if (
                    deadline_warning_at < adaptive_limit
                    and self.steps_without_material_progress >= deadline_warning_at
                    and self._last_deadline_reminder_limit != adaptive_limit
                ):
                    self._last_deadline_reminder_limit = adaptive_limit
                    self.reasoning_progress_reminders += 1
                    self._schedule(
                        "reasoning_progress_deadline",
                        "[Progress Deadline "
                        f"{self.steps_without_material_progress}/{adaptive_limit}] Before "
                        "more reading, use record_proof_progress if you have a new "
                        "evidence-backed fact-hypothesis-test checkpoint; otherwise edit, run "
                        "Verus, or take the single missing targeted Action. Repeated summaries do not "
                        "qualify.",
                    )
                if self.steps_without_material_progress >= adaptive_limit:
                    raise RuntimeError(
                        "Verus loop stopped after "
                        f"{self.steps_without_material_progress} consecutive tool turns "
                        "without material proof progress. Evidence-backed reasoning "
                        "checkpoints may extend the base limit only within the bounded "
                        "per-stage allowance"
                    )
        else:
            self.steps_without_material_progress = 0

    def summary(self) -> dict[str, Any]:
        return {
            "strict_explicit_completion": True,
            "max_consecutive_format_errors": self.max_consecutive_format_errors,
            "max_premature_completions": self.max_premature_completions,
            "max_repeated_tool_failure": self.max_repeated_tool_failure,
            "max_repeated_action_observation": self.max_repeated_action_observation,
            "max_steps_without_material_progress": self.max_steps_without_material_progress,
            "reasoning_extension_turns": self.reasoning_extension_turns,
            "hypothesis_extension_turns": self.hypothesis_extension_turns,
            "max_reasoning_extensions_per_stage": self.max_reasoning_extensions_per_stage,
            "max_progress_action_enforcements": self.max_progress_action_enforcements,
            "progress_action_enforcements": self.progress_action_enforcements,
            "pending_progress_action_violations_at_end": self.pending_progress_action_violations,
            "required_progress_action_pending_at_end": self._required_progress_evidence_turn is not None,
            "required_progress_evidence_turn_at_end": self._required_progress_evidence_turn,
            "maximum_adaptive_no_progress_limit": (
                self.max_steps_without_material_progress
                + self.reasoning_extension_turns * self.max_reasoning_extensions_per_stage
            ),
            "max_adaptive_no_progress_limit_seen": self.max_adaptive_no_progress_limit_seen,
            "skill_navigation_enabled": self.skill_navigation_enabled,
            "skill_navigation_interval": self.skill_navigation_interval,
            "exploration_nudge_interval": self._exploration_nudge_interval,
            "format_errors": self.format_errors,
            "premature_completions": self.premature_completions,
            "tool_errors": self.tool_errors,
            "material_progress_events": self.material_progress_events,
            "reasoning_progress_accepted": self.reasoning_progress_accepted,
            "reasoning_progress_rejected": self.reasoning_progress_rejected,
            "reasoning_progress_reminders": self.reasoning_progress_reminders,
            "reasoning_progress_events": list(self.reasoning_progress_events),
            "stage_reasoning_extensions_at_end": self._stage_reasoning_extensions,
            "stage_reasoning_extension_turns_at_end": self._stage_reasoning_extension_turns,
            "skill_navigation_checkpoints": self.skill_navigation_checkpoints,
            "steps_without_material_progress_at_end": self.steps_without_material_progress,
            "max_steps_without_material_progress_seen": self.max_steps_without_material_progress_seen,
            "edit_verus_cycles": self.edit_verus_cycles,
            "no_progress_guard_armed": self.no_progress_guard_armed,
            "max_information_action_streak": self.max_information_action_streak,
            "repeated_tool_failure_count_at_end": self.repeated_tool_failure_count,
            "repeated_action_observation_count_at_end": self.repeated_action_observation_count,
            "intervention_count": len(self.interventions),
            "interventions": list(self.interventions),
        }


def create_reasoning_progress_tool(guard: VerusLoopGuard) -> Tool:
    @tool(
        name="record_proof_progress",
        description=(
            "After an effective edit-to-Verus cycle, record a strict epistemic checkpoint "
            "before further exploration. Separate direct tool facts from a tentative "
            "hypothesis and a concrete next test. A failed assertion or postcondition means "
            "only that Verus did not prove it, not that the property is false. Cite one or "
            "two real Action turn IDs; the host classifies verifier-confirmed progress and "
            "chooses a bounded extension. The same evidence cannot earn time twice."
        ),
    )
    def record_proof_progress(
        obstacle: str,
        evidence_turns: list,
        observed_fact: str,
        working_hypothesis: str,
        next_test: str,
        next_action: str,
    ) -> str:
        """Record a bounded, auditable fact-hypothesis-test checkpoint.

        Args:
            obstacle: Concise current proof obstacle.
            evidence_turns: One or two integer Action turn IDs from this proof stage. For
                a changed diagnostic, cite the immediately preceding run_verus Action turn.
            observed_fact: Only facts directly present in cited tool output; say unproved,
                never false or violated, for a failed Verus obligation.
            working_hypothesis: Explicitly tentative causal interpretation using language
                such as may, might, could, insufficient, unknown, or needs testing.
            next_test: Concrete check or smallest change that could confirm or refute the
                working hypothesis.
            next_action: Exact tool name: read_skill_reference, read_file, search_file,
                search_verus_docs, lookup_vstd_symbol, edit_lines, insert_lines,
                replace_text, or run_verus.
        """
        return guard.record_proof_progress(
            obstacle=obstacle,
            evidence_turns=evidence_turns,
            observed_fact=observed_fact,
            working_hypothesis=working_hypothesis,
            next_test=next_test,
            next_action=next_action,
        )

    return record_proof_progress


class ProgressInterventionClient(LLMClient):
    """Inject one pending host nudge into the next request without changing history."""

    def __init__(self, inner: LLMClient, guard: VerusLoopGuard) -> None:
        self.inner = inner
        self.guard = guard

    def _messages(self, messages: list[Message]) -> list[Message]:
        intervention = self.guard.consume_intervention()
        if intervention is None:
            return messages
        updated = [Message(role=m.role, content=m.content) for m in messages]
        suffix = "\n\n[Host Progress Intervention]\n" + intervention
        if updated and updated[-1].role == "user":
            updated[-1].content += suffix
        else:
            updated.append(Message(role="user", content=suffix.lstrip()))
        return updated

    def chat(self, messages: list[Message], settings: ModelSettings | None = None) -> str:
        return self.inner.chat(self._messages(messages), settings)

    async def chat_async(
        self, messages: list[Message], settings: ModelSettings | None = None
    ) -> str:
        return await self.inner.chat_async(self._messages(messages), settings)

    async def aclose(self) -> None:
        close = getattr(self.inner, "aclose", None)
        if close is not None:
            await close()
