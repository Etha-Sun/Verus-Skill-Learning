# Optimizer branch-awareness transcript audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-09-26`
- status: `complete_read_only_audit`
- scope: matched augmented extraction agent calls and merge information flow

## Question and evidence

The user asked whether trace-analysis agents recognized augmentation and
multiple checkpoint continuations. The existing augmented extraction contains
three per-task Codex sessions and one merge session, with CLI metadata, visible
agent messages, completed shell commands and outputs, and final JSON proposals.
The calls used `gpt-5.6-sol` with high reasoning effort.

AC explicitly identified six checkpoints with three continuations each; AL
identified seven checkpoints with paired hinted/no-hint branches. IR initially
used generic trajectory wording, then explicitly compared all fresh branches,
including failed/slower arms. Recorded commands read branch events, source/diff
snapshots, hints, validations and paired costs. IR corrected one initial path
resolution error. Final per-task sidecars compare minimal preservation repair
with proof rewrites, acknowledge a failed hinted AC arm, retain slower AL hints,
and acknowledge identical actions across all arms at another AC checkpoint.

This is evidence of branch-aware comparison in visible behavior and outputs.
It does not establish exhaustive comprehension, causal hint benefits, or new
skill-card efficiency. Checkpoints are correlated; fresh actors lacked the
historical prefix; hindsight and historical runtime differences remain caveats.

## Merge evidence gap

Per-task `card_evidence` contains detailed executed actions, counterexamples,
cost observations and limitations. Actual `merge_inputs.json` entries only have
`reasoning`, `edits`, `source_task`, and `evidence_root`. The current
`fork_card_optimize.py` normalisation path forwards the patch, omitting the
top-level sidecar. The merge session made no tool calls to recover it. Thus
detailed branch comparisons were retained on disk but not directly supplied to
the merge. Whether supplying them improves cards requires a separate experiment.
The analyst prompt also deliberately excludes numerical claims from deployable
card text; absence of numbers in cards does not imply absence of analysis.

## Artifacts and record boundaries

All pointers below are relative to external run storage:

- Sources: `skillopt-validation-20260923/extraction/augmented/optimizer/`
- Readable audit: `skillopt-validation-20260923/audit/analysis-session-review-20260926/README.md`
- Four rendered transcripts and hash inventory: same audit directory.
- Prompt contract: repository `skillopt-verusage/prompts/fork_cards/matched_analyst.md`.

The wrapper retained visible JSON events, stderr and command metadata; it did
not retain stdin verbatim. Prompt components and reflection inputs remain
separately available. These records are not hidden reasoning or a full wire-level
API transcript.

## Next action and safety

A possible extraction-only follow-up is a frozen-input merge comparison with
full evidence sidecars and explicit justification for retained/merged/dropped
cards. No extraction code changes, merge reruns, API calls or GPU use occurred
here. Validation remains stopped pending the separate incomplete-payload audit.
Only readable derived audit files and compact research memory were written.
Original traces, optimizer outputs and raw/sealed data remain unchanged.
