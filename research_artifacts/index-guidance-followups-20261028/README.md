# Index v2 and main-instruction follow-up experiments

This is the reviewed follow-up to the [seven-arm / 112-run publication](../skill-chain-seven-arm-20261022/README.md).
It publishes the exact evaluated skill bundles, intervention diffs, experiment
drivers, selected contract fields, reviewed reports and scalar results for three
completed comparisons. No new experiment was run for this publication.

## Comparisons and results

All batches used DeepSeek V4 Pro, reasoning effort `max`, two workers, and the
same four development tasks: Rely, Unpack, De Morgan and Filter. A primary pass
requires Verus and Lynette success on the **same candidate observed within 600 s**.
Failures are retained. Repeat labels are scheduling blocks, not shared seeds.

| Batch | Matrix | Control → modified passes | Main finding |
|---|---:|---:|---|
| [Index v2](index_v2/REPORT.md) | 2 arms × 4 tasks × 2 = 16 | I0 5/8 → I2 6/8 | Some matching and cost signals; later supplementary retrieval remained absent. |
| [Main G1](main_G1/REPORT.md) | 2 arms × 4 tasks × 3 = 24 | G0 9/12 → G1 10/12 | No established matching or efficiency advantage; one G1 bulk-read deviation. |
| [Premise sentence G2](premise_G2/REPORT.md) | 2 arms × 4 tasks × 3 = 24 | G1 10/12 → G2 8/12 | G2 was not retained; more cost and no observed improvement in the intended explanations. |

The index-v2 De Morgan second repeat has a valid final candidate, but host dual
success was observed just after 600 s; it remains a primary failure. Do not replace
6/8 by its 7/8 final-validity secondary count. Identical G1 instructions produced
6/12 selective-reading episodes in the first main comparison and 3/12 in the
G1/G2 batch, despite both scoring 10/12. The first batch additionally exposed all
ten bodies in one Filter episode; exposure is not adoption or causal benefit.

The current engineering choice is **v2 index principles + provisional G1**.
It is not an established optimum. Historical reports preserve their recommendations
at the time of review; this paragraph states the later choice. G0 + v2 remains a
useful control. Four repeatedly inspected development tasks cannot establish
held-out gains or a general harmful-missed-read rate.

## Exact materials to inspect

| Comparison | Control | Modified | Intervention |
|---|---|---|---|
| Index | [I0 SKILL](index_v2/bundles/I0_old_index/SKILL.md) | [I2 SKILL](index_v2/bundles/I2_matching_v2/SKILL.md) | [I0–I2 diff](index_v2/I0-I2.diff): only the index changes |
| Main | [G0 SKILL](main_G1/bundles/G0_original_main/SKILL.md) | [G1 SKILL](main_G1/bundles/G1_obligation_main/SKILL.md) | [G0–G1 diff](main_G1/G0-G1.diff): three approved insertions |
| Premise sentence | [G1 SKILL](premise_G2/bundles/G1_current/SKILL.md) | [G2 SKILL](premise_G2/bundles/G2_premise_check/SKILL.md) | [G1–G2 diff](premise_G2/G1-G2.diff): one replacement |

Every bundle includes the exact `cards.json` and `card_read.py`. All use the same
ten new structured bodies from the seven-arm `new_skeleton` condition; this is
**structured guidance, not pseudocode**. [All bodies as Markdown](../skill-chain-seven-arm-20261022/material-views/new_skeleton--all-cards.md)
are already published. [v2 index](INDEX_V2.md) sharpens obligation and entry
boundaries; under the same local tokenizer the original index has 690 tokens and
v2 has 521.

G1 keeps the original instructions and adds three short prompts to reconsider
cards when the obligation/premises/scope changes, revisit earlier choices, and
turn guidance into a locally checked step. See [approved insertions](main_G1/reviewed-insertions.json)
and [guidance description](main_G1/GUIDANCE.md). There is no mandatory opening
read, deadline-awareness prompt or task-specific card prescription.

The index comparison deliberately retained the shared `card-001` example.
Before the main comparison, **both G0 and G1** changed it to the valid `new-001`:
[common ID correction](main_G1/COMMON_ID_FIX.diff). Thus the main comparison isolates
G1 under v2 with that shared correction; it does not directly compare the final
G1+v2 package to the original seven-arm run. Each batch also includes host `EXECUTIVE.md` and `TASK.md` (its personal vstd path
is replaced with `${VSTD_SOURCE_ROOT}`); main-SKILL wording affected by G1 is part of its intervention.

## Time and cost

[Timing report](timing/REPORT.md), [40 measured episode cells](timing/cells.csv),
[per-task calculations](timing/per-task.csv), [aggregate results](timing/summary.json).

For each task, first average all repetitions in each arm, including failures.
Compute **modified / control**, then arithmetic-mean the four task ratios with
equal task weights. These are mean per-task time ratios, not ratios of sums or
means over successful runs only.

| Change | End-to-end ratio | Final Verus ratio | Cumulative verification-command proxy ratio |
|---|---:|---:|---:|
| Index v2 | 0.919 | 1.069 | 0.874 |
| G1 main, both v2 | 1.158 | 1.137 | 1.182 |

v2 shows a small end-to-end benefit in its batch; G1 does not. Neither reduces the
final Verus check time. End-to-end includes actor exit/timeout and host final
checks. Final Verus is a separately timed process including startup/front-end/SMT,
not pure solver time. The cumulative proxy includes intermediate attempts,
scratch checks, shell overhead and mixed commands that cannot be split into
Verus and other work. Pure SMT time was not logged. Failed checks may terminate
early; always read timing together with pass rate.

v2 reduced aggregate total tokens by 13.8%, output tokens by 15.8%, and estimated
API cost by 12.5% (about $1.811 → $1.585). These are batch-total cost comparisons,
not the time-ratio estimator above. Total tokens are input + output; reasoning
is a subset of output. Repeated/cached input is counted. Reduced token totals do
not translate proportionally to latency. Costs are estimates, not invoices.
Do not combine savings from these separate batches.

Recompute the published timing ratios without model calls, raw logs or Verus:

```bash
python3 research_artifacts/index-guidance-followups-20261028/timing/recompute_ratios.py
```

The [original log-analysis script](timing/archive_analyze.py) is retained for method
inspection. Its original location was `RUN_ROOT/followup-timing-20261028/analyze.py`;
it requires the original sibling run directories and absolute paths in their
historical reports. Do not run it inside this publication directory. The portable
calculator above works on the reviewed measurements published here.

## Experiment code and offline tests

| Purpose | Driver |
|---|---|
| Shared R0/R1 orchestration and read audit | [evaluate_retrieval_reassessment.py](../../scripts/evaluate_retrieval_reassessment.py) |
| Earlier index preparation / v1 orchestration dependency | [prepare_index_ablation.py](../../scripts/prepare_index_ablation.py), [evaluate_index_ablation.py](../../scripts/evaluate_index_ablation.py) |
| Index-v2 sixteen-run experiment | [evaluate_index_matching_v2.py](../../scripts/evaluate_index_matching_v2.py) |
| G0/G1 twenty-four-run experiment | [evaluate_obligation_guidance.py](../../scripts/evaluate_obligation_guidance.py) |
| G1/G2 twenty-four-run experiment | [evaluate_guidance_premises.py](../../scripts/evaluate_guidance_premises.py) |

These are historical guarded drivers, not a self-contained deployment of the
private run archives. Preparation needs their source runs, verifier installation,
review receipts, research preparation documents, original contracts and hash
manifests. Published `contract-summary.json` files are selected review fields,
not launch contracts. Historical budgets/authorization logic do not authorize
new API calls; live launch approvals and credentials are intentionally absent.

From an environment with the repository test dependencies installed:

```bash
PYTHONPATH=scripts:src:skillopt-verusage/src:skill-evolution-pilot/src \
python3 -m pytest -q tests/test_retrieval_reassessment.py \
  tests/test_index_ablation.py tests/test_index_matching_v2.py \
  tests/test_obligation_guidance.py tests/test_guidance_premises.py \
  tests/test_index_guidance_publication.py
```

Tests use fixtures and mocked launches, not live API/prover execution. The G2
fixture path now points to the published byte-exact G1 bundle, rather than an
external private run directory. Other historical driver behavior is unchanged.

## Provenance and publication boundary

[manifest.json](manifest.json) records original relative source names, source
SHA-256 hashes, published hashes and transformations. `RUN_ROOT` denotes the
external `skillopt-verusage` run directory. Each batch's `episodes.csv` contains
selected reviewed outcome, cost and read-behavior fields; repeats are one-based.
The detailed reports retain original conclusions. Non-published evidence links
are labeled archive references, rather than broken links to private files.

Frozen bundles, diffs and EXECUTIVE are byte-identical to evaluated inputs.
TASK retains all wording except the installed vstd path placeholder; its original
source hash is preserved in the manifest, and it is not an executable run receipt.
Reports and scalar tables normalize machine paths. Raw requests/responses,
complete trajectories, final candidate solutions, launch approvals, credentials,
provider ledgers and complete run directories are not included. Original archives
were not edited, and no completed historical review was rerun.
