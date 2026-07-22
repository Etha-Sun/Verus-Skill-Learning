# Qwen capability calibration gate

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-21T17:21:29`
- status: `in_progress`
- objective: replace the one-task mechanical smoke with a leakage-safe
  30-task Qwen3.6-27B capability map, then freeze one stable pass,
  closest-failure, and stalled qualitative case before viewing H1/H2 outcomes
- dataset/split: effective train manifest only; 30 calibration tasks balanced
  15 Anvil / 15 IronKV; model inputs come only from canonical `unverified/`
  files; a standard-trace paired verified artifact is required; sealed MA/NR
  content excluded
- baseline: H0 hands-off prompt through the existing Copilot harness,
  Qwen3.6-27B, TP=4, fixed tools/context/timeout
- variants: none during the R040B screen; H1/H2 are introduced only after
  R040D tier freeze and R041 prompt freeze
- metrics: security-valid solved, candidate presence, Verus/Lynette outcomes,
  usage, wall time, context/tool failure, repetition stability, tier occupancy
- leakage controls: exclude R040 normalized task ids and normalized source
  hashes; reject 7-token-shingle Jaccard >=0.90; sealed content reads 0; raw
  data remain read-only
- stop condition: do not deploy R040B until the 30-task audit and model-free
  sanity pass and all four local GPUs are available; stop/branch the local
  contrast if all tasks stall, infrastructure failures dominate, or tiers are
  unstable

## Planning Decisions

1. R040A freezes and audits the 30-task manifest.
2. R040B runs one H0 repetition on all 30 tasks.
3. R040C adds two H0 repetitions only for predeclared boundary candidates.
4. The completed screen showed the old `near_miss` rule is unreachable because
   every source has exactly one error. R040C therefore selects three H0-only
   candidates each for pass, `closest_failure`, and stalled, and R040D freezes
   the first stable task in each class. `closest_failure` requires a proof-safe,
   compilable candidate with one localized residual proof failure; it is not
   reported as strict verifier progress. Timeout, context exhaustion, and tool
   failure remain a separate infrastructure tier.
5. R041 remains the independent 30-trace prompt-distillation run.
6. R041A runs the frozen global H2, length-matched H1, and H0 on exactly three
   frozen tasks for 27 records. This is qualitative only.
7. Calibration results cannot support the held-out method claim; R042-R053
   remain the live evaluation path.

## Commands

```bash
# Completed read-only preflight
set -a; source .env; set +a
PYTHONPATH=src python3 -m verus_self_evolve.data_layout
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu \
  --format=csv,noheader,nounits

# Planned after implementation
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_calibration select ...
PYTHONPATH=src python3 -m unittest tests.test_handsoff_calibration -v
```

## Outputs

- canonical plan: `refine-logs/EXPERIMENT_PLAN.md`
- versioned plan: `refine-logs/EXPERIMENT_PLAN_20260722_125407.md`
- canonical tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- versioned tracker: `refine-logs/EXPERIMENT_TRACKER_20260722_125407.md`
- research contract: `idea-stage/docs/research_contract.md`
- planned run root: `${VERUS_SKILL_RUN_ROOT}/qwen_capability_calibration_20260721/`
- planned manifest: `r040a_tasks.jsonl`
- planned metrics: `r040a_selection_summary.json`,
  `r040a_leakage_report.json`, and later `capability_summary.json`

## Preflight Results

| metric | result |
|---|---:|
| data/run layout validation | PASS |
| metadata-eligible train rows after R040 exact exclusion | 2,752 |
| metadata-eligible unique tasks | 425 |
| eligible row groups | 1,703 Anvil / 1,049 IronKV |
| local GPUs at planning time | 4/4 busy at 99-100% utilization |
| sealed content reads | 0 |

## Independent Code Review

The first implementation passed 58 unit tests but received `NO-GO` from an
independent reviewer. Blocking findings included non-canonical variant bias,
trusting manifest hashes without physical-path checks, missing source-uniqueness
gates, absent tokenizer context enforcement, unsafe incomplete tier freezing,
missing two-stage boundary selection, and the invalid use of total
`verified_count` as proof progress.

Per the experiment-bridge restart rule, the first attempt is being cleanly
reimplemented from the revised contract rather than incrementally patched.
The revised route uses canonical `unverified/` tasks, standard paired verified
artifacts, physical hash/containment checks, tokenizer-based 32,768 context
eligibility, mutually exclusive outcomes, immutable complete-only tier freeze,
and target-error-count reduction for `near_miss`.

Review artifact:

- `refine-logs/EXPERIMENT_CODE_REVIEW_20260721_173320.md`

## R040A Result

The fourth, canonical attempt freezes 30 canonical originals with 15 Anvil / 15
IronKV and 10 tasks in each small/medium/large tokenizer-size bin. All 30 tasks
are unique by normalized task and source hash, all fail the source Verus
precheck, and all 30 paired standard-trace answers pass both the current Verus
and Lynette comparison against the canonical source. R040 exact-task,
exact-source, and >=0.90 near-code overlap are all zero; sealed content reads
remain zero. The largest selected static prompt+source context is 2,447 tokens
under the frozen 32,768-token configuration.

Canonical compact artifacts:

- `${VERUS_SKILL_RUN_ROOT}/r040a_qwen_calibration_20260721_attempt4/`
- `${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_manifest_attempt3/`
- `${VERUS_SKILL_RUN_ROOT}/r040b_sanity_20260721_attempt3/`

The earlier attempts remain preserved as failed audit history and must not be
used for R040B. The final implementation passes 69 repository tests and checks
source, prompt, H0 condition, model alias/path/config hash, tool binary hashes,
timeout, and max-context identity before tier aggregation.

Final independent code review verdict: `GO`, with the sole non-blocking note to
reconfirm free GPUs and the live 32,768-context vLLM service immediately before
launch. Review artifact:

- `refine-logs/EXPERIMENT_CODE_REVIEW_20260721_175704.md`

## R040B Live Deployment

The external workload was released and the reviewed environment was launched
as screen `r040b_vllm_attempt2_20260721`. The endpoint exposes only the frozen
`qwen35-27b` alias with TP=4 and `max_model_len=32768`; live Copilot automatic
tool calls require the Qwen3 reasoning parser and Qwen3-Coder tool parser.

Canonical live root:

- `${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_live_attempt2/`

Rank 1 (`0645a55f07be097402be`) finished without timeout. Candidate, Verus,
Lynette, usage, and manifest records are all present; Verus failed, Lynette
passed, and all frozen identity fields match. `_run_record` classifies it as
`stalled`. Copilot reports 979 seconds, approximately 1.1M input tokens and
31.5k output tokens. This is one calibration outcome, not a model-capability or
knowledge-effect conclusion.

The remaining 29 H0 jobs are running sequentially in screen
`r040b_remaining_attempt2_20260721`. The resumable driver checks endpoint
health before every task and refuses to overwrite partial outputs.

Rank 1 also exposed an unmodeled tool-adherence caveat: its Copilot log shows
12 temporary Verus API probes written below `/tmp` despite the workspace-only
instruction. After exact enumeration these scratch files were removed; formal
run evidence was preserved and the read-only raw corpus was untouched. This is
not currently represented by `_run_record`'s pass/near-miss/stalled taxonomy.
To preserve the frozen screen contract, neither the prompt nor classifier will
change until R040B completes.

## Interpretation

R040B completed 30/30 immutable H0 records at 2026-07-22 04:43 America/Chicago.
Strict security-valid solve is 7/30 (23.3%): 7 pass, 11 stalled, 10
timeout/infrastructure failures, and 2 unsafe. Usage is available for 21/30.
All 30 manifests, Copilot logs, usage/validation files, and result files are
present; one timed-out run correctly records no candidate and therefore has no
Verus/Lynette logs. No H1/H2 outcome has been viewed.

The intended `near_miss` tier is unreachable on this frozen calibration set:
all 30 sources have exactly one Verus error, while the classifier requires a
strictly smaller candidate error count without passing. A zero-error,
proof-safe candidate would normally be a pass. The observed zero near-miss
count therefore does not justify expanding the screen under the same rule.

## Rationale Pilot Decision

- verdict: `branch`, retaining the three-trajectory rationale comparison as a
  qualitative mechanism pilot
- action: freeze one stable pass, one H0-only `closest_failure`, and one stable
  stalled task before any H1/H2 result is viewed
- reason: the original pass/near-miss/stalled scientific contrast is useful,
  but the numeric near-miss definition cannot instantiate its middle case on
  one-error sources
- constraint: `closest_failure` must be predeclared from H0-only evidence,
  require a proof-safe compilable candidate with a localized residual proof
  failure, and must not be reported as the original `near_miss` tier
- evidence: frozen R040A task manifest and completed R040B live attempt2
- claim boundary: three cases are qualitative mechanism evidence only, not a
  solved-rate or token-efficiency result

## R040C And R041 Execution

The H0-only selector found 7 pass, 5 `closest_failure`, and 6 stalled records
among the completed screen, excluding 10 infrastructure failures and 2 unsafe
records. It froze three candidates per qualitative class with Anvil/IronKV
coverage and generated 18 rep2/rep3 H0 jobs. Those jobs are running
sequentially in screen `r040c_reps_20260722`; no H1/H2 outcome has been read.

Canonical R040C artifacts:

- `${VERUS_SKILL_RUN_ROOT}/r040c_qualitative_candidates_20260722_attempt2/`
- repetitions are stored beside the original rep1 records under
  `${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_live_attempt2/runs/`

R041 independently packed compact patch/log evidence from the frozen 30 R040
train traces and made one direct local-Qwen global distillation call. The raw
H2 output required three safety corrections: remove permissive
`external_body`/`assume` advice and name the actual Verus+Lynette validation.
The trace-free H1 was trimmed only to satisfy the length gate. The reviewed
prompts are frozen at H1=633 and H2=632 tokenizer tokens (0.16% delta), contain
no frozen task identifiers, pass the bypass-advice lint, and are explicitly
not task-specific. Distillation usage was 28,206 input and 634 output tokens;
AI-agent review/edit time was 5 minutes and human edit time was 0.

Canonical R041 artifacts:

- `${VERUS_SKILL_RUN_ROOT}/r041_prompt_distillation_20260722_attempt1/`
- `${VERUS_SKILL_RUN_ROOT}/r041_frozen_prompts_20260722_attempt3/`
- compact reviewed copy: `refine-logs/r041_prompts/`

The first independent R041 review returned NO-GO for missing group-specific
containment, declarative rather than enforced prompt provenance, mislabeled
human edit cost, and insufficient negative tests. The implementation now
enforces the full selection-to-freeze hash chain, records AI-agent/human edit
time separately, and covers sealed/provenance/freeze/bypass gates. Follow-up
verdict: GO, with 76 repository tests passing. Review artifact:
`refine-logs/EXPERIMENT_CODE_REVIEW_20260722_132102.md`.

## Next Action

Monitor the 18 active R040C repetitions, freeze the first stable task per class
as R040D, then prepare the immutable 27-record H0/H1/H2 R041A manifest. Preserve
R040B and the failed near-miss design as audit history; do not change their
recorded classifications.
