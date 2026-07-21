# 自动科研工作与结果总览（截至 2026 年 7 月 20 日）

## 1. 文档目的与范围

本文总结 Verus 自演化证明修复项目从自动科研流程建立以来所完成的工作、
实验结果、失败结论、路线调整和当前状态。

- 可审计时间范围：`2026-07-03` 至 `2026-07-20`。
- `2026-06-28` 左右形成的 self-evolving / Verus-specificity 调研作为
  前置背景，不与本周期新产生的实验结果混淆。
- 项目：`verus_self_evolving`。
- 当前代码工作区：`verus-self-evolve-scaffold/`。
- 当前主线：从成功的 hands-off frontier-agent traces 中蒸馏知识，在
  project-held-out Verus repair 任务上验证是否能够保持成功率并降低推理成本。
- 本文严格区分离线 proxy、机械完整性测试和真实 downstream agent 结果。

## 2. 一页结论

截至目前，自动科研已经完成了四类关键工作。

1. **建立了可持续、可审计的科研基础设施。**
   - 建立 `research_memory/`，统一保存计划、实验、决策、会议和结果。
   - 规定原始 trace 数据只读，derived artifacts 不写回 raw corpus。
   - 建立可执行 scaffold、实验 tracker、数据/代码分离方案和安全检查。

2. **验证了若干测量和分析方法，但主动否决了过早的方法结论。**
   - 离线 rule replay 显示 motif-aware 规则的 false-stop rate 最低，说明
     Verus-specific steering 值得研究；但它不是 live repair 证据。
   - action information gain 的工程实现可用，但多轮 matched-control 实验
     发现 action artifact 不能稳定优于 shuffled/irrelevant controls，因此
     不能声称 action IG 已经找到有用 skill。
   - patch/full-proof IG 出现正向 pilot signal，尤其 full proof 在 6/6 状态
     为正，但样本只有 3 traces / 6 states，仍是 self-supervised proxy。

3. **把研究主线从“先做复杂 self-evolution”纠正为“先做简单、真实、可证伪
   的 trace-distilled prompt baseline”。**
   - 最终系统指标改为 solved rate、uncached tokens/solved、wall time、
     tool iterations 和 model cost。
   - IG 降级为 artifact ranking / diagnosis 的辅助指标。
   - “击败 hands-off”的第一定义是：结果相当但 token 更少，或者更小模型
     加知识后接近大模型；不是单纯提高 offline 分数。

4. **完成了 hands-off 主线的 M0 完整性门槛和 R040 数据选择。**
   - 冻结并审计 9,383 条 hands-off trajectories。
   - 隔离 6 条与 sealed evaluation 近重复的 train traces，最终 exact/near
     overlap 为 0，sealed trace content reads 为 0。
   - 完成统一 Copilot H0/H1/H2 harness；live mechanical smoke 的 usage、
     Verus 和 Lynette 指标均可记录。
   - 从有效 train pool 中确定性选出 30 条 verified traces，task/source 均
     不重复；Anvil/IronKV 各 15，五种 frontier model 各 6。
   - 当前下一步是 R041：蒸馏并冻结 `<=800 tokens` 的 H2 trace prompt 和
     长度匹配的 H1 generic control。

最重要的当前判断是：

> 数据、泄漏控制、测量 harness 和第一批 train trace selection 已经就绪；
> 但“知识能够降低真实 agent 推理成本”的核心 claim 还没有被验证。

## 3. 研究路线如何演变

### 3.1 初始方向：从轨迹中挖规则，减少无效循环

最初问题是：能否从 VeruSAGE/Verusage traces 中发现重复失败、错误—动作循环
和成功 proof skeleton，用规则帮助 agent 少走弯路。

初始候选包含：

- generic repetition rules；
- project-aware rules；
- Verus motif-aware rules；
- proof skeleton cache；
- 基于 verifier error delta 的 continue/reroute 决策。

### 3.2 第一轮纠偏：规则不能阻断强模型思考

自动科研结合 ReAct、Reflexion、Voyager、LATS、AgentSpec、TACO 和 VeruSAGE
等方向，把问题重新定义为：

> Non-blocking verifier-guided self-evolving steering。

核心原则是：

- 不用硬规则替代 LLM 的自由探索；
- hard rule 只用于非法修改、作弊或安全约束；
- 一般知识以 soft recommendation、critique prompt、retrieval hint 或
  sampling prior 的形式注入；
- skill 必须经过 verifier-grounded replay、held-out check 或 live rerun
  才能进入稳定 memory。

### 3.3 第二轮纠偏：用 information gain 衡量 rationale/skill 是否真正有信息

项目随后实现了 artifact-conditioned scoring：

```text
IG(artifact; trajectory_t)
  = score_T(target | trajectory_t, artifact)
    - score_T(target | trajectory_t)
```

目标包括：

- 下一步 observed action；
- proof-relevant patch span；
- 完整 final verified proof。

同时加入 shuffled、irrelevant、same-error 和 exact-token-matched controls，
避免把“多了一段文字”误当成“有用知识”。

### 3.4 当前主线：先做 hands-off trace distillation 的真实 agent baseline

2026-07-17/18 的组内讨论进一步明确：当前优先级不是方法新颖性，也不是立即
构建大型 self-evolution loop，而是：

1. 从 frontier-model + agent 的成功 hands-off traces 中提炼短知识；
2. 在 held-out Verus repair 上，用完全相同的 model/scaffold/budget 比较；
3. 看是否保持 solved rate，同时减少 token 或支持更小模型；
4. 只有简单 prompt baseline 有信号后，再研究压缩、retrieval、IG ranking、
   skill evolution 或 harness evolution。

## 4. 已完成工作的时间线与结果

| 时间 | 阶段 | 做了什么 | 结果/决策 |
|---|---|---|---|
| 07-03 | 科研基础设施 | 建立 research memory、只读数据约束、项目卡和索引 | 完成；成为后续 canonical memory |
| 07-03 | 初始 scaffold 与离线 replay | 解析 traces、挖 candidate rules、做 generic/project/motif ablation | 工程可用；motif-aware 最安全，但仅为离线 proxy |
| 07-03 | 研究 framing | 提出 non-blocking verifier-guided steering | 采用；反对硬 gate 阻断强模型探索 |
| 07-04 | 初版 IG probe | 建 action/full-proof/patch targets 与 QwQ scorer | 测量可行；irrelevant control 也为正，方法结论不成立 |
| 07-11 | ATLAS taxonomy | 40 train tasks 上归纳 Verus failure taxonomy | 28 codes，36/36 calls 成功；只证明 taxonomy induction 可行 |
| 07-11 | Corrected action IG | 固定 action ontology、补 matched controls 和 audit | artifact-quality gate 失败，不允许 skill-quality claim |
| 07-13 | Control-null action pilot | 六状态、五种 token-matched null controls | STOP：specific gain 为负，禁止按原计划扩展 |
| 07-14 | Qwen3.6 三目标 IG | action/patch/full-proof 共 126 cases | full-proof signal 最强，但仍是 3-trace proxy，audit=`WARN` |
| 07-17/18 | hands-off 路线转向 | 从聊天约束提炼真实成本目标与实验顺序 | 确立 trace-distilled prompt 为第一主线 |
| 07-19 | 长线实验设计 | 冻结 R036-R061 gated roadmap | 完成；昂贵实验受 gate 控制 |
| 07-19/20 | M0，R036-R039 | corpus inventory、leakage audit、harness、mechanical smoke | M0=`GO`，只允许进入 train-only R040-R041 |
| 07-20 | R040 | 选 30 条 leakage-safe verified train traces | 完成；artifact audit=`PASS` |
| 07-20 | repo/data contract | 规划 `verus-skill-learning` 与外置数据 roots | 决策完成；尚待正式迁移/发布 |

## 5. 详细结果

### 5.1 初始离线 rule replay

数据快照：

- traces：2,996；
- verified：1,691；
- nonverified：1,305；
- effective total tokens：1,524,386,760。

| policy | 覆盖 failed traces | 估计节省 failed tokens | false-stop rate | peer diff |
|---|---:|---:|---:|---:|
| generic | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project-aware | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif-aware | 227 | 309,382,084 | 0.005322 | 0.777778 |

解释：

- generic 规则覆盖量最大，但误停风险最高；
- motif-aware 覆盖更窄，却显著更安全；
- 结果支持“Verus-specific policy 值得研究”，但不能证明 live solved rate
  或实际 token cost 已改善。

主要产物：

- `verus-self-evolve-scaffold/runs/latest/`
- `verus-self-evolve-scaffold/docs/eval_summary.md`

### 5.2 初版 information-gain 测量管线

完成内容：

- 3 条 verified traces；
- 7 个 early/middle/late trajectory prefix states；
- action、patch span、full-proof targets；
- 84 个 scoring cases；
- QwQ-32B/vLLM token-logprob scorer；
- raw prompt 和 explicit action-prediction prompt 对比。

初版 explicit action prompt 的 artifact mean IG：

| artifact | mean IG |
|---|---:|
| trace rationale | 1.0817 |
| generic skill | 0.8894 |
| irrelevant control | 0.6295 |

结论：测量工程通过，但 irrelevant control 同样为正，因此不能说明 trace
rationale 的正增益来自特定知识。

### 5.3 ATLAS Verus failure taxonomy pilot

设置：

- 40 个唯一 train tasks；
- 12 个 reserved eval tasks；
- normalized-task overlap：0；
- ATLAS commit `afbf010117ce`；
- Codex `gpt-5.6-sol/high`。

结果：

- final taxonomy：28 codes；
- system / role / Verus-domain：6 / 11 / 11；
- Codex calls：36/36 成功；
- Step-7 structural violations：0。

结论：证明可以从 corpus 中归纳紧凑、Verus-specific 的 failure vocabulary；
没有证明分类准确率，也没有证明 taxonomy 能改善 repair。

主要产物：

- `atlas-verusage-reproduction/runs/pilot_v1/REPORT.md`
- `atlas-verusage-reproduction/runs/pilot_v1/taxonomy_sol_high_v2/`

### 5.4 Corrected action IG 与第一次明确否定

在 3 条 traces / 7 个 states 上重新定义 observed-action PMI，并加入更严格
controls。

| comparison | trace-control mean bits | trace wins |
|---|---:|---:|
| trace vs shuffled | +0.0449 | 3/7 |
| trace vs irrelevant | -0.0748 | 2/7 |
| trace vs generic | +0.8014 | 5/7 |
| trace vs word-count neutral | +0.7497 | 6/7 |

独立重算确认 PMI/entropy 数学实现正确，但 artifact-quality hypothesis 不被
支持：irrelevant 平均优于 trace，shuffled 与 trace 接近；原 7 个 action labels
中还有 1 个被拒绝。

科研决策：不允许声称 skill quality 或 downstream improvement。

### 5.5 Control-null action pilot 与 STOP 决策

设置：

- 3 条 verified traces；
- 6 个 locally accepted action states；
- 22-way fixed ontology；
- 5 个 exact-token-matched null controls；
- QwQ-32B。

| 指标 | 实际结果 | 预设 gate |
|---|---:|---:|
| mean specific gain | -0.2079 bits | > 0 |
| positive states | 2/6 | >= 4/6 |
| wins vs same-error | 3/6 | >= 4/6 |
| wins vs shuffled | 2/6 | >= 4/6 |
| wins vs irrelevant | 2/6 | >= 4/6 |
| evidence mean conditional PMI | -0.1922 bits | 诊断指标 |

此外，固定 A-V candidates 的 raw probability mass 只有
`5.00e-12` 至 `3.96e-10`，说明 22-way candidate-normalized PMI 是强制选择
proxy，不是 QwQ 自然 action policy。

科研决策：`STOP` 原 action-only 扩展路线；先重做 scoring interface 或改为
actual agent-generated reasoning/action，再谈扩规模。

### 5.6 Qwen3.6 action/patch/full-proof 三目标 IG

设置：

- local `Qwen3.6-27B`；
- HF exact chunked teacher forcing；
- 3 traces / 6 states；
- 3 targets × 7 artifact/control conditions = 126 cases；
- context length 131,072，0 truncation；
- 保存 1,499,498 行 token-level score；
- 总运行约 51 分 33 秒。

| target | mean specific total IG | bits/target-token | positive states |
|---|---:|---:|---:|
| action | 0.9612 | 0.309137 | 4/6 |
| patch span | 12.7686 | 0.017837 | 4/6 |
| full proof | 22.3031 | 0.001580 | 6/6 |

关键 matched-control 结果：

- action vs irrelevant：mean `-0.5398` bits，wins `2/6`；
- action vs shuffled：mean `-0.6236` bits，wins `3/6`；
- patch vs irrelevant：mean `+15.8062` bits，wins `5/6`；
- patch vs shuffled：mean `-3.0562` bits，wins `4/6`；
- full proof vs irrelevant：mean `+50.6492` bits，wins `6/6`；
- full proof vs shuffled：mean `+16.0122` bits，wins `6/6`。

结论：

- action artifact 仍不能通过 control separation gate；
- patch 有混合信号；
- full-proof signal 最强，但 per-token effect 小且样本极少；
- 独立 GPT-5.5 xhigh audit verdict 为 `WARN`；
- 该结果只支持 IG arithmetic/mechanical feasibility，不支持 solved rate、
  token efficiency、held-out generalization 或 agent improvement。

主要产物：

- `refine-logs/EXPERIMENT_RESULTS_20260714_162614.md`
- `refine-logs/EXPERIMENT_AUDIT_20260714_163500.md`
- `verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/`

### 5.7 Hands-off trace distillation 长线实验设计

冻结了 R036-R061 的 gated roadmap，最多支持两个核心 claim：

1. 同模型、同 scaffold 下，trace knowledge 保持 held-out solved rate，同时
   降低 uncached tokens/solved；
2. 同一 frozen knowledge 能改善 local 27B，并缩小它与 frontier no-knowledge
   baseline 的差距。

主要条件：

- H0：原 hands-off prompt；
- H1：长度匹配 generic control；
- H2：`<=800 tokens` trace-distilled global prompt；
- H3/H4：retrieved / mismatched skills，仅在 H2 dev gate 后启用。

Dev GO gate：

- H2 相对 H0 不多损失超过 1 个 security-valid solve；
- total uncached tokens/solved 至少下降 15%；
- H2 优于 H1；
- illegal-edit 不增加。

### 5.8 M0：corpus、leakage、harness 和 live mechanical smoke

#### R036：corpus inventory

- 总 trajectories：9,383；
- train：3,347；
- dev：3,015；
- sealed test：3,021；
- sealed trace content reads：0；
- 历史 train logs 中可解析 usage：283/3,347。

这也证明历史 usage coverage 很低，因此未来成本 claim 必须依靠 live harness
accounting，不能只用旧日志。

#### R037：split 和 leakage audit

初始审计发现 IronKV train 与 sealed NR evaluation 存在 near-duplicate。采用
fixed-point quarantine 后：

- 移除 train traces：6；
- effective train：3,341；
- final exact-name overlap：0；
- final exact-code overlap：0；
- 7-token-shingle Jaccard `>=0.90` near overlap：0；
- sealed content reads：0。

#### R038：统一 hands-off harness

实现并固定：

- Copilot CLI prompt injection；
- H0/H1/H2 仅 knowledge payload 不同；
- source/base-prompt/payload hashes；
- provider/model/version；
- candidate capture；
- current/historical Copilot token footer parsing；
- timeout 与 footer flush；
- Verus validation；
- Lynette target-mode executable-code safety comparison；
- output collision 和 sealed path 防护。

M0 共 15 个 regression tests 通过；加入 R040 后总计 17 tests 通过。

#### R039：live mechanical smoke

QwQ direct/adapter route 没有产生可执行 tool calls，判定为 model/scaffold
incompatibility，而非 harness failure。随后切换到先前工具调用验证过的
Qwen3.6-27B。

| condition | input tokens | output tokens | wall time | Verus | Lynette |
|---|---:|---:|---:|---|---|
| H0 | 1.2M | 11.1k | 516s | FAIL | PASS |
| H1 | 1.1M | 10.1k | 478s | FAIL | PASS |
| H2 | 1.3M | 11.8k | 560s | FAIL | PASS |

三个 canonical runs 都生成了 candidate，并最终耗尽 32,768-token context。
这暴露了一个真实 failure mode：agent 在简单 proof 上反复试错，产生巨大
context/token cost。

M0 结论为 `GO`，但含义仅是：

- 数据边界、usage accounting、Verus/Lynette validation 和 failure-path
  recording 已经机械可用；
- 可以进入 train-only R040-R041；
- 不能把 0/3 solved 当作知识效果；
- 不能替代 R042 所需的 frontier-model baseline。

运行后 vLLM 四个 worker 忽略 SIGTERM，最终按明确 PID 强制清理；GPU 0-3
恢复到 1 MiB、0% utilization。

主要产物：

- `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/`
- `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/m0_summary.json`

### 5.9 R040：30 条 train traces 的确定性选择

输入：R037 后的 3,341 条 effective train rows。

成功定义：effective-train row 具有非空且实际存在的 paired verified artifact。

选择规则：

- 规范化 task ID 去重；
- 规范化 source hash 去重；
- Anvil/IronKV 平衡；
- Opus 4.5、Sonnet 4、Sonnet 4.5、GPT-5、o4 平衡；
- 使用 train log 的 motif/error-family/variant 关键词标签做 diversity sampling；
- 标签只用于采样，不声称 taxonomy accuracy。

结果：

- selected traces：30；
- unique normalized tasks：30；
- unique normalized sources：30；
- Anvil / IronKV：15 / 15；
- 五种已知模型：每种 6；
- corpus variants：5/5 都覆盖；
- selected log + verified path audit：30/30 PASS；
- sealed trace content reads：0。

失败与修复记录：

- attempt1：summary serialization 的 Python boolean 拼写错误；
- attempt2：把 `verified` 非空字典误当成功，但其中 3 条 `path=null`；
- attempt3：改为严格检查 `verified.path` 非空并验证文件存在，成为 canonical。

Canonical JSONL SHA-256：

```text
fa192540148c6ad5a82fe239ca977aaa8c0998c2483717ca8e46f23caa32281b
```

主要产物：

- `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/selected_traces.jsonl`
- `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/selection_summary.json`

### 5.10 Repository 与数据分离决策

决定将活跃代码仓库命名为 `verus-skill-learning`，而 full trace corpora 和
大型 run outputs 不进入 Git。

预定接口：

```text
VERUS_SKILL_DATA_ROOT=/absolute/path/to/verus-skill-learning-data
VERUS_SKILL_RUN_ROOT=/absolute/path/to/verus-skill-learning-runs
```

代码仓库保存：

- source、tests、configs、docs；
- schemas、hashed manifests、split metadata；
- small fixtures 和 compact result summaries。

外置保存：

- raw trajectories；
- sealed test corpora；
- token-level score tables；
- large run outputs。

原因：legacy repo 已跟踪约 309,688 个文件，Git pack 约 1.22 GiB，不适合作为
新的协作开发仓库。该决策已经完成，但正式迁移、license/secret audit 和 remote
创建尚未执行。

## 6. 已实现的主要工程产物

| 产物 | 作用 |
|---|---|
| `verus-self-evolve-scaffold/src/verus_self_evolve/` | trace parsing、rule mining、IG scoring、M0/M1 tools |
| `verus-self-evolve-scaffold/tests/` | parser、scorer、harness、timeout、安全与 selection 回归测试 |
| `verus-self-evolve-scaffold/runs/latest/` | 初始离线 rule replay |
| `verus-self-evolve-scaffold/runs/corrected_ig_20260711/` | corrected action IG |
| `verus-self-evolve-scaffold/runs/control_null_ig_20260713/` | matched-null STOP 实验 |
| `verus-self-evolve-scaffold/runs/qwen36_three_target_ig_20260714/` | 三目标 exact-scoring pilot |
| `atlas-verusage-reproduction/runs/pilot_v1/` | ATLAS taxonomy pilot |
| `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/` | M0 和 R040 hands-off 主线 |
| `refine-logs/EXPERIMENT_PLAN.md` | R036-R061 canonical roadmap |
| `refine-logs/EXPERIMENT_TRACKER.md` | 当前实验状态 |
| `research_memory/` | canonical research memory |

## 7. 自动科研中发现并修复的问题

自动科研的价值不仅是产生正结果，也包括发现实验设计和工程中的隐蔽错误。

已发现并修复：

1. 历史 usage regex 不兼容部分 model-line 格式，首次解析 coverage 为 0；
2. 新版 Copilot footer 使用 `Tokens ↑ ... • ↓ ...`，旧 parser 无法识别；
3. harness 的 relative tool/output path 在 live fixture 中有缺陷；
4. timeout 直接 kill 导致 Copilot token footer 丢失，后改为 graceful flush；
5. QwQ 能输出类似 tool-call 的文字，但 Copilot 实际收到 `tool_calls=[]`；
6. Qwen vLLM shutdown 后 worker 忽略 SIGTERM、占用显存，需要精确 PID cleanup；
7. R040 attempt1 的 serializer boolean typo；
8. R040 attempt2 把 `verified.path=null` 错判为成功；
9. action IG 中 positive mean 会被 irrelevant/shuffled controls 混淆；
10. 固定 22-way action candidates 的 raw probability mass 极低，不能当自然 policy。

这些问题都被保留在 run log、failed attempt 或 audit 中，没有删除不利结果。

## 8. 目前哪些结论成立，哪些不成立

### 8.1 目前有证据支持

- 能从 Verus traces 构建可执行、可复算的 parser/scorer/harness。
- motif-aware offline rules 比 generic hard gates 更低 false-stop。
- 可以从少量 traces 归纳结构化 Verus failure taxonomy。
- action/patch/full-proof token-level IG 可以精确计算。
- full-proof target 在当前极小 pilot 中有最强 control separation signal。
- 9,383 条 hands-off corpus 可以在 sealed-content-zero-read 条件下建立
  leakage-safe split。
- H0/H1/H2 live mechanical metrics 可以由同一个 Copilot harness 记录。
- 已获得 30 条平衡、去重、verified、train-only 的蒸馏输入。

### 8.2 目前没有证据支持

- 不能声称任何 distilled skill 已经提高真实 Verus solved rate。
- 不能声称 action IG 能可靠识别有用 rationale。
- 不能声称 offline token-saving estimate 等价于 live token saving。
- 不能声称 Qwen3.6 smoke 中 H2 比 H0/H1 更好；三者均未解出任务。
- 不能声称 full-proof IG 已经跨 task/project 泛化。
- 不能声称小模型加知识已经达到 frontier-model baseline。
- 不能声称 sealed test 上有任何效果；sealed evaluation 尚未运行。

## 9. 当前状态

截至 `2026-07-20`：

- R036：DONE；
- R037：DONE；
- R038：DONE；
- R039：GO（mechanical only）；
- R040：DONE；
- R041：TODO；
- R042-R044：等待 R041 prompt freeze；其中 frontier runs 还需要 cloud auth；
- R046-R061：按 roadmap gate 暂时 BLOCKED/CONDITIONAL。

当前 readiness：

- 数据 provenance：ready；
- leakage control：ready；
- train subset：ready；
- prompt injection harness：ready；
- live usage accounting：ready；
- Verus/Lynette validation：ready；
- distilled prompt：尚未生成；
- frontier dev baseline：尚未运行；
- 核心方法 claim：尚未验证。

## 10. 下一步计划

### R041：蒸馏并冻结第一版 prompts

输入只允许使用 canonical R040 attempt3 的 30 条 train traces。

需要产出：

- H2：`<=800 tokens` 的 trace-distilled global prompt；
- H1：与 H2 长度匹配的 generic Verus advice；
- 每条知识到 source trace IDs 的 provenance table；
- prompt SHA-256、bytes、words、token counts；
- prohibited-term scan，禁止 `assume`、`admit`、`external_body` 等绕过；
- distillation model、input/output tokens、wall time 和 human edit cost；
- inference cost 与一次性 distillation cost 分开记录。

### R042-R044：同模型 paired dev experiment

在 OS/VE/ST/NO dev tasks 上比较：

- H0 original hands-off；
- H1 generic control；
- H2 trace-distilled prompt。

必须固定同一：

- frontier model；
- Copilot scaffold/version；
- tools/permissions；
- reasoning/search budget；
- task snapshot；
- Verus/Lynette checker；
- run order randomization 规则。

只有 H2 通过 dev gate，才进入压缩、retrieval、ablation 和 sealed test。

## 11. Canonical evidence 索引

- 当前状态：`research_memory/CURRENT.md`
- 项目卡：`research_memory/projects/verus_self_evolving/PROJECT.md`
- 初始 offline summary：`verus-self-evolve-scaffold/docs/eval_summary.md`
- non-blocking idea：
  `research_memory/projects/verus_self_evolving/ideas/20260703-100812-non-blocking-verifier-guided-self-evolving-steering/ENTRY.md`
- initial IG：
  `research_memory/projects/verus_self_evolving/experiments/20260704-103535-information-gain-reward-probe/ENTRY.md`
- ATLAS：
  `research_memory/projects/verus_self_evolving/experiments/20260711-095153-atlas-adaptive-failure-taxonomy-reproduction-for-verusage-traces/ENTRY.md`
- corrected action IG：
  `research_memory/projects/verus_self_evolving/experiments/20260711-145632-corrected-action-information-gain-pilot-and-audit/ENTRY.md`
- control-null STOP：
  `research_memory/projects/verus_self_evolving/experiments/20260713-141547-control-null-direct-action-information-gain-pilot/ENTRY.md`
- three-target IG：
  `research_memory/projects/verus_self_evolving/experiments/20260714-164002-qwen3-6-three-target-information-gain-pilot/ENTRY.md`
- hands-off meeting：
  `research_memory/projects/verus_self_evolving/meetings/20260718-112059-hands-off-trajectory-distillation-and-inference-cost-objective/ENTRY.md`
- long-horizon roadmap：
  `research_memory/projects/verus_self_evolving/experiments/20260719-103727-hands-off-trace-distillation-long-horizon-experiment-roadmap/ENTRY.md`
- M0：
  `research_memory/projects/verus_self_evolving/experiments/20260720-001046-m0-hands-off-corpus-integrity-and-unified-harness-execution/ENTRY.md`
- R040：
  `research_memory/projects/verus_self_evolving/experiments/20260720-164228-r040-leakage-safe-stratified-train-trace-selection/ENTRY.md`
- repo/data contract：
  `research_memory/projects/verus_self_evolving/decisions/20260720-163408-verus-skill-learning-repository-and-data-separation-contract/ENTRY.md`

## 12. 最终总结

自动科研目前并没有产出一个可以直接宣称成功的新算法，但已经完成了更重要的
前置工作：

- 把一个模糊的“self-evolving agent”想法收敛为可证伪的成本—效果问题；
- 建立了 trace、scorer、control、audit、split 和 live harness；
- 用 matched controls 否决了不可靠的 action-IG 结论；
- 找到 full-proof IG 这一值得继续验证、但尚未成熟的信号；
- 完成 leakage-safe hands-off corpus 和第一批 30 条蒸馏 traces；
- 明确下一实验必须直接测真实 agent 的 solved rate 与 token cost。

因此，当前项目已经从“想法探索期”进入“第一版真实方法实验准备完成期”。
R041-R044 将决定 trace-derived knowledge 是否真正有用；在此之前，不应对外
宣称 agent performance 或 inference efficiency 已经提高。
