# GLM-5.3 No-Skill Evaluation Setup

## Technical summary

This document records the exact setup that produced the GLM-5.3 no-skill result of **16/20** on 20 August 2026. It is intended for task-level comparison with another GLM run, not as a claim that 16/20 is the stable expected accuracy of the model.

Before comparing success rates, check these four items first:

1. **Verifier version:** this run used Verus `0.2025.07.12.0b6f3cb` (`0b6f3cb`), not the VeruSAGE-Bench-recommended commit `ddc66116`. Runs using those two verifier revisions are not configuration-equivalent.
2. **Model endpoint:** the provider alias was `glm-5.3` at `https://api.z.ai/api/paas/v4`. No immutable provider-side model snapshot ID was available, so alias drift is possible.
3. **Agent harness:** this was Codex CLI `0.147.0` with maximum reasoning, a Responses-to-Chat bridge, tool use, and iterative verifier feedback. It was not a one-shot chat completion.
4. **Scoring and fixtures:** success required both Verus and Lynette to pass. Tasks 9 and 19 are reported as failures for every model because of known fixture defects.

The run was a single serial pass with no explicit decoding seed and no explicit temperature. Stochastic variation therefore remains a plausible explanation for some task-level disagreement even after all recorded settings match.

## Reference result to reproduce

| Metric | Recorded value |
|---|---:|
| Condition | no-skill |
| Split | test |
| Solved | 16/20 |
| Failed task numbers | 9, 11, 19, 20 |
| Failure types | task 9: final verification failed; tasks 11, 19, 20: timeout |
| Total wall time | 4,508.347 s |
| Mean wall time over all tasks | 225.417 s |
| Mean wall time over solved tasks | 140.671 s |
| Estimated provider cost | $8.423304 |
| Mean cost over all tasks | $0.421165 |
| Mean cost over solved tasks | $0.204882 |
| Provider requests | 624 |
| Input tokens | 25,369,274 |
| Output tokens | 224,505 |
| Reasoning tokens | 98,218 |
| Cache-hit input tokens | 24,632,896 |
| Cache-miss input tokens | 736,378 |
| Coverage / fidelity / safety | complete / complete / complete |
| Contract violations | 0 |

Blocked prohibited filesystem probes and malformed actor-log events were recorded as audit observations only. They did not automatically make a task fail. The recorded counts were three blocked probes and six malformed events across eight tasks.

## Frozen benchmark scope

The input was the unchanged 20-task `test` split under:

```text
/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/fixed-claude-stratified-80-seed20260814/test/items.json
```

The 40 training tasks used to construct the baseline skill were excluded. The no-skill actor received no skill tree and no training trajectory, verified solution, sibling output, or test metadata.

| Frozen identity | SHA-256 |
|---|---|
| Split file | `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42` |
| Ordered task projection | `f863a48142310e3382246851662f5e23efc98420973f5348ac5b6f31e709fd64` |
| Outer test projection | `593cd9cd382e39818c33ceec4139b9c39c619919ffde1d3a5fdbe65c2ab6f912` |
| Project composition | AL: 7, AC: 6, IR: 7 |

The complete frozen item records and full source hashes are preserved in `glm-5.3/no-skill/test/configuration/split_items.snapshot.json`.

## Model and API configuration

| Setting | Value |
|---|---|
| Logical model | `glm-5.3` |
| Provider | Z.AI |
| Upstream base URL | `https://api.z.ai/api/paas/v4` |
| Environment variables | `GLM_API_KEY`, `GLM_BASE_URL`, `GLM_MODEL` |
| Provider protocol | Chat Completions |
| Codex-facing protocol | Responses API |
| Bridge mode | Responses-to-Chat translation |
| Reasoning effort | `max` |
| Thinking field | enabled |
| Reasoning history field | `reasoning_content` |
| Context window exposed to Codex | 1,048,576 tokens |
| Normal maximum output | 8,192 tokens per request |
| Retry maximum output | 131,072 tokens |
| Temperature | not explicitly set by the runner or bridge |
| Top-p | not explicitly set |
| Random seed | not set |
| Upstream streaming | disabled (`stream=false`) |
| Upstream request timeout | 1,800 s |
| Request retries | 4 |
| Stream retries | 4 |
| Allowed Codex tool names | `exec_command`, `write_stdin` |

The bridge translated Codex Responses messages and tool history into Chat Completions messages, preserved prior reasoning in `reasoning_content`, sent `reasoning_effort=max` and `thinking={type: enabled}`, then converted the provider response back into Responses events.

No temperature field was added during this translation. If another run explicitly sets temperature, uses a different provider default, disables thinking, or invokes a different `glm-5.3` alias snapshot, it is not an exact replication.

## Codex agent configuration

| Setting | Value |
|---|---|
| Agent harness | Codex CLI |
| Codex version | `codex-cli 0.147.0` |
| Codex model name | `glm-5.3` |
| Reasoning configuration | `model_reasoning_effort=max` |
| Approval mode | `never` |
| Codex sandbox flag | `danger-full-access` inside a stronger outer isolation namespace |
| User configuration | ignored (`--ignore-user-config`) |
| Session persistence | ephemeral |
| Git repository requirement | disabled (`--skip-git-repo-check`) |
| Task scheduling | serial, task 1 through task 20 |
| Task timeout | 600 s |
| Final verification timeout | 120 s |

Each task workspace contained:

```text
AGENTS.md
TASK.md
input.rs       # immutable
candidate.rs   # only editable proof candidate
```

There was no `skill/` directory in the no-skill workspace, and the frozen manifest records `skill: null`.

## Exact actor prompt

```text
Repair the Verus proof in candidate.rs.

Rules:
- This is the no-skill control; no proof-repair skill is supplied.
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with /zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both /zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus candidate.rs and
  /zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette compare -t input.rs candidate.rs to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
```

`TASK.md` additionally contained only `Repair candidate.rs.` The final generic phrase about a supplied immutable skill remained in the prompt, but no skill was actually present; the explicit first rule and manifest identify this as the no-skill control.

## Tool and filesystem isolation

The model could use an audited shell and persistent shell sessions through `exec_command` and `write_stdin`. Within the actor namespace it could:

- edit only `candidate.rs` in the current task workspace;
- run the mounted Verus binary;
- run Lynette comparison;
- inspect the read-only Verus/vstd installation and Rust toolchain.

The namespace hid the host home directory and the broader scratch tree, used private PID, mount, temporary, and network namespaces, dropped capabilities, and allowed network access only through the task-scoped loopback bridge relay. The task workspace was writable; Verus, Rust, and Lynette were mounted read-only.

Attempts to inspect trajectories, verified answers, sibling task outputs, or held-out metadata were blocked and returned to the model as ineffective tool operations. A blocked probe was recorded but was not itself scored as failure, allowing the model to continue working.

## Verifier, safety checker, and scoring

| Component | Recorded version or identity |
|---|---|
| Verus binary | `/zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus` |
| Verus version | `0.2025.07.12.0b6f3cb`, release, Linux x86-64 |
| Verus toolchain | `1.88.0-x86_64-unknown-linux-gnu` |
| Verus binary SHA-256 | `c3afe80bbaabc45527a18e490fc124dea9cd79afe8861f698a7cf33c7123178d` |
| Lynette binary | `/zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette` |
| Lynette reported version | `0.0.0` |
| Lynette SHA-256 | `bcdd8e1b1fc407bfd415814f2791af91f1ac30c2af9ee0085ae97b4fd38deb11` |
| Scoring policy | `proof-outcome-v3` |

A task counted as success only when the final `candidate.rs` passed both:

```bash
/zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus candidate.rs
/zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette compare -t input.rs candidate.rs
```

The evaluator also checked that `input.rs` remained immutable and rejected unsafe or specification-weakening edits. Ordinary task failures were limited to:

- the 600-second actor timeout; or
- a completed actor turn followed by failed final Verus/Lynette verification.

Provider exhaustion stopped the batch as incomplete and was resumable; it was not converted into a proof failure. A final-verification failure required a terminal completed actor event.

### Important Verus mismatch

The source repository for VeruSAGE-Bench specifies Verus commit:

```text
ddc66116aa7a844a9e19cc50922fe85c84b8b4a5
```

A clean build of that commit reports approximately `0.2025.09.11.ddc6611`. This GLM run instead used `0.2025.07.12.0b6f3cb`. A result obtained with the `ddc66116` binary should be treated as a different verifier condition until the same candidates are replayed under both versions.

## Timeout and retry semantics

The 600-second limit applied to the Codex actor process. Workspace preparation, process teardown, auditing, and final verifier checks occurred around that interval, so recorded task wall times can slightly exceed 600 seconds. For example, the three timeout tasks recorded approximately 621.1, 617.0, and 616.0 seconds.

The provider request timeout of 1,800 seconds was larger than the actor limit; the 600-second task limit therefore dominated. Codex request and stream retry limits were each four. Provider failures were observations unless all retries were exhausted, in which case the batch remained incomplete and the supervisor resumed it.

The no-skill arm completed before the shared USD 20 guard became limiting. Its recorded estimated cost was $8.423304. Later budget extensions used to finish the with-skill arm did not alter the completed no-skill tasks.

The cost estimator used these recorded GLM rates per one million tokens:

| Token class | USD / 1M tokens |
|---|---:|
| Prompt cache hit | $0.26 |
| Prompt cache miss | $1.40 |
| Completion | $4.40 |

These are harness-side estimates from provider-reported usage, not an independently reconciled billing statement.

## Task-level reference outcomes

| # | Project | Task ID | Source SHA-256 prefix | Raw outcome | Wall time (s) | Estimated cost |
|---:|---|---|---|---|---:|---:|
| 1 | AL | `AL__leads_to_by_borrowing_inv` | `20bb68867bdf` | PASS | 100.190 | $0.072044 |
| 2 | AL | `AL__entails_implies_leads_to` | `5487d61bd99b` | PASS | 36.924 | $0.024100 |
| 3 | IR | `IR__marshal_v__impl3__lemma_serialize_injective` | `c341f1b4c97d` | PASS | 75.391 | $0.074353 |
| 4 | AL | `AL__push_to_set_seq_to_set_insert` | `2b796a0cc86f` | PASS | 70.973 | $0.093747 |
| 5 | AC | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` | `6fcbfdf7012f` | PASS | 477.912 | $0.818753 |
| 6 | AC | `AC__vreplicaset_controller__proof__liveness__spec__invariant_since_phase_iv_is_stable` | `58fe0d84f137` | PASS | 80.377 | $0.062784 |
| 7 | IR | `IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive` | `aac3faf8dde4` | PASS | 59.969 | $0.060449 |
| 8 | AL | `AL__seq_filter_preserves_no_duplicates` | `0e9962fa5675` | PASS | 160.854 | $0.165968 |
| 9 | IR | `IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` | `39731482101e` | final_verification_failed | 403.484 | $0.681093 |
| 10 | IR | `IR__host_impl_v__make_send_only_event_results` | `f5263090467a` | PASS | 29.206 | $0.019637 |
| 11 | AC | `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` | `153a036e66c0` | timeout | 621.117 | $1.635235 |
| 12 | AL | `AL__always_implies_to_leads_to` | `27f134d15831` | PASS | 104.115 | $0.101513 |
| 13 | AC | `AC__vreplicaset_controller__proof__liveness__spec__invariant_is_stable` | `727cdd32ddae` | PASS | 55.244 | $0.071948 |
| 14 | AL | `AL__always_to_current` | `f13bca3450bb` | PASS | 21.049 | $0.016263 |
| 15 | AC | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` | `8d37dd9244ae` | PASS | 205.641 | $0.467718 |
| 16 | IR | `IR__delegation_map_v__impl4__empty_key_range_is_consistent` | `50d21c8ab0a2` | PASS | 137.822 | $0.147899 |
| 17 | IR | `IR__delegation_map_v__impl3__values_agree` | `2cea72cbda58` | PASS | 141.511 | $0.132631 |
| 18 | AL | `AL__leads_to_shortcut_temp` | `b6b510353a6a` | PASS | 493.565 | $0.948300 |
| 19 | IR | `IR__single_delivery_model_v__impl2__send_single_cmessage` | `0a72fa7be540` | timeout | 616.961 | $1.720219 |
| 20 | AC | `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` | `fb01080e4d16` | timeout | 616.041 | $1.108650 |

### Uniform handling of fixture defects

Tasks 9 and 19 are reported as failures for all four response models in the cross-model comparison:

- **Task 9** did not preserve a required per-item `--extern verus_builtin_macros=.../libbuiltin_macros.so` compiler mapping in the uniform standalone fixture. This run already recorded it as final verification failed.
- **Task 19** contains the problematic `extern crate verus_builtin_macros as builtin_macros` line. This run timed out on it.

Do not post-hoc count either task as success in a cross-model success-rate comparison unless every model is rerun under the same repaired fixture and verifier command.

## Implementation identities

| Artifact | SHA-256 or identifier |
|---|---|
| Actor contract | `628ef5a8170229724ff42004dd396d5d7dc1d12ed3b4c4c979884d449e6edeb0` |
| Actor runner | `86ab7f957c0565166d566628c0c29a6843f9d12ec33c174aaf088ae882d0887c` |
| Isolation runner | `d2f7d64e936b294e4c4916ac9b39a6040f831efe6529f2aafa1a62aab8bd3015` |
| Responses-to-Chat bridge | `18dced3a21caf87b643a88f06493aa6da6f4f937573849aa51143c0769d7ada3` |
| Bridge source provenance | `d6fc7754602f320db90a32401ec1ca1739ac2b1c` |
| Bridge configuration | `2b8d2b2ca70372a5ef80f44abba67315737fe2e35b5cef56a915763bca1cc629` |
| Codex binary | `cb0a15567e9a60a5820d54b0f6ae86d504dc3805c1eab21a47f70e3eb7b73a40` |
| No-skill summary | `8d718746e89aaa240190096537904afae4283032b622705136bce233c59de526` |

These hashes are more reliable than the current Git worktree state for reproducing the completed run because the worktree contains subsequent uncommitted changes.

## Reproduction commands

Use a new output directory. Never run a replication into the completed reference directory.

### Exact paired driver used for the original experiment

The original driver preflighted and then ran no-skill followed by with-baseline-skill:

```bash
python3 /zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/baseline-test-20260819/code/run_glm_5_3.py \
  --preflight \
  --env-file /zp_vegeta/scratch_sb/xinyueh/.env.glm \
  --approval-limit-usd 20

python3 /zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/baseline-test-20260819/code/run_glm_5_3.py \
  --execute \
  --env-file /zp_vegeta/scratch_sb/xinyueh/.env.glm \
  --approval-limit-usd 20
```

### No-skill-only reproduction

The following invokes the same actor directly while writing to a fresh run root. Port 4335 must be free.

```bash
GLM_REPRO_ROOT=/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3-noskill-replication
ACTOR_RUNNER=/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/trace2skill_verusage_cross_task_global_skills_20260814/code/run_actor_matrix.py
SPLIT_ROOT=/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/fixed-claude-stratified-80-seed20260814
BASELINE_SKILL=/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/cross-task-global-20260814/native_official_baseline_v1/skill/verus-proof-repair

python3 "$ACTOR_RUNNER" \
  --preflight \
  --provider glm \
  --split test \
  --split-root "$SPLIT_ROOT" \
  --condition no-skill \
  --skill-dir "$BASELINE_SKILL" \
  --output-root "$GLM_REPRO_ROOT/preflight/no-skill/test" \
  --run-root /zp_vegeta/scratch_sb/xinyueh/verus_skill_runs \
  --scratch-root /zp_vegeta/scratch_sb/xinyueh \
  --env-file /zp_vegeta/scratch_sb/xinyueh/.env.glm \
  --codex-bin /home/xinyueh/.codex/packages/standalone/releases/0.147.0-x86_64-unknown-linux-musl/bin/codex \
  --verus-bin /zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus \
  --rust-root /zp_vegeta/scratch_sb/xinyueh/tools/rust \
  --lynette-bin /zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette \
  --timeout-seconds 600 \
  --verification-timeout-seconds 120 \
  --proxy-port 4335 \
  --approval-limit-usd 20 \
  --prior-spend-usd 0 \
  --request-reserve-usd 0.25

python3 "$ACTOR_RUNNER" \
  --execute \
  --provider glm \
  --split test \
  --split-root "$SPLIT_ROOT" \
  --condition no-skill \
  --skill-dir "$BASELINE_SKILL" \
  --output-root "$GLM_REPRO_ROOT/no-skill/test" \
  --run-root /zp_vegeta/scratch_sb/xinyueh/verus_skill_runs \
  --scratch-root /zp_vegeta/scratch_sb/xinyueh \
  --env-file /zp_vegeta/scratch_sb/xinyueh/.env.glm \
  --codex-bin /home/xinyueh/.codex/packages/standalone/releases/0.147.0-x86_64-unknown-linux-musl/bin/codex \
  --verus-bin /zp_vegeta/scratch_sb/xinyueh/tools/verus/bin/verus \
  --rust-root /zp_vegeta/scratch_sb/xinyueh/tools/rust \
  --lynette-bin /zp_vegeta/scratch_sb/xinyueh/qwen_five_skill_eval/tools/lynette \
  --timeout-seconds 600 \
  --verification-timeout-seconds 120 \
  --proxy-port 4335 \
  --budget-state-path "$GLM_REPRO_ROOT/provider_budget_state.json" \
  --approval-limit-usd 20 \
  --prior-spend-usd 0 \
  --request-reserve-usd 0.25
```

Add `--resume` to the execute command only when resuming an incomplete output produced by the same frozen contract.

## Comparison checklist for the lower-scoring run

Compare the other run in this order:

1. Confirm the exact 20 ordered task IDs and the split/projection hashes.
2. Compare `verus --version` and the Verus binary SHA-256. A `ddc66116` run is not directly equivalent to this `0b6f3cb` run.
3. Confirm Codex CLI `0.147.0`, not another agent framework or direct Chat Completions loop.
4. Confirm `glm-5.3`, maximum reasoning, thinking enabled, 8,192 normal output tokens, and the same Z.AI endpoint.
5. Confirm that no temperature or seed was explicitly set.
6. Confirm serial scheduling and a 600-second actor timeout plus 120-second final verification timeout.
7. Compare the exact prompt and verify that no skill files were present.
8. Confirm access to iterative Verus diagnostics, Lynette, and read-only vstd inspection.
9. Confirm that blocked answer-search operations were returned to the actor rather than immediately scored as proof failures.
10. Confirm success required both Verus and Lynette, and that tasks 9 and 19 were forced to the same reporting policy.
11. Diff task-level outcomes rather than only the aggregate count.

For the fastest diagnosis, request these three files from the other run with credentials removed:

```text
experiment_manifest.json
bridge_manifest.json
summary.json
```

Then compare their task projection, actor contract, bridge configuration, Verus hash, Codex hash, model settings, and individual failed task IDs against the identities above.

## Limitations and interpretation

- This is one nondeterministic run per condition; it does not estimate run-to-run variance.
- The provider model name is an alias rather than a frozen weights revision.
- The run used a Verus revision older than the VeruSAGE-Bench-recommended commit.
- Tasks 9 and 19 contain fixture defects and are retained only under a uniform all-model failure policy.
- Mean time and cost can be dominated by timeout tasks; compare solved count and paired task transitions separately.
- A different result does not by itself imply a broken model or harness. It first establishes that either stochastic execution or at least one configuration variable differs.

## Auditable source artifacts

All paths below are read-only evidence from the completed run:

```text
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/experiment_manifest.json
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/bridge_manifest.json
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/configuration/split_items.snapshot.json
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/summary.json
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/progress.json
/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/baseline-test-20260819/glm-5.3/no-skill/test/bridge_calls.jsonl
/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/baseline-test-20260819/code/run_glm_5_3.py
/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/trace2skill_verusage_cross_task_global_skills_20260814/code/run_actor_matrix.py
/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/trace2skill_verusage_cross_task_global_skills_20260814/code/actor_isolation.py
```

Secrets are intentionally excluded from this document. The only credential name required for the run is `GLM_API_KEY`.
