> Publication note (2026-10-28): historical review, including its then-current recommendations. Current status and corrected timing comparisons are in [the package README](../README.md). Original log references are archive pointers, not files included here. Counts and conclusions are unchanged; only local paths and links are normalized.

# 新旧正文 × 同一v2索引：24轮结果审查

2026-10-24 10:02:55 UTC（05:02:55 CDT）完成24/24，服务正常退出。当前审查仅离线读原始证据，没有新API、重跑、续写或改动冻结材料。

**结论：新正文净多通过1次，但未证明改善了“证明义务变化→找到适用卡→局部验证”的完整过程。** 两组均出现1次失败后的后续补读；新组补读更早，但选到的009不满足当前义务。新组还存在一次禁止的直接整库读取。建议保留新正文为候选，暂不凭这一批将其认定为更优默认流程。

## 1. 通过与完整性

主指标：600秒内观察到同一候选Verus和Lynette均通过。每格顺序为三次独立重复，不是共享随机种子。

|题目|原正文G0|新正文G1|通过数|
|---|---|---|---|
|Rely|✓ ✓ ×|✓ × ✓|2/3 → 2/3|
|Unpack|× ✓ ✓|✓ ✓ ✓|2/3 → 3/3|
|De Morgan|✓ ✓ ×|× ✓ ✓|2/3 → 2/3|
|Filter|✓ ✓ ✓|✓ ✓ ✓|3/3 → 3/3|
|合计|9/12（75%）|10/12（83.3%）|+1次，+8.3个百分点|

正常退出也为9/12与10/12。所有19个通过均独立核对host最终验证：同一哈希、两工具returncode0且均在600秒内。五个机器失败全部检查，最终Verus均未通过，保存的actor命令也未发现整文件0错误的成功输出；无人工改判，不存在上一批管道漏计或601秒最终有效案例。

实际输入两组都是批准的v2索引；G1仅三处短插入，G0/G1共同修正读卡示例ID。326个冻结输入哈希未变。672条API请求均已结算，未知费用0、预留0，bridge已排空；无上游attempt error。日志出现的本地BrokenPipe没有导致调度中断或未结算账目；不据此剔除超时样本。

证据：独立计分与账本复核（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/manual-adjudication.json`）、原始机器报告（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/report.json`）、[组间差异](G0-G1.diff)。

## 2. 成本并没有明显改善

|指标|原正文G0|新正文G1|变化|
|---|---:|---:|---:|
|输入token（含缓存与重复上下文）|12,849,636|13,077,457|+1.77%|
|输出token|351,623|342,828|−2.50%|
|累计actor秒数|3,767.2|3,761.2|−0.16%|
|请求数|325|347|+6.77%|
|账本估算美元|2.179434|2.159103|−0.93%|

合计$4.338537104。使用冻结harness费率逻辑的账本估算，不是供应商实际账单；周末折扣可能使该估算偏高。reasoning计入输出，不重复相加。

输出token按题变化：Rely +13,800；Unpack −35,641；De Morgan +1,998；Filter +11,048；合计−8,795。节省集中于Unpack，另外三题抵消大部分收益。Filter三轮都通过，但新组输出10,440→21,488，累计actor161.7→298.7秒；只有第一轮整库读，不能把全部Filter开销增长都归因于整库读。

## 3. 读取：按需选择与整库暴露必须分开

|指标|G0|G1|
|---|---:|---:|
|通过card_read按需读取的episode|5|6|
|任何正文暴露的episode|5|7|
|helper正文返回数|10|11|
|直接整库正文暴露|0|10张／1次命令|
|全部正文暴露次数（非去重卡数）|10|21|
|首次读取发生在修改失败之后|2|1|
|先读卡、后失败、再补读的episode|1|1|

全部24条轨迹、12个发生正文暴露的episode以及672份实际转发请求已核对，所有计入的完整正文均进入模型请求上下文。原分析脚本只覆盖helper返回；本批发现直接整库读后，离线分析已增加direct与helper分栏，原始计分不变。工具次数、选择次数、唯一卡数不能混用。

**整库异常：G1 Filter第1次，11.1秒执行`cat card_read.py && head -50 cards.json`。** 虽然是head命令，JSON每张卡的正文以转义字符串储存，这次实际返回全部十卡。两组共同正文明确禁止bulk-read；这是指令遵循偏差，不是按需检索改善。模型最终称“No cards were consulted”，与实际暴露不同；它可能没有有意使用卡，但不能据此计为未读。该轮证明/保真通过仍按预定指标保留，不事后删除以改变分母。

## 4. 真正的后续补读发生了，但匹配仍有问题

### G1 De Morgan第3次：补读早，但009不适用

- 27.4秒读008；42.3秒明确选择两方向entailment再调用`temp_pred_equality`。
- 112.1/117.4秒出现无法推断trigger；122.3秒在`assert(!a_to_p(w).satisfied_by(ex))`失败。
- 142.8秒回头读取009。这是读后失败驱动的补读，不是开局连续多卡。
- 009正文要求的是**execution-equality helper前提中的逐点等式trigger义务，且此前projection语法已修复**；此处没有该helper/义务，不能仅因出现trigger就认为匹配。
- 补读后仍有多次失败。478.6秒模型根据自己的probe确定closure应用形态；480.98秒Verus、485.34秒Lynette通过。

所以可以说“新正文组出现一次较早补读”，不能说“补读到了适用卡并因此通过”。008的一般路线与后续动作一致，但卡正文的family参数需要适配；模型没有遵循先独立验证两方向再调用helper的全部细节。

### G0 De Morgan第3次：原正文也会补读

342.8秒首次读008，369秒同类witness实例化仍失败；597.5秒补读005/006。006不匹配稳定性目标，005也缺少该卡的temporal-lifting入口。补读后没有新编辑或验证就超时。两组均1次补读，差别是时机与后果，不是0→1的独有能力。

### Rely中段的目标行为仍未出现

G1 Rely第1次86.8秒只读008，133.3秒已说明没有匹配的等式helper；之后多次定位作用域和entailment实例化问题，仍未按需补读005/010，最终567.7秒通过。第2次开局读008/006/005，后续继续量词与作用域探索但没有补读，超时。第3次完全未读卡，286.8秒通过。

本批G1没有按需选读010；Filter整库暴露010不等于Rely取到了它。另一方面，模型已识别问题并有明确修复时，无需强制读卡；这里不能把所有未读都标成错误，也不能声称补读010必然成功。

## 5. 唯一净增题Unpack：有局部采用证据，也有错配

G1第1次80.2秒读取005/006，代码新增`entails_apply`、`spec_at_suffix`等helper，体现实例化后使用后果的步骤。修复一个trigger问题后146.2秒Verus报告5verified，最终双通过。005的泛化指导与实现一致，构成局部采用信号；但首读时只是空体postcondition失败，尚未满足005“已有pointwise/temporal-lifting尝试”的严格入口。

006的判断不一致：128.8秒说两张都符合计划，最终总结又明确拒绝006，因为目标不是稳定性合取。代码确实使用已有stable前提，未证明稳定性组合，因此不能把它记作006正确应用，也不能把最后的拒绝自述当作全过程筛选准确。

G1第3次读009/005后首个完整证明通过，但当前没有009规定的失败条件，模型仍称两卡匹配。G0第3次也能先拒绝001，再选择005/010并一次通过；这是同一初选阶段内的拒绝后改选，不是新失败后的第二阶段。有效拒绝/迁移不是新正文独有。

因此，Unpack的2/3→3/3与局部指导采用相伴，但不能把全部收益归因于新增规则，或据此证明匹配精度普遍提高。

## 6. 全部读卡案例清单

次数采用1起始；下列每行链接包含原始事件行号、时点、候选哈希、命令与输出。语义判断另存semantic-review.json（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/semantic-review.json`）。

|组/题/次数|正文返回时点|判定摘要|
|---|---|---|
|G0 Unpack 1（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G0_original_main--9b9f6ccef89db4103c7f--repeat-0.md`）|95.9s: 009；95.9s: 008|开局读009/008；当时没有009要求的execution-equality前提trigger失败，也不是008的目标等式。后续valid实例化和作用域探索未闭合，超时。|
|G0 Unpack 3（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G0_original_main--9b9f6ccef89db4103c7f--repeat-2.md`）|113.7s: 001；121.3s: 005/010|先读001并明确拒绝，再读005/010；没有中间编辑或验证，是同一初选阶段中的拒绝后改选。读前尚无010要求的具体失败，属于提前迁移；最终if分支和完整entailment实例可见，首个完整候选通过。|
|G0 Rely 2（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G0_original_main--a23a4969155913255f76--repeat-1.md`）|8.8s: 008|开局读008，但Rely是布尔等价且没有该卡匹配的等式helper。模型迁移pointwise思路后自行修复作用域及完整实例化，通过。后续未补选005/010。|
|G0 De Morgan 2（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G0_original_main--aded79905be896942897--repeat-1.md`）|167.7s: 008|已有双向entailment路线且遇到witness实例化失败后首读008；读后probe/SMT日志定位lambda应用形态并修复。相关一般路线，不能把先前路线选择或具体trigger解法归因给卡。|
|G0 De Morgan 3（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G0_original_main--aded79905be896942897--repeat-2.md`）|342.8s: 008；597.5s: 005/006|342.8秒在已尝试的mutual-entailment路线失败后首读008；597.5秒读005/006。006不是稳定性目标，005无temporal-lifting入口；太晚且没有后续新编辑/检查，不能证明补读有效。|
|G1 Filter 1（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--62ff0a3cf2c458b36ac8--repeat-0.md`）|11.1s: 001/002/003/004/005/006/007/008/009/010|11.1秒cat card_read.py && head -50 cards.json暴露完整十卡，违反两组共同禁止批量读库的说明；provider捕获确认全正文。最终称未consult卡与实际暴露不同，不能作为未读证据。代码一行调用已有subset lemma即通过，无需卡的因果证据。|
|G1 Unpack 1（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--9b9f6ccef89db4103c7f--repeat-0.md`）|80.2s: 005/006|80.2秒读005/006；128.8秒把两者都描述为符合计划，最终报告又明确拒绝006。代码是使用已有stable前提而非证明稳定性组合，故不能视为始终准确匹配；005实例化思路对应entails_apply等helper，5verified整体通过。|
|G1 Unpack 3（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--9b9f6ccef89db4103c7f--repeat-2.md`）|140.2s: 009；140.3s: 005|140.2秒仅空体postcondition失败时读009/005；146.3秒说两卡支持计划，最终也声称匹配。实际未发生009入口的execution-equality trigger错误；005为提前迁移，代码确实体现实例化路线并一次通过。错误适用性自述不能由成功结果洗掉。|
|G1 Rely 1（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--a23a4969155913255f76--repeat-0.md`）|86.8s: 008|86.8秒读008，133.3秒说明没有对应helper；后续出现作用域及完整entailment实例化问题，多次probe，未补选005/010，567.7秒双通过。不是008严格适用例。|
|G1 Rely 2（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--a23a4969155913255f76--repeat-1.md`）|65.9s: 008；70.6s: 006/005|开局同一读取阶段读008再006/005，150.5秒说明无本地helper。006目标不匹配，005提前泛化；后续量词shuffle/作用域/定义probe无补读，超时。|
|G1 De Morgan 1（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--aded79905be896942897--repeat-0.md`）|97.6s: 008|已有helper/双向断言路线且失败后97.6秒首读008；读后仍在negation/lambda触发形态上反复试验，无补读，超时。没有证明008提供足够局部解法。|
|G1 De Morgan 3（归档证据：`RUN_ROOT/obligation-guidance-20261024-run24-v1/final-review/timelines/dev_G1_obligation_main--aded79905be896942897--repeat-2.md`）|27.4s: 008；142.8s: 009|27.4秒读008后42.3秒明确采用双向entailment路线；触发器诊断和断言失败后142.8秒补读009。但当前不是execution-equality helper前提；之后仍多次失败，478.6秒自己通过probe确定closure应用形态，485.3秒双通过。补读确实发生，但未证实匹配或直接贡献。|

## 7. 判断与下一步

本批结果可以带限制使用：计分、用量和暴露证据完整；正文改动的机制改善尚未建立。四个已知开发题、每组每题三次，三处插入一起改变，不能隔离单句效果或推断总体泛化。

保留v2索引的决定不受此批影响。新正文可保留作候选，不宜凭9/12→10/12直接提升为已验证的默认版本；暂沿用原正文+v2作为稳定基线。若继续研究，应优先解决“按失败关键词选卡、忽略必要前提”的适用性判断，并观察指导落实，而不是继续强化读卡数量。是否改正文或开展新实验由后续任务决定；此次不修改两组材料、不自动扩展运行。

本轮检查覆盖：24个唯一单元、19个成功的独立最终验证、5个失败的原始检查、12个正文暴露episode、672份转发请求、独立账本重算、326冻结哈希。未穷举每一步未读机会，没有给全量检索precision/recall，也不能从保存的公开消息恢复隐藏推理。没有新增验证器/API调用；利用既有事件核查，不从失败checkpoint续写。

复现离线核查：依次运行`final-review/analyze.py`、`final-review/audit.py`、`final-review/independent_audit.py`。人工机制判定不能由脚本自动证明。原始结果、冻结卡、历史实验和账本均未改写。
