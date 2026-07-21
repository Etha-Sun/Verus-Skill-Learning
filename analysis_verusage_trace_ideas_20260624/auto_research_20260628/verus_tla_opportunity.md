# verus-tla 机会判断

结论：**有机会，但应该作为 Verusage 主线下的一条小而尖的 case study，而不是单独开成一个大项目。**

## 1. 为什么有机会

verus-tla 是一个把 TLA+ temporal logic embedding 到 Verus 的 crate。它的核心结构很适合和 Verusage trace 连接：

- `defs`：定义 `Execution`、`TempPred`，以及 `always`、`eventually`、`leads_to`、`weak_fairness`、`tla_forall`、`tla_exists`、`stable` 等 temporal connectives。
- `rules`：提供 liveness/safety helper lemmas，例如 unfold、entails、always、eventually、leads_to、invariant 相关规则。
- `state_machine`：提供 `Action`、`StateMachine`、`NetworkStateMachine` 这种 precondition/transition 结构。
- `mutex_example.rs`：展示 two-thread mutex liveness proof，使用 weak fairness、leads-to transitivity、or-leads-to 等 proof motif。

这和 meeting 中 Lean4Agent/AgentSpec 的讨论形成一个很自然的三角：

- Lean4Agent：用 Lean4 formalize agent workflow/trajectory。
- AgentSpec：用 DSL runtime enforce agent safety/reliability constraints。
- verus-tla + Verusage：用 Verus/TLA temporal proof obligations 约束 proof-repair agent 的搜索和 reroute。

第三个点更 grounded，因为它直接服务于 Verus proof repair，而不是泛化 agent 行为验证。

## 2. 本地 trace 已经有 AL/TLA 信号

从现有离线结果看，Verusage 主批次中已有 `AL__...` 任务，文件名和 verus-tla motif 很接近：

- `AL__leads_to_always_tla_forall`
- `AL__always_and_equality`
- `AL__leads_to_apply`
- `AL__always_tla_forall_apply`
- `AL__init_invariant`
- `AL__leads_to_rank_step_one`
- `AL__always_lift_action_unfold`

主数据中 AL 的粗略情况：

| model | tasks | verified | failed/timeout | verify rate | effective tokens |
|---|---:|---:|---:|---:|---:|
| claude | 89 | 73 | 16 | 82.02% | 9,883,356 |
| claude-s4 | 89 | 65 | 24 | 73.03% | 13,931,991 |
| gpt5 | 89 | 77 | 12 | 86.52% | 8,729,406 |
| o4mini | 89 | 46 | 43 | 51.69% | 20,316,759 |

AL 不是最大 token sink，但它是最适合做 “formal/temporal proof skeleton” 的区域。它的价值不是降耗最大，而是叙事最干净：从 generic agent verification 走到 Verus/TLA proof agent。

threshold=8 repetition gate 在 AL 上仍有信号：

- gated traces：81
- nonverified gated：75
- verified false stops：6
- estimated saved tokens：12,674,971

跨模型成功 skeleton 也有信号：

- claude AL covered failures：6
- claude-s4 AL covered failures：14
- gpt5 AL covered failures：2
- o4mini AL covered failures：33

这说明 AL/TLA proof 中确实存在 “某个模型失败但另一个模型成功” 的 skeleton reuse 空间。

## 3. 推荐的研究问题

不要写成：

> Can we use verus-tla to verify agents?

这个太大，也会回到 meeting 里老师批评的 “formal verification for agent for what?”。

建议写成：

> Can temporal-logic proof motifs from verus-tla guide LLM proof-repair agents on Verusage TLA-style tasks?

更具体一点：

> When Verus proof repair enters repeated error-action loops on TLA-style temporal lemmas, can a verifier-grounded skeleton memory retrieve `always/leads_to/weak_fairness/tla_forall` proof motifs and reroute the agent more efficiently?

## 4. 方法草案

第一版完全可以 offline：

1. 从 `AL__...` trace 中抽取 motif：
   - filename motif：`always`、`eventually`、`leads_to`、`weak_fairness`、`tla_forall`、`init_invariant`。
   - action motif：`USELEMMA`、`INSTANTIATE_FORALL`、`CASE_ANALYSIS`、`INDUCTION`、`COMPUTE`。
   - lemma motif：从 preprocessing 的 `Lemmas found` 和 success diff 文件名中抽。
2. 建 `AL` 专用 skeleton cache：
   - key：motif + error prefix + lemma names。
   - value：成功 trace 的 action sequence 和 proof rule sequence。
3. 建 AgentSpec-style runtime rule，但 rule 只针对 Verus/TLA proof：
   - 如果 `leads_to`/`always` 类任务连续 8 次重复同一 `(error, action)`；
   - 禁止继续同 action；
   - 强制检索 temporal skeleton；
   - 如果 skeleton 中出现 `wf1/leads_to_trans/or_leads_to/tla_forall_apply`，优先提示模型调用这些 lemma。
4. 用 offline replay 评估：
   - 能覆盖多少失败 AL traces；
   - reroute action 是否不同于重复 action；
   - 成功 skeleton 与失败 trace 的 motif overlap。

## 5. 和 Lean4Agent / AgentSpec 的定位差异

Lean4Agent 的强点是把 workflow/trajectory 放进 Lean4 里验证；AgentSpec 的强点是 runtime rule enforcement。我们的 verus-tla 支线应该吸收这两点，但避免重复：

- 不做通用 agent workflow formalization；
- 不做泛用 safety policy；
- 只做 Verus/TLA proof repair 的 verifier-grounded runtime control。

一句话定位：

> Lean4Agent/AgentSpec verify or enforce agent behavior; we use verifier feedback and temporal proof motifs to improve a proof-repair agent on Verusage.

## 6. 风险

- AL 任务总体 verified rate 较高，可能不如 AC/NR/OS 那样带来最大 token savings。
- verus-tla 仓库本身较小，不能单独支撑大规模 benchmark。
- 如果只做手写 temporal rules，容易变成工程 heuristic，论文贡献不足。

因此 verus-tla 最好作为主方法的 case study 或 ablation：

- 主方法：trace skeleton memory + repetition reroute。
- Case study：AL/verus-tla temporal proof motif。
- 证明点：在 TLA-style proof 中，formal motif 比 generic action retrieval 更可解释。

## Sources

- Lean4Agent: https://arxiv.org/abs/2606.06523
- AgentSpec: https://arxiv.org/abs/2503.18666
- verus-tla: https://github.com/anvil-verifier/verus-tla
- verus-tla README notes: `defs`、`rules`、`state_machine`、`mutex_example.rs`

