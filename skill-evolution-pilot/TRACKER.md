# Skill Evolution Pilot Tracker

Last updated: 2026-07-29

## Current state

Token evolution R1-R6 and the first OpenRouter/Qwen small-model matrix are
complete. Full-proof InfoGain R1-R2 are scored; R3 trajectory generation is
complete but R3 scoring and final aggregation are still outstanding.

| item | status | evidence / blocker |
|---|---|---|
| three isolated objective loops | specified | `EXPERIMENT_PLAN.md` |
| call accounting for `n=4` | specified | first round: 31 Codex invocations, 12 Qwen trajectories, 28 scorer sequences |
| solver/meta visibility boundaries | specified | `INFORMATION_CONTRACT.md` |
| credential handling | specified | env-only, redaction gate required |
| Codex reusable baseline | canonical fidelity smoke passed | smoke 03 requests detailed/raw reasoning visibility; smokes 01-02 are non-canonical |
| OpenRouter Qwen adapter | live preflight passed | exact model identity, complete response, usage/reasoning fields, zero secret matches |
| local-Qwen fallback adapter | not implemented | must share normalized schema and remain a separate arm |
| canonical three-task H0 | complete | 3/3 F3, 3/3 solved under the reasoning-capture contract |
| token meta-agent | complete for one-task G6 smoke | exact three-profile schema; post-hoc visibility replay passes |
| token skill smoke | complete | all three F3+solved; conservative/aggressive/structural changed uncached tokens by -38.9%/-20.5%/+13.0% on one task |
| fourth task | frozen as `hard_solved` | standard and no-lemma `range_consistent_impl` both solved under current Codex |
| full-four token meta-agent | passed after isolated retry | schema valid; zero outside-workspace commands; three frozen skills |
| first token matrix | complete | 12/12 F3, 12/12 solved; best aggregate delta -853 uncached ETtS (-1.63%) |
| token metric | implemented | uncached ETtS ledger, H0 variance, failure-aware comparison |
| Qwen agentic fidelity | passed | five requests, 57.86 seconds, solved, F3, Verus+Lynette pass |
| small-model metric | first round complete | H0 and all three skills solve the same 2/4 tasks; every skill uses more provider-reported tokens |
| InfoGain scorer gate | passed | four complete reference proofs fit the 32,768-token context; exact repeated scores match bit-for-bit |
| InfoGain R1-R2 | complete | 12/12 exact pre/post scores in each round, with token-level logs and aggregate summaries |
| InfoGain R3 | scoring queued | 12/12 F3 trajectories (11 solved); a GPU-safe watcher will run the frozen 24-sequence scorer as soon as all four local GPUs are free |

## Next executable sequence

1. Monitor the queued frozen-Qwen scoring of the 12 R3 InfoGain trajectories
   (12 pre + 12 post sequences).
2. Aggregate R1-R3 using bits and bits per target token; do not pool raw bits
   across tasks without length normalization.
3. Plot task-skill heatmaps and round-best trends, retaining InfoGain's status
   as a secondary offline proxy.
4. Decide whether another small-model round is justified by an editable
   failure mechanism rather than by solve-rate improvement.

## Immediate stop conditions

- any credential or reference-proof leakage;
- model identity mismatch;
- unbound verifier result;
- output outside the external run root;
- missing trace payload that prevents reconstruction;
- local/API results mixed in one condition;
- unresolved fourth task at full-round launch.

## Planning-phase completion checklist

- [x] detailed experiment plan
- [x] information and trace contract
- [x] staged debug gates
- [x] per-round model/call accounting
- [x] OpenRouter fallback and stop policy
- [x] implementation plan converted into tested infrastructure code
- [x] Codex fidelity smoke passed
- [x] OpenRouter Qwen fidelity smoke passed
- [x] token-first engineering smoke passed
- [x] fourth task frozen with corrected `hard_solved` label
