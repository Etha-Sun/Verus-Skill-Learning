# repaired78 的 Trace2Skill-style 组织平行实验

状态：用户批准审计后的剩余题目继续运行；v5保留24条结果，仅补15项未启动和1项技术中止。
费用总上限仍为 USD30，历史已知和未知费用预留均保留，服务器 systemd 持久托管。
任务、skill包、actor配置和原评分不变，衍生汇总单独披露协议/传输异常；见 CONTINUATION_STATUS.md。
初稿日期：2026-10-11；执行状态更新：2026-10-12。
以下路径均相对于仓库根目录；运行产物仅写入 `VERUS_SKILL_RUN_ROOT`。

## 0. 用户确认的约束与执行范围

- 所有新增模型调用统一使用 **DeepSeek V4 Pro/max**：不仅actor，还包括Router、
  Reducer、模型辅助审查和任何修订调用。不偷偷切换便宜模型、其他provider或reasoning档位。
- 使用最新已审阅的router v2，启动构建前冻结文件哈希。主Executive、TASK、
  单次600秒评测预算、工具权限与评分口径保持本计划约定。
- 首轮reference按整个文件读取，内部是合并去重后仍保留条件的多张规则卡；
  内部目录不是第二层按需加载接口。不自行引入在线router、逐卡检索或强制读取。
- 用户要求：遇到影响方法或费用的模糊处及时询问，不默默选一种实现。
  reference粒度、超长组拆分和未决语义冲突须在实际分组可见后审阅，再冻结候选。
- 密钥由运行时从用户确认的本地env文件读取，不输出/复制到仓库、prompt、日志
  或审计记录。用户确认使用相邻workspace的`Trace2Skill/.env.deepseek`；
  目录名称非仓库相对路径，命令行只传路径，不传密钥。固定官方endpoint和Pro/max，
  不从env里的模型字段自动覆盖实验模型。

用户已确认：每题每组1次，共40个episode；候选短索引已审阅并要求开始评测。
评测共享上限原为 USD20，技术中断后用户明确改为 USD30 并要求重新跑。
新上限包含此前评测已结算费用、未知调用的保守预留和合同审查，不含 USD1.74243608 构建费用。
用户另批准两组统一使用本机同版本 Verus，披露 rust_verify 哈希不同于历史运行。
以下保留构建阶段费用记录：构建总上限USD5，
顺序调用、请求前按UTF8输入上界/输出上限及峰时价格预留，未知费用立即停止。
Router初次输出cap65536未完成；用户批准保持完整输入/prompt/Pro-max、改cap131072
重试一次。Reducer每组cap32768（含reasoning）；除此批准外不自动付费重试。
这是构建预算，不是actor每题预算。历史40次评测约USD4.54–5.72，只用于估算；
此前暂拟的 USD10 评测上限已被用户明确改为 USD20，配置检查及合同审查通过后直接启动。
首次Router ledger估算USD0.29765604保留；重试单次保守预留USD0.71604588，
从同一累计USD5预算中扣除，实际以结算ledger为准，不把未完成调用当零费用。
费率依据：2026-10-12 UTC核对的DeepSeek官方pricing页与仓库Pro峰/谷单价一致。
现有ledger时段函数未处理周末/节假日，可能高估；保留其原始估计，不改既有方法代码。
详见 [BUILD_STATUS.md](BUILD_STATUS.md) 的本轮合同、测试与进度。

原runner的合同审查门槛保留，但若需要新增模型审查，审查角色也必须使用上述
DeepSeek配置；历史Astra回执不等于本轮批准，也不授权调用其他模型。

## 1. 要回答的问题

在 Yuechun 推荐的共同配置下，把同一份 repaired78 从“78条扁平短索引 + 独立卡”
改成“语义去重整合 + 按证明问题组织的 references”，能否提高限时双通过率，
或在不降低成功率的情况下减少求解 token、时间和费用？

这里测试的是**组织与整合的组合方案**。Reduce 会改写、合并卡正文，reference
读取会改变一次暴露的信息量，不能把结果单独归因于“分类”或“索引变短”。
读卡少、卡多、没有去重只是待验证的机制假说，不是已经证明的性能瓶颈。

本轮只增加一个平行实验组，不重新收集 trace、不重新生成 hint、不换 Executive，
不直接运行另一套 Trace2Skill benchmark。Trace2Skill 仅作为 reduce 思路和分层文档
形式的参考；用户明确不要求沿用原版算法、router、prompt 或 merge 调度。
我们自行设计组织方法，不宣称复现其原生完整训练方法。

## 2. 已上传输入与版本冻结

基准代码提交：`045b9b2ddd2cfdef00eb6a68f745344fbb8f2dea`。
已拉取5个新提交。以下三个入口均已本地核对数量、唯一 ID 和 manifest SHA-256：

| 输入 | 路径 | 用途 |
|---|---|---|
| original63 | `research_artifacts/deepseek-20261011/cards/original63.json` | 仅历史对照材料，不加入新卡库 |
| augmented78 | `research_artifacts/deepseek-20261011/cards/augmented78.json` | 核对修订来源，不作为本轮基线 |
| repaired78 | `research_artifacts/deepseek-20261011/cards/repaired78.json` | A/B 两组唯一的知识内容起点 |
| 短索引/修订配方 | `skillopt-verusage/review/augmented78_revision.json` | 复原 A 组，保留已修正的边界 |
| 原始 Executive | `skillopt-verusage/skills/initial.md` | 两组正文前缀不变 |
| 已发布控制 SKILL | `research_artifacts/deepseek-20261011/cards/card-repair-validation-20261008-3gtA3H/revised78/bundle/SKILL.md` | 重建一致性检查 |

冻结的本地文件 SHA-256：

```text
repaired78.json  ae38b9ace8560cb7e819eb348d152b916b0486e206b3d09c1b862e8681517f27
initial.md      96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40
revision.json   8536416bc8f40ca20adbd334d68e3e0090f177b798660b099f296f92317b276a
control SKILL   10acd2d687754e70a470fc1d041a7e1308c82c4f34ac108de85d874ab50d07c1
```

注意：发布过程进行了 JSON 规范化/脱敏。需要区分发布文件哈希与历史源文件哈希，
不能把所有已发布副本都当成历史字节级副本。恢复缺少的控制 reader、训练 provenance
时，按 `manifest.json` / `files.jsonl.gz` 定位、校验并仅恢复所需文件；不全量解包
整个1.7GB发布包，也不让构建模型接触其中的 validation 运行结果。

## 3. 实验两组

| 维度 | A：`repaired78_flat` | B：`repaired78_reduce_refs` |
|---|---|---|
| 原始知识 | 同一 repaired78 | 同一 repaired78 |
| Executive | 原始 `initial.md` | 相同字节前缀 |
| 顶层入口 | 现有78条短索引 | 按证明问题分组的短路由目录 |
| 正文 | 原78张卡，不改写 | 组内 reduce 后的 reference 文档 |
| 获取正文 | 自主 `card_read.py <id>` | 自主读取选中的 reference |
| 强制读取/额外检索模型 | 无 | 无 |

A 必须同轮重跑，不能直接拿历史16/20或其他最高成绩当作对照。
B 顶层只放路由、适用/排除信号和 reference 链接，不把全部策略答案前置到 TASK。
两组都允许不读、读后不采用、按需要再读；不增加“停滞后必须读卡”等行为指令。

## 4. 固定配置与允许变化的边界

| 固定项 | 合同要求 |
|---|---|
| TASK | 两组使用当前共同修正的 `build_prompt`，相同标准库根；保存最终文本与哈希 |
| Executive | `skills/initial.md`，不使用 diagnostic-first-v1，不修改终止/候选恢复策略 |
| Actor | `deepseek-v4-pro`，`reasoning_effort=max`，相同模型目录和桥接实现 |
| 预算 | 每 episode 600秒；context 1048576；output cap 131072 |
| 协议 | 现有 native Responses；普通失败不自动重试；provider error fail-closed |
| 并行度 | 共用 runner 的 workers=2，不另给 B 额外 worker/推理预算 |
| 工具/权限 | 相同 Verus、Lynette、工作目录权限、已安装 vstd 只读权限 |
| 检索引导 | `autonomous_retrieval=True` 的可选读取语义；`diagnostic_guidance=False` |
| 题目 | 同一冻结 validation20，原始任务起点，不用挑选过的 checkpoint |
| 判分 | 正常600秒预算内 Verus 与 proof-only safety 双通过 |
| 费用 | 同轮相同价格口径，保留原始 usage/缓存字段与结算账本 |

131072是单请求输出上限，不是整个 episode 的输出 token 总额度。
bridge 的1800秒 request timeout 不替代 actor 的600秒主预算。
运行前核对实际模型 catalog、工具二进制与代码哈希；本次发布不是完整运行环境。

允许变化的白名单：索引结构/措辞、卡内容的去重整合、references 布局、读取入口
与其必要的使用说明。B 的读取助手仅按 ID/路径返回文档并记录暴露内容，不排序、
不搜索、不调用额外模型。路径约束、只读性与 A 保持一致。
除白名单外出现 prompt/tool/permission 差异就停止，不把它混入本实验。

## 5. B 组怎样组织

### 5.1 Inventory：先建立可追溯的78卡清单

- 收集 card ID、正文哈希、短描述、Trigger/Action/Why/Validate/Avoid when。
- 从训练 provenance 恢复源题/轨迹支持；无法恢复的字段标为 unknown，不猜测。
- 区分源题数和同题分支数；同一题的三个 fork 不算三个独立支持。
- 构建输入白名单只含上述卡、索引、原始 Executive 和必要的训练证据。
  不包含 validation/test 题目、答案、解题轨迹或手选相关卡标签。

### 5.2 Cluster：离线 semantic organizer，在线由 actor 自主选读

可审阅prompt草稿：[router_system.md](prompts/router_system.md)；构建模型为
DeepSeek V4 Pro/max。输入/输出与执行边界见 [prompts/README.md](prompts/README.md)。
已实现构建runner、结构验证器与renderer，当前执行进度见BUILD_STATUS。
v2审查见 [router_review.md](prompts/router_review.md)：补充下游使用场景、
分类粒度、Verus入口状态及多用途卡的case级条件路由；不是已验证的分类效果。

**建议实现一个离线 LLM 语义组织角色，可以称为 semantic router，但不是解题时
额外调用的检索 agent。** 它在构建阶段把卡分配到 reference 家族；部署后只留下
静态目录和文档。在线仍由原求解 actor 根据当前证明状态自主选读，无额外模型调用。
这两种 routing 不混为一谈：离线是 card → family，在线是 proof state → reference。

首版采用结构化 LLM 分组，不先引入 embedding 模型、向量库或固定 K 的聚类算法。
用下面的明确阶段实现，不需要常驻多 agent 系统；可由同一构建模型分阶段调用：

1. **提取卡的语义特征。** 从完整正文提取 `proof_object`、`failure_signal`、
   `required_premises`、`repair_action`、`avoid_when` 和 `version_scope`，绑定原 ID。
   不只用旧短描述，否则可能把原索引的模糊边界原样带进分组。
2. **全局提出 taxonomy。** 同时比较78张卡的结构化特征，提出 family 定义及其
   `include_when`、`exclude_when`、与易混淆 family 的区别。分类数由内容决定，
   不预设“压成10组”。量词/见证、时序 lifting 等只作示例，不是强制标签。
3. **按 taxonomy 分配并核对正文。** 输出每张卡的 `primary_family`、可选
   `cross_links`、分配依据和 `needs_review`。依据适用条件与修复动作，不按题号、
   源项目或相同关键词机械归组。每卡恰有一个主要归属，跨组只放链接。
4. **检查组内和组间边界。** 结合完整卡文审查：哪些是真近重复，哪些是同主题
   但不同前提/不同操作，哪些仅词汇相似。记录 `duplicate_candidate`、
   `complementary`、`conditional_alternative` 等关系；同组不代表可合并。
   对不匹配的卡可新建 family 或保留 singleton，不强塞；歧义项进入审查。
5. **冻结分组并生成对比式目录。** 每个 family 给出简短的“何时读/何时不读”，
   必要时指出更合适的相邻 family。比如区分“缺少量词前提”和“有前提但触发失败”，
   而不把两者都写成“quantifier problems”。目录不提供新证明策略。

离线 `cluster_manifest.json` 保存 families、assignments、卡间关系及依据。
同卡的不同适用情形以cases记录，并保留原文定位；整卡只存一次，跨组链接带case
和使用条件。只有跨链接的family只作导航页；Reducer处理有主要归属正文的family，
保留全部cases并输出case到rule的映射，确保链接在reduce后仍然有效。
程序校验：原卡集合与分配集合完全相等、主要归属不重复、所有引用有效、每条分配
可追溯到原文。人工/代理审查不能只看模型自报置信度；逐项检查歧义、跨组近重复
和条件冲突。只可依据卡及训练证据修订，不能用 validation 表现选择 taxonomy。

随后5.3仅对已确认近重复的规则做 reduce，互补规则和有条件的替代方案保留各自
适用范围。这样把“方便找到同类经验”和“可以合并为同一条规则”分成两个判断。

**方法贡献候选**：按证明状态与适用边界组织经验，通过对比式路由减少误匹配，
再进行保留前提/禁用条件的语义整合与证据追溯。不是把“加文件夹”本身当作创新。
目前只是设计假说；是否相对已有工作新颖需另做相关工作核对，有无收益需本轮
对照验证。若要评估外部在线 semantic router，另立消融并计入其时间/token/费用，
不要悄悄加入本轮固定配置。

### 5.3 Reduce：去重但不抹掉边界

可审阅prompt草稿：[reduce_system.md](prompts/reduce_system.md)，同样使用
DeepSeek V4 Pro/max。采用“保留适用条件的去重”，不是把每组强压成一张摘要卡。
输出按规则/claim绑定源卡；独特或无法安全合并的卡由程序原文保留。

- 参考而非照搬 Trace2Skill：合并重复、保留独特信息、依据证据处理冲突、保持简洁、
  reference 创建与顶层链接成对更新；不复制已有 Trace2Skill skill 中的新知识。
- 先组内合并近重复规则；必要时分层 reduce，最后仅统一术语和路由，不强行跨族合并。
- 每条规则保留 Trigger、Action、前提/避免条件、验证要求、版本限制和原 card IDs。
- 如果证据不足以裁决冲突，保留分支条件或显式不确定性；不能凭成功分支补写因果解释。
- 保护 repaired78 中已经修正的内容，尤其量词 implication、时序 lifting 和 API
  适用范围；不因为概括而把修正回滚成更泛化但不成立的建议。
- 78张全部有去向：保留、并入某条规则或重复覆盖。不得静默删卡。
  无法忠实合并的卡保持独立小节/reference，不为压缩率牺牲独特策略。

构建模型统一使用 DeepSeek V4 Pro/max，作为离线构建角色单独记账；实施时冻结
构建 prompt、模型参数、分组顺序、输出上限与调用预算，再启动调用。
允许修正格式/丢失映射等离线审查问题，记录全部修订；禁止用 validation 分数
反复挑选更有利的聚类或摘要版本。正式评测前只冻结一个候选。

### 5.4 部署形态

主文件模板：[SKILL.md.tmpl](templates/SKILL.md.tmpl)；索引条目模板：
[REFERENCE_INDEX_ENTRY.md.tmpl](templates/REFERENCE_INDEX_ENTRY.md.tmpl)。
完整组织与渲染约束见 [templates/README.md](templates/README.md)。固定采用当前
router v2，并在实际构建时冻结其文件哈希，不在运行中自动追随prompt改动。
原Executive逐字保留，只追加自主读取说明与全reference短目录。用户于10月12日
确认精简：每组一行ID/文件链接＋最多150字符英文入口描述，保留关键诊断区别；
完整适用/排除条件、版本限制和邻组区别留在reference正文，不在主文件再次展开。
短索引修订仅改目录，既有37组、72条规则及全部reference字节不变；主文件总字节
不得超过flat control，不能静默截断。这取代初版逐项展开所有边界的过重设计。
family已生成，模板占位符不得进入正式评测。root索引完整覆盖常规正文页、
拆分后的子reference及存在时的跨链接导航页；正文不全文前置到root。

```text
bundle/
  SKILL.md                  原始 Executive + 可选读取说明 + 短分类目录
  reference_read.py         按名称读取并记录结构化事件，无排序/模型调用
  references/
    <proof-family>.md       共性规则 + 条件分支 + 独特卡策略
audit/                      不部署到求解工作区
  cluster_manifest.json     family 定义、卡分配、跨组链接和关系审查
  coverage.json             78个原 card ID 到新规则的完整映射
  provenance.json           规则到原卡再到训练源题的可追溯映射
  reduction_review.json     合并、冲突、保留项和修订记录
```

目录名称为示意，不预先替实际卡库决定主题。root 到 reference 的链接必须可达、
无越界路径或悬挂引用。大组可拆成可单独读取的小文档；不让一次“读相关卡”变成
被动灌入整个卡库。读取长度/内容是处理的一部分，需要完整记录而不是声称已控制。

## 6. 实现顺序与验收

| 阶段 | 工作与拟用入口 | 验收/停止条件 |
|---|---|---|
| P0 输入冻结 | 校验已发布 repaired78、描述、Executive、manifest；重建 A | 78个唯一 ID；A 的 SKILL 与发布控制一致；所有差异有解释 |
| P1 离线组织 | 特征提取、全局 taxonomy、语义分配与边界审查 | 78/78唯一主要归属且可追溯，无 validation/test 输入；不改变源卡 |
| P2 构建 B | reduce生成references，审阅后精简主目录 | 全覆盖、无断链、逐条审查合并；短索引完整且主文件不长于A组 |
| P3 双臂合同 | 薄 wrapper 复用现有 validation driver | TASK/Executive/权限/判分一致，差异仅在白名单 |
| P4 零API检查 | 单元测试、fake actor、部署/日志/统计 dry-run | 不调用 provider；所有预期 episode 与读取事件可核算 |
| P5 正式开发对照 | 预算批准、合同审查后运行预注册的完整矩阵 | 不按中途成绩停跑、挑题或改 B；结束后 bridge drain、全量结算 |
| P6 分析 | 成功率、费用、token、时间与读取机制分析 | 汇报全部结果及无效运行，不把读得更多等同于有用 |

具体代码落点建议：`skillopt-verusage/src/skillopt_verusage/card_organization.py`、
`scripts/validate_card_organization.py` 和对应 `tests/`。复用 `card_bank.build_bundle`、
`skill_artifact.load_skill_artifact`、`scripts/validate_card_revision.py`；参考
`scripts/validate_executive_revision.py` 的共享 TASK/哈希/调度保护，但不要沿用其
换 Executive 的处理，也不要复制一套新评测引擎。

容易踩的两个现有默认值：

1. `validate_card_revision.prepare` 默认只跑4道选定题，必须显式传入完整 val20。
2. 标准库权限默认只给 revised，必须显式设置
   `installed_library_conditions=('old', 'revised')`，保证双臂相同。

重建 A 使用 repaired78 + 原 Executive + 修订短描述，关闭 diagnostic guidance。
扩展读取审计以支持 reference 事件；不能让现有仅识别 `read_ids` 的统计把 B
误记为零读取。直接文件读取也需要从 actor 工具事件识别，区分读目录与读正文。
日志只用于观测，不向求解模型注入额外提醒。

付费运行沿用现有“合同 SHA 绑定审查回执”门槛。缺少运行配置、工具、凭据或批准
预算时停在 dry-run；不得从历史 trace 复制凭据或假定历史额度授权了本轮实验。

## 7. 评测矩阵和统计口径

### 7.1 历史参照与必须复用的口径

历史各轮配置、12个条件的全部有效运行资源、success-only及joint-success表、
四臂检查点诊断已列入 [HISTORICAL_COMPARISONS.md](HISTORICAL_COMPARISONS.md)。
只有同轮内部可直接比较；原始Executive+共同修正TASK的最近全量控制为14/20，
不是修正/引导轮的16/20。本轮重跑A，不将任一历史分数当作固定目标。

本轮遵循该文件第6节：provider有效且正常预算内最终双通过；按 `(task_id, repeat)`
配对；drain后账本结算；同时保留总体、成功分布、共同成功配对和全部物理尝试费用。
成功/超时分布沿用线性分位数；总体/配对资源变化用相同集合的累计量计算。
输入含缓存/重复前缀，reasoning已在输出内，`total_tokens=prompt+completion`。

复用 `scripts/summarize_success_timeout_tokens.py` 的统计函数口径，新增薄
适配器和回归检查，不复用硬编码历史路径。输出`episodes.csv`、`statistics.json`、
配对表、费用清点和读取审计；reference机制指标为新增附表，不替代原指标或改判分。

### 7.2 新实验矩阵

用户已固定 **20题 × 2组 × 1次 = 40个 episode**，全部从原始任务起点启动。
这替代最初两次重复的建议。每臂分母为20，单次随机运行仅提供探索性开发证据；
不按结果补跑第二次或择优取值。生成并审阅候选后才能另行启动评测。

按题/重复交错、平衡 A/B 提交顺序；保留相同 workers=2、独立工作区和完整时间戳。
不假设服务支持可复现随机种子。保存实际启动顺序、缓存 usage、模型目录和时段。

### 主要结果

- 主指标：600秒内严格双通过数；每臂 `/20`，不混成40题，
  逐题配对结果，以及 A成功B失败/B成功A失败的全部题目。
- 效率：全部 episode 的 input/output/reasoning tokens、缓存命中/未命中、
  结算费用、actor wall time、超时率；另报双方均成功子集，不以子集替代总体。
- 额外诊断：首次双通过时间、结束时间及其间开销，但不更改原主判分。
- 区分一次性构建成本和在线求解成本：B 构建费用单列，并报告摊销假设。
- 主成功率差沿用原主比较：以题为簇、保留A/B配对一起重采样，10000次、
  seed20261006，报告95% percentile bootstrap区间。不把40次运行当40道
  独立题，小样本不作强显著性宣称。

超时/验证失败保留，不能被成功重跑替换。技术性 provider 错误单独列为无效运行，
依据预先冻结的恢复规则补齐相同单元；保留原失败记录及全部费用，不据结果择优。
若矩阵不完整或账本未结算，报告 incomplete，不计算一个貌似完整的主结论。

### 机制分析（次指标）

- 初始索引字节/token、正文读取 episode 数/次数、unique reference 数、实际暴露
  的原卡集合和字节/token、读取发生在首次成功前还是后。
- 根据读取当时的诊断和前提，审查相关/不相关/信息不足、采用/拒绝及原因；
  依据 trace 给证据，不把手选相关卡标签提供给 actor。
- 分别解释“目录已足够”“找不到相关内容”“读到但不适用”“适用但没有收益”。
  这属于事后机制解释，不直接证明中介因果。

## 8. 结果解释与后续边界

- 成功数增加：报告增加和倒退在哪些题，同时报告成本，不只报净增。
- 成功数相同、token/费用减少：只能称本轮观察到效率优势；不是成功率提高，
  也不等同于已证明统计意义上的非劣。
- 读取增多但成功/成本无改善：不能称组织方案有效。
- 如果有收益：先独立重复或扩大可靠性检查，再考虑更多改动。
- 若要隔离原因，后续可另开“仅聚类、保留原卡正文”消融；不自动把本轮扩成三组。
- validation20 已多轮参与开发，repaired78 也继承开发修订历史。本轮结果只能作为
  开发比较；组织时不新增泄漏不意味着它变回独立验证集。
- test20 本轮不访问、不调参、不运行；后续仅在方法完全冻结、另获授权后做最终评测。

## 9. 交付清单

- A/B 可部署 bundle 及每个文件哈希、构建模型/prompt/调用记录。
- 78卡全覆盖 mapping、训练支持 provenance、reduce 差异和人工/代理审查记录。
- 冻结合同、共享 TASK、完整任务矩阵、审查回执、工具/模型/配置哈希。
- 全部运行结果与费用、配对汇总表、正文读取与相关性审计、明确证据边界的报告。
- 仓库仅保存经审查的紧凑记录；原始/封存数据不修改，全部新运行写到运行根目录。

## 10. 依据

- 推荐配置与因果边界：
  `research_memory/projects/verus_self_evolving/notes/20261011-010654-deepseek-proof-augmentation-cards-and-inference-comprehensive-progress-report/REPORT.md`，第256行及相关实验节。
- 新上传卡与恢复说明：`research_artifacts/deepseek-20261011/README.md` 和 `manifest.json`。
- Trace2Skill reduce 原则：
  `trace2skill-verusage/baselines/native-official-20260819/configuration/merge_system_prompt.txt`。
- 本地 Trace2Skill 原生实现范围：`trace2skill-verusage/README.md`；这里只借用原则与组织形式。
