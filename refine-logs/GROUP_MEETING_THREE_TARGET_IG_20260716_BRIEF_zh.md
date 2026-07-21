# Verus Proof Agent：端到端评测框架

## 1. 目标

长期目标是构建 self-evolving Verus proof agent：agent 从历史证明中提炼 rules 或 skills，并在后续任务中复用。

本轮不主张已经找到了有效 evidence，主要贡献是实现一套端到端离线评测框架：

```text
真实 VeruSAGE trace
  -> trajectory state
  -> action / patch / full-proof target
  -> artifact 注入
  -> 本地模型逐 token 评分
  -> 聚合、审计与可视化
```

## 2. 实验设置

- 3 条真实成功 VeruSAGE hands-on traces；
- 6 个 locally accepted states；
- 本地 Qwen3.6-27B；
- exact teacher forcing，不重新生成 proof；
- 126 个 scoring cases；
- 1,499,498 条 token-level probability/logprob 记录；
- 最长序列 78,392 tokens，无截断；
- 原始 trace 只读，派生产物位于独立 run 目录。

框架支持三种 target：

| Target | 内容 |
|---|---|
| Action | 下一步 observed repair-action label |
| Proof patch | 当前代码到最终 verified 文件的修改部分 |
| Full proof | 完整最终 verified Verus 文件 |

## 3. 已实现内容

1. 从真实 trace 自动提取 state，并构造三种 target。
2. 为同一 state/target 构造 baseline、artifact 和 matched-control cases。
3. 对短 action、局部 patch 和超长 full proof 统一进行 teacher-forcing 评分。
4. 保存每个 target token 在两种条件下的概率、logprob 和差值。
5. 支持长上下文 chunking、进度显示、断点续跑和结果聚合。
6. 生成逐点图、配对比较图、跨 target 图和可复现 manifest。
7. 保存 cases、aggregates、token table 和文件哈希；27 项实现测试全部通过。

## 4. 对当前 Pilot 的校准

Pilot 中的 `evidence_artifact` 只是已有 trajectory 的结构化摘要：

```text
evidence = f(trajectory)
```

它没有给已经看到完整 trajectory 的 agent 提供新事实。因此，当前 log-probability 变化只能视为上下文重排或提示方式的影响，不能解释为严格的信息增益，也不能证明该 artifact 改善了修复。

所以本次组会不强调当前 artifact 的数值结果。相关数据只用于验证框架完整运行并可被审计。

## 5. 本轮结论

**已经完成：**

- 打通真实 trace 到 token-level likelihood、统计和可视化的端到端链路；
- 在统一框架中支持 Action、Patch、Full-proof 三种 target；
- 保证无截断、可复现、可逐 token 审计，并且不污染原始数据。

**尚未证明：**

- 当前 evidence 有真实修复价值；
- likelihood difference 可以直接用于 skill promotion；
- solved rate 提升或 token consumption 下降；
- 对 held-out projects 的泛化。

## 6. 下一步

将当前摘要替换为 trajectory 之外的新信息：

1. 额外 verifier/SMT action 得到的 counterexample 或 diagnostic；
2. 能定位 invariant、lemma 或 definition 的 repair-critical hint；
3. 从严格训练 traces 提炼、在 held-out task 检索的 skill；
4. 从当前 GT proof 生成的 rationale，仅作为 oracle upper bound。

先在现有框架中测量条件 log-likelihood difference，再让 agent 实际生成 action/patch 并执行 Verus，最终比较 solved rate、repetition、verifier calls 和总 token。

## Takeaway

> 当前成果是一个可扩展、可审计的 end-to-end evaluation scaffold。下一阶段的关键不是继续解释现有摘要的数值，而是接入真正新增的、可验证的修复信息，并测量它是否改善在线证明结果。

详细版：[GROUP_MEETING_THREE_TARGET_IG_20260716_zh.md](GROUP_MEETING_THREE_TARGET_IG_20260716_zh.md)
