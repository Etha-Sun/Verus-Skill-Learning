# Implementation and execution plan

## Authorized bounded repair, no paid execution

The user authorized fixing confirmed discrepancies before reviewing all design
details. This supersedes the launch implementation below only for the bounded
repair; the archived campaign remains diagnostic-only and must not be resumed.

1. Reuse verifier-gated proof pruning, exact verifier calls, target-proof line
   coverage and token alignment; expose progress plateaus/regression transitions
   without inventing branch counts, rankings, thresholds or midpoint fallbacks.
   Verify with fixtures where verifier counts stay unchanged but proof progress
   changes, and where pruning or snapshot/token alignment fails.
2. Expose reconstructible shared prefixes and aligned original/hinted suffixes
   with checkpoint identity checks; require comparative fork analysis in the
   card prompt. Remove unapproved two-card/700-byte limits while keeping evidence
   and leakage/safety checks. Verify reconstruction and negative-branch retention.
3. Provide an agent-visible title/trigger index with direct per-ID card reads;
   keep optional search as a helper, not the only way to discover cards. Verify
   all IDs are visible without exposing private provenance.
4. Prevent old paid entry points from launching before design review. Test that
   rejection happens before preflight, budget creation and model calls. Record
   incomplete coordinator/grouping/budget work explicitly, not as a ready run.

Evidence tier is auxiliary/dev: mocked unit/regression tests, no claimed live
efficacy, no real provider calls or forty-source pruning run. Open settings:
checkpoint policy and K/group size; learning spend boundary and per-method
amount; card/index exposure limits. Review these before finishing the new
coordinator, budget-frontier scheduling or downstream launch.

Superseded for execution and method interpretation by
[MEETING_ALIGNMENT_AUDIT.md](MEETING_ALIGNMENT_AUDIT.md). Preserve this as launch
provenance; do not implement or resume its selector/grouping/card limits as the
meeting-approved method.

## Selected direction and common inputs

Use a fresh common train40 corpus to compare native plain SkillOpt, original-only
cards and task-grouped original-plus-one-hint cards. Initial skill is a fourth
common deployment reference. Keep native Reflect/Aggregate/Select/Apply algorithms;
replace only model transport with guarded native DeepSeek Responses. Native
minibatches remain success/failure separated, at most eight traces, four edits
per minibatch and top-four selection. Do not edit the ignored upstream checkout.

## Minimal code map

- New guarded client in `skillopt_verusage`: use existing native bridge parsing,
  model/usage checks and accounting, including direct teacher/extractor calls.
- New campaign module: unique source IDs, frozen stagnation/midpoint selector,
  lossless complete teacher evidence, isolated continuation and exact card dedup
  with provenance union; no old three-task export or eight-source semantic merge.
- Native optimizer adapter: inject guarded callbacks into existing native
  reflection/merge/ranking modules; never expose file paths as unread direct-API
  evidence, never substitute a custom algorithm while calling it native.
- Existing card-search bundle and actor runner: reuse with matched O/H deployment;
  archive exposure audits. Full bank reads are possible; no enforced top-k claim.
- Validation scheduler: freeze artifacts before reading val sources, do two
  separate complete 80-attempt repetitions with balanced condition ordering.
- Focused tests cover identity, complete evidence, card fields/provenance,
  schedule, cap/denial, no automatic replay, truncation and provider accounting.

## Runtime and budget

Fresh external campaign, no overwrite of historical results. Global new USD 80
guard covers every paid request. Per-method reference learning ceiling USD 25,
including shared original recorded/uncertain cost; extraction/finalization at
most USD 5 per method, with a finalization reserve. Use frozen reference rates
alongside actual time-band estimates. Hold unknown requests conservatively.
Actor/hint continuations max/1800; common validation max/600. Teacher and
extractor use high as in the earlier proposal, with identical S/O/H settings;
model is Pro for all roles. Worker count starts bounded, raises to eight for
verified actor paths. No unknown-error automatic paid retries.

## Gates and fallback

1. Offline input/hash/context and code tests; then an included training-source
   teacher/card smoke (not held-out tuning). No silently truncated evidence.
2. Generate one branch maximum per frozen eligible source, keep unsolved,
   harmful/screen-rejected branches and their costs. Budget stops can reduce m
   but cannot silently drop original40 coverage.
3. Native baseline and O/H extraction cover all40 sources or explicitly stop.
   Freeze identical card schema/rules; audit task-specific proof leakage.
4. Freeze four artifacts, val schedule, cost profiles and exposure protocol.
   Evaluate two complete paired repetitions; test20 remains untouched.
5. Audit coverage, validators, fidelity, all costs and disagreements. Record
   supported/refuted/inconclusive, then route to analysis, not more paid retries.

If provider/usage/model validity fails, preserve attempt and stop affected launch.
If budget cannot cover a whole next phase, report the completed scope and request
direction rather than changing model, sample count or artifact rule silently.
Do not claim strict equal-cost superiority from unequal realized costs.

## Current frontier

Implement and run model-free regression tests. Experiment tool-specific
`bash_exec`/artifact interfaces are unavailable in this session; use repository
runner plus external durable manifests and canonical research memory as fallback.
