# Hint-visible SkillOpt fork-card diagnostic from complete historical traces

## Inputs and export

The original-three archive was retrieved from the public GitHub Release
`skillopt-original-three-20260922`. Its 1,260,734 bytes, 241 files, and SHA-256
`e3ebeb101e965f9a3c10bb0219e2cff69ed4e51cdf3fa47b1c70b1caa8e89ad2` match the
provided transfer manifest. The recovered historical hint publication is
commit `76f75dae6a0ad791e22aea5dab44ede0e820c3c0`.

The real external packet root is
`${VERUS_SKILL_RUN_ROOT}/skillopt-fork-packets-20260922/`. It contains three
tasks, 19 checkpoints, and 57 continuation branches (38 hints, 19 no-hint).
Original event counts: IR 104, AC 148, AL 94. Every original prefix plus suffix
reconstructs the corresponding complete event stream; all copied branch hashes
were verified. The actor did not observe its historical prefix, a distinction
preserved in the exported packet. Teacher hints are labeled interventions.

## Optimizer configuration and result

GPT-5.6 Sol/high via the existing Codex backend, initial skill seed, one Reflect
item per task, at most two proposals per task, native failure merge, and at most
four selected edits. Three analysts produced six candidate cards.

The first output, `skillopt-hint-visible/`, is retained as rejected evidence.
The generic merge prompt converted cards into prose insertions and dropped
all four required field labels. One insertion also split a seed sentence.
The automatic audit rejected it rather than treating it as a usable card bank.

A fork-specific merge prompt now preserves four explicit fields and append-only
cards. `--reuse-reflections-from` validates the source packet, skill, model,
analyst prompt and batching settings, then records patch hashes and reuses all
three task patches. The revised output at `skillopt-hint-visible-card-merge/`
contains four cards and passes the automatic audit. Candidate size is 3,901
bytes; SHA-256 is
`a88338dc417afe72de72a1d926fced5fbbae980eba0bf76a2644775bf78757f6`.
The initial skill remains intact.

Card topics: source-witness activation and lifting; proof-import safety drift;
unsupported inner trigger attributes; common-suffix sequence cancellation.
The final pool has four edits, so native rank returns it without a model call.

## Usage and verification

Across both invocations there were five successful native optimizer attempts:
three analyst calls and two merge calls. No analyst was rerun for the format
correction. CLI-reported cumulative input was 2,581,891 tokens and output was
25,226 tokens, excluding independent Astra review. These totals are neither
a single context size nor an inferred dollar charge. The original summary
counted logical-call records as extra calls; the corrected summary counts only
attempt records. The original result is retained, with corrected combined
usage in `skillopt-hint-visible-card-merge/combined_usage.json`.

Focused tests: 21 passed, 6 subtests passed. Regression checks cover per-card
field requirements, append-only shape, and logical/attempt count separation.

## Independent Astra review and interpretation

Astra reviewed all 57 terminal branch results, all 19 original checkpoint
signals, six task proposals, both candidates, and representative source/event
transitions. Its report and corrected provenance are below
`skillopt-hint-visible-card-merge/astra-audit/` (`AUDIT.md`,
`audit_metadata.json`, `branch_outcomes.json`). This was not an exhaustive
independent semantic read of every event. The candidate hash was rechecked.

All four cards are evidence-supported diagnostic outputs. They refine
observable triggers and actions relative to the ordinary train-40 stage-1
skill, while retaining less broad guidance (including no explicit bounded
rollback, infrastructure baseline, named-closure restrictions, or broad lemma
planning). All four underlying mechanisms already occur in original traces;
multiple no-hint branches also reproduce them. No augmentation-exclusive
mechanism or downstream utility is established by this run.

The raw merge rationale incorrectly attributes some AC cases to IR. The
reviewed sidecar corrects witness support to IR+AC, import support to IR+AL,
unsupported-auto support to AC, and sequence support to AL. The raw candidate
and rationale remain untouched. Two unsuccessful AC hint branches are
preserved; a successful helper-based AC branch prevents treating helper
abstraction itself as the cause of failure. Automatic shape acceptance alone
does not certify semantic provenance.

The ordinary reference was learned from 40 tasks and this diagnostic from
three; the candidate starts at initial.md, not from the ordinary reference.
No matched downstream or original-only optimizer comparison has been run.
The backend retains an attempt/usage ledger, but not a complete analyst
file-read transcript; it is not possible to certify that every available
file was actually inspected. All evidence was supplied as complete packets;
manual review verifies specific supporting and contradicting examples.

No original or continuation trajectory was rerun. No raw or sealed input was
modified, and generated traces, skills, and ledgers remain in external run
storage. No causal hint-effect or downstream performance benefit is claimed.

## User clarification: stage-specific efficiency is central

The user clarified that useful skills should capture checkpoint-local hints
associated with large reductions in subsequent search, even if the original
trajectory eventually discovered the same mechanism. The first audit's lack
of augmentation-exclusive mechanisms does not rule out that kind of value.
An offline supplement now exists at the revised output's
`efficiency-audit/EFFICIENCY_FINDINGS.md`, with all 19 paired costs in the
external `checkpoint_costs.json`. Illustrative same-checkpoint successes show
substantially lower actor completion counts for IR CP06, AL CP03, and AC CP01
v2, alongside corresponding repair-path contrasts. Teacher counts are listed
separately, unsuccessful arms are retained, and CLI/tool drift limits causal
interpretation. No additional model call or rerun occurred.

The first analyst prompt did not explicitly request cost comparisons or avoided
search detours; a future extraction should require a checkpoint-local cost and
path contrast as evidence for each card. Timing/search reduction and mechanism
novelty must be evaluated separately. The existing card output only partially
captures this clarified objective.
