# Candidate skill: generated, reviewed with conservative fallback, not evaluated

**最新：用户已授权并完成主目录精简。当前主SKILL为7957字节，37组与正文不变；
新产物位置及检查见[SHORT_INDEX_REVIEW.md](SHORT_INDEX_REVIEW.md)。下文保留初版
长索引的构建审查记录，不再是当前候选的主文件长度。**

## 当前结论

候选skill已生成，本次完整Router重试及37次Reducer响应已保存。
37个reference覆盖原始78张repaired卡，
审查后的正文有72条规则：66条直接复制原卡，6条合并规则各对应2张源卡。
主文件保留原始Executive字节前缀，追加可选读取说明与完整reference索引。
未启动40episode评测，尚未批准冻结为最终B组。

主要问题不是缺少产物，而是**目录仍过长，且两处模型合并不符合保真要求**。
已按既定保守策略把这两处回退为原卡；没有另造证明知识或额外收费重试。
目录长度问题未擅自改prompt或taxonomy来解决，留待审阅后确认。

## 产物位置

以下均相对于`VERUS_SKILL_RUN_ROOT`，未将完整run复制进仓库：

`skillopt-verusage/card-organization-20261012-reduce-v1/`

- `candidate/SKILL.md`：候选主文件，完整37项reference目录。
- `candidate/references/*.md`：各组正文，适用/排除条件、规则与条件交叉链接。
- `candidate/reference_read.py`：按ID读取整个reference，校验路径与内容哈希。
- `candidate/reference_manifest.json`：reference路径、哈希、字节数、源卡ID。
- `candidate_manifest.json`：文件哈希、来源记录、未解决问题、费用与禁止评测标记。
- `proposals/reduce/*.json`：37次Reducer的原始解析输出，未覆盖。
- `reviewed_proposals/*.json`：渲染使用的版本；仅两组发生明确记录的原文回退。
- `reduction_review.json`：按原始响应SHA绑定的回退原因和待确认项。
- `router_normalization.json`：Router格式转换记录，不改语义。
- `calls/`、`provider_capture/`、`provider_calls.jsonl`：请求、响应与用量证据。

完整Router重试的原始响应仍在`skillopt-verusage/card-organization-20261012-v2/`，
详见[ROUTER_RESULT_REVIEW.md](ROUTER_RESULT_REVIEW.md)。第一次未完成请求的
响应体未被旧client保存；不能声称它也已恢复。两次Router费用均计入总额。

## 构建与验证结果

| 项目 | 结果 |
|---|---|
| Router | 78卡、86个适用case、37个family；源文引用全部匹配 |
| Reducer | 37/37完成，全部DeepSeek V4 Pro/max，未收费重试 |
| 模型原始规则数 | 70，其中9条标为merged |
| 审阅后规则数 | 72，其中6条merged、66条verbatim |
| 源卡覆盖 | 78/78，每张源卡在最终规则来源中恰好出现一次 |
| 主SKILL字节数 | 31507；对照11545；是对照的2.729倍 |
| reference正文总字节数 | 168020，包括导航、来源标记与规则正文 |
| 最大reference | compound-stability-existing-rules，9732字节 |
| 读取检查 | 37/37reader返回与文件一致，哈希与源ID一致 |
| 文件与Executive检查 | 40个bundle文件哈希匹配，原Executive前缀逐字节一致 |
| 离线测试 | 139通过；不是Verus策略正确性或actor效果验证 |
| 评测 | 0个episode；未读取封存test进行构建 |

字节数不等于token数，不能把2.729倍称为输入token或费用增加比例。
不过它明确说明：把78张卡组织成37组，并未自动让主目录更短。
当前渲染器在主目录完整展开每组include/exclude/distinguish描述，是长度的重要来源。

保留的6组合并：045+071、047+062、060+075、038+042、055+065、006+069。
逐项对照了原始卡与合并条款，但这仍是文本审阅，不是运行Verus证明这些建议。
合并条件、版本限定、原卡的独立任务支持强弱，并不会因为该组织方式而自动改善。

## 两处保守回退

### 003与043：不同证明方向，不宜强行当重复规则

003由marshalability与序列化相等推view相等；043由view相等推marshalability相等。
模型放进同一merged规则后，主要是在共同字段标题下并列两套不同条件/动作，
还把fallback构造器分析的要求写在前提列表中，容易被读成直接路线的必要前提。
因此保留同一个family，但两张卡分别原样保留；并未移组或改其证明内容。

### 018/034/057：不能擅自消解原文中的措辞冲突

018的Action要求独立处理两种诊断，Validate却同时叙述两步修复。Router没标记；
Reducer也没标记，而是把Validate改成按诊断选择修复的版本。这是未获授权的
源文解释，不只是去重。将受影响的两条merged规则回退成018/034/057三张原卡。
所有case和条件交叉链接仍保留，原卡冲突仍显式列为未解决，而非被宣称已修好。

循环组035/036/041最终保持3条独立原文，没有把Router所说的层次关系变为强制流程。
052保持成功后的warning cleanup，没有当作失败证明的通用trigger修复。

## 费用与边界

账本估算：Router第一次USD0.29765604，完整重试USD0.29574336，
37次Reducer合计USD1.12518296，累计**USD1.71858236**，低于USD5构建上限。
Reducer输入325606tokens（58240cache hit、267366miss），输出194368tokens。
全部37次费用已结算到本地账本，没有未决请求或剩余reservation。
这是现有计费逻辑的估算，不是供应商账单；时间段/周末折扣 caveat见BUILD_STATUS。

没有收费的第三次Router调用，也没有收费的Reducer重试。规范化、审阅回退、
渲染、测试和reader检查全部离线。原卡、历史结果、原始/封存数据均未改动。

## 下一步需要确认

建议先审阅本候选，而不是立即评测。若精简主目录，可在不改变37组归属、72条
正文规则及可选读取行为的前提下，缩短每项入口描述，把详细排除条件与相邻组
区别留在reference正文。是否这样改、是否保留37组粒度，需要确认后再产生新版。
这不是要求遵循Trace2Skill原版，也不意味着更短目录必然提高效果。
共同TASK、原Executive、相同权限和未来20×2×1评测逻辑保持既定约束。
