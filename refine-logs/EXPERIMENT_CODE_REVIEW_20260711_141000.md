# Corrected IG Experiment Code Review

**日期**：2026-07-11  
**审查方式**：local-only（当前工具环境无独立 reviewer agent 接口）

## Verdict

R016 one-state smoke 可以运行。R017 扩大前必须先检查 R016 的 option token、candidate-normalized probabilities、baseline identity 和 context length。

## Blocking Checks

- PASS：action target 来自 trace manifest，而非 scorer 输出。
- PASS：artifact generation 不读取 final proof 或 future trajectory。
- PASS：chat generation boundary 将 context 和 option target 分开编码。
- PASS：action options 包含 manifest 中所有 demonstrator actions，排序确定。
- PASS：每个 candidate 的 raw token logprob 与归一化分布均保存。
- PASS：information density 除以 artifact tokens，不再除以 action target tokens。
- PASS：baseline context 在 artifact variants 间通过 cache 复用。
- PASS：derived outputs 仅写入 scaffold `runs/`。

## Non-Blocking Risks

- 当前 action probability 是在 manifest-observed candidate set 内重新归一化，不是全语言输出概率；所有报告必须写 `candidate-normalized`。
- A-D 固定映射可能有 option-position bias；正式 scale 需要 permutation/order ablation。
- QwQ 是 reasoning model，直接 option token 的绝对概率可能很低；candidate normalization 可用于 ranking，但必须检查分布是否退化。
- `trace_rationale` 是 state-conditioned restatement，不是已学习或 self-evolved skill；不得据此 claim skill quality。
- shuffled rationale 在小样本中可能碰巧具有相同 error type，需要按 state/error 匹配情况分层报告。

## R016 Required Audit

1. 四个 candidate probabilities 对每个 condition 求和为 1。
2. 同一 state 的 baseline distribution 在七个 artifact cases 中完全一致。
3. option target tokenization 稳定且不再包含 context-space boundary artifact。
4. 输出包含 PMI bits、entropy reduction、artifact token count 和 density。
