> Publication note (2026-10-28): historical review, including its then-current recommendations. Current status and corrected timing comparisons are in [the package README](../README.md). Original log references are archive pointers, not files included here. Counts and conclusions are unchanged; only local paths and links are normalized.

# 当前G1与单句修改G2：24轮离线审查

审查结论：**本批G1通过10/12，G2通过8/12；G2消耗更多，且没有观察到预期的“卡ID—当前义务—步骤前提”说明改善。暂不采用这处单句替换，保留当前G1+v2为这条实验分支的比较基线。** 这不是统计上确证该句有害，也不是证明G1优于更早的原正文；每题每组仅三次，仍有明显行为波动。

实验于2026-10-24 12:51:44 UTC（07:51:44 CDT）完成24/24，systemd正常退出。审查在2026-10-25 UTC进行，仅使用既有记录，没有新增API、验证器调用、重跑或checkpoint续写。

## 1. 结果、计分与完整性

主指标保持原合同：600秒内观察到同一候选Verus和Lynette均通过。每格按第1/2/3次顺序列出；repeat标签不是共享随机种子。

|题目|G1当前正文|G2单句修改|通过数|
|---|---|---|---|
|Rely|× ✓ ✓|× ✓ ✓|2/3 → 2/3|
|Unpack|✓ ✓ ✓|✓ × ✓|3/3 → 2/3|
|De Morgan|× ✓ ✓|× × ✓|2/3 → 1/3|
|Filter|✓ ✓ ✓|✓ ✓ ✓|3/3 → 3/3|
|合计|10/12（83.3%）|8/12（66.7%）|−2次，−16.7个百分点|

18个成功均独立核对保存的host最终检查：同一候选哈希、两工具returncode0、均在600秒内。6个失败均超时，最终Verus未通过；没有人工改判。G2 Unpack第2次有3条“0 errors”输出，但命令明确验证的是scratch.rs局部probe，不能算目标candidate.rs通过。这与历史管道漏计成功案例不同。全部24个最终Lynette检查通过，不代表失败轮的证明成立。

660个API请求全部结算，每次只有一个上游attempt、无attempt error，未知费用0、预留0，bridge排空，调度failures为空。本地日志BrokenPipe不等于API中断：请求结算和24单元完整性均核对；不据此排除超时轮。

351个冻结输入哈希未变。G1与上一批G1逐字节相同；G2仅包含批准的那一句替换，原三处插入、v2索引、十卡、reader、Executive与harness固定。24份初始TASK逐字节相同，全部实际正文与已读卡内容在660份转发请求中确认。额外独立扫描553条完成的命令输出，9次完整正文暴露全部与读卡审计一致，无遗漏的整库读取。

证据：独立计分与账本复核（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/manual-adjudication.json`）、原始报告（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/report.json`）、[冻结差异](G1-G2.diff)、逐轮明细（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/EPISODES.csv`）。

## 2. 成本与时间

|指标|G1|G2|G2相对G1|
|---|---:|---:|---:|
|输入token（含缓存与重复上下文）|10,283,786|16,137,045|+56.9%|
|输出token|309,626|379,767|+22.7%|
|累计actor秒数|3,426.9|4,165.0|+21.5%|
|actor秒数中位数|239.6|366.7|—|
|请求数|273|387|+41.8%|
|账本估算美元|0.967195|1.247388|+29.0%|

整批估算$2.214583272，低于$20上限。这是harness账本估算，不是供应商账单；reasoning已经包含在输出token中，不重复加总。输入增长包含多次请求重复发送上下文，不能理解为“新增几个词本身多花了57%”。

新增输出70,141token中，Unpack贡献38,859，De Morgan贡献28,028，两题合计约95.4%。这些差异伴随额外超时和不同证明路线，不证明新增句子使模型犹豫或造成超时。

按题三次actor时长（秒，含失败轮，保持分母）：

|题目|G1第1/2/3次|G2第1/2/3次|
|---|---|---|
|Rely|600.4 / 146.9 / 533.6|600.5 / 295.6 / 407.6|
|Unpack|266.7 / 212.5 / 149.7|150.1 / 600.4 / 325.7|
|De Morgan|600.5 / 388.3 / 358.9|600.5 / 600.6 / 412.7|
|Filter|36.4 / 107.5 / 25.5|72.9 / 27.5 / 71.0|

actor终止稍晚于600秒不等于接受超时后的证明；计分仍使用验证事件时点。上述分布揭示大幅轮间变化，不能将某个同编号repeat当作共享随机种子的严格配对反事实。

## 3. 读卡和修改目标

|指标|G1|G2|
|---|---:|---:|
|按需读卡episode|3/12|2/12|
|helper完整正文返回次数|6|3|
|直接整库暴露|0|0|
|首次读取在修改失败之后|1|0|
|已读卡后再失败并补读的episode|1|0|

“修改失败后”区别于对初始空体的基线检查失败；同阶段连续读多卡不算后续补读。读得更少本身既不是优点，也不是缺点。

**本次新增句子的直接目标没有在G2读卡轮的公开说明中得到确认。** G2两次读卡都发生在Rely；检查全部公开进度消息和已有最终总结，没有卡ID与当前义务/实际步骤前提之间的明确联系说明，也没有明确区分完整路线采用与通用技巧迁移。卡ID出现在工具命令中不等于给出适用性理由。不能由此恢复模型隐藏推理，但至少没有证据表明该句改善了可观察的匹配解释。

同样不能说G2已经消除了错误匹配陈述：如果没有给出适用性说明，不能把“没说错”当成“判断更准确”。G1则已有明确拒绝不匹配helper路线的例子，不需要这次新增句子才能做到。

## 4. 所有五个读卡episode的机制审查

历史诊断入口不一定是一般技巧的逻辑必要前提。本轮依预先协议区分探索、拒绝、完整路线采用、合理迁移与无依据采用，不把“读了入口不完全相同的卡”直接记成错误。

|案例（链接至带事件时点、原始行号和候选哈希的时间线）|审查判断|
|---|---|
|G1_current Rely 1（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/timelines/dev_G1_current--a23a4969155913255f76--repeat-0.md`）|52.4秒读008/006；112.7秒先说008主题相符，随即指出本模块没有所需helper前提，明确拒绝其chain，转为直接展开。这是拒绝不匹配路线的正例，不能截取fits一词判错。006没有对应稳定性目标，也未得到单独适用性说明。后续明确遭遇前提作用域/实例化失败，无补读，超时。|
|G2_premise_check Rely 1（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/timelines/dev_G2_premise_check--a23a4969155913255f76--repeat-0.md`）|65.8秒仅空体postcondition失败时读008/009；没有008要求的匹配等式helper，也没有009对应的execution-equality trigger诊断。全部公开进度未指出卡ID、必要前提或拒绝/迁移依据。后续是双向展开、binder和实例化探查，无补读，超时。不能仅因入口不同就认定错误套用，也不能因没有说matched就算匹配判断改善。|
|G1_current De Morgan 1（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/timelines/dev_G1_current--aded79905be896942897--repeat-0.md`）|474.7秒首读008，此前已进行双向证明和extensionality探查。503.5秒报trigger必须是函数调用/字段访问/算术项；552.0秒补读009/010，属于失败后的第二阶段。不是009完整execution-equality入口，最新诊断也不是010的前提作用域问题；可作为探索，但之后只有库搜索，无新候选修改/验证，不能证明采用或帮助。|
|G2_premise_check Rely 3（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/timelines/dev_G2_premise_check--a23a4969155913255f76--repeat-2.md`）|69.3秒开局读010，尚无该卡记录的内部断言失败。后来helper和主证明在实际需要的前提上显式if分支；342.0秒明确说分支已处理==>前提不可用问题，继续修复实例化，最终通过。可认定合理预防性迁移的代码一致性证据，不应以入口未触发判错。但公开进度及最终总结均未把010与该步骤前提联系起来，新增句子的目标行为没有明确出现。|
|G1_current De Morgan 3（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/timelines/dev_G1_current--aded79905be896942897--repeat-2.md`）|34.3秒读008，47.0秒说明分两个entailment再用temp_pred_equality，首个候选体现该路线。但断言和helper同次提交，没有先独立验证两方向再调用helper。后续自行定位closure应用trigger，最终命名not_a_to_p并验证通过。支持路线采用和合理适配，不证明卡给出了最终trigger修复或独立因果收益。|

详细结构化判定：semantic-review.json（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/semantic-review.json`）。

G2 Rely第3次是一个局部正信号：读010后，最终代码确实用合法if分支建立所需前提，随后通过；无需先人为制造卡中记载的失败才允许这样做。但没有公开的卡—步骤前提联系说明，也没有反事实证据，不能将成功归因于新增句子或该次读取。G2 Rely第2次完全未读卡，也自行用显式分支并通过。

G1 De Morgan第3次读008后采用双向entailment再调用helper的路线并通过；卡未给出最终closure trigger修复，而且模型没有完全执行“先独立验证两方向、再调用helper”的顺序。应记为有适配的路线采用，不能夸成照卡一步到位。

## 5. 少通过的两题发生了什么

G2 **Unpack第2次**全程未读卡。主要在valid/量词实例化、let-bound值与参数的probe中迂回；213秒转向scratch实验，586.5秒才表示要改为小helper，589.7秒目标仍3verified、2errors，最后超时。scratch的局部成功不代表目标成功。创建scratch文件也偏离TASK的只编辑candidate.rs要求，保留原分母与失败计分，单独记录；不是卡采用导致的可见证明错误。

G2 **De Morgan第2次**全程未读卡。24.8秒就已选择temp_pred_equality与双向entailment路线，之后在否定量词、witness和closure触发形态上反复尝试，495秒转入SMT日志，最终超时。第1次也未读卡并超时，第3次仍未读卡却通过。因此本批不能支持“只要强制读008就能解决”；两次失败都已自行知道008的一般路线，真正未闭合的是具体局部量词义务。

两组Rely第1次也都超时。G1已经明确拒绝008的helper链，后来遇到前提作用域问题仍未补读010；G2开局读008/009后继续展开和实例化探查，没有补读。没有观察到新增句子使后续重评更可靠。

## 6. 波动与建议

仅引用上一批已审汇总，不重跑历史审查：字节完全相同的G1，在上一批与本批都是10/12且各题通过数相同；但按需读卡轮次从6降到3、helper正文返回从11降到6，输出token从342,828变为309,626。上一批另有1轮整库暴露，本批没有。**相同prompt也能产生明显不同的读卡行为。** 这不能证明所有差异都是随机噪声，却足以反对根据单个读卡案例继续逐句追补prompt。

本批方向不支持采用G2：少通过2次、更高开销，预期的可观察适用性说明也未建立。但每题每组仅三次，属于四个已知开发题；没有统计上确证总体负效应，不作泛化结论。

建议保留G1+v2为当前实验分支基线，G2作为未获得支持的候选归档；这不撤销之前“G1也未被证明优于更早原正文”的限制。暂不追加新措辞、不自动扩展实验。后续若研究匹配，优先稳定判据和重复设计，避免把缺少说明当成准确、把合理预防性迁移当成错用。

## 7. 审查覆盖和复现

可带上述限制使用。覆盖24个唯一单元、18个成功host双检查、6个失败及其全部保存的零错误输出、660份转发请求与账本、553条命令输出、351个冻结哈希、全部5个正文暴露episode的语义审查。所有24条轨迹生成时间线，全部公开进度消息作筛查。未穷举19个未读轮的每个检索机会，不报告全量precision/recall；无法断言隐藏推理中的适用性判断。报告为Markdown/CSV，没有交互图表或发布页面。

离线复现：`python3 final-review/analyze.py`、`python3 final-review/audit.py`、`python3 final-review/independent_audit.py`。语义结论还需要对照时间线和候选改动人工审查。

原始report/summary/账本、冻结输入、历史审查均未改写；没有新API、验证器执行、重试或checkpoint续写。状态单独记录于review-status.json（归档证据：`RUN_ROOT/guidance-premises-20261024-run24-v1/final-review/review-status.json`）。
