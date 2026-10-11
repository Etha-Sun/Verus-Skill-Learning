# VeruSAGE 长轨迹经验提炼：诊断与最小实验计划

日期：2026-10-10。状态：方法诊断方案，等待用户确认付费试点；没有启动新 DeepSeek 实验。新颖性结论：incremental but valuable，尚不足以作为论文级新方法宣称。

## 固定的问题锚点

Improve a frozen DeepSeek V4 Pro agent's ability to extract useful, transferable experience from long VeruSAGE repair traces, with downstream budgeted Verus-plus-Lynette success and efficiency as the goals. Start with the existing train40 and validation20. Evaluate Verus-specific claims on VeruSAGE; a claim of general code-generation benefit requires a later code-generation benchmark.

具体目标是：从训练任务的执行证据中提炼出可在其他同类题使用的经验，改善固定预算下的通过率和开销。长上下文是候选瓶颈，尚不是已证实的解释。现有轨迹、知识合并、适用条件和推理时使用都可能有问题。

## 为什么仍值得做，为什么要收窄论证

“长 trace 有信息”是合理动机，但不代表每个步骤都有学习价值。现有工作也不普遍只做一次性拼接：Trace2Skill 有并行分析与层次合并，SkillOpt 有小批量反思，SKILL-KD 有对比和续跑验证，DeFA 已做依赖关系引导的失败归因 [2–5]。我们必须与这些路线比较，不能以弱拼接基线代表领域。

本地证据同样要求谨慎：78 张增广卡有 71 张只有一个独立题支持；31/40→32/40 的增广收益区间为 [-5,+10]pp；最近 Executive 的 14/20→15/20 伴随时间/费用增加。它们说明当前经验收益不稳定，不能证明长 trace 是原因。已有修正套件的正向结果也保留，但其卡片、索引和库权限一起变化，不能隔离提炼机制。

## 一个主要机制

建议先测试“以 verifier 状态变化为分析单位”，而不是直接扩张 agent 团队或增加新模型。

输入依然是相同训练 trace。解析时把可核查的 pre/post 代码、实际修改、Verus/Lynette 输出、相关 helper 与必要读文件上下文对应起来；分析者据此输出一条条有证据引用的经验，包括适用前提、建议动作和不适用条件。未保存的历史代码、未观察到的内部思考、无法重放的因果链都明确标为未知。

两个关键限制：其一，不把“错误数变少”或“最终参考文本更接近”当作语义进度证明；其二，pre/post 差异只是观察，只有受控重放才支持局部干预结论，依然不能自动推出全轨迹反事实。第一轮不额外加入重放搜索，避免把额外计算误认为表示优势。

复用现有 SkillOpt 合并、skill 注入、公共 evaluator 与账本，只改变分析的证据组织方式。普通层次分析与新方法使用同一经验输出格式、最终 skill 容量和运行时访问接口；不同时改 Executive、检索器、停止规则或预算。

## 三个验证阶段

### 1. 零模型调用的数据与可行性诊断

- 核对 train40 的原始轨迹、分叉 ancestry、快照、代码修改与 verifier 事件的覆盖率；不重新采集 rollout。
- 依据任务来源、trace 长度和快照覆盖预先选定 8 个内部 probe 目标。它们及其所有分叉、同题卡片、答案不得进入学习输入。余下最多 32 个题作为 donor；若近重复任务族需要额外排除，donor 会更少，必须在合同中记录，不能默默放宽隔离。若无法做到任务族隔离，结论只限于现有分布内的任务留出迁移，不能声称跨任务族泛化。
- 区分 trace 的实际文本长度、逐请求累计 token 和缺失内容。当前 shell 未配置数据/输出根路径，必须从经过批准的机器配置恢复；所有实验输出只写到 VERUS_SKILL_RUN_ROOT。
- 确认固定划分实际为 40/20/20。额外 test 池另做来源、重复和既往暴露审计，不能默认当前 test20 从未被看过。

验收：冻结输入哈希、8 个 probe 清单、donor 清单、证据覆盖表和可复用的提炼/evaluator 接入点。若精确状态覆盖不足，先报告，不能伪造“可执行证据”。这些只读核对和计划准备已获当前任务授权；具体源轨迹盘点尚待路径恢复。

### 2. 一次有上限的内部试点

先在 donor 内比较直接长上下文、普通 token 分块和 verifier 分块的分析结果。使用相同证据池及相同总分析预算，记录真实截断、原文访问和证据遗漏。这个分析对照不消耗 probe 的 trace，也不能单凭评审分数宣称下游提升。

随后在 8 个 probe 目标上运行四臂，各 1 次，共 32 个 actor episodes：

| 臂 | 经验来源 / 方法 |
|---|---|
| B0 | 固定基础指导，无本次 trace 学习 |
| B1 | 只用 donor 重新生成的原生 SkillOpt |
| B2 | 只用相同 donor 的普通层次分析与合并 |
| M | 相同 donor、以代码/verifier 变化组织证据的分析 |

B2 与 M 共用合并器、输出 schema、最终 skill token 上限、部署接口；这是主要方法对照。线上结果估计固定部署策略下整个提炼配方的效果，不能完全隔离提炼、读卡选择和运行时遵从的作用；读卡与误用只作诊断。B1 是当前方法对照，B0 是经验是否有净价值的下限。B0 和各臂共用的基础指导也必须审查来源；不能含 probe 特定知识。不能把含 probe ancestry 的 repaired78 当 B1。已有 Trace2Skill 全 40 条构建 wrapper 有精确输入哈希限制；内部子集需要单独的临时适配合同，不能改写历史生产约束。

actor 使用 deepseek-v4-pro，并继承已审查的 Pro/max600s 比较设置和 verifier/toolchain。旧 calibration YAML 的 high/长任务超时不能直接替代当前设置。每次最多 600 秒、两个 workers；最多 5.33 aggregate actor-hours，理想满并发执行时间约 2.67 小时（不是墙钟上限），另加提炼及排队开销。

拟议费用上限：提炼及分析合计 USD5，actor 合计 USD10，总计 USD15。不是价格预测；派发前必须按请求的最大可能费用预留并发在途额度，不能只在结算账本达限后停止。若无法实施可靠的费用预留，试点不得启动。达限停止并保留部分结果；未完成的四臂不能以不匹配的已完成子集冒充完整比较。学习臂的总分析 token/调用额度必须在源轨迹长度盘点后、首次派发前冻结，并计入合并调用；明确前置 direct/chunk/verifier 分析是否属于各臂额度，不能给 M 额外分析；若等预算比较无法在上限内完成，提交不可行结论，不隐式加钱或给新方法额外额度。跨臂次序交错；普通失败/超时不补跑，基础设施无效重试另记全部调用和费用。

验收与停止：零任务/规范/数据泄漏；逐题报告通过、倒退、超时和全尝试资源。新增成功或“无观测通过损失且总 actor token 降低至少15%”只作为扩展线索，不作为显著性或非劣性证明。若 B2 匹配 M，优先保留简单方法；若只提高离线分析评分、没有行为收益，不扩展主张。8 题 1 次只是可行性筛查，不证明稳定性。

### 3. 冻结候选后的正式验证

内部试点支持继续时，再确定全 train40 的提炼合同，冻结一个候选，与同时运行的固定对照在 val20 各做 2 个全新重复，共 80 episodes。这一步另行批准，不包含在 USD15 试点内。

val20 已多轮开发使用，因此结果标为开发验证，不能升级成最终无偏 test。最终 test 必须先完成来源/暴露/任务族审计，冻结方法后一次性评估。按任务聚类给配对差异区间，不能把重复次数当独立题数。

这一机制在概念上能用于带测试的普通代码任务，因此若试点后仍保留这种通用形式，按用户要求增加代码生成评测。可考虑 EvalPlus [8] 的固定、去重且与经验来源分离的任务；另定合同、预算和污染边界。VeruSAGE 始终优先，不在当前阶段同时展开第二条实验线。

## 指标合同

主指标：固定预算内且输入合规的 Verus+Lynette dual-pass solved rate。效率：所有尝试上的 input/output/cache token、时间、费用、超时率；单独报告共同成功配对的条件分析。offline 提炼成本和推理成本都保留，给出摊销所需部署量。information gain、卡数、读卡次数、文字质量和 reviewer 分数仅作诊断。

## 方法审阅与批准边界

ARIS 被选为研究工作流，不是被证明优于其他工具的研究方法。外部 Claude reviewer 180 秒超时，未返回结论；费用/使用量未知，CLI 设置的 USD1 限额不等于已结算费用。补充的独立 Codex 上下文审阅已完成两轮：首轮 REVISE，收窄方案后 READY_FOR_DIAGNOSTIC。它属于同模型家族，不是跨模型验证，也没有独立核实所有论文。原文见 REVIEW_RESPONSE.md。仍需完成任务/来源清单、具体 token/调用额度、并发费用预留、路径/快照/evaluator 接入和部分结果解释后才能派发。

本方案建议进入零调用诊断；付费试点和后续 80 次验证需要分别明确启动授权。工具或 reviewer 的“批准”不代替用户的支出授权，也不证明假设成立。

## 参考文献

[1] Liu et al. Lost in the Middle: How Language Models Use Long Contexts. https://arxiv.org/abs/2307.03172
[2] Ni et al. Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills. https://arxiv.org/abs/2603.25158
[3] Ma et al. SkillOpt: Executive Strategy for Self-Evolving Agent Skills. https://arxiv.org/abs/2605.23904
[4] SKILL-KD: Contrastive Skill Distillation for LLM Agents. https://arxiv.org/abs/2607.28048
[5] DeFA: Dependency-Guided Failure Attribution for LLM Agents. https://arxiv.org/abs/2610.01256
[6] Yang et al. ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration. https://arxiv.org/abs/2605.03042
[7] ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research. https://arxiv.org/abs/2606.07591
[8] EvalPlus official repository. https://github.com/evalplus/evalplus

完整文献覆盖（含 ExpeL、PlugMem 和独立的 EDA Trace2Skill）与工具评价见 LITERATURE_AND_TOOL_AUDIT.md；本地逐项证据见 CRITICAL_REVIEW.md。
