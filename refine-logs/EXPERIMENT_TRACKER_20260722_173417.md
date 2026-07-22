# R041A + ATLAS Paired Experiment Tracker

历史 R036–R061 见 `EXPERIMENT_TRACKER_20260722_125407.md`。本页记录当前并行分支；状态：TODO / IN_PROGRESS / DONE / GO / PARTIAL / BLOCKED / STOP。

| Run ID | Purpose | Matrix | Primary checks | Status | Notes |
|---|---|---|---|---|---|
| R040D-A | freeze adaptive qualitative cases | 3 H0-only cases | strict stable-pass, strict stable-closest, mixed-safe unstable; hashes | DONE | exactly one eligible case per class; H1/H2 reads 0 |
| R041A-M | freeze contrast manifest | 3 cases × 3 conditions × 3 reps | 27 immutable records; 9 H0 refs + 18 new jobs | DONE | records SHA `ef23ef30...` |
| R041A-L | local rationale contrast | Qwen H1/H2 on 3 cases, 3 reps | result/usage/Verus/Lynette/config identity | IN_PROGRESS | serialized live screen `r041a_contrast_20260722` |
| A001-F | freeze paired ATLAS contract | taxonomy + 8 held-out failures × 2 models | input/taxonomy/model/transport hashes | DONE | 4 FAILED + 4 TIMEOUT; 8 unique tasks |
| A001-Q | ATLAS local classification | 8 traces × Qwen3.6-27B × 1 | schema/code validity, evidence, usage, time | DONE | strict 8/8 valid; 0 vendor coercions |
| A001-G | ATLAS frontier classification | 8 traces × gpt-5.6-sol/high × 1 | schema/code validity, evidence, time | DONE | strict 8/8 valid; 0 vendor coercions |
| A001-A | paired failure-mode analysis | 8 matched pairs | code/category agreement, grounded evidence, recovery specificity | DONE | code agreement 7/8; blinded quality 36 small vs 45 large, large wins 7/8 |

## Immediate queue

1. Complete R040D-A and A001-F manifests; run unit tests.
2. Launch A001-G and A001-Q; monitor exact completion counts.
3. When A001-Q releases local vLLM, launch R041A-L immediately.
4. Analyze ATLAS pairs while R041A-L continues; update durable memory only from completed audited artifacts.
