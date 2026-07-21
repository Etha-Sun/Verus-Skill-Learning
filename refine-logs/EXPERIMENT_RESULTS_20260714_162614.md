# Qwen3.6 三目标 Information Gain Pilot

**时间**：2026-07-14  
**模型**：本地 `<model-root>/Qwen3.6-27B`  
**评分 backend**：HuggingFace Transformers (`hf`) exact teacher forcing  
**评估类型**：`self_supervised_proxy`（verifier-grounded demonstrator likelihood，不是真实 downstream ground truth）  
**范围**：3 条 trace、6 个 locally accepted trajectory states、3 类 target、7 类 artifact，共 126 cases

## 实验设置

目标为实际 trace 中已观察到的后续输出：

1. `action_primary`：结构化 action label；
2. `patch_span`：最终 verified proof 相对输入程序的修改片段；
3. `full_proof`：完整最终 verified proof。

每个 target 比较 baseline context 与 artifact-conditioned context：

```text
raw IG = log2 P(target | state, artifact) - log2 P(target | state)
```

主 reference 是 `evidence_artifact`。Specific IG 从 raw evidence IG 中减去五类 tokenizer-length-matched controls 的 raw IG 均值：`cross_trace_same_error`、`cross_trace_any`、`block_shuffled`、`counterfactual_error`、`irrelevant_archive`。`empty_container` 仅作 wrapper 诊断，不进入 matched-control 均值。

评分采用 exact chunked teacher forcing；最大序列长度 78,392，小于 131,072 context 上限，没有 sliding window 或截断。完整 proof 运行带 target-token 进度条、逐 case checkpoint 和 resume。

本轮主实验使用 `--observed-target-only`，因此 action 测量是实际 observed action string 的 raw/specific IG；没有运行 22-way candidate-normalized action distribution，`action_distributions.jsonl` 为空。

## 完整性

- 126/126 aggregate cases 完成；每个 target 42 cases。
- 1,499,498 条 token score，恰好对应 749,749 个目标 token 的 baseline/artifact 两种条件。
- 所有概率和 logprob 有限，概率均在 `(0, 1]`。
- `sequence_truncated=0`，locally rejected action=0。
- reference 与五类正式 controls 均 exact token matched；18 个非 exact 标记全部属于刻意短小的 `empty_container`。
- 评分耗时约 51 分 33 秒。

## 主结果

下表的 specific IG 是 evidence raw IG 减去五类 matched controls 的平均 raw IG。跨长短 target 比较时应优先看 bits/target-token；total bits 会随目标长度累积。

| Target | Mean specific IG (total bits) | Median | Mean bits/target-token | Positive states |
|---|---:|---:|---:|---:|
| action | 0.9612 | 1.4028 | 0.309137 | 4/6 |
| patch span | 12.7686 | 5.7258 | 0.017837 | 4/6 |
| full proof | 22.3031 | 16.6490 | 0.001580 | 6/6 |

### 对单个 control 的结果

| Target | Control | Mean evidence-control (bits) | Evidence wins |
|---|---|---:|---:|
| action | irrelevant archive | -0.5398 | 2/6 |
| action | block shuffled | -0.6236 | 3/6 |
| action | counterfactual error | 4.8631 | 5/6 |
| patch | irrelevant archive | 15.8062 | 5/6 |
| patch | block shuffled | -3.0562 | 4/6 |
| full proof | irrelevant archive | 50.6492 | 6/6 |
| full proof | block shuffled | 16.0122 | 6/6 |

Action 和 patch 的 state-wise specific IG 排序完全一致（Spearman `rho=1.0`，符号一致 6/6），但它们与 full-proof specific IG 的 Spearman 相关都只有 `0.3143`。样本仅 6 个状态，不能把该相关性当作稳定规律。

## 解释与结论

1. **不是“irrelevant 总是有效”**：它的 raw action IG 均值为正（1.0510 bits），且 evidence 仅在 2/6 action states 上胜过它。这说明 action raw IG 仍受上下文扰动等混杂影响。
2. **五类 control 平均会掩盖 action 弱点**：action 的 mean specific IG 为正，主要由 evidence 显著胜过 `counterfactual_error` 和 `cross_trace_any` 拉动；它没有稳定胜过 shuffled 或 irrelevant。因此当前 artifact 不能通过强 action-promotion gate。
3. **patch/full-proof 提供不同信号**：patch 对 irrelevant 为 5/6，full proof 对 irrelevant 和 shuffled 均为 6/6。完整 proof 的 per-token 效应很小，但在长序列上累计成正 total specific IG。
4. **当前结论只是 offline likelihood pilot**：它没有测量 verifier solved rate、agent token 消耗或 live trajectory 改善，也没有 held-out project split。不能声称 self-evolving agent 已提升。

当前最稳妥的研究结论是：三种 IG operationalization 可计算且并不等价；action IG 对无关上下文仍不稳；patch 在本 pilot 上较好地区分 evidence 与 irrelevant，但未在均值上胜过 shuffled；只有 full-proof specific IG 同时稳定胜过 irrelevant 和 shuffled。上述现象值得扩大到 held-out traces 验证。

## 产物

- 正式运行：`verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/`
- 聚合分析：`analysis/analysis_summary.json`
- target 汇总：`analysis/target_summary.csv`
- control 汇总：`analysis/control_summary.csv`
- state 明细：`analysis/specific_state_gain.csv`
- 状态映射：`analysis/state_mapping.csv`
- 可视化：`analysis/specific_ig_three_targets.png` 和 `.pdf`
- 逐 token 概率：`token_scores.jsonl`

## 哈希

- cases: `3beedd831e65f6b48bfe953d75aea432c0674d1772ea27dca31921462908ef79`
- aggregates: `160ac09ecbbead2c294a9d8911e02cb0735914cbd9d6d7f1c5f878e8e31c945b`
- token scores: `07466f3241adc9e725a060d10934e80361e2e866cb4ae5a3567d23c55ca331ef`
