# Timing of the v2 index and G1 main-text changes

2026-10-28. Offline analysis of two completed concurrent comparisons. No new model calls, Verus runs or outcome adjudication.

**The v2 index shows a modest end-to-end time reduction in its batch; G1 does not. Neither shows lower final-candidate Verus verification time.** These are small development comparisons, not established general gains.

## Comparisons and measurement

- **Index v2:** 2 groups × 4 tasks × 2 repeats = **16 runs**. I0 original index versus I2 v2 index, with original R0 main text, ten new structured card bodies, Executive and harness fixed.
- **Main text G1:** 2 groups × 4 tasks × 3 repeats = **24 runs**. G0 original main versus G1 modified main, both using v2. Both arms share the reader-ID correction. This measures the incremental main-text change under v2, not G1+v2 versus the original seven-arm condition.
- Tasks: Rely, Unpack, De Morgan and Filter. Each comparison uses its own concurrent control; do not combine percentages across the two batches.

For each task, average all repeats in each arm, including failures. Divide **modified / control** and take the arithmetic mean of the four task ratios. Each task has equal weight; a ratio below 1 means lower relative time. This is not a ratio of summed run times or an average of individually paired repeat ratios. Repeat labels do not imply shared random seeds.

**End-to-end:** original `result.wall_seconds`, from episode start through agent exit/timeout and final host checks. Failures retain actual wall time, approximately 600 seconds, rather than being omitted.

**Final Verus check:** separately recorded `result.validation.verus.wall_seconds`, one host check of the final candidate after the agent stops. Includes Verus startup, front end and SMT, but excludes generation and Lynette. It is not pure SMT time. Failed candidates retain their actual check time, not 600 seconds.

**Cumulative command proxy:** sum completed actor command windows containing Verus invocations, including failed attempts and scratch probes, plus the final host check. Some commands also run Lynette or other operations. Shell and output handling remain included. This is verification-related command time, not precisely isolated cumulative prover time.

## Primary comparison: mean per-task ratios

| Change | End-to-end | Final Verus check | Cumulative command proxy | Dual passes, control → modified |
|---|---:|---:|---:|---:|
| Index v2 | 0.919 | 1.069 | 0.874 | 5/8 → 6/8 |
| Main G1 (both v2) | 1.158 | 1.137 | 1.182 | 9/12 → 10/12 |

v2: mean per-task relative end-to-end time is **8.1% lower**, and the cumulative command proxy is **12.6% lower**. Final Verus time is **6.9% higher**; this does not show faster proof checking. The lower cumulative proxy is consistent with fewer completed verification-command windows (97 → 72), but does not establish better card selection as its cause.

G1: mean per-task relative end-to-end time is **15.8% higher**, final Verus time **13.7% higher**, and the cumulative proxy **18.2% higher**. It has no timing advantage in this batch despite one additional pass. The older report's nearly unchanged summed actor time is a different statistic; equal task weighting gives short Filter tasks the same weight as Rely and De Morgan.

## Per-task end-to-end time

Seconds are the mean of all repeats for that task; failures are included.

| Comparison | Task | Control mean s | Modified mean s | Modified / control |
|---|---|---:|---:|---:|
| v2 index | Rely | 457.2 | 567.2 | 1.241 |
| v2 index | Unpack | 384.8 | 209.8 | 0.545 |
| v2 index | De Morgan | 601.0 | 445.2 | 0.741 |
| v2 index | Filter | 53.7 | 61.8 | 1.151 |
| G1 main | Rely | 435.8 | 494.8 | 1.136 |
| G1 main | Unpack | 325.4 | 200.5 | 0.616 |
| G1 main | De Morgan | 442.5 | 461.1 | 1.042 |
| G1 main | Filter | 54.5 | 100.2 | 1.839 |

v2 is faster on Unpack and De Morgan, slower on Rely and Filter. G1 is faster only on Unpack; Filter rises by about 83.9%. The existing G1 review identified bulk card exposure in one Filter run, but that alone does not explain all three Filter runs' increased time. No cases are dropped after observing outcomes.

## Absolute time scale (descriptive, not ratio estimator)

| Batch | Arm | Runs | Mean end-to-end s | Mean final Verus s | Mean cumulative proxy s |
|---|---|---:|---:|---:|---:|
| index_v2 | I0_old_index | 8 | 374.186 | 0.673 | 5.380 |
| index_v2 | I2_matching_v2 | 8 | 320.974 | 0.713 | 4.605 |
| main_G1 | G0_original_main | 12 | 314.554 | 0.597 | 4.606 |
| main_G1 | G1_obligation_main | 12 | 314.138 | 0.680 | 5.612 |

## Verification and limitations

All 40 unique episodes are present with the expected task/arm/repeat counts. Final Verus times exactly match independent host verifier events. Actor times reconcile with original reports. Existing deadline audits agree with the frozen primary outcomes; no historical review was rerun. The v2 De Morgan second repeat remains a failure under the original 600-second observation rule despite final checks passing just after the cutoff.

416 completed actor command windows were counted once using episode/item IDs; derived verifier echo events were excluded. There are no missing start/end records among detected invocations. A secondary scan of uncounted commands with Verus-related paths or verification results found only three reads of tool scripts and one invalid wrapper call, all correctly excluded. 48 mixed command windows cannot be split into separate Verus/ancillary durations. Scratch probes and shell/output overhead are retained in the proxy. Pure SMT timing is unavailable.

All 124 source files are hash-checked unchanged (40 results, 40 event logs, 40 deadline audits, and four report/audit files). Failed candidates can terminate verification early; successful proofs and failed checks are not equivalent workloads. Single timings also reflect host load and runtime variability. These four repeatedly inspected development tasks do not establish causal or held-out gains.

## Sources and reproduction

- [Per-task calculations](per-task.csv), [40 episode cells](cells.csv), command timing windows (archive-only: `RUN_ROOT/followup-timing-20261028/commands.csv`), [aggregate analysis](summary.json) and [source hashes](source-hashes.json)
- [Original log-analysis script](archive_analyze.py): requires the original external run layout; do not run it in this publication directory. [Portable ratio calculation](recompute_ratios.py) reads the published cells only.
- [Index v2 original review](../index_v2/REPORT.md)
- [G1 original review](../main_G1/REPORT.md)
