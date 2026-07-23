# Verifier-Grounded Skill Distillation: Research Synthesis

**截至：** 2026-07-22

**研究对象：** 从 Verus proof-repair trajectories 中学习可复用知识，并判断应以外部
skill、workflow/program 还是小模型参数的形式部署。

## Executive summary

目前项目完成的是 **leakage-safe trace selection、small-model capability screen、
prompt-level skill extraction/contrast、failure diagnosis 和 fresh agent exploration
baseline**，还没有完成“validated transferable skill learning”或“parametric knowledge
distillation”。

最重要的经验结果有三条：

1. Qwen3.6-27B 在 30 条 screen 中 strict solve 7/30，说明不是“完全没有能力”，也不适合
   直接用全部 trace 做方法比较。
2. 三样例 H0/H1/H2 中，trace-distilled global H2 为 4/9，低于 H0/H1 的 5/9，
   同时 token、wall time 和 safety 更差；当前 global rationale 不应扩跑。
3. Codex fresh exploration 3/3，但 closest-failure 的 Qwen agent-loop 存在 Verus
   permission confound。下一步必须先做 verifier-access matched control；否则“大小模型
   差异”和“rationale 效果”都会被基建差异污染。

因此最简洁、最有论文潜力的研究转向是：

> 从 whole-trace/global-rationale summarization，转向 verifier-conditioned、
> task-state-specific skill operators；用 counterfactual live rollouts 验证每个 operator
> 的因果效用，再决定外置调用还是向小模型内化。

## 1. 我们当前到底在研究什么

研究问题不是“能否让另一个 LLM 总结历史证明”，而是：

> 历史 proof-repair experience 中，哪些 verifier-grounded decision rules 能跨实例
> 提高预算内 strict solve，并且对小模型尤其有用？

主终点：

| 维度 | 主指标 | 防止的伪提升 |
|---|---|---|
| 正确性 | independent Verus + Lynette strict pass；Pass@k | 只让日志看起来更接近答案 |
| 效率 | Expected Cost to Success、wall、tool/model tokens | “失败得更快所以 token 少” |
| 安全 | bypass/unsafe edit rate | 用 `external_body` 等换取表面通过 |
| 迁移 | held-out theorem family、OOD、cross-model | 对来源 trace 过拟合 |
| 生命周期 | 构建、验证、部署、repair 的总成本 | 只计算推理时 prompt tokens |

Information gain 仍可用于便宜的候选预筛，但它不是 primary endpoint，也不能替代
live solve-rate 证据。

## 2. 本项目已经如何做 skill distillation

### 2.1 已完成链条

| 阶段 | 本项目实现 | 当前证据 | 判定 |
|---|---|---|---|
| Trace curation | R040 leakage-safe stratified selection；不向测试 arm 暴露旧答案/轨迹 | source hashes、sealed split、H0-only selection | 已建立 |
| Student capability gate | R040B Qwen3.6-27B 30-task live screen | 7 solve / 11 stalled / 10 timeout-or-infra / 2 unsafe | 已完成，证明需分层选样 |
| Qualitative case design | stable pass、closest failure、unstable 三类，各 3 reps | H0 3/3、0/3、2/3 | 已完成 |
| External rationale contrast | H0 no knowledge、H1 generic guidance、H2 trace-distilled global rationale | 5/9、5/9、4/9；H2 cost/safety 退化 | 当前 H2 stop |
| Failure diagnosis | ATLAS：同 8 条 FAILED/TIMEOUT traces 比较 Qwen 和 gpt-5.6-sol/high | failure-code 7/8 一致；blind quality 36 vs 45；大模型 recovery actionability 更强 | 机制线索，非 gold accuracy |
| Fresh exploration baseline | Codex 对三冻结任务各跑 1 次；不可见 old trace/answer/rationale | 3/3 Verus+Lynette；完整 events/commands | 机制参照，非 solve-rate estimate |
| Parametric internalization | 尚未开始 SFT/DPO/RL | 无 held-out live evidence | 未完成 |

### 2.2 当前 work 的正确命名

当前最准确的表述是：

> **Externalized trace-to-rationale prompt distillation pilot**

还不能称为：

- validated skill learning：H2 没有在 held-out probe 上稳定增益；
- student-aware distillation：同一个 global rationale 没有针对模型容量或当前 proof
  state 编译；
- causal skill credit assignment：尚未删除/替换 skill components 并做 paired live
  rollouts；
- parametric knowledge distillation：没有将验证后的 skill-conditioned trajectories
  训练进模型权重。

这个边界很重要：负结果不是“整个 skill learning 方向失败”，而是说明 **whole-trace
global textual compression 的粒度不对**。

## 3. 文献中的工作是怎样做 skill distillation 的

全部代表性方法都可落到五阶段：

| 阶段 | 弱实现 | 强实现 | 代表工作 |
|---|---|---|---|
| 1. Experience collection | 只收成功的完整 trajectory | 成功、失败、反馈、alternative branches、环境状态 | STaR, ExpeL, ReasoningBank |
| 2. Credit assignment | LLM 自由总结整条 trace | success/failure pairing、counterfactual objective、loss/execution/verifier attribution | SCOTT, Toolformer, ReGAL |
| 3. Abstraction | 删除变量名后写 advice | parameterized workflow、typed API、program、latent operator | AWM, CRAFT, CODI/DART |
| 4. Consolidation | embedding 相似即合并 | 验证、去重、裁剪、版本、held-out gate、negative scope | ExpeL, TroVE, SkillOpt（preprint） |
| 5. Deployment | 全部拼入 prompt | task-conditioned retrieval/gating/composition，或训练进参数 | ReasoningBank, ASI, Mentor-KD |

skill 的落点决定了验证方式：

| 载体 | 代表论文 | 优势 | 主要风险 |
|---|---|---|---|
| 自然语言 memory | Reflexion, ExpeL, ReasoningBank | 易生成、解释、在线更新 | 泛化难证、context 膨胀、冲突 |
| 参数化 workflow | AWM | 可复用且保留结构 | 仍依赖 LLM 正确执行 workflow |
| code/API/program | Voyager, CRAFT, ReGAL, TroVE, ASI | 可执行、可验证、可组合 | 适用范围受可编程性限制 |
| 模型参数 | STaR, SCOTT, Mentor-KD, Skip-Thinking | 部署开销低 | 错误知识固化，在线更新困难 |
| latent state | CODI, DART | 显著减少显式 reasoning token/latency | 训练复杂，解释与调试困难 |
| 外置后内化 | SkillRL 等前沿工作 | 先验证，再训练 policy | 数据隔离和 credit assignment 更难 |

## 4. 为什么当前 H2 会失败

H2 不是“知识太少”，更像同时违反了三个设计原则：

1. **不是 state-specific。** 当前 subgoal 已经从“理解 serialization”收缩到
   “找到 bytes library lemma”或“证明 offset extensionality”，但 H2 仍提供全局建议。
2. **没有 verifier-grounded acceptance。** rationale 由 trace 总结产生，没有以
   independent held-out proof rollouts 决定保留哪条规则。
3. **没有 negative scope。** 没有明确约束“不得新增 `external_body` helper、不得改
   spec、不得把 Verus `&&&` 当错误语法”，导致 over-edit 和 safety regression。

closest-failure 更揭示了第四点：**tool feedback 是 skill 生效的必要输入**。如果 Qwen
不能稳定调用 Verus，再好的 proof hint 也无法完成 error-driven refinement。

## 5. 推荐方法：Verifier-Grounded Student-Aware Skill Operators

### 5.1 最小方法核心

不要先做一个巨大的 self-evolving meta-skill 系统。先证明更小、更清楚的机制：

```text
trace + verifier states
        ↓ diagnose transition bottleneck
candidate state→action operator
        ↓ paired counterfactual rollout on disjoint probes
validated operator + negative scope
        ↓ compile for target student/state/budget
external skill or skill-conditioned training trace
```

候选 skill schema：

| 字段 | 内容 |
|---|---|
| `name` | 可审计的操作名 |
| `preconditions` | proof state、error pattern、已知 facts |
| `goal` | 下一条要消除的 verifier obligation |
| `decision_rule` | 何时选择本 operator |
| `actions` | 有顺序的 lemma search / assertion / program steps |
| `expected_observation` | 下一次 Verus 应如何变化 |
| `failure_indicators` | 什么输出说明方向错误 |
| `recovery` | 失败后的下一个受限编辑 |
| `negative_scope` | 不适用状态和禁止动作 |
| `evidence` | 来源 trace hashes 和 held-out probe results |
| `utility` | solve delta、cost delta、unsafe delta、置信区间 |

closest-failure 的候选 H3 不需要透露答案，只需编译为：

- 若 serialization 是固定 8-byte prefix + payload，优先查找现有 `vstd::bytes`
  lemma，禁止发明 `external_body`；
- prefix length 通过后，若只剩 sequence equality，把目标转成 `forall i` 的
  extensional proof；
- 使用 serialized index `8+i` 连接两个 payload，而不是断言 sequence cancellation。

### 5.2 因果效用

对 candidate skill \(s\)：

\[
U(s)=
\mathbb{E}_{x\sim D_{\text{probe}}}
\left[R(x\mid s)-R(x\mid \varnothing)\right]
-\lambda C_{\text{total}}(s)-\mu N_{\text{unsafe}}(s)
\]

其中 `R` 首先是 strict solve/partial verifier progress，`C_total` 包含生成、验证、
context、tool 和 repair 全生命周期成本，`N_unsafe` 是负迁移与 safety failure。

对组件 \(s_j\)：

\[
\Delta_j = U(s)-U(s\setminus s_j)
\]

只有 \(\Delta_j\) 在 paired probes 上稳定为正，才把组件保留为 validated knowledge。
这把“总结得合理”变成“对 verifier outcome 有因果边际贡献”。

### 5.3 Student-aware compilation

同一知识不应原样交给不同学生：

| Student/state | 编译形式 |
|---|---|
| 已懂 Verus、只缺 library routing | 一个 lemma-search trigger + 禁止项 |
| 能定位但不会完成 extensionality | 分解为 prefix length、index bounds、pointwise equality 三步 |
| 很小且难执行长文本 | 结构化短 operator 或少量 verified demonstrations |
| 可训练学生 | 用 validated skill-conditioned trajectories 做 SFT / preference / RL |
| 大模型 | 更少提示，只保留 state routing 与 safety guard |

这正面回应现有实验：更强、更长的 rationale 并不自动更适合 27B 学生。

## 6. 外置后内化的实验矩阵

在 P0 harness control 通过后，再比较：

| Arm | 训练/运行知识 | 回答的问题 |
|---|---|---|
| A. H0 | 无外部 skill | 学生自身能力 |
| B. Raw trajectory retrieval | 检索来源不重合的历史 trace | 完整经验复用是否足够 |
| C. Generic reflection/global rationale | 当前 H1/H2 类文本 | 总结型 memory 的基线 |
| D. Validated state-specific operator | 通过 held-out gate 的 H3 | 抽象+验证是否优于总结 |
| E. Raw-trace SFT | 原始成功/修复轨迹 | imitation baseline |
| F. Teacher long-CoT SFT | 教师 rationale | conventional CoT KD |
| G. Skill-conditioned verified SFT | H3 引导且 verifier 通过的 trajectories | 外置后内化是否更适合学生 |
| H. G + runtime operator | 参数与外部 skill 同时使用 | 是否仍有互补收益 |

必须至少报告：

- strict solve / Pass@k；
- Expected Cost to Success；
- model/tool/input/output tokens 与 wall；
- unsafe edit rate；
- skill build+validation amortized cost；
- ID/OOD theorem families；
- 两种以上 backbone，含 strong→weak；
- component deletion、wrong-skill 和 negative-scope ablation；
- 随经验量增长的 scaling curve。

### 四层数据隔离

| Split | 用途 |
|---|---|
| `D_trace` | 产生 trace 和 candidate rationale/operator |
| `D_skill_val` | 接受或拒绝 candidate skill |
| `D_meta_val` | 若以后学习 meta-operator，用于接受其更新 |
| `D_test` | 完全冻结后的最终评价 |

如果 meta-skill 反复看 `D_skill_val`，它会把 validation 学进去；所以两时间尺度方案必须
有独立 `D_meta_val`，否则“持续提升”可能只是 meta-overfitting。

## 7. 论文创新门槛：中稿工作告诉了我们什么

正式接收池的创新并不统一，但有稳定规律：

| 论文强度 | 仅靠什么通常不够 | 至少需要什么 |
|---|---|---|
| L2 | 新 extraction prompt、更多 reviewer agents、skill.md、embedding retrieval | 可复现实用系统；更适合 Workshop/Demo |
| L3 | 单域 prompt 组合 | 明确 failure mode + 针对机制 + 多设置稳定证据 |
| L4 | 泛化口号、LLM 自评 | 新表示/目标/验证/更新机制之一，最好两项；held-out/OOD/强基线 |
| L5 | 局部模块提升 | 新学习闭环或范式，并有跨任务/模型的强证据 |

21 篇正式接收论文的具体创新见 `PAPER_MATRIX.md`。压缩成一句话：

> 被接收的工作通常改变了学习单位、反馈/验证信号、技能更新机制中的至少一个；
> 强方法稿往往同时改变两个，而不是只把 trajectory 总结流程做得更复杂。

### 对本项目最现实的 L4 路线

可选贡献很多，但第一篇论文不应同时承诺全部。最小、最可证的主故事是：

1. **Verifier-grounded skill credit assignment：** 从 proof-repair traces 提出
   state→action operators，并用 paired counterfactual rollouts 识别真正有用的组件。
2. **Negative-scope-aware deployment：** 同时学习何时不该调用 operator，降低
   unsafe edits 和负迁移。
3. **Student-aware compilation：** 在相同知识下，为不同模型容量编译不同粒度，
   证明比 global rationale 和 raw trace retrieval 更有效。

“外置后内化”可以作为后半实验或下一篇工作；只有 H3 live evaluation 成立后再投入
SFT/RL，能避免把无效或有害的 H2 固化进学生参数。

## 8. 近期 TODO

| 顺序 | TODO | 成功标准 | 失败后的决定 |
|---:|---|---|---|
| 1 | 修复并验证 Qwen agent-loop 的 Verus access | smoke task 中 agent 可调用 wrapper，读取真实 stderr/stdout；final validator 保持独立 | 不做任何 rationale claim |
| 2 | closest-failure 上重跑 matched H0/H1/H2，各 3 reps | 完全相同 harness、tool access、timeout、model；无 permission denial | 若 H2 仍不优，永久 stop global H2 |
| 3 | 生成最小 H3 state-specific operator | 不含 verified answer；带 precondition、expected error transition、negative scope | 若 safety/成本退化，拆成 component arms |
| 4 | H3 component ablation | lemma routing、offset proof、negative scope 各自可测 | 只保留有正 \(\Delta_j\) 的组件 |
| 5 | 扩到分层 30-task 或新 held-out set | strict solve、ECTS、safety 同时满足 gate | 不进入 parametric distillation |
| 6 | strong/weak matched comparison | 同 harness 下区分 diagnosis、actionability、feedback-use、recovery | 再决定 student-aware compiler 形式 |
| 7 | 仅在 H3 成立后做 SFT | G 优于 E/F，且 OOD 与成本不退化 | 外置 skill 作为最终形态 |

**立即下一步只有 TODO 1。** 不应同时启动 meta-skill evolution、Pareto optimizer 和
student SFT；先消除 harness confound，并证明一个 state-specific operator 的真实效用。

## 9. 最终研究判断

本项目最独特的资源不是“有很多 trace”，而是：

- ground-truth formal proof obligations；
- 可重复调用的 exact verifier；
- 精确 proof states 和 counterexamples/errors；
- 可度量的 strict success、安全性与执行成本。

所以最弱路线是让多个 LLM 把 trace 写成更漂亮的文档；最强路线是把 verifier 变成
skill learning 的因果监督：

```text
correlated trace pattern
        ↓ counterfactual verifier rollouts
causally useful state→action operator
        ↓ student-aware compilation
external skill / verified training trajectory / model parameter
```

如果能做到这一点，研究才从当前 L2–L3 的 prompt-level distillation pilot，推进到有
主会竞争力的 L4 方法工作。
