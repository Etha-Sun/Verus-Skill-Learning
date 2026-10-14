# 内部目录语义审查与 v2 修订

## 结论与范围

2026-10-13，用户要求继续审阅并直接修订。已审查全部 **21 个多规则 reference、56 条组内规则**，对照原始 Trigger、Action、Avoid、共享 Scope 和实际目录。其余 16 个单规则 reference 不需要内部选卡，未做新语义改写。

本次是 coding assistant 的本地、source-only 审查，不是独立 DeepSeek 评审，也不是模型检索准确率实验。没有读取 validation/test 解答来优化目录，没有新的 API 调用或评测。

**“每条写了 When/Avoid”不等于可唯一选中。** 主导关系分类：5 组按目标/对象较清楚可分，4 组一般与特例，3 组明显重叠，2 组互补证明层次，1 组失败后的细化，1 组同目标替代策略，5 组混合关系。分类是人工审查判断，不是量化的性能结果。

v2 做了三类修改：

1. 每个多规则目录增加一小段 Relationship，明确独立目标、上下位、可并用或真实重叠；不要求全读。
2. 修订 23 条规则的短标题/When/Avoid，突出前提到目标、当前诊断、已有 helper 或证明层次。其余 33 条短描述保留；不制造规则原文不支持的互斥条件。
3. 修正 5 个 reference 的共享导航 Scope 中过宽的排除条件。这些修改同步到目录、选中规则文件、整篇 fallback，避免目录说能读而正文前言又说不适用。

**72 条规则正文、78 张源卡覆盖、聚类、Executive、37 项主索引、reader 逻辑均保持不变。** 主 SKILL 与 selective-v1 逐字一致，仍为 8,195 bytes。旧版不覆盖，生成 selective-v2。

## 逐组审查

下表中的编号是源卡编号；merged 指现有合并规则，不是新合并。

| reference | 主导关系 | 原文依据与主要问题 | v2 处理 |
|---|---|---|---|
| compound-stability-existing-rules | 混合 | 026 的 universal fairness/action 与 045/071 的 always conjunction 不同；045/071 与 047/062 的目标可同时成立；072 是具体 extra-wrapper precondition 失败 | 对比 pairwise helper 与 proof object/macro；承认两者可同时匹配，072 不写成必经步骤 |
| direct-existing-lemma-bridge | 一般/特例 | 001 的库 lemma 匹配很宽；003 从可序列化且序列化相等到 view 相等；043 从 view 相等到 marshalability 相等；共享 Scope 错将手动 constructor fallback 整体排除 | 写清两种方向，一般规则不排除特例；修正 Scope，仅限制 direct route，不删除 003/043 原有条件 fallback |
| eventual-witness-index-bridge | 混合 | 008 已有 eventual action occurrence；009 已有绝对位置 raw state witness；061 是已有 existential 后需要 witness index，可能与 008 重叠 | 保留 When，说明三种起始证据状态及 061/008 的交集，不声明固定先后顺序 |
| finite-set-fold-cardinality-induction | 目标可分 | 017 结论为 fold 结果 finite；048 结论为 fold 等于 image。共享 cardinality induction 不能替换目标 | 保留描述，明确按结论选，不以“都用归纳”当作重复 |
| function-field-projection-syntax | 明显重叠 | 015 同时覆盖 method-as-field、field-as-method、缺 antecedent；028 为 record pointwise equality 的语法/trigger；060/075 涉及 field-call 及后续 trigger，交集很大。旧 Scope 排除 actual method，与 015 直接冲突 | 标明三者侧重点而非互斥边界；Scope 纳入 015 的实际方法误用和独立 antecedent 分支，genuine-method 排除只约束 stored-function 规则 |
| ghost-empty-witness | 一般/特例 | 054 是返回的多字段 empty ghost aggregate；073 是 initial-state relation 要求的 empty ghost history 字段。history 可属于 aggregate | 保留描述，明确对象层次与重叠，不编造“不是 initializer 才能用 054” |
| loop-termination-and-invariants | 互补层次 | 035 缺 decreases；036 entry assumptions 在 loop body 不可用；041 packet-prefix set invariant 同时也携带 pre-loop facts。旧 Scope 把 simple numeric termination 的条件加给所有规则 | 按当前失败义务区分，041 与 036 可并用；对 Scope 的 counting-only、unchanged-assumption-only 限制加作用范围 |
| natural-integer-type-mismatch | 诊断可分 | 040 subtraction 得到 int 但期望 nat；066 sequence length 是 nat 但接口期望 int，或 empty sequence 缺 element type | 标出相反转换方向及额外类型推断分支，避免泛称 numeric mismatch |
| opaque-spec-function-facts | 混合 | 019 拒绝无 decreases wrapper 的 fuel reveal；021 需要 open counterpart/connector；053 是 header/payload injectivity 且已有 fixed-width length/roundtrip lemma。后两者可在 length 子目标上重叠 | 将可用库证据写入 When，声明 021/053 可能交叠；不是把所有 opaque failure 视为一个策略 |
| post-verification-cleanup | 混合 | 038/042 是 executable shape；024 是 module directive；050 是 set proof import/macro，可能与 024 同时成立；052 仅成功后的 warning | 保留描述，说明 directive/import 是可能的替代处理而非互斥诊断；warnings-only 与 safety difference 分开 |
| proof-helper-qualified-path | 一般/特例 | 055/065 是一般 out-of-scope helper/macro；068 是 sequence equality closure 特例，还涉及 equality obligations | 说明上下位关系，允许同一 seq helper 匹配两条，不禁止一般规则处理 sequence |
| quantified-proof-antecedent-binder-scope | 明显重叠 | 006/069、023、074 均可处理 quantified implication 缺 antecedent；023 额外讨论 binder shadowing；074 强调 helper-call precondition，但原 Trigger 也有一般 warning 分支 | 不把 023 缩成“仅 shadowing”、不把 074 缩成“仅 call”；用覆盖重点区分，明确同一诊断可匹配三条 |
| record-function-field-equality | 失败后细化 | 004 有 full pointwise agreement 且仅 record postcondition 未过；005 明确要求 direct function equality 未过且 helper 不可用/被拒 | 保留两者适用阶段；不是强制先试一次 004 才准读 005，而是依据已有失败证据 |
| sequence-fold-concat-equality | 同目标替代 | 063 用 prefix/last decomposition；064 已有 split lemma 和 accumulator-compatible formulation。两者证明同一 concatenated-fold 目标 | When 写可用事实/lemma；明确同具条件时没有已知唯一最优路线，不强制两条都用 |
| set-equality-membership-witness | 一般/特例 | 002 Trigger 宽称 set/image，但 Action 实际使用 image/union witness；049 是 duplicate-free sequence removal 和 shifted indices | 对 002 明示具体正文是 image-union case，避免过度泛化；049 保留 no-duplicates 必要条件 |
| temporal-existential-witness-lifting | 混合 | 016 与 032 均有 leads-to witness lifting 和 chaining，差异是模板/中间链关注点；033 是 equality，所需为 equality/witness-introduction rules，不是 per-witness leads-to lemma | 明示两条 leads-to 规则重叠；修正 Scope，不把 016 的 atomic-source、per-witness 条件强加给 033 |
| temporal-predicate-equality-pointwise | 目标可分 | 029 两边是 universal/always commutation；070 两边是同一 operator 一次与两次应用 | 保留描述，按 equality 两端形式选，而不是泛称 temporal equality |
| temporal-suffix-shift-helper | 前提/目标可分 | 014 nested always goal + forward-shift helper；025 always-lifted action premise + suffix-wise action conclusion | 明示 premise/goal 方向；较大证明可同时需要，局部可分不等于全题互斥 |
| transition-system-step-safety | 互补层次 | 010 外层 temporal invariant induction；011 network multiset 更新后的 membership/preservation；012 controller 不发 external request 子情形 | 标注证明层次，不把三个可互相依赖的步骤当成三种互斥解法 |
| trigger-inference-annotation | 明显重叠 | 034 trigger-only；018、057 都有 trigger/antecedent 双分支，分别强调 witness/entailment 与 state/suffix terms；同一 universal assertion trigger 错误可全匹配。Scope 原先排除 antecedent-only，与后两条冲突 | 修正 Scope，承认三条可同时匹配；侧重点不是硬性准入条件。018 原 Action/Validate 张力保留，不称已经解决 |
| universal-instantiation-concrete | 事实对象可分 | 037 whole sequence 到 index；058 entailment 到 execution；076 propagated stability 与 alias-sensitive recursive-helper precondition | 保留描述，强调已有事实的对象，不与缺 premise、trigger inference 混为一谈 |

## 模型实际看到的差异示例

### 可明确区分：003 与 043

003：

> When: Both values are marshalable, serialized representations agree, and an existing trait/instance promises view equality.
>
> Avoid: Trait unavailable or its view relation cannot imply the required structural equality.

043：

> When: The premise is abstract-view equality and the goal is equality of marshalability predicates.
>
> Avoid: The goal has a different proof direction; an uninstantiable direct bridge requires the original conditional fallback.

组级说明同时声明：general library-lemma entry 可以匹配上述特例，不是第三种互斥目标。

### 无法诚实唯一划分：018、034、057

- 034：只有 trigger inference 主题，assertion 或 choose 无法推断 trigger。
- 018：trigger 或 missing antecedent，正文重点有 witness/entailment term。
- 057：trigger 或 missing antecedent，正文重点有 state/suffix term。

组级实际说明包含：**An assertion trigger error can match all three.** 不声称“choose 只能读 018”“state 只能读 057”。选一条先读或多读皆可；真实卡片内容近似不是改两个形容词就能消除的。

## Source-only 边界检查（人工静态审查，不是模型测试）

| 假设的局部证明状态 | 可支持的路由判断 | 不应制造的判断 |
|---|---|---|
| marshalable + equal serialization，目标 equal views | 003 明确匹配；有匹配 lemma 时 general 项也可匹配 | 043 因含有 view 一词就等价匹配 |
| equal views，目标 equal marshalability | 043 明确匹配 | 003 的证明方向可以任意反转 |
| genuine method 被当作 field 取用 | 015 的原文直接支持 | 共享 Scope 排除所有 genuine methods |
| universal assertion cannot infer trigger | 018/034/057 都可能匹配 | 保证只会选到一张 |
| quantified assertion antecedent-only warning | 018/057 覆盖；034 的 trigger-only 项不覆盖该单独诊断 | 排除整个 trigger family |
| helper fails under unassumed antecedent，无 shadowing | general 与 074 匹配，023 也有 antecedent 分支 | 023 仅适用于 shadowing |
| temporal equality 有 equality/witness-introduction rules，无 per-witness leads-to lemma | 033 不应因缺后者被组级 Scope 排除 | 对 equality 额外要求 leads-to helper |
| concat fold 同时存在 split lemma 与 prefix/last decomposition | 两条是可选路线 | 规定唯一最优或必须先后执行 |
| loop 的 entry assumption 不保持不变，但存在 evolving packet-prefix relation | 不能直接携带不变 assumption；仍可检查 041 | 一条规则的不适用条件排除整个 family |
| direct function equality 已失败且 helper 不可用 | 005 的阶段信息能区分 | 为读取 005 强制重复失败 |

这些检查支持目录修订的合理性，不产生检索准确率、成功率或因果效果估计。目录没有完整的形式化适用性判定，模型仍可能选择不当。

## 一致性、开销与实验解释

- 30 项离线测试通过，包括旧版本的 19 项；新增测试覆盖 21 组与 56 条索引项、无效修订拒绝、冻结父产物、全部 72 规则、单条/多条/整篇读取和 Markdown 目标/anchor。
- 新 candidate 的所有原规则块、source IDs、共享 conditional links 与原版逐字一致；16 个单规则文件未改；reader 和主 SKILL 与 selective-v1 完全相同。
- **5 个整篇 reference 不再与 B 完全同字节**，唯一差异为已记录的共享导航 Scope；其余 32 个整篇 reference 仍同字节。不能沿用 v1“所有 full fallback 都与旧版相同”的说法。
- v2 目录为 1,596–2,912 bytes，中位数 2,124；主 SKILL 没有增长。
- 56 种“先目录再读一条”的静态内容字节比，对原 B 整篇，中位数 86.24%；11 种不小于整篇，最大 118.63%。比 v1 的中位数 79.46% 更重。此处不含 JSON、额外回合和上下文重放，也不是模型 token/费用节省率。
- 因而本次改进优先消除误导性边界，而非保证省 token。真实重叠组可能还是需要多读；不应为了缩短目录删掉必要的否定条件或伪造单选。

当前 control 仍为未改动的 grouped B。如果后续直接比较它与 v2 C，处理因素是**细粒度读取＋内部导航/Scope 修订**，不能将效果全部归因于“读取粒度”。若需要严格隔离粒度，应先另行明确是否对两组同步同样的导航 Scope 修订并冻结新对照；本次没有擅自改变 control。该选择应在评测前落实。

卡片本身的 inherited issues（尤其 018 的 Action/Validate、不完全泛化的原始经验）仍保留。尚未做独立模型选择测试或 live inference；不声称问题已全部消除，不启动评测或复用旧预算。

## 产物和复现

新产物后缀：`skillopt-verusage/card-organization-20261013-selective-v2/`，位于 `VERUS_SKILL_RUN_ROOT`。

- `candidate/SKILL.md`：主文件。
- `candidate/references/direct-existing-lemma-bridge.md`：方向可分的例子。
- `candidate/references/trigger-inference-annotation.md`：真实重叠的例子。
- `routing_review_v2.json`：21 组 review、scope replacements、23 条 cue overrides。
- `rule_cues.json`：完整生效后的 56 条组内描述。
- `candidate_manifest.json`：parent manifest/hash、代码与配置 hash、每条 rule hash、5 处 scope 变更、仍需审阅/未授权评测的状态。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/revise_selective_routes.py \
  --source-run "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-organization-20261013-selective-v1" \
  --output "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-organization-20261013-selective-v2"
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  skillopt-verusage/tests/test_selective_references.py \
  skillopt-verusage/tests/test_selective_route_revision.py
```

仅新输出目录可构建；同名输出拒绝覆盖。父 v1 manifest SHA256：
`17ca790403573951d7d5d6c6372d3dbd573f93dd43371accc344d5ab8376ccf5`。
旧 compact-v1、selective-v1、历史运行、原始/封存数据和凭据均未修改。
