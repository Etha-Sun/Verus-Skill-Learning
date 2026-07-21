# Towards Verifiable VeruSAGE Self-Evolving Agent

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-03T09:51:55`
- status: `draft`

## Objective

Prepare a concise Chinese group-meeting draft for the current research direction:
using VeruSAGE/Verusage traces to build a verifier-grounded self-evolving proof
repair agent.

## Context

This draft is based on:

- Meeting transcript:
  `analysis_verusage_trace_ideas_20260624/20260629120534-kexin-talk-new-project-transcript-1.txt`
- VeruSAGE provenance audit:
  `research_memory/projects/verus_self_evolving/notes/20260703-093115-verusage-repair-scaffold-provenance-audit/ENTRY.md`
- Current scaffold:
  `verus-self-evolve-scaffold/`
- Offline eval summary:
  `verus-self-evolve-scaffold/docs/eval_summary.md`
- Earlier reports:
  `analysis_verusage_trace_ideas_20260624/auto_research_20260628/`

## Method / Actions

Drafted a short meeting outline with conservative claim boundaries:

- Treat AgentSpec/Lean4Agent as legacy questions and positioning baselines.
- Treat VeruSAGE as a real code-backed harness, not an invented scaffold.
- Frame self-evolving as decision-layer learning over verifier-grounded traces,
  not just parameter tuning of the orchestrator.
- Keep evaluation caveat: current trace rules are offline and need split-safe
  validation.

## Evidence

Known source/code facts:

- Public code: `https://github.com/microsoft/verus-proof-synthesis/tree/main/verusage`
- Local code: `<scratch-root>/RL-verus-1129/autoverus/verusage`
- VeruSAGE paper: `https://arxiv.org/abs/2512.18436`
- Leaderboard: `https://microsoft.github.io/verus-proof-synthesis/`

Known local trace stats:

- traces: 2,996
- verified: 1,691
- nonverified: 1,305
- effective total tokens: 1,524,386,760

Current offline replay policy results:

| policy | covered failed | saved failed tokens | false-stop rate | peer diff |
|---|---:|---:|---:|---:|
| generic | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project-aware | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif-aware | 227 | 309,382,084 | 0.005322 | 0.777778 |

## Result

### 组会草稿

## Towards Verifiable VeruSAGE Self-Evolving Agent

### 0. One-sentence pitch

我们想做的不是再训练一个小模型，也不是泛化地优化 agent workflow，更不是把 LLM 锁死在 hands-on 小步 scaffold 里。核心想法是：保留 hands-off 的自由探索，在关键决策点注入 verifier-grounded 的 soft steering signals，让 agent 少重复、少烧 token、但仍然能大步探索。

### 1. Legacy Questions from Prior Paper Discussion

这些不是我们对相关工作的最终评价，而是之前讨论 AgentSpec / Lean4Agent 时 prof 提出的 critique。它们给我们当前设计提供了约束。

**对 AgentSpec 的 critique**

- AgentSpec 的核心是 runtime rule enforcement：人类用 DSL 写 trigger / predicate / enforcement rule，系统在 agent 执行时拦截或约束行为。
- prof 当时的问题是：这些规则到底从哪里来？规则是否主要还是人类写的？
- AgentSpec 自己的回答是两层：
  - 主实验中，rules initially manually developed based on detailed risk descriptions；也就是说核心规则主要由人类/开发者根据安全风险描述实现。
  - RQ2 中，他们进一步让 OpenAI o1 自动生成规则：prompt 包含 agent 描述、tool 列表、开发者提供的 3 个 illustrative rules 及 predicate functions，并可选加入 in-context examples；然后在 held-out risky scenarios 上评估。
- 他们报告 LLM-generated rules 也有效：code agent 中 enforcement rate 87.26%；embodied agent 中 precision 95.56%、recall 70.96%；AV 场景中阻止 5/8 个 law-breaking scenarios。
- 但这仍然需要较多人类结构化输入：DSL schema、domain predicates/events、risk descriptions、developer examples、rule review/approval，以及人工评估部分结果。
- 因此我们不能只做一个 AgentSpec-like rule layer。我们的目标应该是：让 LLM 从 VeruSAGE hands-off / hands-on traces 中提出候选规则，再用 Verus verifier-grounded replay / sampling / rerun 筛选规则。规则来源应从“人类写 safety policy”推进到“trajectory-induced proof-repair policy”。

**对 Lean4Agent 的 critique**

- Lean4Agent 的 story 是把 agent workflow / trajectory formalize 到 Lean4 中，并验证 workflow 是否满足某些 property。
- prof 当时的问题是：为什么这个 workflow 必须被 formal verification？验证以后具体改善哪个 downstream task？
- Lean4Agent 自己的回答不是单纯“数值更好”，而是 verification 改善/诊断了 workflow 的具体层面：
  - **structural layer**：workflow graph 是否结构正确，是否有合理连接和 loop-back。
  - **semantic layer**：每个 step 的 pre/postcondition 是否自洽，变量规格是否精确，信息流是否被 context-insensitive step 打断。
  - **runtime trajectory layer**：当一次执行失败时，能定位是哪一步违反了 predicate，而不是只看到最终失败。
  - 论文分析中，passing workflows 往往有更 precise variable specifications、well-structured retry loops、more reasonable context management；failing workflows 常见问题是 unsatisfied preconditions、缺少 valid retry mechanism、context-insensitive execution steps 破坏 information flow。
- LeanEvolve 利用这些 diagnostics 修改 workflow，尤其对 edge cases 和 cross-file modifications 有帮助；formal-guided refinement 比 pure-LLM evolution 更擅长定位“该改 workflow 的哪一步”。
- 这对我们的启发不是“也去 formalize agent workflow”，而是要建立类似的 **可检验性质 -> 诊断 -> 决策改进** 链条：

| Lean4Agent 验证对象 | 它改善的 workflow 层面 | 我们的对应对象 | 我们希望改善的 VeruSAGE 层面 |
|---|---|---|---|
| workflow graph | step 连接、loop-back、retry 结构 | repair action trajectory | 什么时候继续、reroute、检索 skeleton |
| pre/postcondition consistency | step 输入输出是否自洽 | Verus error/action state delta | action 是否真的减少 target error |
| information flow/context predicates | context 是否足够且不污染后续判断 | prompt/context/motif signals | project-aware context compaction |
| trajectory violation localization | 定位失败 workflow step | repeated `(error, action)` 和 verifier delta | 定位低价值 repair loop |
| LeanEvolve diagnostics | 修改 workflow | rule/skill/skeleton evolution | 修改 soft steering policy |

- 因此我们的回答应是：Verus proof repair 的 verifier feedback 更直接，规则或 skill 的好坏可以通过 target-error delta、solved rate、false-stop rate、token cost、action diversity preservation 来检验。验证不是为了证明 agent 本身正确，而是为了诊断 repair decision 哪里低效，并把诊断转成 non-blocking steering。

### 2. VeruSAGE Mechanism

**这些 traces 来自什么 harness？**

- 不是我们临时搭的 harness。VeruSAGE 有公开代码和文档：
  `microsoft/verus-proof-synthesis/verusage`。
- 本地也有对应代码：
  `<scratch-root>/RL-verus-1129/autoverus/verusage`。
- 当前 trace 主要来自 VeruSAGE-style hands-on repair scaffold，而不是纯 generic coding agent。

**核心流程**

1. 运行 Verus，得到 structured verification errors。
2. `RepairMainLoop` 选择一个目标 error。
3. `AgentOrchestrator` 根据 error type 路由到 specialized agent。
4. Agent 采用 observation-reasoning-action 流程，选择一个 repair action。
5. Action 生成 proof candidate。
6. Verus + safety checker 验证 candidate，接受或拒绝。
7. 重复直到 verified、timeout 或达到 step limit。

**关键观察**

- VeruSAGE 已经有 Verus-specific tools/actions：
  `USELEMMA`、`CASE_ANALYSIS`、`INSTANTIATE_FORALL`、`POSTCONDITION_REPAIR`、`INVARIANT_REPAIR` 等。
- 但它的 decision layer 仍然有大量手写和局部启发式：
  error priority、agent routing、action selection、candidate acceptance。
- Paper 自己也承认：hands-on scaffold 有时会因为 hard-coded policy 限制强模型的大步探索，导致 Sonnet 在 hands-on 下反而不如 hands-off。

### 3. VeruSAGE Trace Observations

**数据概况**

- 当前解析主批次：2,996 条 traces。
- Verified：1,691。
- Non-verified：1,305。
- Effective total tokens：约 1.52B。

**观察 1：重复失败很常见**

- 很多失败 trace 会在同一个 `(Verus error, action)` 上反复尝试。
- 例如 `AssertFail + USELEMMA`、`PostCondFail + postcondition_repair`、`AssertFail + CASE_ANALYSIS`。
- 这说明 agent 并不是没有 action，而是不会判断“当前 action 已经不值得继续”。

对应实验：**实验 A，重复错误-动作 gate**。方法是解析每条 trace 的 `Target error: VerusErrorType.X` 和 `primary_action`，模拟同一个 `(target_error, primary_action)` 第 `k` 次出现时停止。

| threshold | nonverified gated | nonverified token saved | saved rate | verified false-stop |
|---:|---:|---:|---:|---:|
| 2 | 1305 / 1305 | 1,212,510,484 | 90.63% | 761 / 1691 |
| 3 | 1299 / 1305 | 1,076,004,993 | 80.43% | 424 / 1691 |
| 4 | 1286 / 1305 | 923,447,476 | 69.02% | 267 / 1691 |
| 5 | 1252 / 1305 | 776,366,321 | 58.03% | 178 / 1691 |
| 6 | 1198 / 1305 | 647,707,759 | 48.41% | 119 / 1691 |
| 8 | 969 / 1305 | 424,591,160 | 31.74% | 51 / 1691 |

Takeaway：threshold=8 已经能覆盖 74.25% non-verified trace 并节省 31.74% failed tokens，但仍会误杀 51 个最终成功 trace，所以不能简单做 hard stop。

**观察 2：停止不是最好的策略，reroute 更合理**

- 简单 repetition gate 可以节省大量 failed tokens，但直接 stop 会误杀一部分最终成功 trace。
- 更合理的策略是：当重复到阈值后，不是停止，而是触发 skeleton retrieval / action reroute / context compaction。

对应实验：**实验 A + 补充实验，skeleton cache 与 reroute prior**。方法是在 threshold=8 触发重复循环时，查找同一 task 的其他模型成功 trace，用成功 trace 同位置 action 作为 reroute prior。

| metric | value |
|---|---:|
| reroute candidates | 372 |
| top peer action different from repeated action | 274 |
| different action rate | 73.66% |

Takeaway：大量失败 trace 在当前 action 上继续重复，但其他模型成功轨迹显示此时应该换 action family；这支持 non-blocking reroute recommendation，而不是直接停止。

**观察 3：Verus-specific rule 比 generic rule 更安全**

Offline replay 中：

- generic rule 覆盖更多失败，但 false-stop 风险较高。
- project-aware rule 更稳。
- motif-aware rule 覆盖少一些，但 false-stop 最低，说明把 Verus/project/proof motif 放进规则很重要。

对应实验：**scaffold policy ablation**。方法是从 trace 中挖候选 rules，比较三类 rule 粒度：generic、project-aware、motif-aware。

三类规则的区别：

| policy | rule scope | example meaning |
|---|---|---|
| generic | 只看 `threshold + repeated_error + repeated_action` | 全局地认为 `AssertFail + USELEMMA` 重复 N 次后应该 reroute |
| project-aware | 加入 `project` 条件 | 只在 `AC` 或 `NR` 等项目内应用这个 reroute rule |
| motif-aware | 加入 `project + proof motif` 条件 | 只在某项目的 temporal / quantifier / arithmetic / bitvector 等 motif 中应用 |

motif 是从文件名、lemma 名、recursive/opaque preprocessing 信息中抽出来的弱结构信号：

| motif | keywords / signals |
|---|---|
| temporal | `always`, `eventually`, `leads_to`, `weak_fairness`, `tla_forall`, `stable` |
| quantifier | `forall`, `exists`, `trigger` |
| arithmetic | `mod`, `div`, `mul`, `aligned`, `pow2`, `nat`, `int` |
| bitvector | `bit`, `mask`, `bitmap`, `addr_mask`, `flag` |
| sequence_set_map | `seq`, `set`, `map`, `filter`, `fold`, `append`, `subrange` |
| induction | `rec`, `recursive`, `induct`, `rank` |
| refinement/state_machine | `refines`, `interp`, `view`, `state`, `step`, `transition`, `invariant` |

| policy | covered failed | saved failed tokens | false-stop rate | peer diff |
|---|---:|---:|---:|---:|
| generic | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project-aware | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif-aware | 227 | 309,382,084 | 0.005322 | 0.777778 |

为什么 project-aware 更稳：

- 不同项目的 proof style 很不一样。比如 AC 更偏 controller/liveness/resource invariant，NR 更偏 page table/refinement/bitvector/address reasoning，MA 更偏 allocator/layout/arithmetic。
- 同样的 `AssertFail + USELEMMA` 重复，在不同项目里可能代表不同问题；全局规则容易误伤，project scope 可以避免把某个项目的失败模式套到另一个项目。

为什么 motif-aware 更稳：

- 同一项目内部也有不同 proof obligation。`temporal leads_to`、`quantifier trigger`、`bitvector mask`、`sequence/set/map` 的有效 reroute action 不一样。
- motif-aware rule 把 “重复了什么 action” 和 “当前证明结构是什么” 绑在一起，因此 false-stop rate 从 generic 的 0.112951 降到 0.005322。

Takeaway：generic rule 更像 token-saving heuristic；project-aware/motif-aware rule 更像 Verus-specific steering prior。我们后续应该默认把 rule 作为 soft recommendation 或 sampling prior，而不是全局 hard gate。

**观察 4：成功 trace 中有可迁移 skeleton**

- 很多失败 task 在其他模型 trace 中有成功版本。
- 这说明同一 task 或相似 proof motif 上存在可复用的 action sequence / lemma sequence。
- 但 exact-task cache 有数据泄漏风险，所以后续必须做 split-safe retrieval 和 evaluation。

对应实验：**实验 B，跨模型成功 skeleton 覆盖上界**。方法是对每个失败 trace，检查同一个 `(project, file)` 是否被其他模型 verified；如果存在，则认为 exact-task success skeleton 给出可复用上界。

| metric | value |
|---|---:|
| covered failed traces | 517 |
| covered failed effective tokens | 377,656,792 |
| total failed effective tokens | 1,337,870,858 |
| failed-token coverage | 28.23% |

Non-exact retrieval sanity check：

| metric | value |
|---|---:|
| eval queries | 517 |
| hit@1 | 0.9865 |
| hit@3 | 0.9923 |
| hit@5 | 0.9923 |

Takeaway：成功 trace 的 action-level skeleton 信号很强，但 exact-task 使用会泄漏；后续要做 no exact-task skeleton 的 split-safe retrieval。

**补充观察：token/context cost 不是均匀分布**

对应实验：**实验 C，prompt/context cost audit**。方法是解析 `llm-prompts/*-input.txt`，共 92 个 prompt groups，46,684 个 prompt files。

| model | project | status | prompt_count | mean bytes | over_100k |
|---|---|---|---:|---:|---:|
| o4mini | AC | TIMEOUT | 1,245 | 167,379 | 1,110 |
| claude-s4 | AC | FAILED | 1,019 | 172,380 | 914 |
| gpt5 | AC | TIMEOUT | 891 | 188,380 | 865 |
| claude | AC | FAILED | 802 | 180,826 | 754 |
| claude-s4 | NR | FAILED | 1,944 | 76,217 | 729 |
| gpt5 | NR | TIMEOUT | 1,465 | 83,506 | 633 |
| o4mini | NR | TIMEOUT | 1,897 | 75,737 | 622 |
| claude | NR | FAILED | 1,418 | 79,186 | 530 |

Takeaway：AC 是最明显的 prompt bloat project，NR/OS 是第二梯队；context compaction 不应全局平均做，应该 project-aware，优先 AC/NR/OS。

### 4. Proposed Direction

我们当前的研究假设：

> VeruSAGE traces 可以被挖掘成 verifier-grounded skills、proof skeletons 和 structured decision rules，用来改善 repair action selection，同时用 held-out evaluation 防止过拟合。

具体可以分三层 memory：

1. **Skill memory**
   - 从成功 proof trace 中总结可复用证明技巧。
   - 例：什么时候使用 sibling lemma、什么时候需要 trigger assert、什么时候需要 case split。

2. **Skeleton memory**
   - 保存成功 trace 的 action sequence / lemma sequence / error transition。
   - 用 project、error type、lemma names、proof motif 做 retrieval key。

3. **Policy memory**
   - AgentSpec-like structured rules。
   - 例：

```text
Trigger:
  AssertFail + USELEMMA repeated >= N
Predicate:
  target error does not decrease
Enforcement:
  block USELEMMA once; route to CASE_ANALYSIS / INSTANTIATE_FORALL / skeleton retrieval
```

### 4.1 Extensible Self-Evolving Architecture

为了避免把 LLM 锁死在 hands-on scaffold 里，基本原则是：

> 永远不阻拦 LLM 的思考，只在可检验的执行/决策环节提供规则、建议或 sampling prior。

架构应当保留三种自由度：

1. **规则生成自由度**
   - 规则不完全由人类写。
   - LLM 可以读取 hands-off 成功/失败例子，提出新的 rule candidates。
   - 人类只定义 rule schema 和验证协议，而不是枚举所有规则。

2. **规则执行自由度**
   - rule 不一定是 hard constraint，默认应该是 non-blocking steering。
   - 可以分成三类：
     - `hard rule`：明显非法或作弊行为，必须阻止；
     - `soft recommendation`：给 action prior 加权，而不是强制改道；
     - `sampling policy`：从多个可行 action 中按 verifier/history-derived score 采样，保留探索。
   - 这样可以避免把强模型限制成小步 hands-on agent。

3. **skill 演化自由度**
   - skill memory 不应只是静态检索库。
   - LLM 可以提出 skill rewrite / merge / split / deprecate。
   - 但 skill 更新必须通过 replay、held-out trace check 或小规模 live rerun 后才能进入 stable memory。

一个更合适的表述是：

```text
Trace examples -> LLM proposes rules/skills
              -> verifier-grounded evaluator scores them
              -> sampling-based policy uses them as priors
              -> live traces update rule/skill memory
```

这比“微调 orchestrator 参数”更开放：orchestrator 只是执行 substrate，真正演化的是 rules、skills、skeletons 和 action priors。

一句话版本：

> 从 hands-off / hands-on traces 中学规则，但规则不直接替代 LLM；规则只作为可验证的 steer，让 LLM 保留探索能力。

### 4.2 Novelty Boundary

这个方向 novelty 低的风险在于：

- 如果只是手写几条 repetition rule，就是 AgentSpec-style policy engineering。
- 如果只是调 action retry 阈值，就是 VeruSAGE orchestrator parameter tuning。
- 如果只是把成功 trace 做 exact-task cache，会有数据泄漏和 benchmark overfit。

有 novelty 的版本应该强调三点：

- **rule induction**：规则由 LLM 从 hands-off / hands-on trajectories 中提出，而不是人类手写。
- **verifier-grounded validation**：规则不是靠自然语言判断，而是通过 Verus error delta、solved rate、false-stop rate、token cost 验证。
- **exploration-preserving execution**：规则不是简单禁止探索，而是变成 sampling prior / soft constraint，让强模型仍可大步尝试。

### 4.3 Optional Case Study: Verus-TLA / Temporal Proof Motifs

Kexin meeting 最后提到可以看看是否和 `verus-tla` 联系起来。这个方向有机会，但更适合作为 VeruSAGE 主线下的小而尖 case study，而不是单独开成大项目。

**为什么适合**

- `verus-tla` 是把 TLA-style temporal logic embedding 到 Verus 的 crate。
- 它包含 `always`、`eventually`、`leads_to`、`weak_fairness`、`tla_forall`、`tla_exists`、`stable` 等 temporal connectives，以及 liveness/safety helper lemmas。
- VeruSAGE 主批次中已有 AL/TLA-style tasks，例如：
  - `AL__leads_to_always_tla_forall`
  - `AL__always_and_equality`
  - `AL__leads_to_apply`
  - `AL__always_tla_forall_apply`
  - `AL__init_invariant`
  - `AL__leads_to_rank_step_one`
  - `AL__always_lift_action_unfold`

**已有 AL/TLA trace 信号**

| model | tasks | verified | failed/timeout | verify rate | effective tokens |
|---|---:|---:|---:|---:|---:|
| claude | 89 | 73 | 16 | 82.02% | 9,883,356 |
| claude-s4 | 89 | 65 | 24 | 73.03% | 13,931,991 |
| gpt5 | 89 | 77 | 12 | 86.52% | 8,729,406 |
| o4mini | 89 | 46 | 43 | 51.69% | 20,316,759 |

AL 不是最大 token sink，但它很适合展示 “formal / temporal proof skeleton” 的价值。

| AL-specific signal | value |
|---|---:|
| threshold=8 gated traces | 81 |
| nonverified gated | 75 |
| verified false stops | 6 |
| estimated saved tokens | 12,674,971 |

跨模型成功 skeleton 也有信号：

| model failed side | AL covered failures by other-model success |
|---|---:|
| claude | 6 |
| claude-s4 | 14 |
| gpt5 | 2 |
| o4mini | 33 |

**更好的研究问题**

不要写成：

```text
Can we use verus-tla to verify agents?
```

这会落回 Lean4Agent/AgentSpec 那类泛化 agent verification 问题。

更好的问题是：

```text
Can temporal-logic proof motifs from verus-tla guide LLM proof-repair agents on VeruSAGE TLA-style tasks?
```

更具体：

```text
When Verus proof repair enters repeated error-action loops on TLA-style temporal lemmas,
can a verifier-grounded skeleton memory retrieve always/leads_to/weak_fairness/tla_forall
proof motifs and steer the agent more efficiently?
```

**可能的 rule / skill 形式**

```text
trigger:
  filename or local context contains [leads_to, always, weak_fairness, tla_forall]
  and same (error, action) repeats >= N

recommendation:
  retrieve temporal skeletons tagged [leads_to, tla_forall, weak_fairness]
  surface candidate lemmas such as leads_to_trans, or_leads_to, tla_forall_apply

execution:
  use as soft recommendation / sampling prior, not as hard block

validation:
  AL-only split-safe replay + no exact-task skeleton + verifier error delta
```

**Positioning**

> Lean4Agent/AgentSpec verify or enforce agent behavior; our Verus-TLA case study uses verifier feedback and temporal proof motifs to steer a proof-repair agent on concrete VeruSAGE TLA-style tasks.

风险：如果只手写 temporal rules，会变成 heuristic；所以 TLA 部分应该展示 rule induction + verifier validation，而不是人工规则 demo。

### 5. Related Work

**TACO**

- TACO 从 terminal-agent trajectories 中学习 observation compression rules，用来降低 token cost。
- 它和我们最接近，因为它也是从 trajectories 中学习规则。
- 区别是：TACO 主要压缩 observation；我们希望学习 proof-repair decision rules。
- VeruSAGE 的优势是 feedback 更强：Verus verifier 给出结构化 error、target error delta、verified/nonverified 等信号。

**AgentSpec**

- 提供 runtime rule enforcement 的 DSL 思路。
- 我们可以借鉴 trigger / predicate / enforcement 的规则形态。
- 但规则来源要从人工规则推进到 trajectory-mined + verifier-validated rules。

**Lean4Agent**

- 证明 agent workflow / trajectory formalization 是重要方向。
- 我们不把“formalize workflow”作为主 novelty。
- 我们的差异是把 verification 落到 Verus proof repair：每个 action 是否改善 proof state 可以由 Verus 直接判定。

**verus-tla**

- 不是泛化 agent verification 工作，而是 Verus 中的 temporal logic proof substrate。
- 可以作为 case study 展示我们的规则不是 generic repetition heuristic，而能利用 `always/leads_to/weak_fairness/tla_forall` 这类 formal proof motif。

### 6. Current Positioning

我们的贡献可以暂时表述为：

> Existing self-evolving agents learn prompts, workflows, skills, or compression rules, but they usually treat environment feedback as generic success/failure signals. Verus proof repair exposes richer verifier-grounded structure. We use this structure to self-evolve repair skills and decision rules for VeruSAGE-style agents.

中文版本：

> 现有 self-evolving agent 多数学习 prompt、workflow、skill 或 compression rule，但通常把环境反馈当成泛化的成功/失败信号。Verus proof repair 的特殊性在于 verifier feedback 本身包含 proof structure。我们利用这些结构化反馈自动蒸馏 skill 和决策规则，从而改善修复策略选择并减少重复失败。

### 7. Risks / Open Problems

- **数据泄漏**：不能从同一 task 的成功 trace 中抽 skeleton 再评估同一 task。
- **过拟合 VeruSAGE scaffold**：需要把方法抽象成 verifier-grounded decision layer，而不是只调当前 orchestrator 参数。
- **探索度下降**：不能只做 token-saving gate；需要学习什么时候收紧、什么时候放开模型探索。
- **live eval 成本**：目前结果主要是 offline replay，下一步需要 split-safe replay 和小规模 live rerun。

### 8. Next Step

1. 建立 split-safe evaluation：
   - task split，
   - project split，
   - model split，
   - no exact-task skeleton。

2. 实现第一版 policy：
   - repetition detection，
   - project/motif-aware reroute，
   - skeleton retrieval，
   - context compaction。

3. 指标：
   - solved rate preservation / improvement，
   - token saved，
   - false-stop rate，
   - reroute success rate，
   - verifier error delta。

## Decision / Next Step

Use this as a concise group-meeting draft. Before converting it into slides,
decide whether the talk should emphasize:

- research positioning against AgentSpec/Lean4Agent/TACO, or
- concrete VeruSAGE trace evidence and offline policy results.
