> Publication note (2026-10-28): historical review, including its then-current recommendations. Current status and corrected timing comparisons are in [the package README](../README.md). Original log references are archive pointers, not files included here. Counts and conclusions are unchanged; only local paths and links are normalized.

# 原索引与 matching v2：16次同期实验结果审查

2026-10-24审查；16/16完成于07:34:18 UTC（02:34:18 CDT）。没有新API调用、续写或补跑。

结论：v2有局部筛选改善信号，但尚未证明可靠改善了读卡匹配或失败后的重新检索。主指标原索引5/8、v2 6/8；两组正文读取总数均7，读卡episode为3/8与4/8。v2仍有不适用候选读取、相关失败后不读取，以及读完不补选的情况。

## 结果及成本

主指标固定为同一候选在600秒内观察到Verus与Lynette均通过，正常退出另列。每题每组2次，表中顺序为第1/第2次；重复标签不是相同随机种子。

|任务|原索引 I0|v2 I2|变化|
|---|---|---|---|
|Rely|通过 / 通过|通过 / 超时|2/2 → 1/2|
|Unpack|通过 / 超时|通过 / 通过|1/2 → 2/2|
|De Morgan|超时 / 超时|通过 / 超时|0/2 → 1/2|
|Filter|通过 / 通过|通过 / 通过|2/2 → 2/2|
|总计|5/8|6/8|净增1次；正常退出也为5/8与6/8|

|指标|原索引|v2|
|---|---:|---:|
|账本估算费用（美元）|1.810830|1.584631|
|输入token（含缓存和重复上下文）|11,341,742|9,781,809|
|输出token|279,443|235,323|
|actor累计秒数|2,987.9|2,561.9|
|已结算请求|257|228|
|读过正文的episode|3|4|
|正文返回数|7|7|
|首读发生在修改后失败之后|2|1|
|读后新失败驱动的补读阶段|0|0|

v2费用下降12.5%、输入下降13.8%、输出下降15.8%、累计actor时间下降14.3%。这是本批总体结果，受通过数和轨迹影响，不能全部归因于索引缩短。总账本估算3.3954602美元，485请求均结算，未知费用0、预留0。费用为沿用harness费率的估算，不声称是供应商账单精确金额。

## 五个机器失败的人工复核

五个全部检查，没有应改判为600秒内通过的遗漏。

特别是v2 De Morgan第2次：

- 581.555秒：候选`6a9b1ccf…` Verus通过。
- 585.214秒：同一候选Lynette失败，输出`Files are different`；新增macro import仍在。
- 598.209秒：模型删除import并展开宏，生成不同候选`5bb57c40…`。
- 600.998/601.004秒：host对最终候选独立Verus/Lynette均通过。

最终文件确实有效，且是在截止前产生；但“600秒内已观察到同一候选双通过”的预定指标仍不满足。不能把581秒的旧候选Verus与601秒的新候选Lynette拼接计分。可作为次指标报告最终文件有效7/8，不能替换主指标6/8。这个病例与上一批管道输出漏计不同。

证据：单独复核记录（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/final-review/manual-adjudication.json`）、原始截止审计（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/episodes/dev_I2_matching_v2--aded79905be896942897--repeat-1/deadline_dual_audit.json`）。原始机器报告未改写。

## 全部读卡episode审查

下表时间为首次正文返回，卡号省略`new-`。7个读卡episode均核对了正文、读前状态、可见解释、后续候选与检查；485份实际转发请求确认相应主文件和所有返回正文确实进入模型上下文。

|组/任务/次数|读卡时点及正文|适用性及后续行为|
|---|---|---|
|I0 Rely 1|129.4秒：008、005、006|已有修改后失败；005实例化/作用域指导有部分迁移依据；008要求的等式helper路线不匹配，006稳定性目标不匹配。后续按实例化链推进并通过；不可把三张都计作有效选卡。|
|I0 Unpack 2|276.8秒：006、003、008|正在处理实例化失败，但目标不是证明稳定性，失败helper也不是003的forward-preservation helper，且不是008目标等式。后续主要自行构造小helper；未见三张卡的严格路线落地。超时。|
|I0 De Morgan 2|60.6秒：008|双向entailment再等式helper有相关性；正文family参数与实际两个TempPred仍需适配。反复卡在lambda/trigger实例化，超时。|
|I2 Rely 1|49.6秒：008、005|仅baseline空体失败，005的“已有pointwise/lifting推理”入口尚未满足，属于提前探索；008也不是准确helper匹配。64秒明确说卡是泛化指导，最后采用任意execution/完整实例化思路，并自行处理syntax与trigger，最终通过。未读010。|
|I2 Unpack 2|94.0秒：003|初选仍不匹配；98.7秒明确拒绝：当前是空体postcondition失败，不是helper前置条件失败。转直接证明，195.8秒已双通过。这是“读后判不适用并不套用”的正面证据，不能说003直接提供了成功解法。|
|I2 De Morgan 1|111.7秒：008|先前已尝试等式helper和两方向assert，失败后才首读。之后有独立逻辑probe→定义/trigger桥接→分支内实例化→双通过273.4秒。等式路线在读卡前已选，因此不能把路线选择归因于008；读后有与指导一致的局部检查。|
|I2 De Morgan 2|108.2秒：008、006、005|006明显不是当前稳定性目标；005首读时尚未有对应证明尝试。144.5秒明确选择008的双向entailment路线；没有充分证据说006被错误应用。后续仍无补选010，最终为上述601秒临界案例。|

每条逐步证据见timelines目录（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/final-review/timelines`），每个事件有原始`agent_events.jsonl`行号、item ID、时间和候选哈希。首次读取之后出现新错误，仍没有第二个补读阶段；相邻无编辑/检查的多个读卡命令算同一阶段。

## 对当前问题的判断

1. **匹配改善是局部的。** v2 Unpack明确拒绝003，且此次没有再读006；但本批v2 De Morgan仍读006，Rely仍以008/005作宽泛候选。不能宣称已经解决错读。候选读取、错误应用、采用正确指导是三个不同指标。
2. **新义务→回头首读出现一次。** v2 De Morgan第1次在helper前提/方向断言失败后111.7秒首读008。不是“读过卡后发现新义务再补读新卡”；后者两组均0。
3. **Rely漏读问题仍在。** v2 Rely第2次从头到尾未读卡，经历量化断言、trigger与前提作用域问题。后来模型自己识别antecedent不在body作用域并改if分支，仍在完整实例化上失败。不能简单说它“不理解问题”，也不能说改索引已经促成及时求助。本批两组都没有读取010；本批没有005+010组合的成功证据。
4. **008不是充分条件。** 本批De Morgan读008的三次：I0第2次失败，I2第1次通过，I2第2次截止后通过。600秒主指标是1/3；且I2成功轮在读卡前已开始同一路线。没有“读到就大幅提升”的可识别因果效应。
5. **不是只有Rely/De Morgan读卡。** v2四次读卡分别为Rely一次、De Morgan两次、Unpack一次。Filter全部未读且通过。
6. **600秒意识未在本批干预。** 固定R0流程、Executive、十张new_skeleton正文、reader与harness，仅索引变化；没有增加deadline提示。此前的预算不可见事实仍是独立待测因素，本批无法判定其因果效应，更不能归因于“悠闲”。

不建议仅根据净增1/8就宣布v2胜出或继续增加索引篇幅。保留v2为候选；下一步若试时间预算提示，应在相同v2索引下单独对照。若试失败后的重新匹配提醒，也应与时间提示分开，保留R1曾增加读卡而降低通过的历史反例。当前只完成审查，不自动扩展实验。

## 完整性与局限

16个唯一实验单元，初始TASK全匹配；两组实际main和7+7正文均确认进入provider请求。301冻结输入哈希复查无变化，bridge已排空，无基础设施失败或未结算请求。I2 De Morgan第2次还发生一次`card-008`无效ID调用，随后纠正为`new-008`；该错误来自两组保留的共享示例风险，不计作正文暴露。

仅4个已知开发题、每组每题2次，不能估计稳定总体提升。正文暴露确认不等于完整私有思维可见；这里审查的是保存的工具输出、公开消息、代码和验证。未做全部未读机会的穷举precision/recall标签，也未把失败诊断位置变化当作每个局部断言独立通过。

可重现离线命令：`python3 final-review/analyze.py`、`python3 final-review/audit.py`（从run目录执行）。数据：analysis.json（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/final-review/analysis.json`）、manual-adjudication.json（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/final-review/manual-adjudication.json`）、原始report.json（归档证据：`RUN_ROOT/index-matching-20261024-run16-v1/report.json`）。原始数据、冻结卡片、历史实验及其账本均未改写。
