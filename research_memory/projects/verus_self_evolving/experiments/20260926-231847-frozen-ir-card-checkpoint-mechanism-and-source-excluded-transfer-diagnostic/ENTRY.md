# Frozen IR card checkpoint mechanism and source excluded transfer diagnostic

## Status

Complete. All 18 authorized continuations finished; independent Astra design
and final evidence reviews are complete. No follow-up expansion was launched.

## Frozen design

Exact IR-only preservation proposals from matched original-only and augmented
analyses were frozen before the later cross-task merge. Conditions: shared
initial executive seed without a card, with the original IR card, or with the
augmented IR card. The prior train-40 full skill is a textual reference only,
not an evaluated arm. Cards were appended directly to the prompt.

Fresh actors received identical checkpoint source and fresh local diagnostics,
not historical conversation, future continuations, hints or reference repairs.
IR CP06: three repetitions each. AL CP07 and two synthetic IR boundaries:
one each. Existing DeepSeek V4 Pro/high, 600 seconds, two workers. Fixed cards
and schedule; no card tuning, extraction rerun, retrieval or local GPU.
All four checkpoint states and hidden repairs passed expected local preflight.

## Findings

All 18 pass independent Verus and preservation within budget, with V2_TRACE,
no incomplete provider responses and unchanged input/seed. On IR, each of the
six card attempts used one minimal import/qualified-macro edit and preserved
the established proof. Two no-card attempts also did so. The third no-card
attempt made seven edits, replaced and rebuilt the working proof, and explored
an unavailable optional formatter. This one large detour dominates the mean.
Both cards show local reminder utility; augmentation does not beat original
extraction on the primary comparison. See external tables for all observations,
input/output usage, medians, ranges, wall time and estimated charges.

AL: every condition removed the unused import without adding an unnecessary
helper call. No-card used the least output; augmented used less input and lower
estimated charge in its single attempt. No stable transfer benefit is shown.
False-assert boundary: all fixed the proof, without blindly applying import
cleanup. Augmented chose a library-lemma rewrite and used more output than the
simple deletion in the other conditions. Mixed-change boundary: both cards
jointly restored main and repaired the import in one edit; no-card needed two.
All preserved the immutable original executable behavior.

Both IR cards already describe a repair available in the original trajectory.
The augmented wording is more explicit about sole-difference diagnosis and
keeping a verified proof, but its incremental utility is not established.
The prior train-40 skill lacks this exact preservation-stage recipe; no live
comparison with that full skill was performed.

## Evidence limits and deviations

These are selected case-level observations. IR is a card-extraction source;
AL is excluded from these IR-only proposals, but researcher-selected from
known training traces. Synthetic boundaries are easy mechanism checks. This
is not blind held-out generalization, autonomous retrieval, discovery of when
to run preservation, or complete-history replay. Repeats are not new tasks or
matched random seeds. Optional diagnostic tool failure affects local cost.

No-card IR r0 passes both validators but violates the instruction to edit only
candidate.rs by writing temporary diagnostics/wrapper files. Protected-location
write attempts were denied. Keep its raw hard/V2 labels and all cost; do not
call it fully process-compliant or delete the inconvenient sample. Astra found
no additional actual outside-candidate writes in the other 17 attempts.

All 18 inherited visibility manifests have a stale initial-candidate field
captured before checkpoint replacement. Original manifests remain untouched.
A separate discrepancy sidecar reconciles each run using the continuation
contract, actual initial event/snapshot, and prompt hashes. Actual checkpoint
and condition exposures match the frozen design; do not claim all raw metadata
fields agree.

## Artifacts and next action

External run root basename: `skillopt-card-case-study-20260926`.
Read `ANALYSIS.md`, `audit/final_review.md`, `audit/outcome_evidence.json`, and
`audit/comparison.json`. Read `audit/ir_cp06--no_card--r0.md` beside the two
corresponding card transcripts for the concrete mechanism and actual diffs.
`closeout.json` records artifact hashes and final gates; `experiment_contract.json`,
`card_provenance.json`, `frozen_inputs.json`, and `schedule.json` fix provenance.
The external driver reuses the existing isolated continuation harness.

Next discriminating study: find a failure mode where original-only traces do
not already reveal the repair and executed forks add positive/negative evidence;
freeze the card before testing separately selected applicable and boundary
cases. Keep direct exposure and retrieval tests distinct. Do not expand this
same preservation example and claim augmentation novelty from repetition.

## Usage and data safety

Recorded actor estimate is about USD 0.62 across 201 settled requests, zero
uncertain requests and zero outstanding reservations. This is not a provider
invoice and excludes historical extraction/teacher expense. Full ledgers and
token tables remain external. Historical raw/sealed trajectories and fixed
benchmark sources were not modified, moved, or committed. Generated variants,
hidden repairs, prompts and traces are external only. No GPU or test access.
