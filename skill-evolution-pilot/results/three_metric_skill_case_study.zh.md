# Self-Evolving Skill 三指标案例研究

## 1. 结论摘要

本报告分别分析三类指标：

1. **Token cost**：`Expected Primary Uncached Tokens to Success`（ETtS，越低越好）。
2. **Small-model benefit**：Qwen 条件下的 verifier-safe solve rate（越高越好）；provider tokens 仅作同 solve count 下的次级成本指标。
3. **Information Gain**：离线 pre/post proxy（越高越好）；它不是 live solving 的主终点。

证据支持的最高强度结论是：

- **Token 指标存在一个很有解释力的同轮好/坏对照**：IronKV 单问题 R3-A `local-proof-surface-cap` 的筛选 run 比 fresh H0 低 29.87%，而同轮 R3-C `three-fact-witness-note` 高 37.02%。两者都成功，因此差异不是“失败得更快”。好 skill 的核心不是更短，而是把完整分支义务在第一次 verifier 前组织好，并对 helper、编辑范围和局部修复施加硬约束。然而三次确认只得到 -5.64%，且小于 H0 自身波动，所以最终结论仍是 **inconclusive**。
- **Small-model 主指标没有任何涨点 skill**：完整条件都只解出与 H0 相同的 2/4。R2-C `verus-contract-match-loop-r2` 只能称为“最少伤害”，不能称为成功。它相对同轮 R2-A 显著减少 token，但相对 H0 仍多 2.99%。
- **InfoGain 的 pre 与 post 偏好不同**：pre 的最佳宏平均来自 R1-S `dependency_bridge_map`，post 的最佳归一化宏平均来自 R1-C `minimal_sufficient_rationale`。前者更像解题前的结构检索，后者更像解题后的压缩记忆。将两者混成一个“最好 skill”会掩盖机制差异。
- 没有证据表明当前涨点来自一个稳定、可累积的 meta-skill 演化过程。最准确的表述是：**meta-agent 偶尔能生成有价值的候选并诊断失败，但尚未形成跨轮保留有效原子、跨任务泛化、且经确认复现的增量演化。**

## 2. 口径与证据边界

### 2.1 A/C/S

- **A — aggressive**：主动压缩探索、限制 verifier cycle，接受更强的行为约束。
- **C — conservative**：最小注入、低认知开销、明确 self-disable。
- **S — structural**：改变 proof state、义务或依赖关系的组织形式。

### 2.2 “好”的定义

三类指标不能共用一个“好”的定义：

- Token：必须 verifier-safe，且 ETtS 下降；invalid、timeout、缺失 usage 的 run 不得算改进。
- Small model：首先看 solve rate；solve count 相同时才讨论 token。
- InfoGain：只描述离线条件概率 proxy；不能外推为 solved rate 或 live token efficiency。

### 2.3 因果判断标准

一个 skill 指标突出，不等于其文本中宣称的机制得到验证。至少还需满足：

- 行为 trace 确实执行了该机制；
- 同轮替代 skill 没有提供更简单的解释；
- 复跑超过 H0 波动；
- 在未参与生成的任务、模型或 seed 上仍成立。

目前没有候选同时满足以上四点。

仓库中没有覆盖本组三指标结果的统一 `EXPERIMENT_AUDIT.json`，因此独立
result-to-claim verdict 按流程标记为 **provisional**。这不否定已有的 run-level
F3、input-unchanged、Verus 与 Lynette 证据，但意味着尚无一个统一审计文件对所有
跨实验聚合口径背书。

---

## 3. Token cost：第一个好 skill 与坏 skill 的深度对照

### 3.1 为什么选这组

最干净的对照来自 **IronKV 单问题实验、同一轮 R3、同一目标问题**：

- 好：R3-A `local-proof-surface-cap`
- 坏：R3-C `three-fact-witness-note`

两者都通过 F3、Verus、Lynette，输入均未修改；因此可以排除“坏 skill 因失败而便宜/昂贵”的混淆。它们还共享同轮上下文和同一目标，优于跨轮、跨任务的宽泛比较。

### 3.2 指标对照

| 条件 | A/C/S | verifier-safe | Primary uncached tokens | 相对 fresh H0 | Solver Verus 次数 | 新 helper | 最终新增行 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fresh H0，3-run ETtS | — | 3/3 | 87,312.7 | 0% | — | — | — |
| R3-A 筛选 | A | 1/1 | 61,232 | **-29.87%** | 2 | 0 | 139 |
| R3-C 筛选 | C | 1/1 | 119,638 | **+37.02%** | 6 | 4 | 302 |
| R3-A fresh confirmation，3-run ETtS | A | 3/3 | 82,391.0 | -5.64% | — | — | — |

Fresh H0 三次为 82,779、83,472、95,687，range 12,908；R3-A confirmation 为 68,303、90,569、88,301，range 22,266。确认阶段的 4,921.7-token 优势小于 H0 range，因此实验自己的最终判定 `inconclusive_within_h0_range` 是正确的。

筛选 run 的成本分解进一步说明差异主要来自反复上下文，而非最后回答本身：

| 条件 | Input | Cached input | Uncached input | Output | Reasoning output | Model tool calls | Wall time |
|---|---:|---:|---:|---:|---:|---:|---:|
| R3-A | 444,510 | 395,008 | 49,502 | 11,730 | 7,286 | 7 | 331.8 s |
| R3-C | 871,743 | 769,024 | 102,719 | 16,919 | 9,386 | 10 | 407.2 s |

R3-A 的 skill 文件本身反而更长：约 3,283 bytes / 460 words；R3-C 约 2,339 bytes / 333 words。故 R3-A 的筛选收益**不是 prompt 更短**，而是它减少了后续候选膨胀、重复 verifier 和上下文回灌。

若只做同轮直接比较，R3-A 比 R3-C 少 58,406 primary uncached tokens，即 **-48.82%**。这比各自相对 H0 的百分比更能隔离同轮好/坏 skill 的执行差异，但仍然只有每条件一次 trajectory。

### 3.3 原文对照

R3-A 的关键原文：

> “List every return path in a compact ledger. Name existing coverage facts for true paths and, for each false path, a witness with lower inclusion, strict upper inclusion, and abstract disagreement.”

> “Make one proof-only patch confined to the existing target body. Reuse supplied lemmas and keep the initial new-helper budget at zero.”

> “Repair only the reported local premise or syntax item.”

R3-C 的关键原文：

> “Before editing, record for every false return one witness and three facts: lower inclusion, strict upper inclusion, and abstract-value disagreement.”

> “Prefer existing lemmas and assertions inside the target body. Add a helper only for a fact reused at least twice.”

> “The small injection preserves the successful local-witness behavior...”

### 3.4 R3-A 为什么突出

两者其实都识别出了 false-return witness 的三个核心事实。真正的区别不是“谁知道更多 Verus 知识”，而是**谁把知识变成了可执行的搜索边界**。

R3-A 有三层约束：

1. **完整 proof-surface gate**：它要求在第一次 patch 前列出 *every return path*，同时处理 true path 的 coverage fact 和 false path 的 witness。这样可在早期发现“局部 witness 正确，但另一个分支义务缺失”的问题。
2. **硬编辑预算**：`initial new-helper budget at zero` 不是温和建议，而是把第一步限制在 target body 内。它直接压制候选扩张。
3. **局部 delta 修复**：失败后只修 verifier 报告的局部 premise/syntax，避免从一个错误重新设计整套证明。

R3-C 只要求记录 false return 的三个事实，并允许“复用两次即可加 helper”。对这个 hard task 来说，它没有约束完整 proof surface，也没有阻止 solver 把一个局部 witness 问题扩展成通用 GLB/helper 重构。实际结果正对应这一差异：302 个新增行、6 次 Verus，对比 139 行、2 次 Verus。

可见 trajectory 也显示 R3-A 对 skill 的关键约束有实际 compliance。它在编辑前写道：

> “The return-path ledger has three proof cases…”

并明确承诺：

> “apply one local proof patch with no new helper functions.”

R3-C 则从首次局部证明逐步扩展为 GLB-tail helper、value-preservation lemma、boundary ownership 和 ordering helpers。换言之，指标差异与“是否控制 proof surface”一致；但由于没有 atom-level ablation，这仍是机制假设，不是唯一因果证明。

因此这里最重要的机制判断是：

> **筛选优势最符合“语义义务完整性 + 硬 proof-surface cap”这一机制假设，而不符合“skill 更短”这一解释；尚需 atom-level ablation 才能做唯一因果归因。**

### 3.5 R3-C 为什么坏

R3-C 在形式上很符合 Conservative：

- 注入短；
- 聚焦三个 witness facts；
- helper 有触发阈值；
- 声称保留最小行为。

但它的 conservative 建立在错误的适用性假设上：它假设 solver 已经拥有正确的全局义务组织，只需要一个局部提醒。IronKV hard task 恰恰不是“少一个事实”，而是“多个 return path、representation bridge 和 witness 义务如何同时闭合”。在这种状态下，过于局部的 C 不会自动减少探索，反而可能让 solver 在不完整框架上持续打补丁。

这说明 C 的 self-disable 条件不能只写“第二次 bridge 失败后停止”，还应包含一个进入条件：

> 只有当所有分支已经有明确 obligation ledger、且唯一缺口是一个局部 bridge 时，才启用 micro-skill；否则立即路由到 structural/aggressive organizer。

### 3.6 泛化性评估

R3-A 的泛化性目前为 **低到中，且未被验证**：

- 可泛化的原子：branch ledger、zero-helper initial budget、local-delta repair，适用于多分支 verifier proof。
- 不可直接泛化的部分：lower inclusion、strict upper inclusion、abstract disagreement 是 IronKV delegation-map 的问题特定结构。
- 统计证据弱：1-run 筛选很强，但 3-run confirmation 只剩 -5.64%，小于 H0 波动。
- 没有 held-out task、held-out model 或不同 verifier 环境确认。

合理的泛化版本不应复制三个 IronKV witness facts，而应检索一个抽象模板：

1. 枚举 control-flow exits；
2. 为每个 exit 指定已知事实、缺失义务和允许的 representation bridge；
3. 第一轮禁止新增 helper；
4. 只有同一局部事实跨两个以上出口复用时才提升为 helper。

### 3.7 它的成功来自 meta-skill 演化吗

答案是：**候选生成部分来自 meta 分析，但不能称为已成功演化。**

支持“部分来自”的证据：

- R1 已识别 late false witnesses 与 candidate growth。
- R2-C `witness-completeness-microcheck` 成为该轮最好条件，提示“第一次 patch 前的语义完整性”比大规模结构重写有效。
- R3 meta 将这个 C 洞察重新编码为 A：不仅检查 witness，还增加完整 branch ledger、zero-helper 和 local repair cap。这是一次有意义的 profile migration。

反对“演化成功”的证据：

- R3-A 是单次筛选胜者，确认效果明显回归；
- 同一个 R3 meta 同时生成了成本极差的 R3-C；
- 跨轮没有显式保留、组合、删除可归因的 skill atoms；
- 没有 held-out 泛化；
- 后续 R6 没有超过早期 R1 的四任务 aggregate 最好值。

所以应表述为：**meta-agent 成功发现并重组了一个有潜力的局部机制，但 self-evolving pipeline 尚未证明能稳定累积该机制。**

### 3.8 A/C/S 是否名副其实；什么策略更利于 token

R3-A 很好地体现了 A，但“aggressive”并不是写更多步骤，而是积极砍掉搜索自由度：

- 全分支一次性登记；
- 第一次 helper budget = 0；
- 只允许 proof-only target-body patch；
- verifier 后仅修局部 delta。

R3-C 也体现了 C 的短小和 helper threshold，但缺少可靠适用性 gate，因而在 hard state 上失效。

对 token 指标最有希望的策略是：

- 可观察、可执行的 stop/cap，而非抽象建议；
- 在第一次 verifier 前完成最小的 obligation coverage；
- 控制 candidate growth，因为更大的候选会在后续每轮重复进入 prompt；
- unchanged-state 不重跑；
- helper 提升以实际复用为条件；
- skill 的启用由 proof state 决定，而不是由固定任务标签决定。

### 3.9 四任务 aggregate 的补充警告

四任务上仅有三个完整 skill 低于 H0 ETtS 52,350：

| Skill | 轮次/类型 | ETtS | 相对 H0 | Solve |
|---|---|---:|---:|---:|
| `bounded-exploration-gate` | R1-A | **51,497.0** | **-1.63%** | 4/4 |
| `micro-direct-kernel` | R6-C | 51,881.0 | -0.90% | 4/4 |
| `backward-contract-frontier` | R5-S | 52,013.5 | -0.64% | 4/4 |

但它们都存在明显 task crossing：

- R1-A 在两个任务省 token，在两个任务增 token；
- R6-C 在其声称适合的 direct task 上反而 +21.85%；
- R5-S 的 R6 审计指出，代表性成功 trace 依赖 naming-convention exploration，而不是文本规定的 backward frontier。

因此 aggregate winner 不能自动作为通用 memory。R1-A 中更值得保留的是以下可执行原子：

> “Apply an evidence gate: use a symbol only if it appears in allowed source or an exact compiler suggestion.”

> “Permit at most two failed verifier runs for the same proof shape.”

> “Do not rerun a checker on an unchanged state except when explicitly required.”

---

## 4. Small-model benefit：没有主指标赢家，只有“最少伤害”

### 4.1 先纠正“涨点”叙述

Small-model H0 为 2/4 solved、29 requests、312,656 provider tokens。R1–R3 所有日志完整的 skill 条件仍然只解出同样的 2/4。故：

> **不存在 small-model solve-rate 涨点 skill。**

如果 solve count 固定，最好的完整 skill 是 R2-C `verus-contract-match-loop-r2`，但它的 321,998 tokens 仍比 H0 高 2.99%。它只能称为 least-harmful。

### 4.2 同轮好/坏对照

选择 R2-C 与 R2-A，是因为两者同为 2/4 solved、29 requests，token 差异不能由 solve count 或请求次数解释。

| 条件 | A/C/S | Solve | Requests | Provider tokens | 相对 H0 | Prompt | Completion | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H0 | — | 2/4 | 29 | **312,656** | 0% | — | — | — |
| `verus-contract-match-loop-r2` | C | 2/4 | 29 | 321,998 | +2.99% | 305,732 | 16,266 | 9,640 |
| `verus-eight-plus-two-ladder-r2` | A | 2/4 | 29 | 490,164 | +56.77% | 455,011 | 35,153 | 29,260 |

在 IronKV hard task 上：

- R2-C：247,823 tokens，10 requests，166.8 s，最终是 47 verified / 1 logical assertion error，Lynette pass。
- R2-A：399,117 tokens，10 requests，611.3 s，最终留下 `unknown prover name ... by (induction)` 的 compile error。

### 4.3 原文对照

R2-C：

> “Pick the lemma whose `ensures` has the same outer operator as the goal.”

> “Call that lemma and add at most one bridge”

> “After the second failed bridge, stop stacking facts.”

R2-A：

> “Requests 1-8: work phase”

> “Write a private three-line inventory...”

> “Requests 9-10: protected checks”

### 4.4 为什么 C 明显优于 A，但仍不算成功

R2-C 把每轮行动压缩成三个低负荷选择：匹配目标外层 operator、调用一个 lemma、最多加一个 bridge。它适合小模型，因为减少了同时维护的抽象状态。

R2-A 则把一个十请求预算进一步切成 work/protected-check 阶段，并要求私有 inventory。这个设计的问题不是“请求太多”——两者请求数完全一样——而是每次请求携带和生成的认知状态更重。最终：

- prompt tokens 多 149,279；
- reasoning tokens 约为 C 的 3 倍；
- hard task wall time约为 C 的 3.7 倍；
- 还没有保证最终候选回滚到可编译状态。

因此 small model 的瓶颈不是缺少更完整的 prose policy，而是**工作记忆、精确 symbol grounding 和可恢复状态管理**。把执行调度写进 prompt 并不等于调度得到执行。

R2-C 仍不成功，因为它只减少了损害，没有带来额外 solve；而且相对 no-skill H0 仍增加 token。它在 hard task 上接近完成，但“接近”不能计为 verifier-safe success。

### 4.5 泛化性评估

R2-C 的机制泛化性为 **中等**，效果泛化性为 **未证实**：

- “outer operator matching”“one lemma + one bridge”“two failures then stop”是模型容量友好的通用动作模板；
- 但 Verus 任务经常需要多层 representation bridge，仅用 outer operator 可能错误匹配；
- 没有带来 solve-rate 提升；
- 只在一个小模型和四个任务上观察到 least-harmful。

适合把它作为**检索到的 micro-card**，而不是每题固定注入的全局 skill。触发条件应是：当前 verifier goal 与一个 visible lemma 的 `ensures` 已近似同构，且只缺一个已知 representation bridge。

### 4.6 它的表现来自 meta-skill 演化吗

只能说 meta-agent 做到了 **damage control**：

- R2 meta 正确诊断 R1 长建议没有提高 solve；
- R2-C 比 R1-C 从 327,572 降至 321,998，下降 1.70%；
- R3-C 为 322,195，基本停滞；
- 所有完整条件 solve count 始终为 2/4。

这不是主目标上的演化成功，而是次级成本上的局部压缩。若以 solve rate 为 fitness，演化没有前进。

### 4.7 A/C/S 与更有希望的策略

- C 最符合小模型：动作少、符号明确、即时 stop。
- A 的 rigid schedule 确实很 aggressive，但对小模型是额外负担；它优化的是“看起来有纪律”，不是实际状态可控性。
- S 若只给抽象 proof DAG/state machine，同样容易超过小模型的工作记忆。

更可能改善 small-model solve rate 的不是更长 skill，而是：

1. 每轮只检索一个与当前 verifier error 匹配的 micro-card；
2. symbol 必须来自 source 或 compiler suggestion；
3. 一个 lemma、一个 bridge、一次 verifier；
4. harness 在外部保存最后一个 Verus-passing checkpoint，并真正执行 rollback；
5. 最终 Verus/Lynette 由 harness 强制运行，不依赖模型记住；
6. 对需要多层结构重构的 hard state 允许 abstain 或路由强模型。

---

## 5. Information Gain：pre 与 post 是两种不同的“好”

### 5.1 汇总指标

归一化四任务宏平均：

| 轮次 | 类型 | Skill | Pre IG | Post IG |
|---|---:|---|---:|---:|
| R1 | A | `proof_state_saturation` | -0.388462 | 0.215590 |
| R1 | C | `minimal_sufficient_rationale` | -0.439964 | **0.219801** |
| R1 | S | `dependency_bridge_map` | **0.070516** | 0.209458 |
| R2 | A | `verifier_delta_atlas` | -0.123545 | 0.168097 |
| R2 | C | `contract_unification_certificate` | -0.070195 | 0.203108 |
| R2 | S | `boundary_cut_proof_dag` | -0.088471 | 0.170301 |

R3 只有 10/12 部分结果，不能与完整轮次并列下结论。

这里必须分别分析：

- **Pre winner：R1-S `dependency_bridge_map`**
- **Post winner：R1-C `minimal_sufficient_rationale`**

### 5.2 Pre：为什么 R1-S 突出

原文：

> “Create a root node for each target conjunct or implication direction.”

> “Add bridge edges wherever adjacent nodes use different representations”

> “Order helper lemmas topologically.”

它把证明前状态组织为目标节点、representation bridge 和拓扑依赖。这与 marshal 类任务的自然形状高度一致：spec/bytes/seq/value 之间不是单个局部 fact，而是一串有序 representation transitions。相比 A 的 proof-state saturation，S 没有要求同时枚举所有可能 verifier residues；相比 C 的 terminal rationale，它在 pre 阶段提供了真正可用于预测下一证明 token 的结构。

因此 S 对 pre IG 的优势可以解释为：

> **模型在尚未看到完整证明时，最需要的是“下一步义务位于哪个表示层、依赖哪座桥”的低熵结构，而不是更多细节或事后压缩。**

但这个 winner 很脆弱：

| R1-S per-task pre IG | 值 |
|---|---:|
| direct | 0.01539 |
| marshal impl2 | 0.10306 |
| marshal impl5 | 0.29008 |
| IronKV hard | -0.12647 |

四任务未加权宏平均为 +0.070516，但按全部 9,354 target tokens pooled 后约为 -0.0587。正值主要由两个 marshal task 驱动；去掉最强 marshal task，宏平均接近 -0.0027。故它不是稳健的全任务 pre winner，而是**结构与任务家族匹配**的案例。

### 5.3 Post：为什么 R1-C 突出

原文：

> “Retain the smallest high-confidence set of facts sufficient to explain a complete Verus proof.”

> “Record only the mismatch between that conclusion and the target”

> “End with five short lines”

Post 阶段已经有完整 proof trace，新增价值不再是展开搜索空间，而是丢弃失败历史、保留已验证的 contract-to-target bridge。R1-C 用“smallest high-confidence set”和固定五行末端格式实现了这一点。

它也是 R1 三个 skill 中最短的：

- C：约 2,109 bytes / 289 words
- S：约 2,839 bytes / 389 words
- A：约 3,030 bytes / 401 words

R1-C 的 post IG 在四个任务上均为正：

| Task | Post IG |
|---|---:|
| direct | 0.06662 |
| marshal impl2 | 0.12201 |
| marshal impl5 | 0.54220 |
| IronKV hard | 0.14837 |

这支持“验证后最小充分摘要”作为 terminal memory representation，但不支持它在 live solving 中降低 token 或提高 solve。

### 5.4 为什么 A 没赢

R1-A `proof_state_saturation` 试图保存更多 proof residues 和状态信息。它很符合 A 的“覆盖更多可能性”，但在 IG 指标中，额外细节会稀释真正 target tokens 的概率质量，尤其在长任务上更明显。

InfoGain 奖励的不是信息总量，而是**对目标 token 的条件概率提升**。如果 skill 注入十条合理但只有两条与当前任务相关的状态，语义上“更完整”，统计上仍可能是负 IG。

### 5.5 泛化性评估

R1-S pre：

- **机制泛化：中等。** 目标节点、表示桥、拓扑依赖适用于 layered proofs。
- **经验泛化：低。** 正值由 marshal family 驱动，对 IronKV hard 为负，pooled 指标为负。
- 最适合作为按 proof topology 检索的结构卡，而不是全局 system prompt。

R1-C post：

- **机制泛化：中到高。** verified terminal trace 压缩成最小充分摘要，是跨任务可复用的 memory write policy。
- **效果泛化：仅限 post proxy。** 四任务都为正，但没有 live endpoint 证据。
- 它更像 memory compiler，而不是 solver skill。

### 5.6 表现来自 meta-skill 演化吗

R1 两个 winner 都是第一次 meta 输出，不能证明跨轮演化。R2 meta 的诊断在概念上合理：区分 task/phase heterogeneity，并分别生成 atlas、certificate、DAG；但实证结果没有前进：

- 三 skill 平均 post：R1 约 0.2149，R2 约 0.1805；
- R2 没有任何正 pre；
- R2-C 将自己的 pre 从 R1-C 的 -0.440 改善到 -0.070，但 post 从 0.220 降到 0.203；
- R3 不完整。

因此这里出现的是一个重要 trade-off：更丰富的 contract-unification certificate 缓解了 pre 的严重负值，却损失了 post 的压缩优势。meta-agent 找到了问题，却没有找到统一改进两个 phase 的表示。

结论：**不是成功的增量演化；是一次揭示“pre 检索”和“post 写回”必须分离的失败。**

### 5.7 A/C/S 与更有希望的策略

- Pre 更可能受益于 S，但只在检测到多表示层、多个依赖 cut 的状态启用。
- Post 更可能受益于 C：只保留经 verifier 确认的最小充分链。
- A 只应在确实存在多个独立 residue、且能控制注入密度时启用。

更好的 InfoGain 策略不是生成一个同时服务 pre/post 的大 skill，而是建立双通道：

1. **Pre retrieval**：按 proof topology 检索一个结构 bridge card；
2. **Post compilation**：把成功 trace 编译成五行左右的 verified summary；
3. 用 state-conditioned retrieval 替代固定全量注入；
4. 加入 length-matched null/ablation，区分语义收益与长度效应；
5. 分别报告宏平均、token-weighted pooled 和 per-task 值，避免聚合方式改变 winner。

---

## 6. 三指标共同揭示的失败机制

### 6.1 当前演化不是 incremental

每轮输出三个完整新 skill，但没有显式的原子级 lineage：

- 哪一条 policy 来自前轮 winner；
- 哪一条被删除；
- 哪一条只改了适用条件；
- 哪一条导致 trace 行为变化。

结果是 meta-agent 每轮更像“重新写三篇 prompt”，而不是对可归因组件做小步选择。R3-A 的有效原子没有在后续形成稳定 dominance，就是直接表现。

更合适的演化单位应是：

```text
skill = applicability gate
      + obligation representation
      + action policy
      + stop/rollback policy
      + memory writeback
```

每轮只允许修改一到两个 atom，并使用 parent/child diff、行为 compliance 和 matched seeds 做归因。

### 6.2 当前组织形式不利于检索

完整 Markdown skill 把任务知识、行为规则、解释和失败风险绑定在一起。固定注入会造成：

- 对不适用任务支付 prompt tax；
- 小模型承受额外工作记忆；
- aggregate winner 掩盖 task crossing；
- pre 需要的结构卡与 post 需要的压缩卡互相污染。

更合理的 memory 形式是原子卡片与索引：

| 字段 | 作用 |
|---|---|
| `applicability_signature` | goal operator、branch count、representation layers、error class |
| `evidence_required` | source symbol、compiler suggestion、verified lemma |
| `action` | 一个可执行动作 |
| `budget` | helper/verifier/edit-size cap |
| `stop_or_rollback` | 可由 harness 观察和执行 |
| `provenance` | 实验、轮次、slot、parent atom |
| `outcomes` | per-task/seed 指标，而非单一 aggregate |

检索时只取一到三张卡，不注入完整历史 skill。

### 6.3 三个指标需要不同策略

| 指标 | 最值得保留的策略 | 不应优化成什么 |
|---|---|---|
| Token ETtS | 完整义务 ledger、硬 proof-surface cap、局部 delta repair | 更长的通用 proof 教程 |
| Small-model solve | 单 lemma/单 bridge、外部 checkpoint/rollback、精确 symbol provenance | prompt 内的十步调度 |
| Pre IG | 按 proof topology 检索 S 卡 | 全局固定注入 |
| Post IG | verifier-confirmed 的 C 型最小摘要 | 把完整探索史写回 memory |

### 6.4 下一轮最关键的验证

1. 将 R3-A 拆成四个 atoms：branch ledger、true/false coverage、zero-helper、local-delta repair。
2. 在 held-out 多分支 Verus tasks 上做 matched ablation，每个 atom 至少多 seed。
3. 记录行为 compliance：是否真的先列全分支、是否新增 helper、每次 verifier 后改动范围。
4. 将 small-model rollback 从自然语言移到 harness。
5. 将 InfoGain 的 pre retrieval 与 post writeback 分成两个独立实验。
6. 主要结论仍以 live verifier-safe solve/ETtS 为准；InfoGain 只用于筛选和诊断。

## 7. 证据位置

以下均为 `${VERUS_SKILL_RUN_ROOT}` 下的只读实验产物：

- 单问题 R3-A：
  `skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/round-3/skills/local-proof-surface-cap.md`
- 单问题 R3-C：
  `skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/round-3/skills/three-fact-witness-note.md`
- R3-A confirmation freeze：
  `skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/final-confirmation/selected_skill.md`
- Token R1-A：
  `skill-evolution-pilot/token-r1-matrix-20260726/skills/bounded-exploration-gate.md`
- Token R5-S：
  `skill-evolution-pilot/token-r5-matrix-20260726/runs/skills/backward-contract-frontier.md`
- Token R6-C：
  `skill-evolution-pilot/token-r6-matrix-20260726/runs/skills/micro-direct-kernel.md`
- Small-model R2-C：
  `skill-evolution-pilot/qwen-small-model-r2-20260726/skills/verus-contract-match-loop-r2.md`
- Small-model R2-A：
  `skill-evolution-pilot/qwen-small-model-r2-20260726/skills/verus-eight-plus-two-ladder-r2.md`
- InfoGain R1-S：
  `skill-evolution-pilot/information-gain-r1-trajectories-20260726/skills/dependency_bridge_map.md`
- InfoGain R1-C：
  `skill-evolution-pilot/information-gain-r1-trajectories-20260726/skills/minimal_sufficient_rationale.md`
- 三指标汇总：
  `skill-evolution-pilot/visualizations/three-objective-results-20260730/`

本报告只读取 raw traces 和 legacy 数据，没有修改、移动或复制任何 raw dataset，也没有声称获得 provider 未暴露的 hidden chain-of-thought。
