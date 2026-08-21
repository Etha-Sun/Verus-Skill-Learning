# Fixed Test-20 Blank versus S2 Results

Date: 2026-08-20

## Superseding Addendum

The worker-20 GLM rows below are retained only as provenance. The stable
worker-2 blank/S2 reruns both scored 12/20, with complete-ledger costs of
$6.976968 and $5.565405. A later official-Verus audit and fresh rerun of the
two version-sensitive IronKV tasks raises the targeted corrected estimate to
GPT 19/18, DeepSeek 14/14, and GLM 13/13 for blank/S2. These are targeted
18-old-plus-2-fresh estimates, not complete official-Verus test-20 reruns.

The current setting comparison, screenshot audit, and exact rerun ledger are
in `IMAGE_RESULT_SETTING_AUDIT_20260820.md`.

## Contract

All completed arms used the frozen 20-task test set, autonomous noninteractive
Codex CLI, 262,144-token context, maximum reasoning, a 600-second task limit,
the same task prompt and verifier wrappers, and either the canonical blank
skill or the hash-locked accepted S2 skill. Remote arms used 20 task workers.
Valid timeouts were scored once; only provider-invalid results were retried, at
most twice. The test outcomes were not used to edit either skill.

## Performance

| Actor | Blank | S2 | Delta | Paired gains | Paired regressions | Stable solved | Stable failed |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 18/20 | 17/20 | -1 | 0 | 1 | 17 | 2 |
| DeepSeek V4 Pro | 13/20 | 13/20 | 0 | 2 | 2 | 11 | 5 |
| GLM-5.3 | 5/20 | 7/20 | +2 | 4 | 2 | 3 | 11 |
| Qwen3.8-27B | pending | pending | -- | -- | -- | -- | -- |

Every completed arm has 20/20 provider-valid final results. The two known
stale-alias IronKV items were unsolved in all six completed arms and remain in
the common `/20` denominator.

S2 did not improve all actors. It lost one historical Claude-failed AC task
for GPT. DeepSeek exchanged two gains for two regressions. GLM gained four
historically normal tasks and regressed on two tasks, including one historical
Claude-failed AL task. Historical Claude-failed solves changed from 3/5 to 2/5
for GPT, 1/5 to 0/5 for DeepSeek, and 1/5 to 0/5 for GLM. The GLM `+2` is
therefore not evidence that S2 improved the difficult historical-failure
stratum.

## Usage and Cost

| Actor | Skill | Successful requests | Prompt/input + completion tokens | Timeouts | V2 traces | Metered API cost |
|---|---|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | blank | -- | 8,905,988 | 1 | 19 | local quota |
| GPT-5.6 Sol | S2 | -- | 10,167,943 | 1 | 19 | local quota |
| DeepSeek V4 Pro | blank | 537 | 21,066,524 | 7 | 13 | $1.598398 |
| DeepSeek V4 Pro | S2 | 465 | 19,000,658 | 8 | 12 | $1.393428 |
| GLM-5.3 | blank | 187 | 3,308,641 | 16 | 4 | $1.535974 |
| GLM-5.3 | S2 | 195 | 3,575,569 | 12 | 8 | $1.705639 |

GPT cost is zero metered API cost because it used local quota. DeepSeek and
GLM costs use their complete bridge ledgers. The GLM ledgers include archived
provider-invalid attempts; retained-task summaries alone report $1.454094 and
$1.612933 and therefore undercount actual formal spend by $0.174586.

Completed formal API spend is $6.233439: $2.991826 for DeepSeek and $3.241613
for GLM. GLM availability/edit smokes plus the two rejected pre-backoff
concurrency attempts add $1.216348, making measured paid spend for this
four-model evaluation campaign $7.449787 so far. GPT used local quota and Qwen
has incurred no API cost.

## GLM Concurrency Finding

Raw GLM concurrency at 20 workers previously produced 19 provider-invalid
results. The bridge now retries only HTTP 429 inside the original request
deadline, honors `Retry-After`, applies exponential backoff with jitter, and
records retry counts and sleep time. Under the corrected bridge, both formal
arms ended with 20/20 provider-valid results. Across blank and S2, 739 internal
429 retries accumulated 9,534 seconds of aggregate per-thread backoff. This is
not wall time, but it shows that 20 workers exceeds the account's effective
GLM throughput. The resulting 16 and 12 task timeouts confound model quality
with rate-limit waiting. Retain these paired results, but calibrate a lower GLM
worker count before scale-up. GPT and DeepSeek did not show this failure mode
at 20 workers.

A subsequent four-task frozen-training calibration at two workers produced
4/4 one-attempt V2 traces and 51/51 accepted upstream calls with zero 429
retry, zero backoff, and USD 0.354103 cost. Three tasks solved. The launcher
now defaults GLM to two workers. Sequential worker-2 blank/S2 test-20 reruns
are in progress; until both complete, the worker-20 scores above remain
reported for provenance but are not stable GLM capability estimates.

## Remaining Arm

Qwen3.8-27B blank and S2 remain pending. All four target GPUs are occupied by
another user's vLLM workers; those processes were not modified. The Qwen
conditions should start at four workers only after the GPUs are released.

## Durable Run Pointers

- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-blank-w20-20260820-152626/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-gpt-s2-w20-20260820-152626/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-deepseek-blank-w20-20260820-152626-retry1/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-deepseek-s2-w20-20260820-152626-retry1/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-blank-w20-backoff-20260820/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-test20-glm-s2-w20-backoff-20260820/`

Raw and sealed datasets were read only. Complete run directories remain below
`VERUS_SKILL_RUN_ROOT`; only this compact audited report is stored in the
repository.
