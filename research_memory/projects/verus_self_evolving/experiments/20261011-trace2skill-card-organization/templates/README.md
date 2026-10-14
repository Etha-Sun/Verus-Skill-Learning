# Main skill and reference index design

状态：初版候选已生成；用户授权精简主目录。保留历史长索引产物与冻结合同，
新增`compact_card_index.py`修订阶段；当前进度见BUILD_STATUS，不自动授权评测。
采用最新router：`../prompts/router_system.md`，输出协议`card-cluster-proposal-v2`；
reducer为`card-family-reduction-v2`。未来构建合同绑定实际文件哈希，不只写“latest”。

## 主文件是什么

[SKILL.md.tmpl](SKILL.md.tmpl)由三个部分组成：

1. **原始Executive**：逐字保留 `skillopt-verusage/skills/initial.md`，不让router
   或reducer改写，避免把知识组织实验变成新的整体解题指令实验。
2. **可选读取说明**：沿用A组自主选择/可以不读/可拒绝建议/同预算/正常验证原则，
   仅把card读取接口适配为reference，并解释一份reference可含多个条件规则。
3. **完整短reference索引**：每份reference一行，ID/文件链接加简短入口描述。
   关键诊断区别保留在短描述，完整适用/排除条件与邻组区别留在reference正文。

主文件不会全文重列78卡，不包含router/reducer的system prompt、构建解释、
源题ID、trace、审查记录、性能数字或私有provenance。原card ID可在正文标明来源。
这些模型仅离线组织知识；在线actor只接收主文件及可选读的reference库。

## 每个索引条目

格式见 [REFERENCE_INDEX_ENTRY.md.tmpl](REFERENCE_INDEX_ENTRY.md.tmpl)：

```text
- [reference-id](references/reference-id.md): 当前可观察goal/diagnostic，加必要的区分条件。
```

实际部署文字为英文ASCII，每条描述最多150字符；ID与链接由程序生成，不计入
描述额度。主文件总字节数不得超过同轮flat control，超限报错，不静默截断。
条目只帮助决定是否打开reference，不替代正文前提检查，不是新的解题步骤。
诊断区别如缺antecedent、trigger推断失败、已有事实实例化、成功后清警告必须保留。
详细前提、版本限制、排除项和邻组边界并未删除，仍在字节完全不变的reference中。
不能把不同入口误写成必须同时满足，也不能用笼统主题词取代可辨认的诊断。

短描述由DeepSeek V4 Pro/max仅基于既有family信息生成，prompt见
`../prompts/compact_index_system.md`。不再运行Router/Reducer或重写Executive。
旧renderer保留用于重现长索引初版；当前候选必须经过短索引修订与长度验收。

## 索引与正文如何对应

```text
bundle/
  SKILL.md                        固定Executive + 可选读取说明 + 全reference索引
  reference_read.py               依据索引ID读取，无在线模型/自动排序
  references/
    <reference-id>.md             组内规则、适用边界及来源card ID
    <navigation-id>.md            仅条件化跨链接的导航页（若需要）
```

- 常规family生成一个reference；若体积过大需要拆分，每个可读子reference也必须
  在主索引中列出。拆分ID/路由需离线审查，不能靠运行时隐藏分块或改变内容预算。
- 只有跨链接的family生成显式导航页，标明是导航而非新增知识。它也在根索引中；
  其带条件链接由`case_rule_map`解析到真正存放规则的reference/锚点。
- 有正文的reference开头放本组范围及本地规则目录，随后分条渲染Trigger/Action/
  Why/Validate/Avoid和前提/版本限制。多个条件分支不能混写成一条通用指令。
- 链接负责“找到文件/规则”，`reference_read.py <reference-id>`负责可审计读取。
  首版读取完整的一份reference，不把锚点选择伪装成已实现的局部读取功能；
  对返回全文计暴露量。直接工具读取文件也纳入审计。
- 共用规则只存一份，其他类别用带条件链接引用；不能复制正文后重复计卡数/支持数。

## 确定性渲染和验收

输入是审查后router目录、reducer规则/覆盖映射和冻结Executive，不是validation
成绩。按reference ID稳定排序，不暗中根据评测效果排序。模板占位符只由构建
程序替换；初版目录已生成，短索引版本须通过同样的可达性与来源检查后才供审阅。

1. 主文件Executive前缀必须与原`initial.md`字节一致。
2. 主索引条目ID集合等于全部可读reference的ID集合；无遗漏、重复或悬挂链接。
3. 链接文件及锚点存在，路径局限于bundle；reader只接受manifest内ID。
4. 每个原卡case都能从根索引到达最终保留的规则；只有ID覆盖不等于语义覆盖。
5. 部署产物没有未替换的`{{...}}`、占位文案或draft/examples；示例读取ID真实存在。
6. A/B除组织方案白名单外保持一致，尤其Executive/TASK/验证逻辑/标准库权限。
7. 记录根索引字节和可取得的token估计、每份reference长度与实际读取暴露；
   不通过静默截断来假装长度匹配或更省token。
8. 短索引ID集合恰好等于全部37个reference；每项一行、描述不超过150字符，
   主SKILL字节数不超过对照。Executive及可选读说明前缀、39个非SKILL文件哈希不变。

构建输出仅写运行根目录。renderer/reader已实现并完成零API检查；实际候选必须
经过语义审阅才能进入未来评测，不按虚构分类预填目录。
