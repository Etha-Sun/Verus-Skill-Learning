# SkillOpt S1 S2 four model held out evaluation

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-21T13:03:58`
- status: complete; independent two-round report audit PASS
- dataset/split: frozen Claude-stratified VeruSAGE test-20, item SHA-256
  `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42`
- baseline: no skill directory, blank SHA-256
  `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`
- variants: accepted S1
  `fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab`
  and final accepted S2
  `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`
- actors: GPT-5.6 Sol, DeepSeek V4 Pro, GLM-5.3, and local
  Qwen3.8-27B BF16
- harness: autonomous Codex CLI 0.147; one task worker per condition; 600-second
  actor budget; final independent Verus and Lynette checks
- main verifier: frozen July-2025 Verus; two version-sensitive IR items also
  received fresh actor reruns with official VeruSAGE Verus `ddc66116`
- metrics: solved/20, paired outcome transitions, runtime, requests/tokens,
  known metered complete-ledger API cost, and Qwen shared-service-window GPU-hours
- leakage controls: no reference proof, prior trajectory, retrieval card, or
  test-driven skill edit; held-out outcomes did not select or update S1/S2
- stop condition: exactly one retained rollout per actor x skill x task;
  provider-valid timeout judged once, invalid provider/fidelity attempt retried

## Commands

```bash
python3 "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/build_matrix.py" \
  --repo-root "$PWD" \
  --run-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage" \
  --output-dir "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/aggregate-live"
```

## Outputs

- run directories: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-*`
  and `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test2official-*`
- reviewed report:
  `skillopt-verusage/refine-logs/SKILLOPT_S1_S2_CROSS_MODEL_FINAL_REPORT_20260821.md`
- machine metrics:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/aggregate-live/matrix.json`
- transitions:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/aggregate-live/transitions.csv`
- per-task data:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/aggregate-live/per_task.csv`
- trajectory notes:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/trajectory_analysis_notes_zh.md`
- experiment contract: `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`

## Results

| actor | blank | S1 | S2 | blank to S2 |
|---|---:|---:|---:|---:|
| GPT-5.6 Sol | 18/20 | 17/20 | 17/20 | -1 |
| DeepSeek V4 Pro | 14/20 | 14/20 | 14/20 | 0 |
| GLM-5.3 | 15/20 | 15/20 | 16/20 | +1 |
| Qwen3.8-27B BF16 | 3/20 | 5/20 | 6/20 | +3 |

All 240 retained main results were provider-valid with unchanged inputs; every
counted solve passed both Verus and Lynette. Historical Claude-failed solves
were GPT 3/5, 2/5, 2/5; DeepSeek 1/5 in all conditions; GLM 1/5 in all
conditions; and Qwen 0/5 in all conditions.

Known metered main plus official-two API spend was USD 9.21704 for DeepSeek
and USD 26.12293 for GLM, USD 35.33997 total. Transport/error requests without
provider usage make this a lower bound rather than a final billing upper bound.
GPT used local quota. Qwen API cost was zero; the main matrix spanned
10,995.54 seconds on a shared four-GPU TP service,
or 12.22 service-window GPU-hours that cannot be exclusively attributed to
this experiment.

Fresh official-Verus two-task scores for blank/S1/S2 were GPT 2/2, 2/2, 2/2;
DeepSeek 1/2, 0/2, 1/2; GLM 1/2, 1/2, 0/2; and Qwen 0/2, 0/2, 0/2. The derived
targeted hybrid is not a full official-Verus test-20 rerun.

## Interpretation

The experiment refutes a model-independent monotonic skill-improvement claim:
blank-to-S2 deltas range from -1 to +3. It provides positive single-rollout
evidence for S2 on GLM and Qwen, but not a stable causal estimate. Qwen S1 to
S2 contains three gains and two regressions; GLM S1 and GPT S1-to-S2 score ties
also hide task exchanges. Useful recurring mechanisms include contract-first
lemma use, explicit semantic bridges, structural induction, and exact
quantifier antecedent handling. Regressions arise when the actor manually
expands a proof instead of using an existing contract, asserts an unproved
semantic equality, or fails to preserve its best valid checkpoint.

Only one rollout was retained per condition. Qwen used BF16 rather than the
author-side FP8 service, and its shared checkpoint revision was not readable
from this account. The author-side native baseline is a different skill tree,
not S1 or S2. These constraints prevent merging the two result grids or
attributing all paired transitions to skill text rather than search variance.
Qwen also deviated from the preregistered owned/sequential service plan: its
three conditions ran concurrently on a shared service. External contention may
affect 600-second search progress and timeout-sensitive score.

All 264 retained actor manifests inherited the stale stage label
`auxiliary_dev_fidelity_smoke`, despite correct arm-level held-out contracts.
Historical raw manifests were not rewritten. The generator now accepts an
explicit stage and future test evaluation writes `formal_held_out_evaluation`.

A read-only two-round reviewer returned PASS after the report, tracker,
generator, and fail-closed aggregator corrections. It independently reconciled
24 arms, 264 retained results, 164 dual-verifier solves, all matrix/CSV/hybrid
values, and the 46/46 plus 80/80 test suites. Remaining caveats are disclosed
evidence boundaries rather than release blockers.

## Next Action

Repeat the Qwen and GLM outcome-transition cases under fixed owned model
revisions and multiple seeds before claiming stable transfer. Prioritize the
six Qwen tasks that changed status and the GLM `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods`/`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` pair; retain
the same Codex contract, verifier identities, timeout, and no-retrieval boundary.
