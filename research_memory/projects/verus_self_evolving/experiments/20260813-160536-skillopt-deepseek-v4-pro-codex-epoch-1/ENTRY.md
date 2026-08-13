# SkillOpt DeepSeek V4 Pro Codex epoch 1

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-13T16:05:36`
- dataset/split: frozen Anvil/IronKV 40 train / 20 selection / 40 held-out,
  SHA `53059264e5d0458e1fc50a3c1786cbeac6c671aedf56dd71fb32843b24d2c553`
- baseline: initial 838-byte skill on the fixed 20-task selection set
- variant: one native SkillOpt epoch; DeepSeek V4 Pro actor through Codex CLI
  native Responses at max reasoning; local `gpt-5.6-sol` optimizer
- metrics: independently judged Verus + Lynette hard solved rate, paired
  selection transitions, fidelity, tokens, and USD cost
- leakage controls: only train trajectories reached the optimizer; selection
  was gate-only; held-out test was not run; raw and sealed data were read-only
- stop condition: complete exactly one epoch and accept only a strict hard-rate
  improvement on the same fixed selection set

## Commands

```bash
python -m skillopt_verusage.codex_deepseek_bridge --native-responses \
  --model deepseek-v4-pro --port 18080 \
  --ledger-path "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/codex-pro-0813-max-sol-e1-20260813/bridge_calls.jsonl"
python -m skillopt_verusage.train \
  --config skillopt-verusage/configs/verusage_codex_pro_sol_e1.yaml
```

## Outputs

- run directory: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-pro-0813-max-sol-e1-20260813`
- logs: `bridge_calls.jsonl`, `optimizer_calls.jsonl`, and per-task prediction directories
- metrics: `summary.json`, `history.json`, and `cost_ledger.json`
- manifest: `config.json`, `bridge_manifest.json`, and per-task `run_manifest.json`
- reviewed summary: `skillopt-verusage/refine-logs/CODEX_PRO_0813_EPOCH1_RESULT_20260813.md`
- compiled reproduction document:
  `skillopt-verusage/refine-logs/SKILLOPT_REPRODUCTION_SUMMARY_20260813.tex`
  and `skillopt-verusage/refine-logs/SKILLOPT_REPRODUCTION_SUMMARY_20260813.pdf`

## Results

| metric | baseline | variant | delta |
|---|---:|---:|---:|
| fixed-selection hard solved | 16/20 | 17/20 | +1 task / +5 pp |
| paired fail-to-pass | - | 1 | +1 |
| paired pass-to-fail | - | 0 | 0 |
| skill bytes | 838 | 2,932 | +2,094 |

Train rollout solved 35/40. The formal actor ledger contains 3,559 native
Responses calls, 197,106,858 input tokens (194,614,016 cache hit and 2,492,842
cache miss), 2,986,236 output tokens, and USD 4.387887398 of DeepSeek cost.
The local optimizer used 9 calls and 992,796 tokens with zero metered cash
cost. All 80 final results completed with 77 V2, 3 V1, zero V0, zero provider
errors, and unchanged inputs. No held-out result was produced.

## Interpretation

The candidate passed the in-loop selection gate with a paired +1/-0 change, so
the epoch supports accepting this candidate for the next iteration. The result
is still inconclusive for general solved-rate or token-efficiency improvement
because selection has only 20 tasks and the held-out test remains sealed from
this epoch.

## Next Action

Audit the single gained task and the four selected edits. If continuing the
loop, start epoch 2 from the accepted best skill with the same frozen train and
selection contract; do not claim general improvement until a predeclared
leakage-safe held-out evaluation is run.
