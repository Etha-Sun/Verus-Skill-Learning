from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from react_agent import AgentConfig, AgentResult, LLMClient, ReActAgent, SystemPromptBuilder

from .docs import VerusDocumentation
from .loop_control import (
    ExplicitCompletionReActConverter,
    ProgressInterventionClient,
    VerusLoopGuard,
    create_reasoning_progress_tool,
)
from .tools import SkillReferenceReader, create_reference_tool, create_workspace_tools
from .workspace import VerusWorkspace


def _skill_body(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :].lstrip()
    return text


def _prompt_builder(skill_text: str | None) -> SystemPromptBuilder:
    context = """You are an autonomous Verus proof-repair agent.

Use only the registered tools. input.rs is immutable; edit only candidate.rs
through edit_lines, insert_lines, or single-line replace_text. For every multiline
change, use edit_lines or insert_lines with one JSON string per physical code line;
never embed literal newlines inside a JSON string. Before replacing a brace-delimited
block, read at least one line beyond both edit boundaries and include each existing
opening or closing brace exactly once; structurally unbalanced edits are rejected
without modifying candidate.rs. Preserve executable behavior, signatures, requires,
ensures, and decreases. Never add assume, admit, external_body, axioms, or
verification bypasses. Treat current Verus diagnostics and installed vstd
declarations as ground truth. Use search_file to locate definitions, symbols,
or related lemmas before scanning large files with broad read_file ranges. Do
not stop after a failed attempt. Every response must contain exactly one valid
Action unless it is the exact completion signal. Explore as much as needed, but
prefer targeted actions that add new evidence and periodically synthesize what is
still missing. Do not make a proof edit merely to satisfy a progress reminder.
After an effective edit-to-Verus cycle, if new tool evidence identifies a
different obstacle, rules out a live hypothesis, or determines the next proof
edit, your next Action MUST be record_proof_progress before further reading or
searching. Cite one or two real Action turn IDs in evidence_turns and set
next_action to an exact registered tool name. Structure the report as: (1)
observed_fact containing only facts directly shown by cited output; (2)
working_hypothesis using explicitly tentative language such as may, might, could,
insufficient, unknown, or needs testing; and (3) next_test naming a concrete check
or smallest change that could confirm or refute the hypothesis. A failed assertion
or postcondition means only that Verus did not prove it; it is not evidence that
the property is false, violated, or that a particular field must be updated. When
the report depends on a changed verifier diagnostic, cite the immediately preceding run_verus Action turn rather than an older supporting read. The host
compares adjacent diagnostics and classifies confirmed verifier progress itself.
The host will not execute any other Action until a mandatory report is accepted.
The same evidence cannot earn extra time twice. Do not report ordinary reading,
repeated analysis, or unsupported guesses. Accepted reports grant only bounded
diagnosis turns. Signal task completion only after run_verus and run_lynette both
pass for the current file. Immediately after run_lynette passes for a candidate
whose latest run_verus also passed, emit exactly ACTION: TASK_COMPLETE. Do not
call record_proof_progress or any other tool after both checks pass.
"""
    if skill_text:
        context += (
            "\nThe following root SKILL.md has been loaded for this session; its full "
            "guidance is included below. If the skill is relevant to the current proof "
            "operation, follow its instructions. Act on your own judgment only when the "
            "skill does not cover the operation. Reference resources mentioned by the "
            "root are available through read_skill_reference in the same conversation. "
            "Open them on demand when the root directs you to lower-frequency detail; "
            "they are not a mandatory first action.\n\n"
            + skill_text
        )
    return (
        SystemPromptBuilder()
        .set_role("You repair Verus proofs through a multi-turn ReAct loop.")
        .set_domain_context(context)
        .set_examples("")
        .set_reminders(
            "Use one Action at a time and wait for its Observation. Keep editing and "
            "verifying in this same conversation. Use ACTION: TASK_COMPLETE only "
            "after both validation tools pass on the current candidate."
        )
    )


@dataclass
class VerusRunResult:
    success: bool
    agent_result: AgentResult
    validation: dict[str, Any]
    initial_diagnostic: str
    reference_reads: list[str]
    loop_control: dict[str, Any]


class VerusProofAgent:
    """Verus adapter around the unmodified upstream Trace2Skill ReAct loop."""

    def __init__(
        self,
        client: LLMClient,
        workspace: VerusWorkspace,
        documentation: VerusDocumentation,
        skill_dir: Path | None = None,
        max_turns: int = 60,
        max_steps_without_material_progress: int = 10,
        verbose: bool = True,
    ) -> None:
        self.workspace = workspace
        self.skill_dir = skill_dir.resolve() if skill_dir else None
        self.reference_reader = (
            SkillReferenceReader(self.skill_dir) if self.skill_dir else None
        )
        self.loop_guard = VerusLoopGuard(
            workspace,
            max_steps_without_material_progress=max_steps_without_material_progress,
            skill_navigation_enabled=False,
        )
        tools = create_workspace_tools(workspace) + documentation.create_tools()
        tools.append(create_reasoning_progress_tool(self.loop_guard))
        skill_text = None
        if self.skill_dir:
            skill_text = _skill_body(self.skill_dir)
            tools.append(create_reference_tool(self.reference_reader))
        prompt_builder = _prompt_builder(skill_text)
        intervention_client = ProgressInterventionClient(client, self.loop_guard)
        self.agent = ReActAgent(
            client=intervention_client,
            tools=tools,
            config=AgentConfig(
                max_turns=max_turns,
                verbose=verbose,
                prompt_builder=prompt_builder,
            ),
            on_step=self.loop_guard,
        )
        self.agent.converter = ExplicitCompletionReActConverter(
            prompt_builder=prompt_builder,
            guard=self.loop_guard,
        )

    def run(self, instruction: str = "Complete the proof in candidate.rs.") -> VerusRunResult:
        initial_diagnostic = self.workspace.run_verus()
        self.loop_guard.set_initial_diagnostic(initial_diagnostic)
        task = f"""{instruction}

The host has already run Verus once on the unchanged candidate. Use this exact
initial diagnostic to choose your first information or editing action; do not
invent a different starting failure.

INITIAL VERUS DIAGNOSTIC:
{initial_diagnostic}
"""
        result = self.agent.run(task)
        validation = self.workspace.validation_status()
        while result.success and not validation["complete"] and result.total_turns < self.agent.config.max_turns:
            missing = []
            if not validation["verus_passed"]:
                missing.append("a fresh successful run_verus")
            if not validation["lynette_passed"]:
                missing.append("a fresh successful run_lynette")
            result = self.agent.continue_with_message(
                self.loop_guard.premature_completion_message(missing)
            )
            validation = self.workspace.validation_status()
        reads = self.reference_reader.read_history if self.reference_reader else []
        return VerusRunResult(
            # Host validation is the proof-outcome authority. A model that has
            # already produced a Verus- and Lynette-clean candidate must not be
            # counted as a proof failure merely because it missed the exact
            # completion signal at the turn boundary.
            success=bool(validation["complete"]),
            agent_result=result,
            validation=validation,
            initial_diagnostic=initial_diagnostic,
            reference_reads=list(reads),
            loop_control=self.loop_guard.summary(),
        )
