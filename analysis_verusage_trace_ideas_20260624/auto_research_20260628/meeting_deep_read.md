# Meeting 细读：研究约束与可执行方向

来源：`20260629120534-kexin-talk-new-project-transcript-1.txt`

## 1. 老师反复强调的主线

这次 meeting 的主线不是 “agent harness 本身很值得 verify”，而是：

> formal verification for agent 必须继续回答 “for what?”，最后要落到一个别人真正在意、并且能量化提升的 agent 任务。

老师明确不满意的方向是：只说要验证 Cloud Code/OpenHands/Codex 这样的通用 harness，或者只说要做语义等价改写。原因有三点：

1. **太 high-level**：如果不知道 agent 最终做什么任务，就无法定义优化目标，也无法解释为什么验证会带来效果。
2. **太 crowded**：SWE-bench、Terminal-Bench、通用 code-agent harness evolve 已经很多人在做。
3. **贡献链条断裂**：就算能写 pre/post condition 或约束 workflow，也要说明它解决了下游 benchmark 的哪个痛点。

老师更认可的落点是：

> 用 agent 做 formal verification，尤其是 Verusage/Verus/Rust verification 这类任务；如果要引入 harness evolution/specification/formalization，也应该服务于这个具体任务。

## 2. 对 Code-as-Agent-Harness 一类工作的判断

学生读到的落差是：论文标题暗示 harness 会变得更规范、可验证，但实际很多 planning/memory/tool-use 模块仍然是半结构化文本，更多是把已有 ReAct、memory、tool calling、feedback control 等理念放进 code/harness 视角。

老师的态度基本一致：

- 这类综述可以当字典，用来查缺补漏。
- 它不是当前项目的直接受众或直接路线。
- 真正有价值的不是 “harness 可以用 code 表达”，而是 harness 如何在某个高价值任务上带来可测提升。

对本项目的含义：不要写成 “我们也要把 harness formalize”。应该写成 “Verusage proof agent 的失败轨迹暴露了若干 harness-level 问题，我们用 Verusage-specific 机制改进它”。

## 3. 对 self-evolving harness 的判断

meeting 中讨论的 self-evolving harness 工作大致是：给定一个 baseline harness，在某个 benchmark 上运行，收集 trajectories，让 proposal agent 修改 harness，再迭代评估。

老师认可 self-evolve 作为工程 baseline，但指出最关键的是：

- evolve 的 fitness/reward 是什么？
- 这个任务是不是有价值？
- 结果是否能用表格说明 “没有我们 vs 有我们”？

老师明确说，harness evolve 中 “证明改写是否 equivalent” 不是主线，而是 regularizer。原因是：

- 大规模程序语义等价本身很难，甚至不可判定。
- harness evolve 后可能本来就应该改变 semantics，而不是保持等价。
- 如果 verification 不提升下游分数，它就是 “so what?”。

对本项目的含义：先做能改善 Verusage score/token 的 constrained evolve 或 offline policy；verification-inspired constraint 后置，作为减少搜索空间和坏循环的机制。

## 4. 对 Lean4Agent 和 AgentSpec 的判断

meeting 中重点讨论的两篇工作应明确为：

- **Lean4Agent: Formal Modeling and Verification for Agent Workflow and Trajectory**。这是 UIUC 相关同学做的工作，使用 Lean4/FormalAgentLib 建模和验证 agent workflow/trajectory，并提出 LeanEvolve 去修改 workflow。
- **AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents**。这是 ICSE 2026 接收的工作，用轻量 DSL 描述 trigger、predicate、enforcement 规则，对 LLM agent 做运行时约束和拦截。

这两篇不是普通 background，而是 meeting 里 “formal verification / specification for agent 到底 for what” 这个问题的直接参照系。

Lean4Agent 更接近 “把 workflow/trajectory formalize 并验证”；AgentSpec 更接近 “用可配置规则 runtime enforce agent 行为”。老师的核心疑问仍然成立：这些 formal/spec 机制最后服务于什么 downstream task，以及为什么能提升那个任务。

meeting 中对 Lean4Agent 类 workflow pre/post condition 验证工作的讨论是：用 DSL 或 formal language 表示 workflow，给每个阶段生成 pre/post condition，再检查 workflow 或 agent execution 是否违反这些条件。

老师的主要疑问：

- pre/post condition 如果是 LLM 生成的，它本身是否 grounded？
- 即使检查出违反，是 agent 错、condition 错，还是 workflow 错？
- 这些 condition 为什么能提升 SWE-bench/Terminal-Bench 分数？
- 如果只是防越权/转账一类行为，可能更像 access-control policy，而不是 Verus 这类 semantic verification 的最佳切入点。

对本项目的含义：不要把 “生成 pre/post condition 并验证 agent workflow” 或 “写 AgentSpec-style policy runtime enforcement” 当主贡献。可以借鉴它们的思想，但必须换成 Verusage 的真实状态变量：

- 当前 Verus error type 是否变化；
- accepted repair 是否真的减少目标错误；
- 是否重复同一错误-动作组合；
- 是否进入同一 lemma/action 的无效循环；
- 是否需要从成功 trace 召回 skeleton。

这些变量比泛化 workflow pre/post condition 更 grounded，因为它们直接来自 Verus evaluator 和 repair logs。

更准确地说，Lean4Agent/AgentSpec 对我们不是要模仿的终点，而是要超越的参照：

- Lean4Agent 的风险：workflow verification 仍可能和 SWE-bench/ELAIP 的真实痛点脱节。
- AgentSpec 的风险：runtime rule enforcement 更偏 safety/access-control，对 proof repair 的成功率和 token 成本不是天然相关。
- Verusage 的机会：把 formal/spec 机制绑定到 verifier feedback、proof obligation、lemma dependency 和 temporal proof skeleton 上，让 “formalization for agent” 终于有一个具体且可验证的 “for what”。

## 5. Meeting 给出的可执行路线

老师最后的建议可以压缩成三阶段：

1. **先别过度 ambitious**：不用一开始就 formally verify 整个 agent/harness。
2. **先把 Verusage 做起来**：约束 evolve/search space，让 Verusage 上分数更好、成本更低。
3. **再加 verification-inspired 方法**：例如用 specification、dependency、lemma、error invariant 去约束搜索，而不是在没有下游目标时验证 agent。

这也是本次离线实验选择的原因：先用已有 trace 证明 Verusage 内部确实有可利用结构，再决定下一步是否值得启动更贵的 agent run。

补充：Kexin 最后提到可以看看是否和 **verus-tla** 联系起来。这个方向是有机会的，但应该作为一条小而尖的支线，而不是替代 Verusage 主线。原因是 verus-tla 正好把 TLA-style temporal logic/liveness proof embedding 到 Verus 中，和 Verusage 的 AL/TLA 类任务、`always/leads_to/weak_fairness/tla_forall` proof skeleton 很接近。

## 6. 明确应该避免的方向

- 不要做 “Cloud Code 的 Rust 重写 + Verus 证明 + 再映射回 TypeScript” 这种长链条项目；太难、太不确定。
- 不要把 SWE-bench/Terminal-Bench 当主战场；拥挤，而且 meeting 中老师怀疑很多分数提升和 verification 方法本身没有因果关系。
- 不要做泛泛的 access-control/security policy，除非能证明这是 Verusage proof agent 的真实瓶颈。
- 不要把 spec generation/security/attack transformation 全部一起做；老师明确提醒不要摊太开。

## 7. 对当前自动化科研的定位

本次自动化科研的任务不是直接证明一个最终 paper claim，而是筛出最有信息量的 Verusage-specific claim：

- 如果失败 trace 大量 token 浪费在重复错误-动作循环，那么 repetition gate 有降耗价值。
- 如果失败 task 经常被另一个模型成功解决，那么 trace-distilled skeleton cache 有提分上界。
- 如果某些项目族 prompt 特别大，那么 project-aware context compaction 有明确目标。

这些 claim 都能用本地 trace 验证，不需要额外 API 预算。
