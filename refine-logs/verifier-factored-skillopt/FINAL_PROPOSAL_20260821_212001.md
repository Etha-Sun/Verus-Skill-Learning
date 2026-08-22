# Research Proposal: V-FACE

## Verifier-Factored Admission of Executable Atomic Proof Skills

**Date**: 2026-08-21
**Status**: design-frozen for Phase 0; empirical verdict REVISE
**Independent review**: 8.00/10

## Problem Anchor

- **Bottom-line problem**: 从已有 SkillOpt self-evolution 与多模型 test 失败轨迹出发，找出 SkillOpt 在 Verus task-specific 场景中的机制性缺陷，并形成可执行、可检验的改进路线。
- **Must-solve bottleneck**: whole-skill、whole-trajectory 的单一成功分数无法区分环境有效性、局部 proof action 有效性、模型是否采用以及 exposure 后行为漂移。
- **Non-goals**: 不把 ordinary retrieval、abstention、proof-state schema 或 multi-file packaging 单独包装成创新；不在已查看 test-20 上选方法；不在无 prospective 证据时声称 solved-rate、token-efficiency 或 causal-credit 增益。
- **Success condition**: Build-only typed executable evidence 能在独立 checkpoints 上，以非退化 coverage，比 observational 或 generic trajectory replay 更安全地预测 card exposure 的 harm/benefit。

## Evidence-Grounded Diagnosis

历史 SkillOpt 的 9 个完整 skill 候选在 selection 上最好为 15/20，task-wise oracle union 仍为 15/20。因而在已有完整文档之间加 router 没有 headroom。多模型轨迹进一步显示：正确规则可能未被采用，额外 skill 文本可能触发过度展开或替代已有正确 lemma，而 harness-invalid failure 又会污染 optimizer。问题的核心不是“reference 不够多”，而是 **优化单位与归因接口错误**。

三个离线 pilot 给出混合但决定性的方向信号：

- whole-skill routing ceiling：NEGATIVE，oracle headroom 0；淘汰整文档路由。
- structured event compaction：POSITIVE，51.7MB → 97KB、533×、180/180 required-field coverage；只证明接口可构造，不证明语义充分。
- naive near-miss extraction：WEAK，8 个 mixed-outcome task 仅 1 个出现机械可见的 success-only lemma contrast；把 action compiler 提升为 P0 gate。

## One-Sentence Thesis

**V-FACE 冻结少量 typed proof-action templates，在 Build checkpoints 上分别收集 compiler-dependent forced-edit validity 与 randomized card-exposure evidence，并预测相同 template 在独立 Evaluation checkpoints 上的 exposure harm/benefit，而不把轨迹成功或 adoption 当作局部 causal credit。**

## Scope and Contribution

- **唯一候选主贡献**: typed executable formal-proof artifact 是否提供 generic trajectory replay 在等 actor/API budget 下缺少的、可跨 checkpoint 迁移的 admission evidence。
- **Supporting output**: prospective formal-skill admission benchmark 与 forced-validity/exposure-disagreement failure taxonomy。
- **Engineering foundations**: compatibility gate、structured checkpoint compiler、Lynette fidelity、typed hard filter。
- **不是贡献**: counterfactual replay、abstention、contraindication、proof-state retrieval、structured skill contract、通用 causal ground truth。

新颖性目前为 **PARTIAL**。如果 V-FACE 不超过 CAR-like、TRACE-like、forced-only 或 exposure-only baseline，工作必须降格为 benchmark/audit，而不是新 optimizer。

## Artifact Model

### CardTemplate

跨 checkpoint 复用，只包含 family、typed role constraints、trigger matcher、action semantics 与 adoption pattern；不包含 source hash、具体 symbol 或 byte range。

第一阶段只冻结三类：

1. `CALL_EXISTING_LEMMA`：唯一解析现有 lemma 与参数，在 proof-only anchor 插入一个 call。
2. `BIND_EXACT_PREDICATE_AND_CALL`：对 predicate-shape mismatch 建立显式 ghost binding，再调用已解析 lemma。
3. `EXTENSIONAL_TWO_WAY_WITNESS`：对 set/map/view equality 插入固定双向 quantified witness skeleton。

不支持任意自然语言 recipe、induction、temporal bridge synthesis 或多步 workflow。

### CardInstantiation

checkpoint-local object，包含 source hash、stable declaration ID、resolved roles、proof-only anchor、typed edit AST 与静态审计。`instantiate_static(template, public checkpoint features)` 只能返回：

- `NON_INSTANTIABLE(reason)`；或
- 唯一 `STATIC_INSTANCE`。

`NON_INSTANTIABLE` 只进入 compatibility accounting，不能作为 REJECT，不能进入 decisive coverage 或 BENEFICIAL/HARMFUL accuracy。

## Two Interventions and One Observation

### Forced-edit verifier contrast

`execute_forced_edit(STATIC_INSTANCE, private source)` 运行 frozen compiler edit、Verus 与 Lynette，得到：instantiable、fidelity-valid、`improve/unchanged/worsen`。它评价 compiler 产生的 action，不是 card exposure 的 causal effect。

- Build：可以执行并进入 Template evidence。
- Evaluation decision 前：严禁运行、缓存或泄露 forced Verus/Lynette outcome。
- Evaluation decision 后：只允许 post-hoc mechanism analysis。

### Randomized exposure ITT

Primary unit 是 Evaluation checkpoint–CardTemplate pair。每个成功产生 `STATIC_INSTANCE` 的 evaluable pair，core 与 exposure 各运行 3 个独立 replicates，运行顺序在 pair 内随机；actor/model/tool/budget/card token envelope 固定。

令 `S_core`、`S_exposure` 为各自 Lynette-valid Verus success count：

- `BENEFICIAL` iff `S_exposure ≥ 2` and `S_core ≤ 1`。
- `HARMFUL` iff `S_core ≥ 2` and `S_exposure ≤ 1`，或 exposure 独有的同类 fidelity-invalid terminal 在 ≥2 replicates 重复。
- `INCONCLUSIVE` otherwise。

无可控 seed 时不宣称 replicate 配对。Cost 只作为次要终点；hard outcome 相同时使用预注册 ±15% ROPE。

### Adoption telemetry

用 frozen normalized AST/call signature 标为 `yes/no/uncertain`，20% stratified sample 双人校验。它是 post-treatment telemetry，不估计 mediation，不用作 causal label。

## Frozen Admission Rule

对一个 Evaluation `STATIC_INSTANCE`，只使用其 Template 的 Build evidence 与当前 static trigger：

1. Build support <8 valid instances 或 <4 independent tasks → `UNKNOWN`。
2. ≥2 independent forced-worsen checkpoints、≥2 independent replicated HARMFUL exposure tasks、或可复现 fidelity-invalid exposure mode → `REJECT`。
3. 只有同时满足以下条件 → `ADMIT`：所有 Build forced edits fidelity-valid；≥2 forced-improve 且 0 worsen；Build exposure 至少 1 BENEFICIAL、0 HARMFUL；Evaluation static trigger exact-match。
4. 其他 → `UNKNOWN`。

`UNKNOWN` 不注入，也不重编码为正确 reject。Decisive coverage 的分母只包括 evaluable pairs：

`coverage = (#ADMIT + #REJECT) / #STATIC_INSTANCE pairs`。

Primary claim 要求 coverage ≥40%；否则直接判 non-deployable/claim fail。

## Phase-0 Compiler Gate

从全新 Build pool 盲取 30 个 eligible checkpoints；两名标注者冻结 family、roles 与 allowed region 后运行 compiler。必须同时满足：

- ≥18/30 可实例化；
- 可实例化 edit 中 ≥90% 经盲审语义符合 template；
- 100% Lynette fidelity-valid；
- 越界/无关 edit ≤5%；
- identity/mismatch control 不系统性改善目标 error。

失败就停止 optimizer/retrieval/admission 开发，输出 extractor failure taxonomy。该 gate 只证明 compiler feasibility，不支持论文性能 claim。

## Prospective Benchmark

### Data firewall

- 已用 40 train + 20 selection：只作 retrospective hypothesis/case study。
- Build：来自当前 SkillOpt 未使用的公开 pool，先做 source hash、declaration、near-duplicate 与 lemma-family audit。
- Evaluation：source/outcome/trajectory 对方法作者封存；决策前只暴露 data steward 生成的 non-outcome static features。
- 现有 test-20：永久 post-hoc diagnostic。

### Equal-budget baselines

共享 frozen Template pool、Evaluation pairs、actor 与 actor/API envelope：whole-skill outcome、atomic observational、CAR-like step replay、TRACE-like context attribution、forced-only、exposure-only、V-FACE。CAR/TRACE 必须做 protocol-faithful reimplementation，不能只引用名字。

主公平性约束是相同 actor rollouts、requests/token cap；另外独立报告 Verus/Lynette invocations、CPU seconds 与 end-to-end wall time。V-FACE 的 CPU checks 不能隐藏，也不能兑换为额外 LLM calls。

### Metrics and claim gate

- Primary: HARMFUL recall、false-admission rate、balanced accuracy on conclusive evaluable pairs。
- Coverage: ADMIT/REJECT/UNKNOWN proportions；预注册 40/60/80% risk–coverage table。
- Safety: retained-success regressions、repeated fidelity invalid。
- Secondary: valid success、cost ROPE、resource cost per correct decision、adoption telemetry。

在 coverage ≥40% 且同 actor/API envelope 下，V-FACE 必须降低 false admission、保持或提高 HARMFUL recall，并且优势不能由 atomic observational、forced-only 或 exposure-only 单独解释。否则拒绝 improved-admission claim。

## Resource Plan

- Inventory/contamination audit：CPU/read-only metadata。
- Compiler gate：CPU-only，30 Build checkpoints，预计 1–2 天。
- Prospective dry run：6–10 Build tasks、2 replicates，≤2 GPUh。
- Bounded admission pilot：只有前两关通过才运行；后续总 GPU 预算≤8 GPUh。
- Final sealed evaluation：不属于当前 idea-discovery run，必须另行预注册。

## Final Verdict

**Design-frozen for Phase 0; empirical verdict REVISE.** 继续加入 retriever、RL、更多 patch family 或 optimizer 只会降低可解释性。下一步是 inventory/contamination audit 与 compiler gate；在它们通过前，不宣称 causal skill credit、new optimizer、solved-rate gain 或 token-efficiency gain。
