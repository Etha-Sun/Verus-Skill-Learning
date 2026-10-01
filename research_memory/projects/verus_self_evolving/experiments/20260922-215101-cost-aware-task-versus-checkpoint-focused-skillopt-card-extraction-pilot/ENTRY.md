# Cost-aware task versus checkpoint-focused SkillOpt card extraction pilot

## Metadata

- project: `verus_self_evolving`
- kind: `experiments`
- created_at: `2026-09-22T21:51:01`
- status: `complete_extraction_diagnostic`
- scope: offline extraction quality on three train tasks

## Frozen comparison

Use the existing complete original plus 57 historical continuation packet;
no actor trajectory is rerun. Historical standard extraction is reference A.
New B reads all checkpoint forks with explicit paired costs and detour questions.
New C shares the same prompt and cost evidence, but prioritizes two selected
checkpoints per task. This is reading-scope comparison, not an information
ablation. Both retain task weight one, two proposals per task, Sol/high,
the initial skill, and at most four merged cards within 4,000 bytes.

C nominates the strongest successful relative actor-completion reduction and
one distinct adverse checkpoint, prioritizing failed arms then the worst cost
ratio. Frozen pairs: IR CP06/CP03, AC CP01/CP03, AL CP03/CP02. Stable row order
then v1/v2 order break ties. This outcome-based selection is train-only and
cannot estimate a causal hint effect.

## Evidence and implementation

The driver checks all supplied actor completion counts and outcomes against
packet results before calls. A new prompt requires per-card quantitative
sidecars, executed shortcut versus actual no-hint detour, visible trigger,
validation evidence, teacher cost, and counterexamples. Failed branches remain
available but cannot qualify as cheap successful support. Source task metadata
is attached before native merge. A forwarding wrapper records optimizer CLI
events externally for access auditing.

Focused checks passed: 22 tests and 6 subtests. A no-model wrapper smoke check
verified stdin, stdout, external event capture, and exit status propagation.
All real cost rows and selected pairs passed the preflight.

## Artifacts

All experiment outputs are below
`${VERUS_SKILL_RUN_ROOT}/skillopt-fork-packets-20260922/efficiency-pilot-20260922/`:

- `experiment_contract.json`, frozen before optimizer calls;
- `selection_and_cost_clarification.json`, unchanged selection details;
- `efficiency_task/` and `efficiency_focus/`, independent optimizer runs;
- `audit_outputs.py`, numeric sidecar and command-access audit;
- `automatic_comparison.json`, `run_summary.json`, and `COMPARISON.md`;
- `astra-audit/AUDIT.md`, `summary.json`, `reviewed_candidate_skill.md`,
  `reviewed_card_provenance.json`, and shape/evidence checks.

## Results and independent review

Both new runs completed with three analyst calls and one merge call each: eight
native optimizer attempts, all successful. B proposed and retained four cards;
C proposed five and merged to four. Both raw candidates pass shape and size
checks. B is 3,168 bytes, SHA-256
`049a146c1479d725310fe412df8c94746ba830f715435132f68c2e3243f88f2b`;
C is 3,279 bytes, SHA-256
`c57cda8c549b6b92f8d563febf18b8cbe918c43232edd83e7de39b5303386955`.
All nine quantitative proposal sidecars match recorded actor counts, success
flags, and the frozen teacher-count table. Numeric validation is separate from
semantic provenance and event-reference review.

Astra recommends B as the base for this pilot: it retains an intermediate
illegal-trigger-to-witness decision that C misses, while C includes a weak IR
CP03 contrast whose teacher-inclusive output-token sum exceeds no hint. Both
merges lose an explicit first preservation check. B overgeneralizes macro-path
repair to helpers; C weakens the required AL proof skeleton and broadens the
AC early trigger. The reviewed derivative restores the check and boundaries,
retains four stage-specific cards, and preserves the initial skill. It is a
separately labeled post-audit artifact, not an unmodified optimizer output.

Final card themes: verify preservation before changing an already verified
proof; fix illegal trigger syntax before judging witness facts; prove the
remaining temporal witness bridge; clear guessed helper names before repairing
newly exposed proof obligations. Evidence and precise event references remain
in external sidecars. Apparent event-number offsets mostly reflect separate
call/result/verifier records; an AC citation points at a call rather than its
following diagnostic and is normalized in the review.

Command logs found no explicit reads of other optimizer candidates/reports.
This is not a hardened information-isolation proof or an assertion of exhaustive
semantic reading. One B command-output truncation marker is retained. C used
less cumulative optimizer input/output in this sample; no dollar comparison
is inferred. Full usage and cost tables stay outside the repository.

The ordinary train-40 reference has broader infrastructure, loop, closure,
lemma-planning, and rollback guidance. This three-task candidate sharpens local
stage decisions; exposure is unmatched and the reference was not the seed.

## Interpretation and next action

This pilot favors explicit cost/detour evidence over the earlier generic
objective, and favors B as a starting candidate over C's outcome-based focus in
this one sample. It does not establish a stable method ranking. Judge extraction by
observable trigger, specific detour avoided, executed repair, verifier evidence,
and correct cost/counterexample handling. Original discovery of the same repair
does not negate the value of a timely reminder. No downstream solved-rate or
token improvement is inferred from this pilot. Raw and sealed inputs remain
unchanged.

The next performance comparison should freeze matched original-only versus
augmented extraction and use separate leakage-safe evaluation. A broad screen
followed by focused evidence review is a proposed next method, not an evaluated
arm. No raw/sealed dataset or historical trace was modified; no actor was rerun.

Reviewed derivative: 3,478 bytes, SHA-256
`f57692e5dcd776534938ba09439af6bcfff25e64a39c813ba175d64bb3a5a838`. All four cards fit the 700-byte per-card budget;
seed bytes and raw B/C candidate hashes were rechecked unchanged.
