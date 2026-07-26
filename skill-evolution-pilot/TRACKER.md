# Skill Evolution Pilot Tracker

Last updated: 2026-07-26

## Current state

The first token round and OpenRouter/Qwen agentic fidelity gate are complete.
The small-model skill matrix is next.

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
| small-model metric | ready for first-round implementation | verifier-safe solve rate; API trajectory and request counts separated |
| InfoGain target | blocked | complete proof/target span and truncation policy not frozen |

## Next executable sequence

1. Feed the best/worst and complete token table back to the isolated
   token meta-agent only if the first-round iteration gate passes.
2. Implement the isolated small-model meta-agent and freeze its three skills.
3. Run the OpenRouter Qwen `3 skills x 4 tasks` first round.
4. Start the InfoGain branch only after its scorer gates pass.

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
