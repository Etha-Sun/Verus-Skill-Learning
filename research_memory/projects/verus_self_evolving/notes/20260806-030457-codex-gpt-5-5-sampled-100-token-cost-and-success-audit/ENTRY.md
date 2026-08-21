# Codex GPT-5.5 sampled 100 token cost and success audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-06T03:04:57`
- status: `complete`

## Objective

Audit token usage, API-equivalent cost, and verifier-safe success for the
completed 100-task Codex GPT-5.5/high rerun.

## Context

- Read-only legacy run:
  `${VERUS_SKILL_LEGACY_ROOT}/runs/codex_sampled_unverified_100_gpt55_20260729/`
- Canonical aggregate:
  `${VERUS_SKILL_LEGACY_ROOT}/runs/codex_sampled_unverified_100_gpt55_20260729/aggregate_100.json`
- Original legacy experiment note:
  `${VERUS_SKILL_LEGACY_ROOT}/research_memory/projects/verus_self_evolving/experiments/20260729-002743-codex-detailed-rerun-on-sampled-unverified-100/ENTRY.md`
- Model contract: GPT-5.5, reasoning effort high, one fresh H0 trajectory per
  task, 600-second cap, no historical proof or trace exposure.

## Method / Actions

- Cross-checked the 100-task aggregate against all per-run `result.json`
  records.
- Defined strict success as the recorded `SOLVED` status, which coincides with
  both independent Verus and Lynette passing.
- Separated raw input, cached input, uncached input, output, and
  reasoning-output tokens. Reasoning-output tokens are a subset of output and
  were not charged twice.
- Applied the current standard GPT-5.5 API-equivalent rates of USD 5.00 per
  million uncached input tokens, USD 0.50 per million cached input tokens, and
  USD 30.00 per million output tokens.
- Estimated the 13 missing timeout usages in two ways: mean extrapolation from
  all 87 observed runs and duration-matched extrapolation from the 13 longest
  observed terminal runs.

## Evidence

| Metric | Value |
|---|---:|
| Tasks | 100 |
| Strict solved | 77 |
| Unsolved | 23 |
| Timeouts | 13 |
| Terminal usage available | 87 |
| Raw input, observed 87 | 66,264,870 |
| Cached input, observed 87 | 61,448,832 |
| Uncached input, observed 87 | 4,816,038 |
| Output, observed 87 | 665,288 |
| Reasoning output, observed 87 | 259,838 |
| Primary uncached input + output, observed 87 | 5,481,326 |

Observed-87 API-equivalent cost components:

- uncached input: USD 24.080190;
- cached input: USD 30.724416;
- output: USD 19.958640;
- total: USD 74.763246.

Projected complete-100 ranges before any long-context uplift:

| Projection | Raw input | Cached input | Uncached input | Output | Cost |
|---|---:|---:|---:|---:|---:|
| observed-run mean | 76,166,517 | 70,630,841 | 5,535,676 | 764,699 | USD 85.93 |
| duration-matched | 89,368,213 | 83,450,368 | 5,917,845 | 891,712 | USD 98.07 |

Official pricing source:
`https://developers.openai.com/api/docs/models/gpt-5.5`.

Outcome-conditioned observed means:

| Outcome | Usage n / total n | Raw input | Uncached input | Output | Primary tokens | API-equivalent cost |
|---|---:|---:|---:|---:|---:|---:|
| Strict success | 76 / 77 | 685,487 | 53,943 | 6,897 | 60,840 | USD 0.792 |
| Failure | 11 / 23 | 1,287,990 | 65,125 | 12,830 | 77,955 | USD 1.322 |

The observed failure group has 28.1% more primary uncached tokens and 66.8%
higher API-equivalent cost than the observed success group. Its missingness
is severe and non-random: 12/23 failures lack terminal usage, versus only 1/77
successes.

Using the mean token profile of the 13 longest terminal runs to impute the 13
timeouts gives:

| Outcome | Projected raw input | Projected uncached input | Projected output | Projected primary tokens | Projected cost |
|---|---:|---:|---:|---:|---:|
| Strict success | 699,664 | 54,343 | 7,033 | 61,377 | USD 0.805 |
| Failure | 1,543,220 | 75,366 | 15,223 | 90,590 | USD 1.567 |

Timeout-scope verification:

- `experiment_contract.json` freezes `timeout_seconds: 600`;
- the batch wrapper passes `timeout_seconds=600` to `run_codex_smoke`;
- `codex_runner.py` starts a 600-second timer around the Codex subprocess,
  sends the process group `SIGINT` at expiry, waits up to 15 seconds, and then
  may send `SIGKILL`;
- after the Codex phase, independent Verus and Lynette checks run with their
  own caps of up to 120 seconds each.

Therefore the ten-minute limit applies to the Codex solver phase, not to the
entire recorded `wall_seconds`. A total wall time above 600 seconds is expected
when shutdown and independent validation consume additional time.

## Result

The strict success rate is 77/100 = 77%. Historical Sonnet 4.5 status on the
same task set was 72 VERIFIED, so the descriptive difference is +5 percentage
points, but this is not a controlled paired model claim because execution
conditions differ.

Exact terminal token usage covers 87/100 runs. The observed usage is therefore
a lower bound for the full batch. A reasonable complete-batch estimate is
76.2-89.4 million raw input tokens, of which 70.6-83.5 million were cached,
plus 0.765-0.892 million output tokens. At standard API-equivalent rates this
is approximately USD 86-98, or USD 0.86-0.98 per task and USD 1.12-1.27 per
strict solve.

The run used Codex CLI rather than an API billing ledger, so these dollar
figures are counterfactual API-equivalent costs, not an observed invoice.
Per-request long-context eligibility cannot be reconstructed from terminal
cumulative usage, so the estimate does not apply the GPT-5.5 long-context
uplift.

Outcome-conditioned cost also cannot be exact for all 100 tasks because the
terminal-only CLI stream loses usage precisely at timeout. For reporting, use
USD 0.79 observed / USD 0.81 duration-matched per success and USD 1.32
observed / USD 1.57 duration-matched per failure. Do not label the projected
failure mean as observed.

## Decision / Next Step

For future cost-complete runs, use the app-server token notifications so
timeouts retain cumulative usage and per-request context lengths. Report
subscription quota consumption separately from API-equivalent dollar cost.
