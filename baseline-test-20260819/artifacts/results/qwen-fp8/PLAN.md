# Qwen3.8-27B Baseline Evaluation Plan

## Objective

Run the same frozen 20-task test split under two conditions:

1. no-skill
2. with-native-official-baseline

The response model will be a locally served Qwen3.8-27B checkpoint and the
agent harness will remain Codex CLI. The DeepSeek and GPT provider profiles,
commands, credentials, logs, and outputs must remain backward compatible.

## Frozen experiment inputs

- Test split: `/zp_vegeta/scratch_sb/xinyueh/Verus-Skill-Learning/fixed-claude-stratified-80-seed20260814/test/items.json`
- Test tasks per condition: 20
- Task timeout: 600 seconds
- Verification timeout: 120 seconds
- Skill: `/zp_vegeta/scratch_sb/xinyueh/verus_skill_runs/cross-task-global-20260814/native_official_baseline_v1/skill/verus-proof-repair`
- Skill tree SHA-256: `fc2c51a283212ffe365fcd9bc91fedca1c6a46d43a51c4310facd7f76f41b74b`
- Scoring and isolation: the existing `proof-outcome-v3` actor contract

## Model audit and selection

- [x] Confirm the old local model is official `Qwen/Qwen3.6-27B`.
  - Local directory: `/zp_vegeta/scratch_sb/xinyueh/models/Qwen3.6-27B`
  - Official revision: `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`
  - Local and pinned official `config.json` SHA-256:
    `69db4eb7196bc8190813231b3018ca05d8c2e3abc7b1af19d55c157af44a9d9c`
  - Existing footprint: approximately 47 GiB.
- [x] Pin the new official model source.
  - Logical model: `Qwen/Qwen3.8-27B`
  - BF16 revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`
  - BF16 weight bytes: 55,563,006,776; this cannot be safely staged on the
    current scratch filesystem, which has approximately 59 GB free.
- [x] Select the official FP8 checkpoint for the four L40S GPUs.
  - Repository: `Qwen/Qwen3.8-27B-FP8`
  - Revision: `017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`
  - Weight bytes: 30,866,866,928 across 66 safetensors files.
  - Rationale: official Qwen/vLLM TP=4 deployment path, enough disk space to
    preserve Qwen3.6 as a rollback point, and ample L40S FP8 support.
- [x] Download the pinned FP8 snapshot to a new immutable directory.
- [x] Validate file sizes, LFS object hashes, config, tokenizer, and revision.
- [x] Keep Qwen3.6 intact; switch the active model only through the Qwen
  provider/service configuration.

## Runtime isolation

- [x] Audit the old runtime.
  - vLLM 0.19.1, Transformers 4.57.6, PyTorch 2.10.0+cu128.
  - Four NVIDIA L40S GPUs, 46,068 MiB each.
- [x] Identify the compatibility gap.
  - The official Qwen3.8 recipe requires Transformers >= 5.8.0.
  - The old environment must not be upgraded in place.
- [x] Create a Qwen3.8-specific runtime overlay without modifying the old
  vLLM environment.
- [x] Freeze package versions and hashes in a runtime manifest.
- [x] Start a detached vLLM service with a distinct served model name and
  service log.
- [x] Validate `/v1/models`, one text completion, usage reporting, reasoning
  extraction, tool calls, and multi-turn tool-result continuity.

Provisional serving contract:

```text
checkpoint: Qwen/Qwen3.8-27B-FP8 at pinned local revision
served model name: qwen38-27b-fp8
tensor parallel size: 4
native context: 262144
KV cache dtype: fp8
reasoning parser: qwen3
tool-call parser: qwen3_coder
thinking/reasoning effort: xhigh (official template default; omitted from the vLLM request schema, which does not accept the literal `xhigh`)
```

Do not enable the optional MTP speculative decoder until the non-speculative
service passes all protocol and proof-harness smoke tests. This keeps the first
comparison simple and avoids introducing an unmeasured decoding variable.

## Codex and bridge architecture

Decision: Qwen needs a bridge for this experiment.

```text
Codex CLI Responses client
  -> task-scoped loopback Responses endpoint
  -> Responses-to-Chat translation bridge
  -> local vLLM OpenAI-compatible /v1/chat/completions
  -> Qwen3.8-27B-FP8
```

Why:

- Codex emits the Responses wire protocol and Responses-style tool history.
- The officially documented Qwen3.8/vLLM path is Chat Completions with the
  Qwen reasoning and tool-call parsers.
- The existing bridge already contains the required Responses-to-Chat and
  Chat-to-Responses conversion, but the current paid provider profiles run it
  in native Responses passthrough mode.
- Qwen will reuse only the translated mode. DeepSeek and GPT will retain their
  current native passthrough mode.

Required isolated profile fields:

```text
profile: qwen_local
wire into Codex: responses
upstream wire: chat_completions
upstream base URL: local vLLM only
API key: local placeholder only, never a paid-provider credential
USD budget guard: disabled; usage tokens remain recorded
model: qwen38-27b-fp8
reasoning effort: xhigh
bridge log: qwen_responses_bridge.log
```

Backward-compatibility gates:

- [x] The default profile remains `deepseek`.
- [x] The old DeepSeek command list is unchanged when no profile is supplied.
- [x] The GPT profile still selects native Responses, `gpt-5.6-sol`, max
  reasoning, and `OPENAI_API_KEY`.
- [x] Qwen has separate ports, model name, environment variables, service
  process, bridge log, and output root.
- [x] No Qwen code path imports or rewrites paid-provider credentials.
- [x] Existing baseline and cross-task unit suites pass unchanged.
- [x] Add focused Qwen translation and profile tests; live reasoning/tool-call
  behavior remains gated on the service smoke below.

## Implementation checklist

- [x] Generalize the existing bridge's translated mode with provider-neutral
  error labels and a profile-selected Chat Completions reasoning effort.
- [x] Audit the translated-mode ledger append; it is already single and remains
  protected by the bridge tests.
- [x] Add a `qwen_local` provider profile to the shared actor runner.
- [x] Make paid-provider budget state mandatory only for paid profiles.
- [x] Preserve zero-dollar token and latency accounting for local Qwen.
- [x] Add a Qwen-specific service supervisor and test-only experiment driver
  below the repository's compact `baseline-test-20260819` code directory.
- [x] Snapshot model/runtime/service/bridge/actor hashes during preflight.

## Validation gates before the 40-run experiment

- [x] Model snapshot audit passes.
- [x] Runtime import and GPU kernel smoke passes.
- [x] vLLM service remains healthy after model load.
- [x] Direct Chat Completions text + usage smoke passes.
- [x] Direct Chat Completions tool-call smoke passes.
- [x] Codex -> bridge -> vLLM synthetic workspace smoke passes.
- [x] Actor filesystem and credential isolation audits pass.
- [x] Frozen test-20 and skill hashes match the DeepSeek experiment.
- [x] Zero-network-to-paid-provider preflight reports exactly 40 actor runs.
- [x] DeepSeek-default and GPT-profile regression assertions pass.

## Execution order

- [x] Run no-skill/test (20 tasks), serially, 600 seconds each.
- [x] Run with-native-official-baseline/test (20 tasks), serially, 600 seconds
  each.
- [x] Aggregate solved count, unsolved task numbers, successful-task mean time,
  all-task mean time, token usage, and GPU service time into `result.md`.

Both vLLM and the experiment driver must run in detached server-side sessions
and survive SSH disconnects. Do not launch the 40-run experiment until every
gate above is checked and the live logs show a stable end-to-end smoke.

## Rollback and safety

- Never modify or delete the Qwen3.6 directory during acquisition or smoke.
- Never overwrite the Qwen3.8 target directory after its snapshot manifest is
  frozen; use a new attempt directory for a different revision.
- Do not modify existing DeepSeek/GPT run outputs.
- Stop only Qwen-owned service/bridge processes, identified by frozen ports,
  PIDs, and manifest instance IDs.
- If disk space falls below the recorded safety margin, stop before download
  or execution and report the exact requirement.
## Completed execution (2026-08-20)

- Status: complete; both 20-task test arms finished with full coverage.
- Result: no-skill 5/20; with-native-official-baseline 4/20.
- Frozen preflight SHA-256: `5f0d5b4b4aa3ceba1dab82c639c2a3b6f7e240b4543274fd941c2e968ea74243`.
- Aggregated results are recorded in `../result.md`; detailed summaries remain under this directory.
- Live driver log: `experiment_driver.log`.
- Service log: `vllm_service.log`.
