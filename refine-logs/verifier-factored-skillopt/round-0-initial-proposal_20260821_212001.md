# Research Proposal: V-FACE — Verifier-Factored Evaluation and Admission of Atomic Proof Skills

## Problem Anchor

- **Bottom-line problem**: 从已有 SkillOpt self-evolution 与多模型 test 失败轨迹出发，找出 SkillOpt 在 Verus task-specific 场景中的机制性缺陷，并形成可执行、可检验的改进路线。
- **Must-solve bottleneck**: 当前 whole-skill、whole-trajectory、单一成功分数的优化，把“知识是否正确”“模型是否采用”“注入是否引发无关行为漂移”“任务/工具链是否有效”混在一起，因而无法给局部 skill 内容可靠归因，也无法安全地决定何时注入。
- **Non-goals**: 不把普通 multi-file RAG、proof-state retrieval、contraindication、abstention 或结构化日志单独包装成创新；不在已经人工查看的 test-20 上选方法或阈值；现阶段不声称提升 solved rate 或 token efficiency。
- **Constraints**: 原始与 sealed 数据只读；开发证据只能来自历史 train/selection 与新建、未查看的 development split；主方法最多一个核心机制，检索器保持简单；先做 CPU verifier replay 与小规模 rollout，GPU 预算不超过 8 GPUh。
- **Success condition**: 在全新 development checkpoints 上，原子 skill 的分解式干预评估比 observational success/failure attribution 更准确地识别有益、无益和有害 artifact；冻结后在新的 sealed tasks 上减少 harmful admission / retained-success regression，且不以更多无效 token 或超时换取结果。

## Trajectory-Grounded Technical Gap

### 1. Whole-skill routing is not the missing mechanism

历史 selection 上 9 个完整 skill 候选的得分为 13、14、12、15、14、13、13、12、14；所有候选的 task-wise oracle union 仍为 15/20，与最佳 E3 相同。因而，在现有候选之间增加 whole-document router 没有任何可兑现的 selection headroom。问题不是“没有挑对整篇文档”，而是优化从未生成和验证可组合、可限域的局部 artifact。

### 2. Outcome labels conflate four different causes

当前轨迹至少混合四类信号：

1. **Environment validity**：8/40 train 与 1/20 selection 任务因 macro/crate/wrapper 不兼容而无效，却进入了 proof-failure 总结。
2. **Action validity**：某个具体 lemma/bridge/induction edit 在当前 proof checkpoint 是否使 Verus error set 收缩、通过 Verus、并保持 Lynette fidelity。
3. **Adoption/incorporation**：card 已在上下文中，但 actor 是否真正执行其核心动作。
4. **Exposure-induced control drift**：额外文本是否诱发过度展开、微迭代、替代正确策略或 timeout，即使 card 内容本身正确。

典型证据：

- Qwen 在 `push_to_set` 上用 S1 的单个现有 lemma 成功，而 S2 改走 pointwise extensional proof 后失败；这不是“lemma 知识错误”，而是 strategy selection / incorporation 失败。
- GLM 在 get/delete 的 S1 中已经看到双向 witness 原则，却直接 assert set equality 而失败；S2 用 133 行显式双向证明恢复。规则存在不等于规则被执行。
- GPT 在 `resource_match` 的 S2 中违背自身“只展开代表性 arm”规则，扩展每个 `Step` arm，留下 bare assertions 并在 632 秒超时；这是 exposure 后的过程控制失败。
- GPT 在 pod-listing 三个条件都解出，但 S1/S2 相对 blank 把输入从 1.420M 增到 2.402M/2.449M tokens、失败 verifier 次数从 8 墫到 14/13；skill 主要改变了工作流，而不是只增加知识。
- GLM 在 serialization 的 S2 放弃已有 sibling lemma，改走底层 vector injectivity，最终只得到 `to_vec().view_equal` 而缺少到 `self.view_equal` 的桥；这是检索/策略选择错误。
- DeepSeek 的 S2 在 temporal task 上把 skeleton 从约 45 行扩到 99 行，仍缺 domain temporal implication；更多通用流程没有补上真正的语义桥。

### 3. Observational atomicization is not enough

在 8 个 development mixed-outcome task 上，朴素的“成功轨迹独有 lemma call”抽取只在 1/8 找到干净原子 card。成功/失败对比不能可靠判断某条规则是原因、伴随物，还是根本未被 actor 采用。最近的 executed-replay 研究也表明常见 step-credit signal 可能只追随模型 fluency，而不是 causal contribution。

## Method Thesis

**One-sentence thesis**: V-FACE 不把一次 skill 注入压成单一 reward，而是在 proof checkpoint 上分别测量原子 card 的 forced-action validity、exposure effect 与 observed adoption，再仅用这些执行证据控制 card admission。

这是最小充分改动：保留现有 actor、SkillOpt optimizer、Verus 与 Lynette；只把优化单元从整篇 Markdown 改为带可观测动作签名的原子 card，并把单一 outcome gate 改为分解式 replay protocol。Typed retrieval、contraindication 和 abstention 只是消费评估结果的系统部件，不作为独立创新。

## Contribution Focus

- **Dominant contribution**: 一种面向 formal proof skill artifact 的 verifier-grounded、checkpoint-local、三效应分解评估与准入协议。
- **Supporting contribution**: 一个等预算 attribution-fidelity benchmark，用完整干预表检验 observational、generic replay 与 V-FACE 对 harmful/useful artifact 的识别能力。
- **Explicit non-contributions**: 新 embedding、复杂 router、通用 causal ground truth、通用 agent memory 框架、proof-state retrieval 本身、无回归保证。

## Proposed Method

### Complexity Budget

- **Frozen/reused**: SkillOpt 的 optimizer/actor 接口、Verus verifier、Lynette fidelity checker、现有 trajectory ledger、基础 core skill。
- **New trainable components**: 0 个为默认；card generator 复用现有 optimizer，retrieval 首先使用确定性 typed filtering + weighted overlap。只有在数据量足够时才把冻结特征喂给 logistic/calibration layer。
- **Intentionally excluded**: graph neural retriever、end-to-end RL、multi-agent optimizer、whole-plugin evolution、Shapley over entire trajectories、多个模型联合训练。

### Atomic Proof Card

每张 card 是一个版本化 artifact：

```yaml
card_id: exact-implies-named-closure-v1
trigger:
  error_family: temporal_postcondition
  goal_operators: [implies, always]
  required_symbols: [partial_spec]
contraindication:
  - required lemma or binding is absent
action_template:
  - bind the exact predicate shape
  - invoke the named closure lemma
adoption_signature:
  ast_or_call_patterns: ["partial_spec", "implies"]
expected_local_delta:
  remove_errors: [postcondition]
fallback: restore checkpoint and search a domain bridge
evidence:
  source_split: development-only
  checkpoint_ids: [...]
  action_replay: [...]
  exposure_replay: [...]
status: experimental | admitted | contraindicated | unknown
```

自然语言解释可以存在，但 trigger、action、adoption signature、expected delta 与 evidence 必须机器可读。Card 不是完整 proof，也不被假定忠实代表一个抽象规则；它只是一个可做局部干预的 artifact。

### Structured Checkpoint Compiler

对每次 verifier 调用记录：source/candidate hash、fidelity、elapsed budget、Verus error family 与 location、target AST/ghost mode、in-scope lemma signatures、last edit diff、best checkpoint、tool terminal state。完整原始轨迹保留为只读 provenance，optimizer 默认只看结构化事件和被选中的局部窗口。

现有 180 条 development 轨迹的离线 pilot 将约 51.7MB 选定原文压到 97KB 结构化表（533×），且保留 outcome、timeout、fidelity、hash、Verus/Lynette 字段。这个结果只证明接口可构造；是否保留 optimizer 判断信息必须由 blinded comparison 验证。

### Three-Effect Evaluation

对 development checkpoint `s` 与候选 card `c`，严格区分：

1. **Forced-action validity**：把 `action_template` 实例化为最小 source edit，在同一 checkpoint 上直接运行 Verus+Lynette。得到局部 hard pass、error-set delta、fidelity、runtime。它评价“该动作在此状态是否技术上有效”，不称为 card 的因果效用。
2. **Exposure effect**：使用相同 actor、budget、seed schedule，对 `core only` 与 `core + one card` 做 paired rollout，测量有效成功、回归、time/token 与 verifier attempts 的分布差。它评价“展示这个 artifact 的净行为效应”。
3. **Observed adoption**：用 `adoption_signature` 与 source diffs 判断 exposed rollout 是否采用了 card 的核心动作。它把“正确但未采用”与“采用后仍失败”分开。

由此得到诊断状态，而非一个伪精确标量：

| Forced action | Adoption | Exposure outcome | Diagnosis | Optimizer action |
|---|---|---|---|---|
| 有效 | 高/是 | 改善 | realized utility | 可进入 admission gate |
| 有效 | 低/否 | 无改善 | incorporation failure | 改写/缩短 realization，不否定机制 |
| 有害 | 任意 | 变差或未知 | semantic contraindication | 收窄 trigger 或拒绝 |
| 有效 | 是 | 变差 | control/cost drift | 加 fallback/预算或拒绝 exposure |
| 无法实例化 | 任意 | 任意 | unknown | 不进入库，等待证据 |

这里不宣称 verifier 提供 card-level causal ground truth。它只为 forced edit 提供可执行判定；exposure 仍需多 seed 估计。

### Optimizer Loop

1. **Compatibility gate**：先把 harness/tool/provider invalid 与 proof failure 分开；invalid 只写 data-quality ledger。
2. **Contrast selection**：从相同 error family / obligation shape 的 success、near-miss、regression checkpoint 中选局部窗口，禁止把全部 raw traces塞入 prompt。
3. **Atomic proposal**：现有 optimizer 只允许输出一张或修改一张 card，不重写 core skill。
4. **Action replay**：验证 card 是否可实例化、是否改变 verifier state；invalid 或 unknown 不晋升。
5. **Exposure replay**：在独立 development tasks 上成对运行 core vs core+card，并记录 adoption。
6. **Conservative admission**：只有 useful/harm sign 的置信区间和 retained-success gate 达到预注册条件才晋升；否则保持 experimental/unknown。负证据写入 trigger 的 contraindication，而非泛化成全局禁令。

### Runtime Retrieval and Use

检索不作为主创新。Query 使用 proof-obligation fingerprint：error family、target AST operators、ghost/executable mode、in-scope lemma type signatures、最近 error delta 与 stagnation indicator。先做 hard compatibility filtering，再做 weighted overlap ranking；最多暴露一张 admitted card。没有兼容且净效用下界为正的 card 时只用 frozen core（abstain）。

这延续现有“invisible search + top-one injection”内部提案，但补上其缺失的学习问题：card 为什么被创建、它的 action 是否有效、actor 是否会采用、以及何时应被拒绝。

## Novelty and Closest-Work Boundary

- 相对 SkillOpt/GEPA：从 whole-document outcome evolution 改为 atomic artifact 的分解式执行评估；不把更长 reflection 当信用。
- 相对 SkillGen：不只从 success/failure contrast 生成 skill，而是显式分开 forced action、exposure 与 adoption，并用它们控制准入。
- 相对 CAR 与 executed-replay credit audit：不主张通用 step causal attribution；研究对象是带可实例化 proof action 与 adoption signature 的 procedural artifact，且 verifier 判定 forced edit 的形式有效性。
- 相对 TRACE/WGSO：不把 context repair 或 scoped patching本身当创新；核心是 skill exposure、动作有效性、采用行为三者的可辨识性与测量协议。
- 相对 RSCB-MC/Anything2Skill/SRA：abstention、contraindication、when-to-load 已有；这里只作为消费 executed evidence 的 admission/runtime policy。
- 相对 RAG-Verus/PROMISE/ReProver：proof-state retrieval 已有；V-FACE 不竞争新的 premise retriever，而评价一个 procedural card 是否应该进入并影响 agent。

因此新颖性目前为 **PARTIAL**，而不是 CONFIRMED。若等预算 attribution benchmark 不能优于 observational 与 generic replay baseline，项目应降格为形式化 proof-skill audit/benchmark，而不宣称新 optimizer。

## Claim-Driven Validation Sketch

### Claim 1 — Attribution fidelity

- **Claim**: 三效应分解比整轨迹 success/failure 与文本归因更可靠地区分 action-invalid、incorporation failure 与 harmful exposure。
- **Minimal experiment**: 在从未用于生成 card 的新 development checkpoints 上建立小型完整干预表：no card、expose card、force action、placebo/mismatched card，多固定 seeds。
- **Baselines**: observational contrast；SkillGen-style contrast；budget-matched CAR/TRACE-like replay；V-FACE。
- **Metrics**: utility sign accuracy、harm recall、Brier/ECE、adoption detection precision/recall、每个正确归因的 replay cost。
- **Success**: 等预算下主要归因指标明显优于最强 baseline；否则拒绝核心 claim。

### Claim 2 — Safer admission, conditional on Claim 1

- **Claim**: 用分解式证据做 card admission 比 whole-skill gate 或 atomic+observational gate 更少引入 harmful exposure/retained-success regression。
- **Minimal experiment**: 新 development tasks 上 `whole vs atomic` × `observational vs executed` × `always inject vs abstain` 析因；冻结后在新 sealed set prospective evaluation。
- **Metrics**: Verus+Lynette valid success、retained-success regressions、harmful admission、adoption、runtime/token/attempt cost。
- **Success**: 先在 dev 上满足 harm/regression gate，再允许进入 sealed evaluation；若只提升 proxy attribution、不减少 harm，则论文只保留 Claim 1。

## Failure Modes and Diagnostics

- **Action template cannot be instantiated**: 标为 UNKNOWN；人工审计 extractor，不让 optimizer 用失败的模板反向污染规则。
- **Card action valid but actor never adopts**: 归入 incorporation；测试 terse call-only realization，不扩大知识库。
- **Exposure helps one actor, harms another**: 分开报告 actor-conditional evidence；不从已查看 test 学 actor threshold。
- **Replay cost explodes**: 只在 uncertainty/high-impact checkpoint 运行 action replay；先做 20×3 CPU pilot。
- **Small dev overfitting**: project/lemma-family disjoint split、冻结阈值、新 sealed prospective set；报告置信区间而非单次增益。
- **Existing test contamination**: test-20 永久降级为 post-hoc diagnostic，不再用于方法选择或 confirmatory claim。

## Experiment Handoff Inputs

- **Must-prove claim**: 分解式执行评估真的更忠实，而不是原子化、abstention 或更多 replay budget 带来的表面收益。
- **Must-run ablations**: 三效应分开；atomic+observational；forced-action only；exposure only；always inject；placebo/mismatch；structured summary vs raw trace blinded optimizer comparison。
- **Critical data rule**: 用旧 60 个 train/selection 只做 retrospective hypothesis generation；从原 benchmark 未使用任务中构造新的 build/dev/sealed partition，final sealed 不读取。
- **Highest-risk assumption**: optimizer 能稳定生成可实例化的最小 action template；现有 naive extraction 仅 1/8 成功，说明这是首要 go/no-go gate。

## Compute and Timeline

- **Pilot A**: 20 checkpoints × 3 forced edits，CPU Verus/Lynette，1–2 天，0 GPUh。
- **Pilot B**: 结构化 summary vs raw trajectory 的 blinded card proposal/audit，20 cases，1–2 天，<1 GPUh 或 API 等价成本。
- **Pilot C**: 6–10 new development tasks × paired conditions × 2–3 seeds，≤8 GPUh，约 3–5 天。
- **Go/no-go**: Pilot A 若可实例化率 <60% 或有效 action 对比不足，先停在 extractor/benchmark；Pilot C 若不能降低 harmful admission，则不进入 sealed evaluation。

## Current Verdict

**REVISE, not yet READY.** 本地证据足以否定 naive whole-skill routing，并支持三效应分解的必要性；但还没有 prospective evidence 证明 atomic action generation 可扩展或 admission 能改善正式终点。最合理的下一步是先建立 attribution-fidelity benchmark，而不是直接实现复杂 retriever。
