# Native Official Baseline Evaluation (2026-08-19)

This experiment compares two conditions on a fixed 40-task held-out set:

1. `no-skill`
2. `with-native-official-baseline`

The held-out set is the unchanged concatenation of the frozen 20-task `val`
manifest and the frozen 20-task `test` manifest from
`fixed-claude-stratified-80-seed20260814`. The 40 training tasks used to build
the native official baseline are excluded.

The first model is DeepSeek V4 Pro. Both conditions use the same audited Codex
CLI harness, native Responses bridge, filesystem isolation, proof-outcome-v3
scoring, high reasoning effort, and a 600-second timeout per task. A blocked
attempt to inspect prohibited files is returned to the actor as an ineffective
operation and recorded as an audit observation; it does not itself make the
proof fail. Ordinary failures are timeout or a completed actor turn whose final
Verus/Lynette checks fail. Unsafe proof changes remain disqualifying.

Large outputs are written below:

`$VERUS_SKILL_RUN_ROOT/baseline-test-20260819/deepseek-v4-pro/`

The repository folder contains only the compact experiment contract and driver.

## Commands

Zero-network preflight:

```bash
python3 code/run_deepseek_v4_pro.py --preflight
```

Paid execution (automatically resumes incomplete sub-runs):

```bash
python3 code/run_deepseek_v4_pro.py --execute
```

## GPT-5.6 Sol max test-only replication

The GPT replication keeps the frozen baseline skill and actor/scoring contract
unchanged, and evaluates only the frozen 20-task test manifest. The shared
actor runner now exposes explicit provider profiles: the legacy default remains
deepseek, while this driver passes --provider openai. Provider credentials,
bridge logs, and run outputs remain separate.

    python3 code/run_gpt_5_6_sol_max.py --preflight
    python3 code/run_gpt_5_6_sol_max.py --execute

GPT outputs are written below:

$VERUS_SKILL_RUN_ROOT/baseline-test-20260819/gpt-5.6-sol-max/



## Other provider replications

The Qwen FP8, Qwen BF16, and GLM drivers use the same frozen 20-task test
manifest, baseline skill, Codex harness contract, scoring policy, and
600-second timeout. Provider-specific transport is selected additively through
an explicit runner profile, leaving the DeepSeek and OpenAI profiles intact.

```bash
python3 code/run_qwen3_8_27b_fp8.py --preflight
python3 code/run_qwen3_8_27b_fp8.py --execute
python3 code/run_qwen3_8_27b_bf16.py --preflight
python3 code/run_qwen3_8_27b_bf16.py --execute
python3 code/run_glm_5_3.py --preflight
python3 code/run_glm_5_3.py --execute
```

## Published artifacts

- `result.md` is the human-readable cross-provider result table.
- `CROSS_PROVIDER_EVALUATION_SETUP_AND_API_BRIDGES.md` documents the shared
  prompt, Codex invocation, provider profiles, and bridge protocols.
- `artifacts/Trace2Skill_native_official_baseline_pure/` contains the frozen
  official-style Trace2Skill baseline skill plus its prompts and compact
  provenance manifests.
- `artifacts/results/` contains final summaries, arm-level summaries,
  experiment manifests, and preflight records for DeepSeek V4 Pro,
  Qwen3.8-27B FP8/BF16, GPT-5.6 Sol, and GLM-5.3.

Raw API/bridge calls, Codex event logs, task workspaces, model weights,
runtime caches, service logs, PID files, and environment files are deliberately
excluded from Git. Their absolute run roots and integrity hashes remain in the
published manifests where applicable.
