# Round 2 Refinement

## Problem Anchor

- **Bottom-line problem**: 从已有 SkillOpt self-evolution 与多模型 test 失败轨迹出发，找出 SkillOpt 在 Verus task-specific 场景中的机制性缺陷，并形成可执行、可检验的改进路线。
- **Must-solve bottleneck**: 当前 whole-skill、whole-trajectory、单一成功分数的优化，把“知识是否正确”“模型是否采用”“注入是否引发无关行为漂移”“任务/工具链是否有效”混在一起，因而无法给局部 skill 内容可靠归因，也无法安全地决定何时注入。
- **Non-goals**: 不把普通 multi-file RAG、proof-state retrieval、contraindication、abstention 或结构化日志单独包装成创新；不在已经人工查看的 test-20 上选方法或阈值；现阶段不声称提升 solved rate 或 token efficiency。
- **Constraints**: 原始与 sealed 数据只读；开发证据只能来自历史 train/selection 与新建、未查看的 development split；主方法最多一个核心机制，检索器保持简单；先做 CPU verifier replay 与小规模 rollout，GPU 预算不超过 8 GPUh。
- **Success condition**: 在全新 development checkpoints 上，原子 skill 的分解式干预评估比 observational success/failure attribution 更准确地识别有益、无益和有害 artifact；冻结后在新的 sealed tasks 上减少 harmful admission / retained-success regression，且不以更多无效 token 或超时换取结果。

## Anchor and Simplicity Check

- 仍只研究 formal proof artifact 的 prospective admission，不扩展成通用 skill retrieval。
- 主文只保留 compiler gate 与 admission benchmark；runtime use 和 sealed end-task evaluation 是条件性后续。
- 第一版 template 与 family 由人工冻结；optimizer discovery 不与 compiler/admission 同时评估。

## Changes Made

1. 明确拆分可复用的 `CardTemplate` 与 checkpoint-specific `CardInstantiation`。
2. 冻结 evaluation 的 checkpoint-card conditional estimand、随机化单位与三值 outcome。
3. 给出可复现、故意保守的 `ADMIT / REJECT / UNKNOWN` 规则；全部 UNKNOWN 计作方法失败而不事后放宽。
4. 把 generic CAR/TRACE-style baselines 写成有预算约束的操作协议。

## Revised Proposal

# V-FACE — Typed Proof-Artifact Admission from Prospective Verifier Evidence

## One-Sentence Thesis

V-FACE 冻结少量可执行 proof-action template，在 build checkpoints 上分别收集 compiler-dependent forced-edit validity 与 randomized card-exposure evidence，并预测相同 template 在独立 evaluation checkpoints 上的 exposure harm/benefit，而不把轨迹成功或 adoption 当作局部 causal credit。

## Artifact Abstraction

### CardTemplate: cross-checkpoint reusable object

```yaml
template_id: exact-predicate-call-v1
family: CALL_EXISTING_LEMMA | BIND_EXACT_PREDICATE_AND_CALL | EXTENSIONAL_TWO_WAY_WITNESS
trigger_matcher:
  error_family: enum
  goal_ast_pattern: normalized AST with typed role variables
role_constraints:
  - role: callee
    kind: proof_fn
    type_scheme: normalized signature
  - role: predicate
    kind: ghost_predicate
    type_scheme: normalized signature
action_semantics: family-specific typed AST rewrite over role variables
adoption_pattern: normalized AST/call pattern over role variables
expected_delta_family: verifier error family | hard pass
version: immutable hash
```

Template 不含 source hash、concrete symbol 或 byte range。第一版仅有三类 frozen family，由两名形式化标注者在 Build 上定义；optimizer 不得创造新 family。

### CardInstantiation: checkpoint-local executable object

```yaml
template_id: exact-predicate-call-v1
checkpoint_id: opaque ID
source_hash: sha256
declaration_id: stable ID
resolved_roles:
  callee: fully-qualified symbol ID
  predicate: checkpoint-local normalized AST
anchor: proof-only byte range
compiled_edit_ast: normalized typed AST
compiled_diff_hash: sha256
compiler_audit:
  symbol_unique: bool
  type_valid: bool
  ghost_mode_valid: bool
  locality_valid: bool
```

`instantiate(template, checkpoint)` 只有 `NON_INSTANTIABLE(reason)` 或唯一的 `COMPILED(instance)`。Build evidence 聚合到 Template；每个 Evaluation checkpoint 只根据公开的 non-outcome proof-state features 产生新的 Instantiation。

## Frozen Compiler

Compiler 只支持：已有 lemma call、exact predicate binding + call、双向 extensional witness。它校验 source hash、唯一 symbol resolution、normalized type、ghost/executable legality 与 proof-only locality；用 family template 产生 typed AST，不接收任意 source text。临时 candidate 必须通过 parser/Verus invocation 和 Lynette fidelity。Identity control 完整经过 pipeline 但不改变 proof AST；mismatch control 只有在 type-correct、fidelity-valid 时才执行，否则记为 non-instantiable。

## Estimands and Randomization

### Primary unit

Primary prediction unit 是 **Evaluation checkpoint–CardTemplate pair**。方法在 rollout 前可见 checkpoint 的 frozen non-outcome features 与实例化审计，但不可见 evaluation outcome、trajectory 或任何 exposure result。Card-level population summary 只是按 template 聚合的次要结果。

### Exposure randomization

在每个 eligible checkpoint-template pair 内，生成 3 个 replicate blocks；每个 block 随机决定 `core only` 与 `core + one instantiated card rendering` 的运行顺序。Actor model/version、system prompt、tool versions、600 秒预算、输出预算与 card token budget 固定。若 provider 不支持可控 seed，不宣称 common-random-number pairing；以独立 replicate 和随机顺序估计 ITT，并按 task/template cluster。

### Frozen outcome hierarchy

对每个 condition，先计算 3 replicates 中的 Lynette-valid Verus success count：

- **BENEFICIAL**: exposure 相对 core 至少把 2/3 replicates 从 unsolved 提高到 solved，且没有任何 core-majority-solved → exposure-majority-unsolved regression。
- **HARMFUL**: core 至少 2/3 solved、exposure 至多 1/3 solved；或 exposure 产生重复（≥2 replicates）的 fidelity-invalid terminal，而 core 没有。
- **INCONCLUSIVE**: 其他情况。

Cost 不改变 benefit/harm 主标签。只有当两个条件 hard outcome 完全相同时，才报告次要 cost effect；预注册 practical ROPE 为 wall time、input+output token、verifier attempts 任一中位数相对变化 ±15%。这避免用 cost 覆盖 hard regression。

Adoption 仍是 `yes/no/uncertain` telemetry，在 20% stratified sample 上双人校验；不进入 ITT label。

## Frozen V-FACE Admission Rule

对一个 Evaluation instantiation，决策只用其 Template 的 Build evidence与当前 non-outcome compatibility：

1. 当前 checkpoint 无法唯一实例化、locality/fidelity precheck 失败 → `REJECT`（instance-level incompatibility）。
2. Template 在 Build 中少于 8 个 valid instantiations 或少于 4 个独立 tasks → `UNKNOWN`。
3. Template 在 Build 中出现以下任一稳定 harm → `REJECT`：
   - ≥2 个独立 checkpoints 的 forced verifier delta 为 `worsen`；
   - ≥2 个独立 tasks 出现 replicated HARMFUL exposure；
   - 任一可复现 fidelity-invalid exposure mode。
4. Template 只有在同时满足以下条件时 → `ADMIT`：
   - 所有 Build forced edits 均 fidelity-valid；
   - 至少 2 个独立 checkpoints forced delta 为 `improve`，且 0 个 `worsen`；
   - Build exposure 中 0 个 HARMFUL、至少 1 个 BENEFICIAL；
   - 当前 Evaluation instantiation 通过 exact typed trigger。
5. 其他 → `UNKNOWN`。

`UNKNOWN` 不注入，也不计作正确 reject；报告 coverage。若小样本导致全部 UNKNOWN，V-FACE 失败，不允许事后降低 support threshold。

该规则刻意不是新学习算法；它把研究问题固定为“verifier/exposure evidence 是否能安全跨 checkpoint 迁移”。未来统计模型只能在 benchmark 证明有信号后研究。

## Compiler Go/No-Go

从新的、未用于当前 SkillOpt 的 Build pool 盲取 30 个 eligible checkpoints。两名标注者冻结 family/roles/allowed region 后运行 compiler。必须同时达到：≥18/30 可实例化；其中 ≥90% 语义符合 template；100% Lynette fidelity-valid；越界/无关 edit ≤5%；identity/mismatch 不系统性改善目标 error。失败即停止 optimizer/retrieval，发布 extractor failure taxonomy。

这 30 个 checkpoint 只验证 compiler feasibility，不支持 admission 或论文性能 claim。

## Prospective Admission Benchmark

### Data firewall

- 历史 40 train + 20 selection：只做 hypothesis/case study。
- Build：从未用于当前 SkillOpt 的公开 pool，经 source hash、declaration、near-duplicate 与 lemma-family audit；冻结 templates/compiler/rule 并收集 evidence。
- Evaluation：task/source/outcome/trajectory 对方法作者封存。只有 data steward 输出 eligible pair 的 non-outcome typed features；所有方法提交决策后才运行 exposure replicates。
- 现有 test-20：永久 post-hoc diagnostic，不进入任何 gate。

### Equal-budget baselines

所有方法共享 frozen Template pool、Evaluation eligible pairs、actor 与总 replay calls：

1. **Whole-skill outcome**: 依据当前 SkillOpt 的 selection-level document score，把包含 template 的整文档统一 admit/reject。
2. **Atomic observational**: 从 Build success/failure trajectories 统计 template adoption 与 outcome 的相关差异；不执行新 replay。
3. **Generic step replay (CAR-like)**: 在 Build 中定位首次出现 adoption-signature 的 agent step，预算内 resample/replace该 step并向后 rollout；只使用 task outcome，不看 forced-edit delta。
4. **Context attribution (TRACE-like)**: 用相同局部 trajectory windows 与同等 verifier/tool-call budget，让 attribution model输出 template 的 create/update/reject judgment；不给 typed forced edit。
5. **Forced-only**: 只使用 compiler validity/delta，使用相同 support/harm thresholds。
6. **Exposure-only**: 只使用 Build randomized exposure ITT，使用相同 support/harm thresholds。
7. **V-FACE**: 使用 frozen rule 的 forced validity + Build exposure evidence。

若外部实现无法直接运行，则报告 protocol-faithful reimplementation，并公开 prompt、budget 和差异；不能只用论文名称充当 baseline。

### Metrics

- Primary: HARMFUL recall、false-admission rate、balanced accuracy on conclusive Evaluation pairs。
- Coverage: ADMIT/REJECT/UNKNOWN proportions，UNKNOWN 不做有利重编码。
- Safety: retained-success regressions、repeated fidelity invalid。
- Secondary: valid success、paired cost ROPE、replay calls/cost per correct decision、adoption telemetry。
- Inference: task/template clustered bootstrap；对小计数同时给 exact interval，不把 compiler 30-case gate当功效充分的主实验。

### Claim gate

在严格相同 replay budget 下，V-FACE 必须相对最强 baseline：

1. false admission 更低；
2. HARMFUL recall 不低；
3. coverage 非退化（不能靠全部 UNKNOWN 获得安全）；
4. 增益不能由 atomic observational、forced-only 或 exposure-only 单独解释。

任一不满足，则拒绝“improved prospective admission” claim。若只发现 forced/exposure 系统性不一致，则降格为 formal-skill failure audit/benchmark。

## Contribution Boundary

不声称发明 replay、retrieval、abstention、structured contract、proof-state representation 或因果 ground truth。唯一候选贡献是：**typed executable proof artifacts 是否提供了 generic trajectory attribution 在同等预算下缺少的局部技术证据，并能预测独立 checkpoint 上的 exposure utility。**

## Execution Order and Budget

1. Inventory + contamination audit：只列 task/hash/lemma-family，不读 Evaluation trajectory。
2. Compiler gate：CPU-only，30 Build checkpoints。
3. Benchmark dry run：6–10 Build tasks、2 replicates，≤2 GPUh。
4. Bounded admission pilot：compiler/dry-run 都通过后才做，所有 pilots 合计 ≤8 GPUh。
5. 不启动 final sealed evaluation；它是独立预注册阶段。

## Current Status

**REVISE / READY FOR PHASE-0 FEASIBILITY ONLY.** 方法定义 blocker 已补齐，但新颖性仍为 PARTIAL，且 compiler 与 prospective admission 尚无结果。任何性能、因果或 optimizer claim 都必须等待 gate。
