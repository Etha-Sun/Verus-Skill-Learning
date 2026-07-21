# 限制与瓶颈

## L1. 在稳定 error signature 上循环

现象：很多日志在一个 dominant error/action pair 上花满 20 次尝试。

证据：1,010 个 logs 中同一个 primary action 至少重复 8 次。

可能根因：

- action router 对同一 error signature 缺少 negative memory；
- acceptance criteria 奖励 local improvement，而不是 final progress；
- prompts 包含 previous attempts，但没有把它们转成可执行约束；
- 每个 action/error pair 没有显式 budget-aware stopping rule。

## L2. 缺少 Verusage-specific proof-plan transfer

现象：跨模型分歧中，一个模型便宜成功，另一个模型昂贵失败。

证据：`top_100_cross_model_disagreements.csv` 中很多文件的成功 run token 远低于失败模型。

可能根因：

- 成功 proof structure 只存在原始 patch/log 文件里；
- retrieval 不是 project-family/lemma-graph aware；
- prompts 重放太多 code，蒸馏后的 proof plan 太少。

## L3. 某些 families 的上下文过宽

现象：AC liveness prompts 包含完整 flatten code 和 generic vstd examples；单次调用可花 40k-60k input tokens。

可能根因：

- 没有 project-family context profile；
- helper lemmas 没有按 premise/conclusion pattern 建图索引；
- previous attempts 以原始 prose 加入，而不是紧凑 state delta。

## L4. Local acceptance 可能增加 global burden

现象：被接受的局部 repair 可能把 postcondition failure 转成 persistent assertion failure。

可能根因：

- acceptance checks 关注 target error-count reduction，而不是 downstream proof obligation complexity；
- 对制造后续 repeated target 的 assertion 没有惩罚；
- 对剩余 errors 的数量和类型没有显式 anti-regression metric。

## L5. Action priors 不够 family-specific

证据：

- `postcondition_repair` 常常有用，但可能制造 assertion loops。
- `add_trigger_assert`、`nonlinear_arithmetic`、`bit_vector_reasoning` 在多个 summary 中调用频繁但 success marks 低。
- `seqsetmap` 在 OS linked-list helpers 中被反复选择。

可能根因：

- action priors 主要由 error type 驱动；
- task family、function name、lemma names 和 prior successful patterns 使用不足。

