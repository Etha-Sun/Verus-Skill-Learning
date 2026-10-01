# Forty task augmentation experiment and budget plan

这份方案落实 10 月 1 日会议的近期目标：在 40 道来源训练题上比较基础 augmentation
与 SkillOpt，取得 from-scratch 下游结果，并记录学习成本。当前小试验尚未证明增强收益。
本文给出建议配置和代码审计；金额、模型切换和执行配置尚未冻结，也没有因此启动实验。

## Recommended first experiment

固定现有 train40 / val20 / test20 划分，先完成一次学习更新。首轮每道符合条件的题
最多新增一条 hint continuation；保留全部 40 条 original，包括失败轨迹。
先不跑三分支、全部分组消融或 hint 与 obfs 的组合。

| 条件 | 学习证据与产物 | 用途 |
|---|---|---|
| S0 | 冻结的 initial skill，不做新提炼 | 共用参考点；不等同于完全无 skill |
| S | 40 条 original，原生 SkillOpt 的 success/failure 分组和 plain skill | 主要基线 |
| O | 同样 40 条 original，同题分析后形成 card bank | 分离卡片方法与增强数据的影响 |
| H | 同样 40 条 original，加上至多每题一条 hint continuation，形成 card bank | 主要增强方法 |

S 与 H 比较整套方法；O 与 H 使用相同提炼规则、卡片限制、初始 skill 和部署协议，
检验给定学习预算策略下加入增强经历的效果。O/H 每道来源题权重为一，不能把分支
当作独立训练题。四组都保留，避免只比较 plain skill 与 cards 后把全部差异归因于 hint。

**重要的适用范围：**现有 hint teacher 依赖 original 的 verified final，并要求
Verus 和 Lynette 都通过。历史 600 秒 train40 只有 23 道成功；若复用该轮且原始文件
齐全，eligible 数最多为 23，还可能因缺少非最终 checkpoint 而减少。因此总轨迹数是
`40 + m`，其中 `m <= eligible <= 40`；不是自动得到 80，更不是 160。
新采样的成功数未知。失败来源题仍进入 S/O/H 的原始证据，不得只留易题。

证据范围补充：23/40 来自历史实验汇总；本机已直接核对恢复的 IR/AC/AL 三条
original 的 manifest、事件文件和最终双验证结果，尚未找到全量 40 条。上述 eligible
上界是基于历史统计和当前 prepare 断言的推断，不是已完成的逐题资格审计。

推荐默认重新采样一次共用的 original40，预计只占数美元，能统一新合同。
只有服务器上已有轨迹的初始 skill、模型、reasoning、工具链、任务预算、源码 hash、
错误重试和完整性均吻合时才复用。历史固定配置 actor 为 max，而近期 hint actor 为 high，
不能默认混用。物理采样可共享一次；计算每个方法的学习成本时，各自计入完整 original 成本。

## Model and runtime proposal

- Actor 和 teacher 使用 `deepseek-v4-pro`，reasoning high；actor 每次任务 600 秒，
  请求输出上限建议显式设为 32,768，teacher 为 8,192。这些都是新实验建议，
  不是历史 Qwen 运行参数，也不是累计会话输出上限。
- Actor 从 4 个 workers 开始；等待预算 reservation 的时间不应耗掉任务的 600 秒。
  原有 `fixed_600s_v1` 合同固定了 max、40 workers 和 Sol 提炼等条件，必须创建新的
  实验合同并保留原合同，不能直接改历史配置或跳过审计。
- 为完整比较美元学习预算，推荐把 S/O/H 的 extractor 都接到同一 DeepSeek
  后端，reasoning high，保留各方法的分析和更新算法。当前 fork extractor 使用
  Codex shell 读取证据路径；切模型名不能让直接 API 读到这些文件，需要适配。
- 若该适配影响近期交付，三个学习条件统一保留现有 Sol/high，可先做效果实验。
  此时 API 现金支出与 Sol input/output token、调用数和额度分开记录；不能把额度调用
  按零成本处理，也不能称为完整的美元预算匹配。两种模式须在开跑前择一冻结。
- 不在主实验同时换 Flash。官方 Flash 别名和价格已经变化，会再引入模型变量。
  记录请求模型、返回模型、能力目录和价格快照；服务端别名不等于不可变模型版本。

## Hint selection and card construction

第一轮选点规则应简单且可复现：在 eligible 的非最终 checkpoint 中，选择按累计输出
token 衡量、验证状态长时间无改善区间的起点；并列取较早位置，没有可用停滞段时
用确定性的中间 checkpoint。无法构造区间或无合法点的题保留 original-only。
这个规则是待实现提案；验证状态只是进展代理，不能声称等同于语义 code progress。
先用训练数据审计选点，随后冻结，不根据 validation 表现挑 checkpoint。

Teacher 可以看训练题完整 hindsight；actor 只获得冻结 checkpoint、允许的上下文和
文字 hint。Actor 不得读取 final proof、teacher 私有文件或其他实验目录。
保留失败、超时及有害 hint 分支及费用，不只分析成功分支。

O/H 首轮均建议每题至多两条带来源的 proposals，要求 Trigger / Action / Why /
Validate / Avoid when。先用确定性精确去重并合并 provenance，保留不同策略；
不做跨题语义 merge，也不套用 native baseline 的全局四 edits 截断。最多 80 条
proposals 不意味着必须产出 80 张卡。空产物、无依据建议和任务专属 proof 必须被审计识别。
这是建议的新 bank 路径，现有 evidence-bank 仍做语义 merge，不能只删除八题限制。

S/O/H 都提供可审计的 skill artifact。O/H 使用相同索引与检索工具；第一轮允许 agent
读取其自身完整 artifact，所有读取均进入实际上下文和成本记录。当前可直接读全库，
所以不能宣称已经有严格的 top-k 暴露上限。若以后研究固定暴露预算，应另加执行层约束。

## Learning budget design

每个方法的费用按阶段记账：

`C_learning = C_original + C_augmentation + C_reflection + C_finalize`

其中 augmentation 包括 teacher 与 continuation；finalize 包括 merge、选择 edits
和产物整理。Selection validation 单独列为 `C_selection`；最终 held-out 评测另列。
报告总研发支出时全部相加，报告部署效率时使用从头解题的 actor 成本。
重试、失败、截断、未知 usage 都不能消失；reasoning 若已包含在 output 中，不重复计费。

同时保存两套账：实际时间和缓存价格下的付款估计，以及用冻结参考费率重算的学习成本。
前者限制花钱，后者避免高低峰排程混淆方法差异。另报告未加权 input/output、cache
hit/miss 和 wall time；现金价格并不完整代表计算量。

**全 DeepSeek 模式的初始预算提案：每个学习方法参考成本上限 USD 25，
其中至多 USD 5 用于提炼和最终整理。**提炼额度的 20% 先留给收尾，剩余用于 reflection。
这些金额不是会议已批准金额，也不是保证足够的报价。先扫描完整训练输入、运行一个
小型训练 smoke 估价；若不能覆盖约定的全部 40 题分析，就在正式学习前重新冻结额度。
不能用未覆盖 40 题的产物冒充完成 40 题学习。预算不足以生成全部 eligible hint 时，
按预先冻结的跨项目顺序停止新增分支，仍分析所有 original，报告实际 m 和未增强原因。

预算调度需要实现以下行为：

1. 生成前检查能否保留完整提炼额度；每组采用固定、按项目平衡的来源题顺序。
   先保障一次来源题覆盖，再考虑额外 reflection；不能按验证集结果优先花钱。
2. 统一的 provider 层在发请求前原子预留：
   `spent + inflight_reserved + unknown_reserved + request_upper + finalization_reserve <= cap`。
   原始采样、teacher、actor、extractor 和 retries 都必须接入，不能只有 actor 有 guard。
3. 发出的 request 必须带真实生效的输出上限；输入 bound 应与完整请求和模型容量一致。
   Reservation 完成后才启动会消耗任务时限的工作，避免大并发等预算时造成假超时。
4. 到预算边界停止启动新分析，保留已完成且通过结构审计的 proposals，使用预留额度
   收尾；不要半途截断 JSON 后当成成功产物。记录 budget_stop 和未完成范围。
5. 超时或缺失 usage 保持保守占款，调用确实结束后才能核销；不得自动退款后重发。
   断点恢复不得再次收费或遗漏已发生费用。

**相同上限不等于实际花费相同。**首轮按冻结算法完成一次学习更新，S/O 可以自然提前
结束，不为凑金额重复调用。报告各自实际花费及上限，最多声称在该预算约束下的比较。
若要证明严格等成本优势，后续应允许 baseline 使用剩余额度继续更新或重采样，
在多个总学习预算点比较成本与成功率；不能用一次便宜 baseline 对一次昂贵 H 替代该证据。
首轮只评测一个预先冻结的主预算点，不为每个中间 proposal 做 validation，以免选择成本膨胀。

## Cost estimate

本节是排期估算。历史固定 600 秒 epoch 的 S0/train40/S1 共 80 个任务已知 actor
费用为 USD 8.035293；扣除两次 val20 的 1.722547 和 1.844379，train40 约为
USD 4.468367，另有一次 usage 未知的 502。历史 optimizer 使用 Sol 本地额度，不能
计为已知免费。历史数值来自[该轮记录](../research_memory/projects/verus_self_evolving/experiments/20260817-140332-skillopt-deepseek-v4-pro-fixed-80-epoch-1/ENTRY.md)。

截至本次核查，Pro 低峰每百万 token 的 cache hit / miss / output 分别为
USD 0.022 / 0.66 / 1.98，高峰为两倍。模型文档列出 1M context、最高 384K output
和 Responses 支持；这是服务能力，实验仍需自己设更小上限。
[官方价格与模型说明](https://api-docs.deepseek.com/quick_start/pricing/)。

| 支出阶段 | 数量与估算假设 | 低峰估算或建议额度 |
|---|---|---|
| 共用 original 采样 | 40 个完整任务，暂按每题 USD 0.08–0.20 | USD 3.2–8；符合合同的历史复用可免本次付款 |
| Hint teacher 加 continuation | teacher 每次 100k–500k 未缓存输入、至多 8,192 输出；续跑暂按完整任务单价 | m=23 约 USD 3.7–12.6；m=40 约 USD 6.5–21.9 |
| 三组提炼和整理 | 全 DeepSeek 时，每组提议上限 USD 5，需训练输入预检 | 合计至多 USD 15；Sol 模式另报额度，不把 USD 15 当实际账单 |
| 从头 validation | 4 组 × 20 题 × 2 次，每次暂按 USD 0.08–0.20 | USD 12.8–32 |

Teacher 的单次保守估算公式是 `0.66 × input_millions + 1.98 × output_millions`。
如果完整 hindsight 超过上表的 500k 假设，费用会更高；不能静默裁剪证据来套用估价。
长上下文的缓存命中、失败率和实际输出会改变账单，需用目标服务器训练 smoke 校准。

建议为首轮规划约 **USD 40–80 的 API 现金空间**，不是承诺支出也不是已获批准的 cap。
这包括 fresh originals、基础 hint、三组提炼和最多 160 次 validation 的规划量；
最坏组合及额外 retries 可能超过 USD 80，必须由冻结的现金上限停止或调整未启动阶段。
若复用 originals 或 m 较小，可能明显更便宜。高峰模型调用费用翻倍；计划尽量低峰执行，
付款 guard 仍应保守处理跨时段调用。GPU 租用和 Sol 订阅分摊未纳入该 API 估算。
最终 test20 不在首轮：以后冻结 winner 与 baseline 再比较，另算预算。

## Evaluation and stopping rules

先冻结全部 artifacts、预算和顺序，再做四组同题配对评测。第一完整轮共 80 次，
第二完整轮再 80 次。两轮在开跑前排定，交错条件并平衡执行顺序；因预算或基础设施
问题停止时保留不完整标记，不能只补跑赢家、失败题或看完结果临时加样本。
第一轮可提前汇报，但不能与二轮结果混为同一重复数。

主指标为 Verus 与 preservation 均通过的 from-scratch solved rate，同时报告每题
配对结果、所有尝试的 tokens/费用/时间、预算终止、基础设施失败和 exposure。
重复两次不会把 20 道独立题变成 40 道；不确定性分析以题目为单位。
共同成功子集上的效率只作辅助，避免忽略失败消耗。20 题上多一道即五个百分点，
小差异需要谨慎解释。优先查看 H/O 与 H/S 的全部分歧题，追溯证据、检索和实际动作，
同时记录有帮助、无效与有害卡片。信息增益只作为离线辅助代理。

不访问 test20 调参。只有冻结学习方法和选定 baseline 后才安排最终测试；不把此前
18 个 checkpoint 诊断或训练来源上的 hint success 当作 held-out utility。

## Pipeline readiness audit

“现成”指代码路径和既有工程证据；当前机器缺少运行配置，以下都不是本机已经启动的任务。

| 环节 | 已有入口 | 状态和剩余工作 |
|---|---|---|
| Native SkillOpt train40 | `skillopt_verusage.train`，`verusage_codex_pro_sol_fixed80_e1_600s.yaml` | 历史跑通过；配置齐全可复现旧 Pro actor + Sol extractor 合同。新模型分工和预算需要新合同 |
| 原始轨迹重新提炼 | `skillopt_verusage.codex_reoptimize` | 可复用合格 source run；现有 Sol 路径，无完整累计学习预算调度 |
| Hint / no-hint 单题续跑 | `scripts/run_hint_augmentation.py` | 三题路线跑通过；需要 verified final、参数化 actor 设置和新的选点/批量调度 |
| Fork packet 导出 | `scripts/export_skillopt_fork_packets.py` | 按 `tasks/{project}` 存放，固定 v1/v2/no_hint 三组；40 题可能覆盖同项目文件，需唯一 source ID 与可变 arms |
| 原始或增强 card 提炼 | `skillopt_verusage.fork_card_optimize` | 按 `fork_{project}` 生成身份；evidence_bank 超过八来源题拒绝。40 题入库/来源保留及 DeepSeek extractor 适配待做 |
| 从头 validation | `skillopt_verusage.skill_validation` | 完整 20 题检查、冻结配置、skill hash、audit、重复、隔离和费用记录可复用；需新四组合同及 H/S 配对汇总 |
| 统一学习 budget | `budget_guard.py`、provider ledgers | Actor 有跨进程 reservation；teacher 直接请求绕过它，extractor 无同等 admission；端到端尚未实现 |
| Obfs | `feat/obfuscation-certified-predicates`，`2ec5b86` | 有 AC certified rewrite smoke；task export / proof stripping 与解题学习闭环未完成，首轮后置 |

还需优先修复：native Responses 请求缺少 `max_output_tokens` 时，bridge 用 131,072
估算 reservation，却没有把该上限写入发送的 payload。现有 guard 因而不能作为本次
严格上限的完整实现。时间费率只检查 UTC 小时，漏掉当前官方说明的周末和公共假日；
Flash 名称/价格也过时。Pro 费率数字相符，但费用重算仍需正确日历或标记保守估计。
当前用全 1M 未缓存输入预留的方式还会在小预算多 worker 场景造成等待，需要与任务时钟分离。

Validation 的现有配对汇总固定以 `original_only` 为参照，可以支持 H/O；H/S 汇总
需要扩展。现有随机排程会混合 main 阶段的不同 repetitions，首轮 80 次完整配对的
交付需要按 repeat 分块排程或相应配置，不能直接把最早完成的 80 次当作完整第一轮。

## DeepSeek readiness and execution gates

**官方服务有接口；本机尚未就绪；另一台服务器尚未核查。**本会话检查的项目环境
未发现 DeepSeek 凭据或配置文件，run/data root 环境变量未配置，Verus/Lynette 未在 PATH，
历史服务器的数据挂载也不可见。本机另有恢复过来的 run 目录，三条 original 和分支
轨迹可读，具体本机路径保存在忽略的 `.agent-context.local.md`；不能将环境变量未设置
当作本机没有轨迹。Codex、uv、Python 和 bwrap 可用。没有进行认证 API
请求，因此无法确认账户余额、权限、真实模型回包或目标服务器状态。

83 项相关离线测试和 10 个 subtests 通过，涵盖 bridge、费用、fork、hint、card、
validation、selection 与 runner。它们验证代码行为和临时 fixtures，不代表 live readiness。

按以下顺序交付，每一步都有明确完成证据：

1. **确认执行服务器。**使用用户提供的 SSH 别名或配置文件路径加载配置，不在消息中
   粘贴 key；只记录 secret 是否存在。确认 raw data read-only、run root、工具版本和隔离。
2. **修复基础合同。**唯一 task ID、多题/单分支导出、40 题 bank、真实请求 cap、所有
   付费入口的统一预算及断点恢复；用同项目多题和耗尽预算的离线用例验证。
3. **冻结 extractor 选择。**全 DeepSeek 时同时适配 S/O/H，并验证证据读取/来源完整；
   Sol 后备方案则明确采用 API 费用加 token/额度的双账本，不声称全链美元匹配。
4. **账户与工程 smoke。**先认证查模型/余额，再用显式小上限验证 Responses 及工具
   round-trip；最后用训练题验证 actor、Verus/Lynette、隔离、teacher 与 extraction。
   [模型能力查询接口](https://api-docs.deepseek.com/api/list-models/)可检查 output/context/effort。
5. **训练输入预检与预算冻结。**确认 40 个唯一 source ID、eligible 数、完整输入大小、
   收尾余量、每方法学习上限和全局现金上限。仅扫描训练材料，不接触 test。
6. **正式学习与配对评测。**保存可恢复的冻结产物及审计，再运行预定的 80/160 次
   validation；输出 solved/cost/coverage 表和分歧案例。更新研究记忆后供另一服务器接续。

4 workers 下，160 次评测按每次都用满 600 秒计算约 6.7 小时，不含 provider 排队和
额外基础设施开销；fresh40 加最多 40 个 continuation 再约 3.3 小时。代码与配置通过
后可以按一个夜间批次规划；当前影响 10 月 9 日交付的主要不确定性是准备工作与服务配置。

## Deferred comparisons

先取得主比较结果，再优先补 matched checkpoint 的无 hint 重采样，检验新增计算是否
已能解释收益；随后考虑随机/停滞选点、分组、card/plain、每题三分支，以及 obfs。
这些保留在[此前消融矩阵](augmentation-experiment-plan.md)，不是首轮全部必跑条件。
如果首轮没有稳定信号，先分析实际增强信息、来源覆盖与卡片使用，不自动增加到 160 条训练轨迹。
