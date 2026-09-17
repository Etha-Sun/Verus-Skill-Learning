# Hint-guided checkpoint augmentation: initial skill, v1 / v2

本实验的目标是：为同题生成可比较的成功／失败经历，与原trace一起组织到SkillOpt minibatch，让optimizer提炼适用条件明确、非重复的经验。**成功率不是有效信息率；典型失败也可有价值，多条相似成功则可能只贡献一个经验主题。** 本包发布0916的hint agent配置，以及装备原initial skill的IR／AC／AL三题双版本实验；不包含此前blank小实验。

## 核心结果与阅读入口

| 题目 | v1最终双通过 | v2最终双通过 | 源码变化次数 v1→v2 | Actor输出token变化 | 详细报告 |
|---|---:|---:|---:|---:|---|
| IR set_map_union | 6/6 | 6/6 | 7→11 | −0.6% | [逐CP两版对照](ir/REPORT.md) |
| AC list-response to create-response | 5/6 | 5/6 | 35→28 | −15.5% | [逐CP两版对照](ac/REPORT.md) |
| AL seq_equal_preserved_by_add | 7/7 | 7/7 | 17→12 | −17.1% | [逐CP两版对照](al/REPORT.md) |
| 合计 | 18/19 | 18/19 | 59→51 | −12.5% | [结果记录](results.json) |

AC v1 CP1与v2 CP3是真实超时未解，最终Verus失败、Lynette通过；不删除失败来美化结果。AC v1 CP2经历hint格式筛查误报，人工审查后使用原hint补跑并成功。38条actor均实际读取同一initial skill。每份报告包含原题与原F、hint全文、实际源码修复、诊断、hint落实／偏离，以及同起点版本对照。

**关于hint效果：** 观察到提示的数学目标被落实，也观察到延迟落实、转用其他路线和未完成。v2在AL较集中，在AC降低总成本但失败点改变，在IR反而多次返工。不能概括为“更强hint总能减少试错”。v2增加的是证据约束的兼容检查，不是要求沿原F走；它是否压缩策略多样性仍是假设。

**关于optimizer的信息增量：** [完整信息审计](INFORMATION_VALUE_AUDIT.md)给38条标了新增、失败、反例或重复主题。IR两版多次库定理复用主要是同一个新增主题；AL大多重演原长度／索引路线。v1独有较清楚的AC成功helper分解，v2的泛型helper失败可与成功例形成互补。若按新增内容选择，本次略偏v1，但更合理的是两版按主题去重混合，而不是整组优选。这个判断是人工模拟optimizer的阅读，不是实际训练或泛化收益结论。

三题、每checkpoint每条件一次采样；同题checkpoint不独立。没有装备相同skill的匹配No Hint组；旧blank组不能作净hint效应的严格对照。尚未运行SkillOpt batch／curriculum训练，未证明skill质量提升。

## Hint agent与actor配置

1. **数据来源固定：** Yuechun的fixed train40、DeepSeek v4 Pro、step_0001初始训练轨迹，原轨迹装备initial skill；本次从中使用三题，全部checkpoint由原提取器给出，排除与原最终源码相同的状态。各题`checkpoints.json`保留事件号／hash，`selection_manifest.json`用于准备时一致性核对。
2. **Hint agent：** DeepSeek v4 Pro，high reasoning，单次原生Responses请求；可看原题、完整原轨迹、当前checkpoint和验证过的原F。对大源码用可还原的baseline相对编码，不截断中间源码。要求给“缺什么事实／前提、下一步目标、为什么及如何检查”，不输出整段答案代码。宿主做schema、证据ID和内容筛查；这不是数学正确性证明，语义仍要审查。
3. **v1/v2：** [v1 system](prompts/v1/hint_system.md)与[v2 system](prompts/v2/hint_system.md)。v2要求独立检查有证据支持的兼容问题，区分已观察失败／潜在风险／无依据风险；不泛称所有import或broadcast禁止。19对实际hint分别重新生成，正文均不同；共同`schema_version: hint-v1`仅表示数据格式相同。
4. **Actor：** DeepSeek v4 Pro、high reasoning，每条600秒，context window 1048576。拿到任务规格、完整checkpoint代码、hint和[原initial skill](initial.md)；不回放原完整对话，不直接提供F。skill按原project-profile方式写入工作区SKILL.md并要求阅读，不额外拼入hint。见[装备核对](SKILL_PARITY.md)、[续跑协议](actor_protocol.txt)。
5. **隔离与验证：** actor无法访问hint-private、原轨迹、凭据及参考目录；vstd合法可读。最终由宿主对候选运行Verus＋Lynette。38条各自目录和API账本独立，历史三题并行、题内v1后v2、checkpoint顺序执行。
6. **失败保留：** 不自动重生成被筛查的hint，不自动重跑失败actor。已完成项不会被静默覆盖。AC v1 CP2是有明确人工审查的筛查放行，不是筛查器自动接受。

## 发布内容与边界

- 三份合并报告、六份分版本报告，三张版本对照图及各版单组图。
- 原题／原F、19份起点源码、38份最终源码、38个hint、最终宿主验证和编辑／诊断节选。过程文件明确标为节选，不冒充完整raw trace。
- 六份运行配置模板、冻结skill／prompt、checkpoint清单、[核心runner](../../skillopt-verusage/scripts/run_hint_augmentation.py)、[边界测试](../../skillopt-verusage/tests/test_hint_augmentation.py)、编排／统计／绘图脚本。
- 完整原轨迹、原始模型请求／对话、provider账本、凭据、完整运行目录留在外部数据区；个人路径已脱敏。报告中未发布的旧材料明确标注，不保留坏链接。

[复现与文件说明](REPRODUCIBILITY.md) · [38条信息分类](information_value_labels.json) · [文件来源校验](publication_provenance.json)
