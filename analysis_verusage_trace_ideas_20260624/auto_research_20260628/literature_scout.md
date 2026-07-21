# 文献调研：为什么路线要落在 Verusage 上

## 1. Agent workflow/specification 方向

**Lean4Agent: Formal Modeling and Verification for Agent Workflow and Trajectory**（arXiv:2606.06523）是 meeting 中真正重要的 UIUC 相关工作。它使用 Lean4 建模和验证 agent workflow/trajectory，提供 FormalAgentLib，并提出 LeanEvolve 来根据 formal verification 结果修订 workflow。它的实验在 SWE-Bench-Verified hard subset 和 ELAIP-Bench subset 上报告 workflow verification/evolution 的收益。

对本项目的启发：Lean4Agent 把 “agent workflow 可形式化” 这件事往前推了一步，因此我们不能再把 “形式化 agent workflow” 当新颖点。我们的差异必须是：Verusage proof repair 的 state/action/verifier feedback 更结构化，可以把 Lean4Agent 的 workflow/trajectory 思想落到 Verus proof obligation 上，而不是继续泛化 workflow。

**AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents**（arXiv:2503.18666，ICSE 2026）是 meeting 中另一个关键参照。它提供轻量 DSL，让用户定义包含 triggers、predicates 和 enforcement mechanisms 的规则，在 code execution、embodied agents、autonomous driving 等场景中运行时约束 LLM agents。

对本项目的启发：AgentSpec 说明 runtime enforcement 是可行且低开销的，但它更偏 safety boundary/access-control。Verusage 中可借鉴的不是安全规则本身，而是把 verifier-grounded 条件转成 runtime/harness rule：例如重复同一 `(Verus error, action)` 到阈值后禁止继续同 action，改为 skeleton retrieval 或 temporal lemma route。

## 2. Agent harness 方向

**Code as Agent Harness**（arXiv:2605.18747）把 code/harness 视为 agent 推理、行动、环境建模和 execution-based verification 的基础设施，覆盖 planning、memory、tool use、多 agent 协作等层次。它的价值是提供 vocabulary，但问题也正是 meeting 中指出的：它太宽，不能替代一个具体的 downstream task claim。

对本项目的启发：可以使用 harness vocabulary，但论文主线必须是 Verusage proof agent 的具体失败模式和改进机制。

**TACO: A Self-Evolving Framework for Efficient Terminal Agents via Observational Context Compression**（arXiv:2604.19572）更接近当前任务。它从 terminal-agent trajectories 中自动发现压缩规则，目标是降低长轨迹上下文冗余。这个工作说明 “从 trajectories 中学习压缩/控制规则” 是合理方向。

但 TACO 面向 terminal observation compression；Verusage 的机会更具体：

- 状态不是任意 terminal output，而是 Verus error、repair action、lemma/dependency、accepted candidate。
- 反馈不是弱 judge，而是 Verus evaluator 和 repair log。
- 目标不仅是 token compression，还包括 proof skeleton reuse 和错误循环中止。

## 3. Verus / Rust proof generation 方向

**Verus: Verifying Rust Programs using Linear Ghost Types**（arXiv:2303.05491）是底层任务背景：Verus 允许用 Rust-like 语言写 specifications/proofs 来验证 Rust 程序。它决定了本项目比泛化 coding agent 更有结构：错误类型、lemma、assert/invariant/reveal 等操作都有 formal verifier 反馈。

**AutoVerus**（arXiv:2409.13082）把 LLM agents 组织成类似人类 proof construction 的多阶段流程，包括初始 proof、generic tips refinement、基于 verification errors 的 debugging。它证明了 Verus proof generation 可以被 agent 化，但也留下了 trace-level 改进空间。

**SAFE**（arXiv:2410.15756）强调 self-evolution：用 verifier 标注正确/错误 proof，并利用大量 synthetic incorrect proofs 训练 self-debugging。这和 meeting 的 “self evolve 可以，但要 grounded” 一致。区别是：SAFE 更偏训练模型；当前预算只有本地 Codex，因此更适合先做 offline trace policy/skeleton，而不是大规模训练。

**KVerus**（arXiv:2605.03822）提出 “Semantic-Structural Gap”：LLM 看到的是语义模式，而 formal verification 依赖刚性的结构依赖。它用 metadata、lemma semantics、toolchain specifics 和 retrieval/self-refinement 解决 cross-file dependency。这个方向和 Verusage 很吻合，也支持我们做 lemma/action skeleton retrieval。

## 4. verus-tla / temporal proof 方向

**verus-tla** 是 `anvil-verifier/verus-tla` 里的 Verus crate，用 Verus embedding TLA+ temporal logic。README 描述其核心模块包括 `defs`、`rules` 和 `state_machine`：`defs` 定义 `Execution`、`TempPred` 以及 `always`、`eventually`、`leads_to`、`weak_fairness`、`tla_forall` 等 temporal connectives；`rules` 提供 liveness/safety helper lemmas；`state_machine` 提供 `Action`、`StateMachine`、`NetworkStateMachine`。仓库还包含 two-thread mutex liveness example。

这和 Verusage 很关键，因为我们本地 trace 里已有 `AL__...` 任务，文件名大量包含 `always`、`leads_to`、`tla_forall`、`weak_fairness`、`init_invariant` 等 temporal proof motif。现有离线统计显示 AL 项目在 4 个模型中共 356 条主 trace，虽然总体 verified rate 高于 AC/NR/OS，但 o4mini 上仍只有 46/89 verified，且 threshold=8 的 repetition gate 在 AL 上仍触发 81 条 trace，其中 75 条 non-verified。

对本项目的启发：verus-tla 可以成为一个小而精的 case study，用来展示 “agent formalization for Verus/TLA temporal proof” 比泛化 AgentSpec/Lean4Agent 更 grounded。

## 5. SWE-bench/Terminal-Bench 不是本项目主战场

Meeting 中老师多次质疑：如果 workflow/spec verification 最终只是让 SWE-bench 分数高，必须解释它解决了 SWE-bench 的哪个痛点。SWE-bench Verified 等 benchmark 已经高度拥挤，而且存在测试充分性、污染、过拟合等争议。

这不表示 SWE-bench/Terminal-Bench 没价值，而是当前项目不应该跟它们正面竞争。Verusage 的优势是：

- 我们已有大量真实 repair trajectories。
- 任务自带 symbolic verifier feedback。
- 错误类型和 action taxonomy 比普通 repo bug fixing 更结构化。
- 更容易做出 “为什么有效” 的分析，而不是只报一个 leaderboard 数字。

## 6. 本项目应形成的差异化

Lean4Agent 和 AgentSpec 已经占住了 “formalize/verify/enforce agent workflow” 的大方向，因此文献给出的空位不是 “第一个 formalize agent harness”，而是：

> 在 Verus proof generation，尤其是 temporal/liveness/TLA-style proof 这个高结构任务里，从历史 agent traces 中蒸馏可复用 proof skeleton、循环控制和 context compaction policy，形成低成本、可解释、Verusage-specific 的 harness-level 改进。

这条线和现有工作的关系：

- 比 Code-as-Harness 更具体；
- 比 TACO 更利用 formal verifier 结构；
- 比 AutoVerus 更关注 trace reuse/token efficiency；
- 比 SAFE 更轻量，不需要训练；
- 和 KVerus 的 retrieval/semantic-structural gap 互补，但数据源是 agent trajectories 而不是只做静态知识库；
- 和 verus-tla 的 temporal proof embedding 互补，可以把 `always/leads_to/weak_fairness` 类 proof skeleton 做成专门 case study。

## Sources

- Code as Agent Harness: https://arxiv.org/abs/2605.18747
- Lean4Agent: https://arxiv.org/abs/2606.06523
- AgentSpec runtime enforcement: https://arxiv.org/abs/2503.18666
- TACO terminal-agent compression: https://arxiv.org/abs/2604.19572
- Verus: https://arxiv.org/abs/2303.05491
- AutoVerus: https://arxiv.org/abs/2409.13082
- SAFE: https://arxiv.org/abs/2410.15756
- KVerus: https://arxiv.org/abs/2605.03822
- verus-tla: https://github.com/anvil-verifier/verus-tla
