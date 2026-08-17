# SkillOpt DeepSeek V4 Pro fixed-80 epoch 1

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-17T14:03:32-05:00`
- status: `complete-with-accounting-caveat`
- dataset/split: frozen reference-free AC/AL/IR 40 train / 20 selection
  (`val`) / 20 test, split SHA
  `a71e2a3838c2222312cc2487fc35b6a24cbc924e0a917d5e9120499f0ba2b49c`
  and manifest SHA
  `b9647679a832392a3368f3c83011076d3bd3ce70380f6c39cd7e2da3418436c3`
- baseline: 838-byte initial skill, SHA
  `96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`
- actor: official `deepseek-v4-pro` alias through Codex CLI 0.146.1 and native
  Responses, reasoning effort `max`; the API does not expose an internal build
  identifier, so this run does not claim runtime proof of an `0813` suffix
- optimizer: local Codex `gpt-5.6-sol`, using the native SkillOpt
  reflect/merge/rank/update path
- epoch: 20 selection S0 rollouts, 40 training rollouts, one optimizer update,
  and 20 same-selection candidate-gate rollouts; held-out test disabled
- concurrency: phase-bounded 20 / 40 / 20 with `workers=40`
- timeout/retry: the completed replacement used one 600-second judgment for
  valid unsolved timeouts and up to two clean retries only for `V0_INVALID`;
  the earlier 1,200 / 2,400 / 3,600-second attempt remains paused during S0
- metrics: independent joint Verus + Lynette hard solved rate, paired selection
  transitions, fidelity, requests, cache-hit/miss input, output, wall time, and
  per-request USD cost
- leakage controls: only train trajectories reach the optimizer; selection is
  gate-only; no test rollout or reference proof is exposed
- stop condition: finish exactly one epoch and accept the candidate only on a
  strict selection hard-rate improvement

## Pricing And Estimate

DeepSeek's 2026-08-16 price change is active. Official peak windows are
01:00-04:00 and 06:00-10:00 UTC. V4 Pro off-peak prices per million tokens are
USD 0.022 cache-hit input, USD 0.66 cache-miss input, and USD 1.98 output;
peak prices are exactly double. The bridge records request start/end UTC,
price band, and per-request estimated cost. A request crossing a price-band
boundary is conservatively priced at peak.

Repricing the previous aligned Pro epoch's exact actor token mix gives USD
11.84 if all traffic is off-peak and USD 23.68 if all traffic is peak. The
planning estimate for this new fixed split is USD 12-16 off-peak after a
20-30% difficulty/retry allowance. This is an estimate, not a spending cap.

Official sources:

- `https://api-docs.deepseek.com/quick_start/pricing`
- `https://api-docs.deepseek.com/updates`

## Commands

```bash
export SKILLOPT_PYTHON_BIN=/path/to/python
export SKILLOPT_MODEL_CATALOG_PATH=/path/to/reviewed/models.json
skillopt-verusage/scripts/run_codex_pro_sol_fixed80_e1_600s.sh
```

The launch script creates a fresh run root, passes `--manifest-path` and
`--model-catalog-path`, starts the bridge with a 540-second upstream timeout,
waits for readiness, removes the real API key from the actor/optimizer
environment, and drains the bridge before final cost accounting.

## Outputs

- completed run directory:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916`
- actor ledger: `bridge_calls.jsonl`
- optimizer ledger: `optimizer_calls.jsonl`
- metrics: `summary.json`, `history.json`, and `cost_ledger.json`
- manifests: `config.json`, `bridge_manifest.json`, and per-task
  `run_manifest.json`
- repository config:
  `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e1_600s.yaml`

## Preflight And Independent Audit

- An independent GPT-5.6 Sol reviewer returned **FAIL / no-go** on the original
  preflight, so no paid request or rollout was launched.
- The static call graph was confirmed as native Codex CLI Responses, not the
  legacy VeruSAGE actor pipeline.
- 50/50 SkillOpt integration unit tests now pass after remediation.
- `compileall` passed.
- Targeted mypy passed for the six changed runtime files with missing external
  import stubs ignored; shell syntax validation passed.
- Fixed split counts are exactly 40/20/20 and all 80 source hashes were
  audited. The split is task-held-out but not project-held-out; AC has
  near-duplicate task contexts across splits.
- The key is configured in the ignored local `.env`. The bridge alone inherits
  it; actor and optimizer subprocesses receive only a non-secret local token.
- The independent remediation re-review returned PASS with no residual blocker.
- One live native-Responses task then passed with `hard=1`, `V2_TRACE`, exact
  returned model `deepseek-v4-pro`, 31/31 metered completed requests, zero
  provider errors, and complete accounting. It cost USD 0.068972596 off-peak.
- The formal epoch launched at `2026-08-17T23:15:29Z` in tmux session
  `skillopt-pro-fixed80-e1-20260817`.
- Full audit: `PRELAUNCH_AUDIT.md` and `PRELAUNCH_AUDIT.json` in this entry.

## Results

| metric | baseline | variant | delta |
|---|---:|---:|---:|
| selection hard solved | 13/20 | 14/20 | +1 task |
| selection actor cost (USD) | 1.722547 | 1.844379 | +0.121832 (+7.1%) |
| selection requests | 464 | 472 | +8 (+1.7%) |
| selection prompt tokens | 19,740,853 | 20,304,709 | +563,856 (+2.9%) |
| selection completion tokens | 516,445 | 569,149 | +52,704 (+10.2%) |
| selection prompt + completion | 20,257,298 | 20,873,858 | +616,560 (+3.0%) |

Training solved 23/40. Across S0, training, and S1, known actor usage was
98,624,902 prompt tokens, 2,354,039 completion tokens, 2,156 metered requests,
and USD 8.035293. All metered requests started off-peak. One additional
CloudFront 502 request in training has unknown usage and cost. The optimizer
used local quota and completed 9/10 logical calls; its successful calls used
596,369 prompt and 30,428 completion tokens. One oversized analyst input failed
three times before the downstream merge/rank/update path completed.

## Interpretation

The candidate passed the strict paired-selection gate, improving hard solved
from 13/20 to 14/20. It did not reduce selection-time tokens or cost: known
actor cost increased 7.1% and prompt-plus-completion tokens increased 3.0%.
This is evidence of a one-task capability improvement on the frozen selection
set, not evidence of token efficiency. `formal_epoch_validation.json` reports
`fail` because actor and optimizer accounting each contain an unknown-usage
event; the expected 20/40/20 task counts are exact. No held-out test was run.

## Next Action

Do not start Epoch 3 until the slow-update path skips byte-identical skill
comparisons and compacts optimizer input below the Codex character limit.
Audit the paired gained/lost selection tasks and make infrastructure-error
accounting explicit. Evaluate any proposed efficiency atoms with a matched
paired run rather than inferring token savings from an accepted gate.

## Scheduled Epoch 2 Continuation

Epoch 2 is scheduled for `2026-08-18T04:01:00Z` through persistent user-systemd
timer `skillopt-pro-fixed80-e2-20260818.timer`. The one-minute boundary buffer
keeps new requests out of the 01:00-04:00 UTC peak window. The timer launches
only Epoch 2 and a 60-second cost monitor; it does not chain Epoch 3.

The continuation reuses this run root and upstream resume state. It requires
step 1, current/best score 0.70, best step 1, no step-2 directory or prior
resume marker, and an idle bridge port. It snapshots the Epoch-1 compact
artifacts and records starting requests, tokens, and USD cost before opening
the bridge. The unchanged slow-update configuration means Epoch 2 can execute
up to 120 actor tasks: 40 training, 20 main gate, two 20-task longitudinal
rollouts, and a 20-task slow gate. This corrects the earlier 60-task estimate,
which counted only the core training and main gate.

Repository launch artifacts:

- `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e2_resume_600s.yaml`
- `skillopt-verusage/scripts/run_codex_pro_sol_fixed80_e2_resume_600s.sh`
- `skillopt-verusage/scripts/launch_codex_pro_sol_fixed80_e2_resume_600s.sh`

### Epoch 2 Result

The timer fired at `2026-08-18T04:01:00Z`, and the continuation completed at
`04:48:23Z`. All 2,303 new metered actor requests were off-peak. The main
training rollout solved 27/40; seven tasks reached the valid 600-second
truncation endpoint. The 3,947-byte candidate solved 12/20 on selection, with
seven truncations, versus the incumbent's stored 14/20. The strict gate
therefore rejected it. Best score remains 0.70 and best step remains Epoch-1
step 1.

| Epoch-2 phase | actor tasks | hard solved | known USD cost |
|---|---:|---:|---:|
| training rollout | 40 | 27 | 2.557402 |
| main selection gate | 20 | 12 | 1.819149 |
| slow previous-skill rollout | 20 | 12 | 1.756627 |
| slow current-skill rollout | 20 | 12 | 1.993222 |
| slow selection gate | 0 | not run | 0 |
| **Epoch 2 total** | **100** | — | **8.126399** |

The two slow-rollout skill files are byte-identical (SHA-256
`6d7deeba5d8754b9fac85ca42e64d178ac8ad9edd44c492db43c9bd776998a1a`).
Their paired outcomes contain 12 stable successes and 8 persistent failures,
with no improved or regressed task. The slow optimizer then received a
1,899,944-character prompt, exceeding Codex's 1,048,576-character limit. Three
identical attempts failed, so `slow_result.json` records `no_content` and no
slow candidate or slow gate exists. These 40 slow actor rollouts cost USD
3.749849 without producing an update.

Epoch 2 added 96,069,157 prompt tokens and 2,317,533 completion tokens. The
cumulative actor ledger is 4,459 metered requests, 194,694,059 prompt tokens,
4,671,572 completion tokens, and USD 16.161692. The continuation itself added
no provider error or unknown-cost request. Cumulative accounting remains
incomplete because of the inherited Epoch-1 502 and unknown-usage optimizer
attempts; the failed slow optimizer adds three more unknown-usage attempts.
No held-out test ran, and no Epoch 3 is scheduled.

## Fixed 600-Second Relaunch (2026-08-18)

The original run was paused during S0 at 18/20 final results after its two
remaining tasks timed out at the initial 1,200-second limit and entered
2,400-second retries. The trainer and both task process trees are stopped, the
bridge is idle, and the old run is retained rather than mixed with a different
time-budget endpoint.

A fresh Epoch 1 launched at `2026-08-18T00:16:07Z` with the following scoped
changes:

- actor wall-time budget: 600 seconds for S0, train, and S1;
- valid unsolved timeout: independent final Verus/Lynette judgment and no
  retry;
- `V0_INVALID` infrastructure failure: up to two clean retries, then abort;
- bridge request timeout: 540 seconds;
- concurrency: unchanged `workers=40`, hence phase caps 20/40/20;
- epoch boundary: exactly one formal epoch is launched, so no later epoch can
  begin after the 01:00 UTC peak-price boundary;
- monitoring: `live_cost_monitor.log` and `cost_ledger.json` refresh every 60
  seconds in a separate tmux session.

The 600-second retry behavior and formal recipe are covered by the full
52-test SkillOpt integration suite. The run entered S0 only after formal
preflight accepted the fresh root, bridge model, split, initial skill, and
timeout ordering.

Live paths:

- run:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916`
- run tmux: `skillopt-pro-fixed80-e1-600s-20260817`
- monitor tmux: `skillopt-pro-fixed80-e1-600s-cost-20260817`
- config:
  `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e1_600s.yaml`

The replacement completed at about `2026-08-18T00:56Z`, before the 01:00 UTC
peak boundary. S0 was 13/20, training was 23/40, and S1 was 14/20, so the
candidate was accepted. Its total wall time was 1,585.1 seconds. The final
known actor cost was USD 8.035293, all off-peak, with the accounting caveats
described above. Both the run and live-cost monitor sessions then exited.

## Epoch 3 And Epoch 4 Closeout (2026-08-18)

Epoch 3's main candidate improved the fixed selection score from 14/20 to
15/20 and became the retained best. Its slow candidate scored 13/20 and was
rejected. A missing eight-failure main analyst batch had overflowed Codex at
1,062,841 characters, so the continuation initially stopped before Epoch 4.

The main Reflect input was repaired by externalizing only the three longest
trajectory bodies in every minibatch as read-only paths. The exact missing
batch then rendered at 341,089 characters and completed. Re-merging the full
Epoch-3 evidence produced a repaired candidate that scored 14/20 versus the
retained 15/20; it was rejected at a separate actor cost of USD 1.284483.

Epoch 4 subsequently completed this exact schedule and cost:

| Epoch-4 phase | actor tasks | hard solved | actor requests | prompt tokens | completion tokens | USD cost |
|---|---:|---:|---:|---:|---:|---:|
| training rollout | 40 | 25 | 958 | 41,015,138 | 890,389 | 3.298833 |
| main selection gate | 20 | 14 | 423 | 17,861,405 | 385,566 | 1.457894 |
| slow previous rollout | 20 | 15 | 400 | 17,888,844 | 400,438 | 1.525049 |
| slow current rollout | 20 | 15 | 401 | 16,364,604 | 363,582 | 1.371737 |
| slow selection gate | 20 | 13 | 362 | 14,034,448 | 344,014 | 1.268472 |
| **total** | **120** | — | **2,544** | **107,164,439** | **2,383,989** | **8.921985** |

All Epoch-4 actor requests were metered off-peak, with no new provider error,
unmetered request, or unknown-cost request. All six main analyst calls, three
merge calls, one ranking call, and one slow-update call succeeded without
retry. The local-quota optimizer used 9,823,189 prompt tokens and 85,817
completion tokens across those 11 calls.

The 5,903-byte main candidate had zero selection gains and one regression
relative to the retained 15/20 skill, so the main gate rejected it at 14/20.
Because the accepted skill did not change, the slow previous/current skill
files were byte-identical (SHA-256
`1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`).
Both rollouts scored 15/20 with identical per-task outcomes, so they provide
trajectory variation but no causal skill comparison. The 8,660-byte slow
candidate had zero gains and two regressions and was rejected at 13/20.

The final best is therefore still the Epoch-3 15/20 skill. The canonical actor
ledger totals USD 35.359983; the separate repair gate raises the combined run
plus repair-validation spend to USD 36.644465. No held-out test was run.
Durable run artifacts include `steps/step_0004/step_record.json`,
`slow_update/epoch_04/slow_result.json`, `cost_ledger.json`, and
`epoch4_after_reflect_repair_complete.json` under the completed run directory.

The launcher's original one-shot final bridge-idle assertion raced request
teardown even though all 120 results and ledgers were complete. Post-run
validation passed all task-count, runtime-state, slow-output, and accounting
checks. The launcher now polls for an idle bridge for up to 30 seconds.

A compact internal-review figure was rendered and visually inspected. It
combines per-epoch actor tokens and API cost with training, main-gate,
slow-gate, and retained-best performance. The source CSV, plotting script,
PNG preview, and PDF are stored in
`figures/epoch_token_performance/` under the run directory. The polish pass
muted the palette, removed the heavy box frame, added light horizontal reading
guides, and simplified the legend. The unequal epoch task counts are labeled
directly, so the total-token bars are not interpreted as per-task efficiency.

For a direct cross-skill cost comparison, a separate reviewed figure uses only
the identical 20-task main-selection set in S0 and E1--E4. The task-ID sets
match exactly. S0/E1/E2/E3/E4 used
20.257M/20.874M/22.690M/13.606M/18.247M prompt-plus-completion actor tokens,
cost USD 1.723/1.844/1.819/1.207/1.458, and solved 13/14/12/15/14 tasks. E3 is
both cheapest and highest-scoring in these five observations, but the result
is descriptive rather than causal because each checkpoint has one stochastic
actor realization and a different candidate skill after S0. The aggregate
CSV, 100-row per-task CSV, generator, PNG, PDF, and self-review note are stored
under `figures/fixed_selection_cost_performance/` in the run directory.

The same directory now contains `skill_evolution_lineage_zh.md`, a Chinese
accepted-lineage audit. It confirms two semantic updates: E1 applied four
edits and moved the historical gate from 13/20 to 14/20; E3 applied two edits
and moved the retained score from 14/20 to 15/20. E1's sole historical U-to-S
task was `a23a4969155913255f76`; E3's was `aded79905be896942897`. The audit
maps the edits to their reconstructed failure minibatches and representative
success examples, while recording that the artifacts do not retain exact
phrase-to-task attribution. It also records the contrary fresh slow-comparison
evidence: S1 scored 14/20 and S2 12/20 on 20 training tasks. The two accepted
updates are therefore auditable, but their stable causal benefit is not yet
established.

The paired task audit confirms that early successful termination drives much
of the lower-cost/higher-score pattern. Across all 80 gate executions, solved
tasks averaged 178.9 seconds and USD 0.0440; unsolved tasks averaged 583.8
seconds and USD 0.1564. Zero solved tasks timed out, versus 23/25 unsolved
tasks, and actor cost correlates 0.955 with wall time. Still, only USD 0.2734
of the USD 0.6124 E2-to-E3 cost decrease came from the three tasks that changed
from unsolved to solved. Stable successes saved USD 0.1259 and persistent
failures USD 0.2132, showing cheaper traces beyond the binary solve-count
change. This remains a descriptive one-realization result.

Next action: audit why both Epoch-4 candidates produced no new selection
successes, and skip or redesign longitudinal slow comparison when the two
skill hashes are identical. Do not claim held-out improvement; test remained
sealed and unused.
