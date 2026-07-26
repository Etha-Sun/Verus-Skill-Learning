# Skill Evolution Pilot Tracker

Last updated: 2026-07-26

## Current state

The token branch is running. No OpenRouter request has been made as part of
this pilot because the credential is not present in the process environment.

| item | status | evidence / blocker |
|---|---|---|
| three isolated objective loops | specified | `EXPERIMENT_PLAN.md` |
| call accounting for `n=4` | specified | first round: 31 Codex invocations, 12 Qwen trajectories, 28 scorer sequences |
| solver/meta visibility boundaries | specified | `INFORMATION_CONTRACT.md` |
| credential handling | specified | env-only, redaction gate required |
| Codex reusable baseline | canonical fidelity smoke passed | smoke 03 requests detailed/raw reasoning visibility; smokes 01-02 are non-canonical |
| OpenRouter Qwen adapter | implemented, live preflight pending | fake-provider, full reasoning-field, model-mismatch, and redaction tests pass |
| local-Qwen fallback adapter | not implemented | must share normalized schema and remain a separate arm |
| canonical three-task H0 | complete | 3/3 F3, 3/3 solved under the reasoning-capture contract |
| token meta-agent | complete for one-task G6 smoke | exact three-profile schema; post-hoc visibility replay passes |
| token skill smoke | complete | all three F3+solved; conservative/aggressive/structural changed uncached tokens by -38.9%/-20.5%/+13.0% on one task |
| fourth task | frozen as `hard_solved` | standard and no-lemma `range_consistent_impl` both solved under current Codex |
| full-four token meta-agent | passed after isolated retry | schema valid; zero outside-workspace commands; three frozen skills |
| first token matrix | running | 3 skills x 4 tasks, Codex concurrency 6, 600-second per-run cap |
| token metric | implemented | uncached ETtS ledger, H0 variance, failure-aware comparison |
| small-model metric | draft frozen | Verus+Lynette solve rate |
| InfoGain target | blocked | complete proof/target span and truncation policy not frozen |

## Next executable sequence

1. Monitor and audit the running 12-run token first round.
2. Reconstruct every run ledger and produce the failure-aware 3x4 matrix
   summary.
3. Feed the best/worst and complete token table back to the isolated
   token meta-agent only if the first-round iteration gate passes.
4. Extend the Qwen adapter into the host-controlled repair loop; use
   OpenRouter only when the credential is available through the environment,
   otherwise label and run the approved local fallback.
5. Start the InfoGain branch only after its scorer gates pass.

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
- [ ] OpenRouter Qwen fidelity smoke passed
- [x] token-first engineering smoke passed
- [x] fourth task frozen with corrected `hard_solved` label
