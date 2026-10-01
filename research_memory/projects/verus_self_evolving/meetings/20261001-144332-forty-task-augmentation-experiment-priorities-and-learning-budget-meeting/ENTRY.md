# Forty task augmentation experiment priorities and learning budget meeting

## Metadata and source boundaries

- project: `verus_self_evolving`
- kind: `meetings`
- created_at: `2026-10-01T14:43:32`
- status: `reviewed_summary_execution_contract_pending`
- scope: 用户要求理解会议和当前研究进度；本轮仅整理、核对与更新研究记忆。
- sources: 用户提供的完整 ASR 文本（269 行，实质讨论 00:08:20–00:55:31）和
  `Meeting - 260930.md`（80 行），并对照仓库研究记录及现有代码。
- date: 录音口述“今天是 10 月 1 号”；汇报文件标为 260930，转写文件前缀为
  20261002052807。此处沿用口述日期，不据文件名推断实际录制日期或时区。
- transcript SHA-256: `85108c7dd8dcef27b837480fc29d4370090d0b297aabeb069616250cf35c986b`
- presentation SHA-256: `e43d2c858d51823e2cef9d01b3c79b919202c0b4e2c0e19a6d57dd5d7b9500d4`

读取的是转写文本，未听取原始音频。汇报材料末尾的图片仅有另一台机器的本地引用，
未随文件提供；有关 progress 图的理解来自转写、历史实验说明和绘图代码。
下文是压缩整理，不是会议逐字稿；原文件保留在本地且不加入版本控制。

## Main outcome

会议将近期优先级收敛到：**先把最基础的 augmentation 方法扩展到 40 道训练题，
与 SkillOpt 在合理、近似匹配的学习预算下完成一次可信的下游比较，再补全面消融。**
老师目前最缺少的是方法有效的量化证据，以及学出的知识为何更有用的实例。
会议没有认为小试验已证明收益，也没有保证扩量后一定有效。

这是相对于 9 月 29 日“先 N=10、有收益后再 N=40”的计划更新。允许先做工程试跑，
但不能继续把所有 N=10 消融或完整矩阵作为 40 题主比较的先决条件。
原来的格式、分组、选点、obfs 等对照仍有研究价值，其近期优先级后移。

关键依据：00:46:15 明确先聚焦 reasonably fair 的有效性数字；00:48:45 明确
40 个训练样本与近似相同的 learn budget；00:54:01 明确先将最基础 augment
方法扩至 40 题。00:55:13 最后对齐的结果分享目标是 **10 月 9 日（周五）**。

## Research rationale and method

### SkillOpt baseline as described in the meeting

SkillOpt 在训练轨迹中先分 success/failure，再以至多 8 条轨迹组成 reflection
minibatch。各组针对同一个 current skill 提出修改，失败组总结缺失指导，成功组
总结可复用策略；随后分侧合并、去重、解决冲突、选取有限 edits，形成候选 skill，
经 validation gate 决定是否接受。学习对象是文本 skill，不是更新 actor 权重。

这是汇报用的概括图。按此前本地代码审计，固定 40 题配置的每组 proposal cap 为 4，
最终 edit cap 随调度变化（初值 4、下限 2）；“最后固定选 3 个”和“一般 3 个 epoch”
是口头举例，不能直接当作本次冻结配置。fast update 的单位是 training step，
本次此前的三题提卡也不等于已经完成新的完整 SkillOpt 训练循环。

### Augmentation hypothesis

原有不同题之间仅按成功/失败分组，可能混合了不同背景下的失败原因。同一道题、
同一可观察状态附近的不同尝试，更有机会支持具体的策略比较：在什么状态下，哪种
动作更有用，哪些替代动作失败或绕路，以及结论的适用边界。

Hint 路线从训练轨迹选点，以 teacher hint 干预后续尝试，再将原前缀与新后缀组织
成分析材料。Hint 不直接给最终 proof 代码；有提示的分支仍可能失败或更慢，会议
00:24:36 明确认可保留这类负例。分析器需要看到 hint、分岔位置和各条实际结果，
才能比较可迁移的决定，而不只是压缩成功轨迹。

Obfs 路线改变训练 problem 的表示，随后重新解题采样。老师在 00:27:03–00:29:18
强调可考虑代码及证明的较广泛变换，以学习对不同写法更稳定的策略；当前只改变小范围
Boolean spec 的实现没有覆盖这个设想。Hint 产生同题解题分支，obfs 产生相关题目，
两者可能组合，但会议倾向先分别看到效果，再考虑组合设计。

目标产物是带 Trigger / Action / Why / Validate / Avoid when 的 cards，配合
简短索引，由 agent 根据当前困难主动检索。会议没有把“卡片格式本身”当作充分的
新颖性主张。核心待验证假设是：新增的可验证经历能否产生原始轨迹分析缺少的有用知识。

## Current progress, reconciled with existing evidence

| 环节 | 已有证据 | 尚不能据此推断 |
|---|---|---|
| Hint 训练经历 | IR/AC/AL 共 3 道独立训练题、19 个 checkpoint；38 条 v1/v2 hint continuation、19 条 no-hint continuation 与 3 条 original 已恢复；同题证据包可组织 | 19 个 checkpoint 不是 19 道独立题；历史运行设置不同，不能直接把成功率差异归因于 hint |
| 卡片提炼 | 原始证据得到 6 张卡，增强证据得到 5 张卡；分支证据转交与来源审计已有实现 | 不代表增强一定增加了新知识；最近结果只是离线 reflect/merge 复用，并非新的完整 40 题优化循环 |
| From-scratch 检索小试验 | 两条件各测 3 道 validation 题，共 6 次：都只解出 AL，IR/AC 均超时；唯一共同成功上增强组记录输出更多 | 尚无成功率或 token 效率增益；少数观测也不足以认定方法一般无效 |
| 局部机制诊断 | 18 次 continuation 全部双验证通过；原始卡和增强卡都能提示部分局部修复 | 增强卡未证明优于原始卡，且不是从头解题主评测；一个无卡样本有过程违规 |
| Obfs 工程 | 本轮只读确认 certified 分支仍为 `2ec5b86`、工作树干净；其已记录 AC 全文件 smoke 连续通过 3 次变换，候选覆盖主要在 AC | 分支文档仍明确 task export / proof stripping 未实现，解题与学习收益未评测；本轮没有重新执行验证或检查外部原始日志 |

实际 retrieval 已观察到不检索、弱相关检索，以及直接读全库绕过 helper 的情况。
所以当前结果存在 bank 覆盖、检索、应用和知识内容等多种可能原因。“目前只有 5 张卡”
只是扩充训练覆盖的动机之一，尚未被证明是效果不足的原因。

Teacher augmentation、card extraction 和 learned-card deployment 是不同阶段：
历史 hint continuation 成功不能替代卡片 utility；分析器读到完整拼接轨迹，不代表
续写 actor 当时回放过原始对话。最终 utility 仍按已有用户决定从原始待证明任务
from scratch 评测，冻结 train-derived skills，保留 40/20/20 划分和最终 test 边界。

## Meeting priorities and what remains open

| 项目 | 本次会议可确认的方向 | 仍需冻结的具体设置 |
|---|---|---|
| 第一轮比较 | 普通 SkillOpt 与最基础增强方法，独立来源训练题扩至 40；先取得可信效果信号 | 第一轮 arms、初始 skill、优化步数/epochs、是否附加 initial-skill 参考 |
| 模型 | 优先利用 DeepSeek，暂不以 Qwen 长预算运行成本卡住主实验 | 精确版本、reasoning、actor/teacher/extractor 分工；现有 extractor 是 Sol/high，“都用 DeepSeek”是否包含提炼器尚不明确 |
| 公平性 | 学习预算大致匹配，给双方合理预算；暂缓追求 wall time 完全相同 | 匹配货币、token 还是两者；是否包含采样、hint teacher、失败重试与 merge |
| 轨迹规模 | 讨论 40 题扩到 160，以及 10 题扩到 40；用于区分同题数与同轨迹数比较 | Hint 例子是每题 original + 3 条新分支，即 160 总量，不是新增 160；未最终冻结每题 K，obfs 的 160 是否含原题也不清楚 |
| Cards 整理 | 希望保留不同方向的卡片，不受单文件少量 edits 的形式限制 | 是否仍做语义去重/冲突检查；卡片上限、长度、部署暴露预算与检索协议 |
| 消融 | 保留 card/plain、random/positive-negative/problem-grouped、original/hint/obfs、random/selected point 等问题 | 不是第一轮全部必跑；也没有要求立即运行 hint × obfs 全组合 |
| 分析交付 | 数字之外，要对比学出的 skill 内容，并回看变好/变差的 trace 解释机制 | 具体分工、样例抽取规则与各人的交付尚未落实 |

00:43:02 的“双方各 10 美元”是预算匹配的举例，**不是已批准的实际金额**。
00:43:40–00:44:18 认可的实现思路是：在分析阶段累计花费，到预算边界后停止增加
分析，再整理已有产物。最终预算范围和 merge 费用是否包含在内还没有定。
00:46:15 暂缓 time 完全匹配，并不等于丢弃成本统计或放开增强一侧的无限开销。

第一轮若 native 单文件与增强卡库同时改变数据、分组、表示和检索，结果支持的是
整套方法的效果；要把收益具体归因于 augmentation，仍需后续匹配变量的消融。
老师接受先完成这种合理公平的主比较，再把 scientific controls 补齐。

## Concrete implementation gaps found in this checkout

以下是本轮代码核对结果，不是录音中已经实现的功能：

1. `skillopt-verusage/src/skillopt_verusage/fork_card_optimize.py` 的 `evidence_bank`
   路径对超过 8 道来源题明确抛错。40 题需要先决定可保留完整来源证据的分级整理，
   或采用经过审计的直接入库设计。不能仅把题数改为 40 就宣称 pipeline ready。
2. 当前 fork 诊断把每道题的证据包当一个 reflection item，`minibatch_size=1`，
   每题最多提 2 个 edits；会议设想的“每题 4 traces、两题凑 8 traces”还不是当前
   运行合同。原始 SkillOpt 每组至多 8 traces、4 proposals 又是另一套设置。
3. 已有 actor 费用 guard 和 optimizer usage ledger，但该提卡入口尚没有会议所说的
   按累计学习费用停止 reflection 的硬限制。最终 edit budget 也不等于费用 budget。
4. 现有 evidence-bank 仍调用语义 merge，只移除了最终四卡截断。00:49:26 的“cards
   不需要 merge、都保留”是新提出的方向；不能当作现有实现。保留不同策略与是否
   去重/检查冲突应分别明确，这里的 merge 也不是 Git 分支合并。
5. 按已有审计，历史选点按 verifier 事件/源码状态；progress-aware 停滞/回退选点
   仍需落成明确规则。需要约定无 verified final、无 eligible 点时如何处理。
6. card search/read 已有接口和暴露审计，但直接读取 cards.json 仍可能绕过接口。
   大实验需要固定实际卡片使用协议，不能把“提供了相同工具”等同于“暴露完全相同”。

## Recommended execution sequence

这是根据会议作出的执行整理建议，不是新的运行授权或已经冻结的实验配置：

1. 写一个最小主比较合同：同一 train-40、两种学习方法、模型角色、预算定义、
   每题分支数、card 整理/提供方式、相同 from-scratch validation 预算与指标。
2. 补齐 40 题提炼路径与学习预算限制；将轨迹生成/teacher、提炼、部署评测费用
   分阶段记录。预算停止时保留完整成功返回的分析，并为剩余整理步骤预留额度。
3. 用少量题完成工程预检，确认来源证据、费用、卡片、验证和完整日志，再运行
   冻结的 40 题主比较。工程预检不替代主结果，也不要求先穷尽 N=10 消融。
4. 汇报双验证成功率、逐题 gains/regressions、全部尝试的 input/output、失败/超时
   和费用；共同成功题的成本可单列，但不能据失败造成的低输出宣称效率优势。
5. 做双向案例分析：有效时展示新经历如何形成规则、该规则如何被读取并改变动作；
   无效时区分重复知识、弱检索、错误应用和失去边界。随后再决定优先补哪些消融。

会议目标约为 10 天，先讨论了 10 月 10–11 日，最后落在 **10 月 9 日分享初步结果**。
不是承诺当天完成整个消融矩阵。汇报者表示先用接下来两天推进启动设置；能跑起来时
在群里报告。与新月的具体分工仍需会后商量。后续采用按进展约会的方式，先发结果，
需要同步讨论时再安排会议；本轮没有发送任何群消息。

## Transcription and interpretation cautions

- skillt / skill odps 等按上下文理解为 SkillOpt；argument/augment 在相关段落
  表示数据增强；obfs/obfuscation 表示变换任务表示；TTS 按 00:38:34 的追问
  理解为 test-time scaling，即给模型更多推理预算。
- 00:25:55 的逻辑例子疑有口误/转写错误：P implies Q 对应 not P OR Q，
  不是 not P AND Q。纪要按讨论“等价改写”的意图理解，不把错误公式写入方法。
- 由最终已验证 proof 逐行删减得到参考，再以 token 为横轴画覆盖率，是 hindsight
  训练分析工具。匹配度下降可能对应有效删减或替代证明，不能直接定义为语义退步；
  单行贪心删减也不保证全局最小证明。需要结合 verifier 状态核对候选选点。
- Verus 接受变换后的 code+proof，不单独证明其与原程序语义等价。会议讨论的
  更广泛生成路线应与现有 certified Boolean 路线明确区分。
- 00:38:05 口述 Qwen3.8 由 6/20 到 17/20，归因于显著增大 token budget；本轮
  未找到对应 run/config。将它作为会议汇报背景，不能与 8 月 26 日 1200 秒的
  blank/S2/Trace2Skill 5/20、7/20、6/20 混为同一轮。此前会话用旧 launcher 的
  8192/131072 设置回答“scale-up 输出上限”，不足以确认这个 17/20 实验的上限。
- DeepSeek 版本讨论有犹豫，会议没有最终冻结型号；不据转写中的版本名称推断
  当前 API 能力、价格或可用性。

## Durable evidence and safety

Repository pointers:

- `docs/augmentation-experiment-plan.md`: 9 月 29 日详细候选矩阵，近期优先级由本纪要更新。
- `research_memory/projects/verus_self_evolving/notes/20260929-181050-group-meeting-augmentation-status-and-from-scratch-scaling-gates/ENTRY.md`: 既有进展、baseline 代码与 obfs 审计。
- `research_memory/projects/verus_self_evolving/experiments/20260926-214543-evidence-aware-card-bank-merge-and-autonomous-retrieval-pilot/ENTRY.md`: 六次 from-scratch 试跑。
- `research_memory/projects/verus_self_evolving/experiments/20260926-231847-frozen-ir-card-checkpoint-mechanism-and-source-excluded-transfer-diagnostic/ENTRY.md`: 18 次局部机制诊断。
- `research_memory/projects/verus_self_evolving/experiments/20260908-215823-verifier-call-output-token-proof-coverage-and-greedy-pruning-pilot/ENTRY.md`: proof coverage 图的定义和局限。

本轮没有启动训练、生成、模型调用、验证器评测或 GPU 作业，没有修改 raw/sealed
数据、旧轨迹或会议原文。记录的是已读材料与实现状态的核对，不宣称重新审计了
外部 run 的完整证据。原始转写、汇报文件与 egg-info 均保持未跟踪；没有提交或推送。
