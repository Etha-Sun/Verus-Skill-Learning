# July Verus Results and Regression Analysis

## 1. July-2025 Verus Main Results

Each cell is one retained rollout per task on the frozen 20-task test set.
Tasks 9 and 19 remain in the denominator.

| Actor | No skill | S1 | S2 | S2 vs. no skill |
|---|---:|---:|---:|---:|
| DeepSeek V4 Pro | 14/20 (70%) | 14/20 (70%) | 14/20 (70%) | 0 |
| Qwen3.8-27B BF16 | 3/20 (15%) | 5/20 (25%) | 6/20 (30%) | +3 |
| GPT-5.6 Sol | 18/20 (90%) | 17/20 (85%) | 17/20 (85%) | -1 |
| GLM-5.3 | 15/20 (75%) | 15/20 (75%) | 16/20 (80%) | +1 |

### Tasks 9 and 19

`U/U/U` means `UNSOLVED` under no-skill, S1, and S2.

| Test position | VeruSAGE task name | DeepSeek | Qwen | GPT | GLM |
|---:|---|---:|---:|---:|---:|
| 9 | `IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` | U/U/U | U/U/U | U/U/U | U/U/U |
| 19 | `IR__single_delivery_model_v__impl2__send_single_cmessage` | U/U/U | U/U/U | U/U/U | U/U/U |

Thus, both tasks contribute zero to every July score, but they are not
hard-coded to false and are not excluded. All 24 actor executions were run;
their final verification did not pass under the July binary. The known
fixture/version incompatibility is why the official-Verus reruns are reported
separately rather than silently replacing these outcomes.

## 2. Final No-Skill to S2 Regression

There is exactly one `SOLVED -> UNSOLVED` transition when comparing the final
no-skill and S2 columns:

`AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req`

- Actor: GPT-5.6 Sol
- No-skill: SOLVED in 300.90 seconds
- S2: UNSOLVED after the 600-second actor cutoff; recorded wall time 631.66 seconds
- Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req.rs`
- Successful no-skill result: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-blank-reference-aligned-retryfix-20260821/predictions/cd1203d23d38c7709903/result.json`
- Failed S2 result: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s2-reference-aligned-retryfix-20260821/predictions/cd1203d23d38c7709903/result.json`

The no-skill and S1 runs handle only the two semantically difficult branches
and reuse the existing domain lemmas. The S2 run expands every `Step` variant,
but leaves the hard `APIServerStep` and `ControllerStep` branches as bare
assertions. Final Verus fails exactly those two assertions.

The S2 rollout clearly follows a longer, less targeted proof strategy. This is
consistent with skill-conditioned search interference: the text of S2 itself
recommends representative-branch validation and checkpointing, but the actor
did not follow those instructions. It does not establish that S2 caused the
regression or contains a logically wrong rule. With only one rollout per
condition, this observation cannot be separated from search variance.

## 3. All Intermediate SOLVED to UNSOLVED Transitions

| Actor | Transition | VeruSAGE task name | Assessment |
|---|---|---|---|
| GPT-5.6 Sol | no skill -> S1 | `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` | Mixed: S1 selected an oversized per-`Step` preservation proof; S2 later recovered with a minimal named bridge. This indicates attention/search interference, but not a logically invalid S1 rule. |
| GPT-5.6 Sol | S1 -> S2 | `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` | Strongest GPT strategy-selection failure: S2 over-expanded all branches and omitted existing domain lemmas, despite its own representative-branch guidance. |
| GLM-5.3 | no skill -> S1 | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` | Mainly stochastic/instruction-compliance: S1 asserted set equality without proving membership directions; an older S1 diagnostic solved it and final S2 recovered it. |
| Qwen3.8-27B BF16 | no skill -> S1 | `AL__always_to_current` | Mainly execution variance: S1 asserted execution equality without calling the available bridge; both no-skill and S2 found `execution_equality`. |
| Qwen3.8-27B BF16 | S1 -> S2 | `AL__push_to_set_seq_to_set_insert` | Strongest evidence of skill interference: S1 solved twice through the exact existing `lemma_push_to_set_commute`; S2 pursued a more specific pointwise extensional proof and failed to fall back to that contract. |
| Qwen3.8-27B BF16 | S1 -> S2 | `IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive` | Most likely rollout variance: S2 retains S1's structural-induction guidance and does not forbid the successful S1 route, but the S2 rollout never executes it. |

The full source and failed-result paths are:

- `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile.rs`
  - Failed S1: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s1-reference-aligned-retryfix-20260821/predictions/e0ff80bd8ec2d2c26eb9/result.json`
- `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req.rs`
  - Failed S2: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s2-reference-aligned-retryfix-20260821/predictions/cd1203d23d38c7709903/result.json`
- `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok.rs`
  - Failed S1: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-s1-reference-finalbridge-20260821/predictions/2532d3f7ba518ccc47a5/result.json`
- `AL__always_to_current`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AL__always_to_current.rs`
  - Failed S1: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-qwen-s1-reference-20260821/predictions/7b4d572de7841b02407d/result.json`
- `AL__push_to_set_seq_to_set_insert`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-anvil/unverified/AL__push_to_set_seq_to_set_insert.rs`
  - Failed S2: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-qwen-s2-reference-20260821/predictions/548b780f15b36ad35124/result.json`
- `IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive`
  - Source: `fixed-claude-stratified-80-seed20260814/sources/verified-ironkv/unverified/IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive.rs`
  - Failed S2: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-qwen-s2-reference-20260821/predictions/22fb8583a583c657c15c/result.json`

## 4. Visualization

- PNG: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/figures/july_verus_cross_model_summary/july_verus_cross_model_performance_runtime_cost.png`
- Vector PDF: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/figures/july_verus_cross_model_summary/july_verus_cross_model_performance_runtime_cost.pdf`
- Figure data: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/figures/july_verus_cross_model_summary/july_verus_summary.csv`
- Reproduction script: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/figures/july_verus_cross_model_summary/generate_figure.py`

The figure compares only no-skill and S2. Runtime and cost average all 20 tasks;
there is no solved-tasks-only series. Cost bars are actual retained per-task API
billing: GPT is labeled local quota and Qwen is labeled API $0. DeepSeek
no-skill ran at peak price and S2 ran at off-peak price; therefore its raw
dollar bars record spending but cannot be interpreted as a skill-induced cost
change. Archived retry cost is excluded from the plotted per-task bars and
remains in the complete-ledger accounting table in the final report.
