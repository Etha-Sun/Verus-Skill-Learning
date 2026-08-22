# Idea Discovery Report: SkillOpt × Verus Failure-Driven Redesign

**Direction**: 基于已有 self-evolution 与多模型 test fail cases，寻找 SkillOpt 在 task-specific formal verification 中最值得做的改进
**Date**: 2026-08-21
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline
**Evidence status**: retrospective diagnosis complete; three offline pilots complete; prospective method evidence not yet available

## Executive Summary

最重要的结论不是“SkillOpt 需要更多 reference”，而是：**SkillOpt 在我们场景中的首要瓶颈是错误的学习与归因单位**。它把整篇 `SKILL.md` 当 action、把整条 stochastic trajectory 的最终成功当 reward，于是无法区分：规则本身是否正确、模型是否采用、额外 context 是否把搜索带偏、以及任务是否因 harness/tooling 本就无效。

这解释了一个表面矛盾：S1/S2 中存在正确的 contract-first、exact predicate、extensional witness 指导，但同一模型仍可能不执行它，或因额外文本改走更长、更差的路线。已有 9 个完整 skill 候选的 selection oracle union 仍是 15/20，与最佳单体相同，直接否定了“先在完整文档之间做 router”这条近路。

本轮推荐的不是一个更复杂的 retriever，而是 **V-FACE**：先冻结三类可执行 typed proof-action template，区分 compiler-dependent forced-edit validity、随机化 card-exposure ITT 与 adoption telemetry，用 Build-only evidence 预测独立 checkpoint 上是否应当暴露 card。独立 novelty review 只把它评为 PARTIAL；四轮方法评审从 6.1 提升到 8.0，但最终仍是 “design-frozen for Phase 0 / empirical REVISE”。真正的下一步是 30-checkpoint compiler gate；不过 gate 就停止，不继续堆 optimizer 或 retrieval。

## Evidence Boundary

- 已查看 test-20 的 outcome 与 trajectory，所以它现在只能作 post-hoc diagnosis，不能再作方法选择、阈值校准或 confirmatory evaluation。
- 已用过的 40 train + 20 selection 只作 retrospective hypothesis generation。
- 信息增益不是本研究主终点。
- 所有数值均来自现有 run artifacts；本轮没有修改 raw/sealed data，没有启动 GPU/live actor experiment。
- 当前不声称 V-FACE 提高 solved rate、token efficiency 或提供 causal ground truth。

## What the Existing Experiments Actually Say

### Epoch-level behavior

Self-evolution 的主要 selection 分数为：S0 13/20、E1 14/20、E2 12/20、E3 15/20、E4 14/20；slow/repair 候选为 13、13、12、14。所有 9 个候选的 oracle union 仍为 15/20。E2 slow 虽获得一个新解，却让三个 retained successes 跨过 600 秒边界；所有 observed selection transition 都与 timeout boundary 强相关。

这意味着 whole-skill gate 有两个结构性缺陷：

1. 不能给新增 clause/card 局部 credit；一个好 bridge 与一个坏 workflow bias 被绑在同一 acceptance decision 中。
2. selection 只看最终 hard count 时，会把“新解 + 多个 retained timeout”压成一个粗分数，不能形成负适用域。

Optimizer 输入还曾达到 1.06M 与 1.90M characters；一次外部化 trace 后降到约 341K/921K。这说明 raw trajectory flooding 本身会改变 optimizer 可用性，但压缩不是研究贡献。

### Cross-model test matrix

80 个 model×task units 的 blank/S1/S2 pattern 为：`SSS=46`、`UUU=24`、`SUS=3`、`SSU=1`、`USS=2`、`UUS=2`、`USU=2`；只有 10/80 units 改变最终状态。

| Actor | Blank | S1 | S2 | Oracle among three | Interpretation |
|---|---:|---:|---:|---:|---|
| GPT-5.6 Sol | 18 | 17 | 17 | 18 | skill 带来一处恢复也带来一处新 regression；整体不增反降 |
| DeepSeek V4 Pro | 14 | 14 | 14 | 14 | 能力集合完全不变，效率方向高度异质 |
| GLM-5.3 | 15 | 15 | 16 | 16 | skill 补上组合性 semantic bridge，但接近 timeout |
| Qwen3.8-27B BF16 | 3 | 5 | 6 | 8 | 有 selective headroom，但同一 S2 也破坏 S1 的两个解 |

该表只支持“effect actor-conditional 且非单调”的诊断，不支持从 test 学 router。

## Concrete Failure-Trajectory Analysis

### A. Knowledge was present, but the actor did not realize it

| Case | Exact trajectory difference | Mechanism diagnosis |
|---|---|---|
| Qwen `AL__push_to_set_seq_to_set_insert` | S1 仅调用一行现有 `lemma_push_to_set_commute`，clean retry 207.08s 通过；S2 写 pointwise set extensional proof，卡在 `push` membership，未回退到现有 contract | card/knowledge 可能有效；S2 failure 是 strategy selection/adoption，不应给 contract-first rule 负信用 |
| GLM get/delete matching pod | blank 287.73s 用 delete/update branches + 双向 membership witnesses 通过；S1 只 assert set equality、215.98s 失败；S2 用 133 行补齐两个方向和 finite-cardinality bridge、301.53s 恢复 | S1 已有 extensional guidance 但未执行；outcome label 混淆“规则缺失”与“规则未被采用” |
| Qwen `AL__always_to_current` | blank 238.28s 调 `execution_equality` 通过；S1 直接 assert suffix equality，600s 失败；S2 恢复 lemma，211.32s 通过 | 不是新知识，而是对已有 bridge 的选择方差 |
| Qwen fold-left | S1 用结构归纳 + `lemma_fold_left_split`，520.05s 通过；S2 留空/超时 | S2 并未删除 induction 指导；新增文本不是单调 superset，trajectory behavior 才是实际 treatment |

### B. Exposure changed proof-search control, not just knowledge

| Case | Exact trajectory difference | Mechanism diagnosis |
|---|---|---|
| GPT `resource_match` | blank 300.90s 与 S1 只处理两个困难 branch并复用 domain lemmas；S2 展开全部 `Step` variants，把 APIServer/Controller 留为 bare assertions，631.66s 超时 | 最强 skill-conditioned search interference；S2 甚至违背自身 representative-arm/checkpoint 规则 |
| GPT temporal invariant | blank 90 行、519.19s，通过 state requirements/equivalence/`invariant_n!`；S1 改成 141 行手工 Step split 并超时；S2 用 exact `implies` + named `partial_spec`，488.79s 恢复 | 同一 skill lineage 既可诱发过度展开，也可促进最小 bridge；whole-document scalar credit 无法区分局部 clause |
| GPT/GLM pod listing | GPT blank/S1/S2 都成功，时间 339.54/479.03/464.71s；pre/all commands 10/26、14/34、34/56；failed Verus 8/14/13；input tokens 1.420M→2.402M/2.449M | 读取 skill 本身只晚约 6–7s，主要开销来自更保守的 decomposition/micro-iteration；skill 是 workflow perturbation |
| GLM serialization injective | blank/S1 调 sibling serialization lemma 通过；S2 改走 vector injectivity，只得到 `to_vec().view_equal`，未 bridge 到 `self.view_equal` | “exact/extensional”局部原则压过更早的 contract-first；策略优先级需要 exposure-level 评估 |

### C. Skill can supply a missing composition to a weaker actor

GLM pod-listing blank 在 602.49s 留下不完整 uniqueness/cardinality proof；S1 558.54s、S2 502.87s 通过。成功链条是：equal Pod views → metadata → name/namespace/kind → ObjectRef → resource key → stored object → no-duplicates。这里 skill 的价值不是某一个 lemma 名字，而是把多个已有 contract 组合为 typed bridge chain。

Qwen `AL__leads_to_by_borrowing_inv` 中 blank/S1 只实例化 premises，未显式建立 `p.and(inv)`；S2 命名 `p_and_inv` 并按 antecedent/suffix 建立局部 invariant，最终通过。这是 exact predicate + named bridge 的可信正例。

Qwen `make_send_only_event_results` 的 blank 把 `ghost(...)` 当字段表达式而 type error；S1/S2 直接构造 `EventResults { recvs, clocks, sends, ios }`，115.92/166.53s 通过。有效模式是读返回 postcondition 后构造逐字段匹配的 ghost value。

### D. More generic scaffolding cannot replace domain semantics

DeepSeek 在 temporal invariant task 的 blank/S1/S2 全失败；S2 把 skeleton 从约 45 行扩到 99 行、requests 从约 30 增到 42，仍缺 domain-specific temporal implication。这反驳“再加一层通用 workflow checklist 就能解决”的想法。真正缺少的是可绑定的 domain bridge，且它是否应暴露必须按 checkpoint 判断。

### E. Tool/data validity contaminates learning if not separated

- 8/40 train 与 1/20 selection tasks 因 macro/crate/wrapper incompatibility 无效，却曾以 proof failure 进入 optimizer evidence。
- DeepSeek get/delete 的一次 S2 candidate 同时通过 Verus+Lynette，但 Responses stream `IncompleteRead`、无 clean terminal event；按预注册规则必须是 `V0_INVALID`，clean retry 又失败。它说明 strategy 可能有价值、运行又不具有效度，不能把 invalid success 当性能，也不能简单给 strategy 正/负信用。
- Qwen `values_agree` 的 blank 把 `int` cast 放进 executable decreases，S1 又有 parser 标点错，S2 才写合法 invariant/decreases；parser/type/ghost-mode 失败需要与 semantic proof failure 分层。

## Root-Cause Taxonomy

1. **Compatibility contamination**：无效 harness/provider/tool terminal 被当 proof evidence。
2. **Wrong credit unit**：整篇文档接受/拒绝，无法定位 clause/template。
3. **Action validity uncertainty**：自然语言 rule 能否在当前 state 编译成合法 proof edit 未知。
4. **Incorporation failure**：有效 action 已描述，但 actor 没有执行。
5. **Exposure/control drift**：额外 context 改变 decomposition、策略优先级和迭代次数。
6. **Missing domain bridge**：通用规则无法合成 task-specific semantic chain。
7. **Budget-bound phase transition**：大量差异由是否跨越 600s 决定，单次二元 outcome 不稳定。
8. **Actor-conditional realization**：同一文本对 GPT、GLM、Qwen 的收益与干扰方向不同。

核心判断：1 是必须修的 hygiene；2–5 是 V-FACE 的研究对象；6 是未来 reference/card corpus 的内容来源；7–8 是评估设计约束。不能把八项都做成一个大系统。

## Three Offline Pilots

### Pilot 1 — Whole-skill routing ceiling: NEGATIVE

- 9 个 monolithic candidates，best fixed 15/20，oracle union 15/20，headroom 0。
- 结论：淘汰 naive whole-document router；必须生成 subdocument intervention 或新 artifact。

### Pilot 2 — Structured trace sufficient statistics: POSITIVE, narrow

- 180 development traces；selected raw evidence 51,692,832 bytes，structured 96,996 bytes，532.94×。
- outcome/timeout/fidelity/hash/Verus/Lynette fields 180/180 覆盖。
- 结论：可避免 million-character optimizer prompt；但 semantic judgment preservation 未证明，需 blinded raw-vs-structured audit。

### Pilot 3 — Naive near-miss constructibility: WEAK

- 8 个 mixed-outcome tasks，success-only unique lemma contrast 仅 1/8，低于预注册 4/8 gate。
- 结论：observational whole-skill trajectories 不能自动给 clause credit；同时 action extraction 是核心可行性风险，必须先 gate。

## Literature Landscape and Novelty Boundary

### Skill evolution and trajectory learning

- [SkillOpt](https://arxiv.org/abs/2605.23904) 与 [GEPA](https://arxiv.org/abs/2507.19457) 已覆盖 trajectory/reflection-driven skill or prompt evolution。
- [SkillGen](https://arxiv.org/abs/2605.10999) 已用成功/失败轨迹生成 skill，并做 same-instance intervention。

### Retrieval, contracts and abstention

- [SRA](https://arxiv.org/abs/2604.24594) 已把 retrieval/incorporation/end-task 分开，并指出 when-to-load bottleneck。
- [RSCB-MC](https://arxiv.org/abs/2604.27283) 已做 risk-sensitive memory routing 与 abstention。
- [Anything2Skill](https://arxiv.org/abs/2606.09316) 的 skill contract 已包含 invocation condition、contraindication、evidence 与 confidence。
- [ERSkill](https://arxiv.org/abs/2608.12720) 已联合演化 retrieval skills 与 router，并有 double frontier。

因此“reference + router + abstain”不是新颖 thesis。

### Attribution and executed replay

- [Causal Agent Replay](https://arxiv.org/abs/2606.08275) 已做 agent-step do-intervention 与 forward replay。
- [Credit Without Ground Truth](https://arxiv.org/abs/2608.19760) 在 executed replay 下发现常见 step credit 接近 chance，且 causal contribution 稀疏。
- [TRACE](https://arxiv.org/abs/2608.09153) 已对 prompt/skill/KB/tool 做 trajectory attribution 与 context repair。
- [WML/WGSO](https://arxiv.org/abs/2607.20999) 已做 workflow node/mechanism attribution、最小 edit target 与 scoped third-party skill reuse。

所以不能声称“首个 causal skill optimizer”或“verifier 提供 causal ground truth”。

### Formal proof retrieval/search

- [RAG-Verus](https://arxiv.org/abs/2502.05344) 已做 repository-level Verus retrieval。
- [PROMISE](https://arxiv.org/abs/2604.05399) 已做 structural proof-state transition mining/retrieval。
- [LeanDojo/ReProver](https://arxiv.org/abs/2306.15626) 与 [COPRA](https://arxiv.org/abs/2310.04353) 已覆盖 premise retrieval 与 verifier-guided proof search。

因此 proof-state fingerprint 与 typed bridge retrieval 只能是系统部件。V-FACE 唯一可能的新意，是把可执行 artifact 的 forced technical validity 与 card exposure 总行为效应分开，并检验 Build evidence 能否跨 checkpoint 支持 prospective admission。

## Ranked Ideas

| Rank | Idea | Local signal | Novelty | Status |
|---:|---|---|---|---|
| 1 | **V-FACE typed artifact admission** | whole-router negative + compiler risk exposed | PARTIAL 5/10；review 8.0 | **RECOMMENDED for Phase 0 only** |
| 2 | Anti-Expansion Governor | GPT over-expansion、timeout boundary 强 | 中低；workflow control 已拥挤 | BACKUP after Phase 0 |
| 3 | Typed Bridge-Chain Miner | GLM pod-listing、Qwen named bridge 正例 | 中低；接近 PROMISE/RAG-Verus | BACKUP content source |
| 4 | Actor-Conditional Skill Realization | test oracle headroom mainly Qwen；GPT harm | 低；像 model-specific prompting | DIAGNOSTIC ONLY |
| 5 | Compatibility Sentinel | 8/40 + 1/20 invalid contamination | 工程必要、非论文创新 | REQUIRED HYGIENE |
| 6 | Negative-Utility Domain Miner | retained-success timeout 与 wrong-route cases | 与 contraindication/WGSO 重叠 | SUPPORTING ONLY |
| 7 | Proof-State Delta Cards | formal representation 合理 | 与 PROMISE/proof-state retrieval 重叠 | MERGED INTO V-FACE DSL |
| 8 | Retain-Success Frontier Bandit | E2 negative transfer 明确 | 与 ERSkill double frontier/RSCB 重叠 | DEFER |
| 9 | Near-Miss Contrastive Optimizer | naive extractor 1/8 | 自动构造尚不可行 | HALTED BY PILOT |
| 10 | Whole-skill router / ordinary reference RAG | oracle headroom 0；prior art crowded | 无 | ELIMINATED |

## Why V-FACE Wins Despite Partial Novelty

V-FACE 不是分数最高的“漂亮故事”，而是唯一直接把已有轨迹中的不可辨识性变成可证伪 gate 的方案：

- 它能区分“一行 lemma 技术上有效但模型没采用”与“lemma 本身不适用”。
- 它不会把 forced edit 的 verifier 结果夸成 card causal effect。
- 它把 1/8 negative pilot 变成 stop rule：compiler 不过就不做 retrieval。
- 它允许最后得到有价值的 negative result：generic replay 已足够，或 formal typed evidence没有跨 checkpoint 信号。

## Refined Proposal and Review

- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Score history: `refine-logs/verifier-factored-skillopt/score-history.md`
- Review progression: 6.10 → 7.10 → 7.70 → 8.00
- Final review verdict: **REVISE empirically; design-frozen for Phase 0**
- Novelty verdict: C1 PARTIAL 5/10；contraindication/abstention 与 checkpoint representation 单独 REJECTED。

## Recommended Next Action

先做 inventory/contamination audit，然后只实现 `CardTemplate → instantiate_static → execute_forced_edit` 的三类 compiler，运行 30-checkpoint CPU gate：≥18/30 instantiable、≥90% semantic correctness、100% Lynette fidelity、越界≤5%。

不要先实现 runtime retriever。只有 compiler gate 与 prospective dry run 都通过，才接回已有的 invisible-search/top-one-injection 设计；现有 test-20 不再参与任何 decision。
