# Success-only token and timeout census

## Scope and method

User follow-up requests timeout counts and successful-trace consumption rather
than only all-run averages. This is a bounded, read-only follow-up to ENTRY.md;
no new inference, validator execution, production prompt, or card changes.

- Five complete downstream comparisons: 304 unique selected episodes, 234
  budgeted dual-pass successes and 70 ordinary timeouts (23.0%). No normal
  non-timeout unsolved or provider-invalid rows in this selected complete set.
- Main experiment: validation20 x four conditions x two repetitions = 160.
  Repair/guidance/latest Executive: validation20 x two conditions = 40 each.
  Executive pilot: selected validation6 x two conditions x two repeats = 24.
  These are correlated observations on the same 20 tasks, not 304 independent tasks.
- The four-task repair smoke is already included in repair20; do not add it again.
  Excluded historical/parked invalid attempts are reported separately below.
- Success requires provider validity, within_budget, final proof_solved and
  safety_passed. Historical primary outcomes remain unchanged.
- Usage is re-aggregated from fully settled provider ledgers using exact task
  keys. Main160 result/ledger hashes checked against the canonical source map;
  later144 usage fields reconcile exactly with their saved settled_usage.
  All185 source files hash-verified after analysis;304 episode paths unique.
- Total tokens = cumulative prompt + completion. Reasoning is already a subset
  of completion: never add it twice. Prompt includes repeated cached context,
  not unique text. Cache-hit + cache-miss = prompt verified for all304 episodes.
- Statistics are per trace. Percentiles use linear interpolation. Comparisons
  are within each run only, not a cross-run causal upgrade ranking.

## 1. Outcome counts

| Comparison/condition | Selected n | Success | Ordinary timeout | Provider-invalid in selected set |
|---|---:|---:|---:|---:|
| Main initial | 40 | 31 | 9 | 0 |
| Main native SkillOpt | 40 | 31 | 9 | 0 |
| Main original-only cards | 40 | 31 | 9 | 0 |
| Main augmented cards | 40 | 32 | 8 | 0 |
| Repair old | 20 | 15 | 5 | 0 |
| Repair revised | 20 | 16 | 4 | 0 |
| Retrieval guidance control | 20 | 16 | 4 | 0 |
| Retrieval guidance enabled | 20 | 13 | 7 | 0 |
| Executive pilot old | 12 | 9 | 3 | 0 |
| Executive pilot revised | 12 | 11 | 1 | 0 |
| Latest full Executive old | 20 | 14 | 6 | 0 |
| Latest full Executive revised | 20 | 15 | 5 | 0 |
| Total selected complete comparisons | 304 | 234 | 70 | 0 |

Separate, NOT pooled: the parked80 run has28 attempted rows,26 valid
(20 successes,6 ordinary timeouts) and2 provider/terminal-invalid rows;
52 cells unstarted. Its valid13 pairs are old11/13 versus revised9/13,
timeouts2 versus4. Main160 recovery also excluded4 earlier invalid parent
evaluation rows before obtaining the canonical matrix. Thus zero invalids in
the304 selected rows does NOT mean the overall history had no infrastructure
failures. Invalid attempts and their known/unknown costs are not erased.

## 2. Successful traces only: distributions

Units: K=1,000 tokens. Total includes prompt and completion. n is success count.

| Condition | n | Total mean K | Total median K | Total p90 K | Output mean K | Output median K | Actor mean s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Main initial | 31 | 467.7 | 237.6 | 858.7 | 14.07 | 11.32 | 157.9 |
| Main native | 31 | 700.8 | 261.4 | 1498.7 | 15.19 | 9.79 | 176.7 |
| Main original-only | 31 | 680.7 | 352.8 | 1461.9 | 13.36 | 8.48 | 161.2 |
| Main augmented | 32 | 831.5 | 395.0 | 2125.1 | 14.75 | 10.02 | 177.8 |
| Repair old | 15 | 1060.0 | 501.4 | 3310.2 | 18.87 | 14.27 | 231.6 |
| Repair revised | 16 | 668.1 | 366.2 | 1958.4 | 13.10 | 9.37 | 166.3 |
| Guidance control | 16 | 565.8 | 347.2 | 1324.7 | 11.24 | 10.55 | 211.4 |
| Guidance enabled | 13 | 820.7 | 461.1 | 1725.6 | 11.99 | 8.41 | 229.5 |
| Executive pilot old | 9 | 1407.3 | 637.7 | 2731.7 | 28.33 | 21.06 | 254.6 |
| Executive pilot revised | 11 | 1456.5 | 619.5 | 3679.6 | 23.78 | 21.43 | 224.5 |
| Latest Executive old | 14 | 461.9 | 341.9 | 816.4 | 10.01 | 8.07 | 199.1 |
| Latest Executive revised | 15 | 619.3 | 433.5 | 1299.1 | 13.29 | 10.83 | 256.9 |

Mean is materially above median in most groups: a small number of long successful
explorations strongly affect totals. Different success sets also differ in
difficulty; the next table matches the same task and repeat.

Success-only token component means, K tokens per trace:

| Condition | Input | Cache hit | Cache miss | Output | Reasoning (inside output) |
|---|---:|---:|---:|---:|---:|
| Main initial | 453.61 | 444.06 | 9.55 | 14.07 | 10.82 |
| Main native | 685.66 | 673.97 | 11.69 | 15.19 | 11.57 |
| Main original-only | 667.35 | 651.47 | 15.88 | 13.36 | 9.76 |
| Main augmented | 816.72 | 797.86 | 18.86 | 14.75 | 11.04 |
| Repair old | 1041.13 | 1017.79 | 23.34 | 18.87 | 14.46 |
| Repair revised | 654.99 | 637.38 | 17.61 | 13.10 | 9.59 |
| Guidance control | 554.52 | 537.85 | 16.67 | 11.24 | 8.34 |
| Guidance enabled | 808.72 | 786.87 | 21.85 | 11.99 | 8.44 |
| Executive pilot old | 1378.96 | 1358.76 | 20.19 | 28.33 | 22.62 |
| Executive pilot revised | 1432.67 | 1407.51 | 25.16 | 23.78 | 19.04 |
| Latest Executive old | 451.90 | 438.01 | 13.89 | 10.01 | 7.00 |
| Latest Executive revised | 605.98 | 588.83 | 17.15 | 13.29 | 10.17 |

Exact sums/means/medians/p25/p75/p90/min/max for every component, successful,
timeout, and all episodes are in statistics.json; episodes.csv contains each
selected trace's counts and settled usage.

## 3. Same task/repeat, both versions successful

Percentages compare sums on exactly the same joint-success pairs, revised
relative to its within-run control. This is a conditional descriptive analysis,
not an unbiased causal effect; retain success/timeout and all-run cost alongside it.

| Comparison | Pairs (distinct tasks) | Input change | Output change | Actor time change | Estimated cost change |
|---|---:|---:|---:|---:|---:|
| Original-only -> augmented | 30 (16) | +47.3% | +17.0% | +17.2% | +27.6% |
| Repair package | 15 (15) | -35.0% | -28.8% | -26.7% | -37.6% |
| Optional retrieval guidance | 12 (12) | +6.3% | +1.3% | +0.6% | +4.5% |
| Executive selected pilot | 8 (5) | +0.04% | -34.8% | -26.2% | -16.3% |
| Latest full Executive | 14 (14) | +30.8% | +21.7% | +20.2% | +23.0% |

Interpretation:

- Augmentation still does not support efficiency improvement after excluding
  mismatched failures: successful matched runs themselves consume more.
- Repair-package efficiency remains positive on matched successes. It changed
  bodies, index and library access together; no single-factor attribution.
- Guidance's all-run time regression (+24.3%) is not reproduced on its12
  matched successes (+0.6%). The changed success/timeout outcomes matter much
  more than broad slowdown among joint successes. This does not identify a
  causal explanation for the four losses.
- Executive pilot's output/time benefit remains on its selected matched
  successes, but fails to generalize to the full run. Latest matched successes
  show substantial extra input/output/time, not just a timeout-composition effect.
- These results do not isolate card retrieval frequency, card quality or index
  exposure as the cause. Reading less is not independently proven to help.

## 4. Timeout costs remain part of total spend

USD estimates from settled usage; not provider invoices. Rounded below.

| Condition | All selected cost | Success cost | Timeout cost |
|---|---:|---:|---:|
| Main initial | 6.493198 | 2.724337 | 3.768861 |
| Main native | 6.683934 | 3.262038 | 3.421895 |
| Main original-only | 6.743518 | 3.177889 | 3.565630 |
| Main augmented | 7.263744 | 3.789912 | 3.473832 |
| Repair old | 2.591690 | 1.540484 | 1.051206 |
| Repair revised | 1.944083 | 0.992690 | 0.951393 |
| Guidance control | 2.606243 | 1.443155 | 1.163088 |
| Guidance enabled | 3.110041 | 1.442297 | 1.667744 |
| Executive pilot old | 1.734914 | 0.893776 | 0.841137 |
| Executive pilot revised | 1.342586 | 1.041286 | 0.301301 |
| Latest Executive old | 2.548294 | 1.081532 | 1.466763 |
| Latest Executive revised | 2.676945 | 1.517477 | 1.159468 |
| Total selected | 45.739190 | 22.906873 | 22.832317 |

The70 timeouts account for49.9% of selected cost. USD45.74 is NOT total project
spend: training/learning, excluded attempts and the parked run are outside this
selected metric projection. Main recovery already records excluded known
evaluation cost USD0.499855576 plus one unresolved request, and a broader
campaign cost ledger. Parked run recorded USD2.529861752 with one unmetered
dispatched error: accounting incomplete, not zero. Preserve those ledgers and
do not charge the selected projection a second time as a separate invoice.

## 5. Did timeouts already contain a verified solution?

All70 raw/normalized streams scanned. Automated extraction is only a candidate
list: `cat tools/run_lynette.sh` returning0 is NOT a safety check; scratch.rs
verification is NOT full-task verification; a pipeline exit0 is NOT Verus proof.
Manual review confirms four episodes with full candidate Verus and Lynette
pass before cutoff, including matching saved candidate hashes at the checks:

| Run/condition/task/repeat | Raw Verus/Lynette lines | Approx first reliable dual-pass s | Final saved dual-pass |
|---|---|---:|---|
| Main original-only a23a4969155913255f76 r1 | 111/116 | 493 | yes |
| Main augmented b9e5384e929589f7b0cd r1 | 136/139 | 553 | no |
| Main augmented b9e5384e929589f7b0cd r2 | 181/183 | 558 | yes |
| Executive pilot old b9e5384e929589f7b0cd repeat1 | 208/212 (explicit Lynette exit0);219 combined recheck | 576 | yes |

Times above are relative to first normalized event (approximate, not exact actor
clock), comfortably before600s. Candidate hashes respectively:
cede7e68db790f8c0dbec9c88670b04fc4d98dc536f84ecdf631234d71d20981,
6ce8e8dfd1a2d9afa10984200400a4044b80af0833aecbeac3651fc66ee3f11f,
13fbcc608b36ed45302df99da4fdd02517279afdae137d67574ecbcecc65459b,
c294efbac0d99819013056137fe09ca0ca20332a15e17ed176af20042a7ef31f.

Main augmented b9e r1 is the clearest failure: lines140/145 explicitly say both
checks pass and invoke card-052 for optional warning cleanup;147 edits,
149/153 fail compilation, and the run times out without a final safe solution.
This is direct evidence of an unneeded post-pass edit losing an already verified
candidate, not proof of how much a stop rule would improve a fresh experiment.

A fifth timeout, main initial b9e r2, passes final host validation after actor
termination, but its saved actor stream has no completed full-task successful
check (last command started at raw73, incomplete). Do not assert that both checks
passed before cutoff. The other65 timeouts have no observed full dual-pass in
the saved actor streams; this is absence of recorded evidence, not proof that
an unrecorded/in-flight command never passed. Thus4 confirmed early dual-pass,
1 final-only timing-unconfirmed,65 no observed full dual-pass; no outcome
reclassification. All11 latest full Executive timeouts are in the latter group.

## Reproducibility and next action

- Script: `scripts/summarize_success_timeout_tokens.py`.
- Unit checks:3 passed; outcome precedence, linear distribution statistics,
  exact task/repeat joint-success matching and duplicate/missing-pair rejection.
- External canonical output under
  `VERUS_SKILL_RUN_ROOT/skillopt-verusage/success-timeout-statistics-20261010-reviewed/`:
  `statistics.json`, `episodes.csv`, `timeout_evidence.json`.
- Output SHA256 respectively:
  cdb83358a937f2f1735562a7589918160a18704c2c549575a60caa3567071c53,
  e32361ebf4dbed7c39ff9d8889cf72cb21db45c7dd79836d8c6023daaba57db0,
  2f1a8395099fa9b296c3618cd4e35bbedbf82e95258071cdd73b90d0fe68d880.
- Replay with Python3, `--run-root` set to the run-root's skillopt-verusage
  directory and `--output` to a NEW subdirectory; existing output is rejected.
- Dedicated artifact/science tools unavailable; local source/output hashes and
  canonical repository memory provide fallback evidence, not a graph API claim.
- Next: retain outcome + success-only + paired success + all-run resource views
  in future reports. A pass-and-freeze stopping experiment is a supported
  candidate, not implemented here; it cannot alone explain latest regressions.
- No raw/sealed/legacy data or frozen runs modified; no paid requests. This
  compact report has no credentials, meeting content, or personal absolute paths.
