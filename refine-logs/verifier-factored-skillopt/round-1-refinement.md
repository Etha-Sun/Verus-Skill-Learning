# Round 1 Refinement

## Problem Anchor

- **Bottom-line problem**: 从已有 SkillOpt self-evolution 与多模型 test 失败轨迹出发，找出 SkillOpt 在 Verus task-specific 场景中的机制性缺陷，并形成可执行、可检验的改进路线。
- **Must-solve bottleneck**: 当前 whole-skill、whole-trajectory、单一成功分数的优化，把“知识是否正确”“模型是否采用”“注入是否引发无关行为漂移”“任务/工具链是否有效”混在一起，因而无法给局部 skill 内容可靠归因，也无法安全地决定何时注入。
- **Non-goals**: 不把普通 multi-file RAG、proof-state retrieval、contraindication、abstention 或结构化日志单独包装成创新；不在已经人工查看的 test-20 上选方法或阈值；现阶段不声称提升 solved rate 或 token efficiency。
- **Constraints**: 原始与 sealed 数据只读；开发证据只能来自历史 train/selection 与新建、未查看的 development split；主方法最多一个核心机制，检索器保持简单；先做 CPU verifier replay 与小规模 rollout，GPU 预算不超过 8 GPUh。
- **Success condition**: 在全新 development checkpoints 上，原子 skill 的分解式干预评估比 observational success/failure attribution 更准确地识别有益、无益和有害 artifact；冻结后在新的 sealed tasks 上减少 harmful admission / retained-success regression，且不以更多无效 token 或超时换取结果。

## Anchor Check

- 原始瓶颈仍是 SkillOpt 对 formal proof skill 的归因单位错误，而不是缺少更大的检索系统。
- 修订后先验证 `card → executable local edit` 是否成立，再研究 admission；这比上一版更直接地攻击 bottleneck。
- 拒绝把新 retriever、RL router 或 whole-plugin evolution 加入主方法，因为它们会绕开当前最危险的不可行假设。

## Simplicity Check

- **唯一主贡献**: typed atomic proof artifact 的 prospective verifier-intervention/admission benchmark。
- **删除**: 第一阶段 runtime retriever、logistic calibration、复杂 contraindication 学习、actor-conditioned realization、Brier/ECE。
- **保留为 telemetry**: adoption，不把它当因果中介效应。
- **保留为工程基础**: compatibility gate 与 structured checkpoint compiler，不列为创新。

## Changes Made

1. 把“三效应分解”改为 `forced-edit validity + randomized exposure ITT + adoption telemetry`，只把 exposure ITT 称为 card 的随机化总行为效应。
2. 冻结三类 typed patch DSL 与 deterministic compiler contract；optimizer 在 gate 前不参与 action family 发明。
3. 将核心任务改成 prospective admission prediction：build evidence 预测完全独立 evaluation checkpoints 的 replicated exposure sign。
4. 把 runtime retrieval 与 end-task gain 降为 compiler/benchmark 通过后的条件性第二阶段。
5. 将 1/8 negative pilot 变成明确 stop gate，而不是为复杂 extractor 辩护。

## Revised Proposal

# Research Proposal: V-FACE — Prospective Evaluation of Executable Atomic Proof-Skill Artifacts

## Technical Thesis

**V-FACE 将一小类原子 proof skill 编译为局部、可审计的 typed source edits，并检验 build-time verifier/exposure 证据能否在独立 checkpoints 上做出比 observational trajectory attribution 更可靠的 artifact admission 决策。**

V-FACE 首先是评估与准入协议，不是新的 retrieval paradigm，也不预设自己是通用 optimizer。若 compiler 或 prospective admission 失败，研究应停止在 benchmark/audit 结论。

## Why This Is the Correct Unit of Study

历史轨迹说明 whole-skill reward 同时混入环境无效、proof action 无效、正确动作未采用和 exposure 后过程漂移。9 个完整 skill 的 oracle union 仍不超过最佳单体 15/20，否定了在现有完整文档之间路由；朴素原子抽取仅 1/8 成功，则说明 card 可执行性而不是 router 是当前首要风险。

## Frozen Typed Patch DSL

第一阶段只支持三类、由人工在 build split 上冻结的 action family：

1. **CALL_EXISTING_LEMMA**
   - 前置：目标 proof block 内存在 hole/error anchor；fully-qualified lemma 与参数都能从当前 scope 唯一解析；调用不修改 executable/spec body。
   - 操作：在唯一 anchor 处插入一个 lemma call statement。
   - adoption signature：resolved callee ID + normalized argument-role pattern。

2. **BIND_EXACT_PREDICATE_AND_CALL**
   - 前置：verifier error 指向 predicate-shape mismatch；目标 lemma 的 predicate parameter 与当前 obligation 可通过 alpha-renaming/显式 closure 唯一绑定。
   - 操作：插入一个 ghost predicate binding，再插入一个已解析的 lemma call；禁止改变 lemma statement 或目标 spec。
   - adoption signature：binding AST shape + resolved callee ID。

3. **EXTENSIONAL_TWO_WAY_WITNESS**
   - 前置：目标是 set/map/view extensional equality，双方 membership/index expression 可解析，且 proof region 允许 ghost assertions。
   - 操作：插入固定的双向 quantified witness skeleton；只允许填充从当前目标 AST 派生的左右表达式与已解析 symbols。
   - adoption signature：两个方向的 normalized quantified AST patterns。

不在第一阶段支持任意自然语言 proof recipe、induction、temporal bridge synthesis 或多步 workflow。这些只有在三类 compiler 通过后才可能扩展。

### Card and Edit IR

```yaml
card_id: string
family: CALL_EXISTING_LEMMA | BIND_EXACT_PREDICATE_AND_CALL | EXTENSIONAL_TWO_WAY_WITNESS
trigger_matcher:
  error_family: enum
  goal_ast_pattern: normalized AST
bindings:
  - role: callee | predicate | lhs | rhs | witness
    symbol_id: fully-qualified ID
    type: normalized Verus type
anchor:
  source_hash: sha256
  proof_block_id: stable declaration ID
  insertion_range: byte range
edit_ops:
  - insert_typed_statement
allowed_region: proof-only byte range
adoption_signature: normalized AST/call pattern
expected_local_delta: error family or hard pass
provenance: build checkpoint IDs only
```

### Deterministic Compiler Contract

给定 `(checkpoint, card)`，compiler 只允许一个结果：

- `NON_INSTANTIABLE(reason)`：hash/anchor 不匹配、symbol 不唯一、type/ghost mode 不合法、family precondition 不满足；不运行 exposure。
- `COMPILED(edit, audit)`：所有 binding 唯一、edit 只触及 proof-only allowed region、normalized AST 与 card family 一致。

执行顺序：

1. 校验 source hash、declaration ID、error anchor。
2. 对所有 symbol 做 fully-qualified resolution 与 type/ghost-mode 检查。
3. 从固定 family template 生成 typed AST；optimizer 不能写任意 source text。
4. 生成临时 candidate，验证 diff 只在 allowed region。
5. 运行 parser/Verus 与 Lynette；任何 source/spec/executable fidelity 改变均为 `FIDELITY_INVALID`。
6. 保存 compiler audit：bindings、normalized edit AST、diff hash、verifier delta。

Card 的自然语言说明不参与 forced edit；因此 forced contrast 明确依赖 frozen compiler，而不是被误称为“card 的因果效用”。

## Two Interventions and One Observation

### Forced-edit verifier contrast

`δ_force(s,c)` 比较 frozen compiler 生成的 edit 与 identity edit 在同一 checkpoint 上的 Verus+Lynette 结果。标签仅为：

- `instantiable / non-instantiable`
- `fidelity-valid / invalid`
- verifier delta `improve / unchanged / worsen`

它评价 compiler-instantiated action 的技术效果，不评价 actor 看到 card 后会怎样。

### Randomized exposure ITT

对固定 actor/tool/budget/seed schedule，随机分配 `core only` 或 `core + one card`。预注册 outcome 为：

1. Lynette-valid 且 Verus hard success within budget；
2. retained-success regression；
3. valid-run cost（time、tokens、verifier attempts）作为次要终点。

`τ_exp` 是 exposure 的 intention-to-treat 总效应。只在 replicated evaluation rollouts 上标为 `beneficial / harmful / inconclusive`，并报告区间；不把单次 rollout 当 label。

### Adoption telemetry

用 frozen adoption signature 对 exposed trajectory 的 source diffs 判定 `yes / no / uncertain`，在 20% sample 上双人盲审。Adoption 只用于解释和错误分析，不作为被识别的 causal mediator，不用 `E[Y|E=1,A=1]` 宣称 adoption effect。

## Prospective Admission Benchmark

### Splits

- **Retrospective-only**: 已用过的 40 train + 20 selection 只用于形成 hypothesis 和历史 case study。
- **Build**: 从从未用于当前 SkillOpt 的公开任务中由数据 steward 选取，按 declaration/lemma-family 隔离；用于冻结三类 DSL、生成 cards、收集有限 action/exposure evidence。
- **Evaluation**: task IDs、sources、trajectories 对方法作者封存；card、compiler、阈值和 replay budget 冻结后才揭示。每张被评估 card 必须在 evaluation 中有同 family 但不同 declaration/lemma context 的 eligible checkpoints。
- **Final sealed**: 只有 compiler 和 prospective admission 两个 gate 都通过后才建立；现有 test-20 永久只作 diagnostic。

### Prediction target without circularity

每种方法只能使用 Build evidence，为每个 frozen card 输出 `ADMIT / REJECT / UNKNOWN` 及理由。Evaluation 上独立、重复的 randomized exposure ITT 形成 scoring target；这些 rollout 不参与 card 生成、阈值或 admission。任务不是复述完整 replay，而是预测跨 checkpoint 的 exposure sign。

### Equal-budget baselines

1. Whole-skill selection outcome（当前 SkillOpt）。
2. Atomic observational contrast（SkillGen-style success/failure mining）。
3. Budget-matched generic step replay/TRACE-CAR-style attribution。
4. Forced-edit validity only。
5. Exposure evidence only。
6. V-FACE：forced validity + build exposure evidence；adoption 只作 telemetry。

所有 baseline 使用相同 card pool、actor、evaluation tasks、token/rollout budget。Atomicization 和 abstention 不得只给 V-FACE。

### Placebos and controls

- **Exposure placebo**: 与目标 card token 长度和格式匹配、但来自不相容 goal/operator family 的真实 card；hard trigger 应判不兼容。
- **Paraphrase control**: 同一 card 的语义等价短改写，检验收益是否只是 wording。
- **Identity forced control**: compiler pipeline 完整运行但输出空 proof-region edit，校验工具/缓存影响。
- **Mismatch forced control**: 只在 type-correct、fidelity-valid 时执行不相关 family edit；若不可合法实例化则记录 non-instantiable，而不是伪造坏 patch。

### Metrics and decision rule

- Primary: harmful-admission recall、false-admission rate、balanced sign accuracy on conclusive evaluation ITT cases。
- Secondary: UNKNOWN coverage、retained-success regressions、valid success、paired time/token/attempt overhead、replay cost per correct admission。
- Statistics: card/checkpoint clustered bootstrap 与 exact binomial intervals；不报告 Brier/ECE，除非未来方法输出概率。
- Claim gate: 在相同 budget 下，V-FACE 必须同时降低 false admission、保持或提高 harm recall，并且优势不能被 `atomic observational` 或 `forced-only` baseline 解释；否则核心 claim rejected。

## Phase 0 Compiler Go/No-Go

在不触碰 Evaluation 的前提下，从全新 Build pool 盲取 30 个 eligible checkpoints：

1. 两名标注者独立确认 family、symbol bindings 与 allowed region；分歧由预定义 adjudication 解决。
2. 冻结三类 compiler 后生成 edit。
3. 必须同时满足：
   - ≥18/30 可实例化；
   - 可实例化 edit 中 ≥90% 经盲审语义符合 card；
   - 100% Lynette fidelity-valid；
   - 越界/无关 edit ≤5%；
   - identity/mismatch control 不系统性改善目标 error。
4. 任一关键门槛失败：停止 retrieval/optimizer/admission 开发；输出 extractor failure taxonomy 与 benchmark design。

## Conditional Phase 1 and Phase 2

- **Phase 1**: compiler 通过后，建立 prospective admission benchmark；只检验 attribution/admission，不部署 runtime retrieval。
- **Phase 2**: 只有 V-FACE 超过等预算 baselines 后，才把 admitted cards 接入已有的 invisible-search/top-one-injection runtime；retrieval 只用 hard typed filter + weighted overlap，不作为贡献。
- **Phase 3**: 只有 development admission gate 通过后，才在新的 sealed tasks 比较 core、monolithic SkillOpt、atomic observational 与 V-FACE；主要终点仍是有效成功、回归和有害注入，不是 IG。

## Novelty Boundary

V-FACE 不声称发明 counterfactual replay、abstention、proof-state retrieval、structured skill contract 或 verifier-guided search。唯一待验证的增量是：**typed executable proof artifact 允许把“动作在该状态是否有效”与“展示 artifact 的总行为效应”分开测量，并且这种 build-time 证据是否改善跨 checkpoint 的 prospective admission。**

若它不超过 generic replay/observational baselines，结论必须是 negative audit，而不是新 optimizer。

## Compute and Stop Rules

- Compiler gate: CPU-only，30 checkpoints，预计 1–2 天。
- Benchmark dry run: 6–10 Build tasks、2 seeds，≤2 GPUh。
- Bounded pilot: 只在 dry run 通过后，最多 3 个 pilot，总计 ≤8 GPUh。
- 不运行或查看现有 test-20；不在当前阶段启动 final sealed evaluation。

## Current Verdict

方法规格已足以进入 **compiler feasibility gate**，但研究结论仍是 **REVISE**。没有 compiler/prospective evidence 前，不宣称新颖 optimizer、solve-rate gain、token gain 或 causal skill credit。
