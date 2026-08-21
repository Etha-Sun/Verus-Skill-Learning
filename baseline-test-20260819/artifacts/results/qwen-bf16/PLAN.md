# Qwen3.8-27B BF16 paired baseline evaluation

## Frozen comparison

- Model: official `Qwen/Qwen3.8-27B` BF16 checkpoint.
- Revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Test split: `fixed-claude-stratified-80-seed20260814/test/items.json` (20 tasks).
- Arms: `no-skill`, then `with-native-official-baseline`.
- Skill tree: `cross-task-global-20260814/native_official_baseline_v1/skill/verus-proof-repair`.
- Skill tree SHA-256: `fc2c51a283212ffe365fcd9bc91fedca1c6a46d43a51c4310facd7f76f41b74b`.
- Codex CLI harness, proof-outcome-v3 scoring, 600 s task timeout, 120 s verification timeout.
- Same split, prompts, verifier, Lynette, isolation, serial execution, and aggregation as the prior Qwen FP8 paired run.

## Isolation contract

- Existing `qwen_local` profile, FP8 checkpoint, FP8 outputs, and paid-provider profiles are preserved.
- New profile: `qwen_bf16_local`; vLLM endpoint `127.0.0.1:8001`; bridge ports 4337/4338.
- Served model: `qwen38-27b-bf16`; tensor parallel size 4; BF16 weights; automatic BF16 KV-cache dtype; 262144 context.
- Existing FP8 service on port 8000 is stopped only to free the same four GPUs; its files and prior results remain restartable.
- Obsolete `models/Qwen3.6-27B` was deleted with explicit user authorization before acquisition; deletion is not locally recoverable.

## Gates

- [x] Download pinned official checkpoint.
- [x] Validate exact file set, sizes, LFS SHA-256 hashes, BF16 config, and absence of quantization metadata.
- [x] Add an independent BF16 service manager, actor provider profile, output root, environment namespace, ports, and driver.
- [x] Preserve the FP8/DeepSeek/GPT/GLM profiles; focused actor tests pass.
- [x] Run runtime preflight and start a stably healthy detached BF16 vLLM service.
- [x] Pass direct text/tool/continuation smoke.
- [x] Pass Codex -> Responses-to-Chat bridge -> vLLM tool smoke.
- [x] Freeze the 40-invocation paired-run preflight.
- [x] Start detached no-skill then with-skill execution and confirm stable progress.
- [ ] Aggregate results after completion.
