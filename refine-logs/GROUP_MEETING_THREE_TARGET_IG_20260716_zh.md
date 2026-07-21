# Verus Proof Agent 的端到端评测框架

## 1. 研究目标

长期目标是构建一个 self-evolving Verus proof agent：agent 从历史证明与修复过程提炼可复用的 rules、skills 或其他 artifact，并在后续任务中使用。

本轮工作的重点不是证明某一种 evidence 已经有效，而是打通可复现的端到端评测链路：

```text
真实 VeruSAGE trace
  -> 选择 trajectory state
  -> 构造 action / patch / full-proof target
  -> 注入候选 artifact 或 control
  -> 本地模型逐 token 评分
  -> 聚合、审计与可视化
```

该框架不训练 RL policy，也不限制 agent 未来的自由探索。它提供离线测量接口，后续可以接入真正的新 evidence、skill 或 verifier diagnostic。

## 2. 重要校准

Pilot 中的 `evidence_artifact` 是当前 trajectory 的结构化摘要，包括 verifier error、局部代码和历史动作。这些内容都可以从已有 trajectory 中获得。

若 trajectory 为 `T`、摘要为 `E`，则当前构造满足：

```text
E = f(T)
```

当 baseline 已包含 `T` 时，`E` 没有引入新的事实。当前模型 log-probability 的变化最多说明上下文重排或注意力提示影响了有限模型，不能据此声称获得严格的信息增益，也不能说明该摘要改善了修复决策。

因此，本汇报不展示或解释当前 artifact 的 evidence-effect 数值。相关结果只作为工程调试记录保留。

## 3. 数据与模型设置

- 数据：3 条真实成功 VeruSAGE hands-on proof-repair traces。
- 状态：6 个 locally accepted trajectory states。
- 模型：本地 Qwen3.6-27B。
- 评分：exact teacher forcing，不重新生成 proof。
- 上下文：最长 78,392 tokens，低于 131,072-token 上限，无截断。
- 数据安全：原始 trace 只读，所有派生产物写入独立 run 目录。

实验矩阵为：

```text
6 states x 3 targets x 7 artifact conditions = 126 scoring cases
```

共保存 1,499,498 条 baseline/artifact token probability 与 log-probability 记录。

## 4. 三种 Target 接口

| Target | 被评分内容 | 未来可回答的问题 |
|---|---|---|
| Action | 下一步 locally accepted repair-action label | artifact 是否帮助选择修复方向？ |
| Proof patch | 当前代码到最终 verified 文件之间的修改部分 | artifact 是否帮助产生关键局部修改？ |
| Full proof | 完整最终 verified Verus 文件 | artifact 是否提高完整证明的条件似然？ |

框架同时保存 sequence-level total log difference 和 token-level log difference，以处理三种 target 的长度差异。

## 5. 已实现的评测能力

### Trace 到 Case

- 读取真实 trajectory prefix 并定位 accepted state；
- 构造 observed action target；
- 计算当前代码到最终 verified 文件的 patch target；
- 读取完整 verified proof target；
- 保留 trace、state、target 和 artifact 的来源标识。

### Artifact 注入接口

- 为同一 state/target 构造 baseline 与 artifact-conditioned prompt；
- 支持 cross-trace、shuffled、counterfactual、irrelevant 和 empty-wrapper controls；
- 支持 tokenizer-level 长度匹配；
- 后续可直接替换为 counterexample、diagnostic 或 retrieved skill。

这些 controls 证明框架可以表达配对实验；由于当前 artifact 不包含新信息，不能用当前 control 胜负推断 evidence utility。

### 长上下文逐 Token 评分

- 使用 Qwen3.6-27B 做 exact teacher forcing；
- 对长 proof 使用 chunked scoring；
- 保存每个 token 的 baseline/conditioned probability、logprob 和差值；
- 支持进度显示和断点续跑。

### 聚合与审计

- 计算 target-level total difference 和 per-token difference；
- 支持 artifact、state、target 三个维度聚合；
- 保存 cases、aggregates、token table、文件哈希与 visualization manifest；
- 生成逐点、配对和跨 target 可视化；
- 27 项实现测试全部通过。

## 6. 本轮结论边界

可以支持：

1. 已打通真实 VeruSAGE trace 到逐 token likelihood、统计和可视化的端到端链路。
2. Action、Patch 和 Full-proof 可以在统一接口下无截断评分。
3. 结果可下钻到每个 target token，并具有可复现的来源和哈希。
4. artifact 构造、模型评分和分析彼此解耦，后续替换输入无需重写系统。
5. 原始数据目录没有被修改。

不能支持：

1. 当前结构化摘要是真正有用的 evidence；
2. 当前 artifact 改善 action selection 或 proof generation；
3. likelihood difference 已经可作为 skill-promotion criterion；
4. solved rate 提升或 token consumption 下降；
5. 对 held-out projects 的泛化。

## 7. 下一步：接入真正的新信息

| Artifact | 来源 | 作用 |
|---|---|---|
| Counterexample / verifier diagnostic | 额外 verifier、SMT 或诊断 action | 指出失败状态或最小失败子目标 |
| Repair-critical hint | 额外分析或严格训练库检索 | 提供候选 invariant、lemma、definition 或修复方向 |
| Retrieved skill | 仅从训练 traces 提炼，在 held-out task 检索 | 测试跨任务复用 |
| GT-proof rationale | 从当前最终 proof 反向解释 | 仅作为 oracle upper bound |

离线框架将比较：

```text
log P(target | trajectory, new evidence)
- log P(target | trajectory)
```

并设置同长度、同错误类型但不匹配当前 state 的 controls。离线结果通过后，再执行：

```text
generate action/patch -> execute Verus
-> measure solved rate, repetition, verifier calls and tokens
```

只有在线 verifier 结果改善，才能说明 artifact 真正帮助了 agent。

## 8. 实验产物

- 实验报告：[EXPERIMENT_RESULTS_20260714_162614.md](EXPERIMENT_RESULTS_20260714_162614.md)
- 完整 run：[`r032_r034_all_states_observed`](../verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/)
- 可视化说明：[`VISUALIZATION_GUIDE_zh.md`](../verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/r032_r034_all_states_observed/analysis/figures_complete_20260716/VISUALIZATION_GUIDE_zh.md)

这些产物保留现有 pilot 数值用于复现和调试，不将其作为 evidence 有效性的研究结论。

## Takeaway

> 本轮完成的是可审计的端到端 evaluation scaffold，而不是对当前 evidence 有效性的验证。下一步应保持框架不变，接入 counterexample、额外 verifier diagnostic、held-out retrieved skill 或 oracle rationale，并最终通过在线 Verus execution 判断 downstream utility。
