# Offline organization prompts v2 (candidate construction)

这两份是构建prompt，不是求解actor的新指令。当前已冻结并启动Router候选调用；
执行和费用状态以 [BUILD_STATUS.md](../BUILD_STATUS.md) 及运行根目录账本为准。
用户指定所有模型调用使用 `deepseek-v4-pro`、`reasoning_effort=max`，包括Router、
Reducer、actor及任何模型审查/修订，不自动切换其他模型或推理档位。
构建调用的输出上限、分批方案、费用上限与最终prompt哈希需在执行前冻结；
不能把actor每题600秒的设置自动当作离线构建调用合同。

## 文件与消息边界

- [router_system.md](router_system.md)：文件全文作为router的system message。
- [reduce_system.md](reduce_system.md)：文件全文作为单个family reducer的system message。
- 输入由未来的构建程序序列化成JSON user message；原卡内容视为数据，不拼接成指令。
- 使用英文prompt和英文产物，保持与原卡及求解技能语言一致。
- 已实现runner、结构验证器、renderer与hash校验reader；语义判断仍需独立审查，
  不能把结构测试通过当作知识正确或评测收益。
- [router_review.md](router_review.md)：本次可执行性审查、实际卡片边界检查与未验证项。
- [主SKILL与reference索引模板](../templates/README.md)：固定Executive加完整路由目录，
  不把构建prompt或全部reference正文部署到主文件。

## 构建流程

```text
repaired78完整正文 + 修订短描述
    ↓ 离线Router：全库比较语义特征，提出taxonomy并分配78张卡
cluster_manifest候选
    ↓ 程序结构校验 + 分组边界审查，冻结taxonomy
每组原卡全文 + family定义 + 相关关系候选
    ↓ 组内Reducer：判别是否真重复；保留前提、分支与独特内容
规则JSON + 逐卡覆盖/冲突记录
    ↓ 原文对照审查 + 确定性渲染 + 顶层目录/链接检查
SKILL.md短目录 + references/*.md
```

Router把特征提取、taxonomy和分配放在一个全局候选响应中，不为每张卡独立造类别。
78张卡必须完整输入、完整输出归属；上下文或输出预算不足时停在preflight，
显式重新设计分阶段合同，不能静默截卡或让独立分批各自发明不同taxonomy。
Reducer逐组处理，不能因为Router标了duplicate_candidate就无条件合并。
一个family可以包含多条独立规则，不要求“一组压成一张卡”。

v2区分“整卡存放位置”和“卡内适用情形”：一张卡只存一次，但可以有多个case。
Router必须逐case说明入口状态、当前可观察信号和来源短摘录。跨组链接附带case
与适用条件，不能把多用途卡的所有建议都当成在同一诊断下适用。
没有主要归属卡、只含跨组case的family只是导航页，直接渲染指向所属reference
的链接，不运行空输入Reducer。有主要归属卡的family才做组内reduce。

## Router输入合同

JSON包含：`schema_version`、`bank_sha256`、`expected_card_ids`、`cards`。
每张card包含 `id`、`content_sha256`、完整`content`、原`index_description`。
只传同一repaired78；不传历史validation题、结果、相关卡标签或test数据。
程序在调用前验证78个ID唯一、内容非空且哈希匹配。

## Reducer输入合同

JSON包含：`schema_version`、`bank_sha256`、`family`、`expected_card_ids`、
`cards`、`relations`、`neighbor_routes`、`card_cases`。
`cards`是该组主要归属卡的完整原文；`relations`仅是待复核建议；
`neighbor_routes`只含已审查的邻组ID和路由边界，不提供邻组新策略正文。
跨组近重复在taxonomy冻结前审查，reducer不得悄悄改归属或拷入邻组策略。
`card_cases`保留该组所存卡的全部已审查case，包括被其他family链接的case。
Reducer输出case到rule的映射，供程序把跨组链接解析到实际保留的规则。

## Reduce准则：保留适用条件的去重，不是摘要比赛

| 卡之间的关系 | 处理 |
|---|---|
| 条件、动作、版本一致的重复建议 | 合并重复表达，保留全部非重复约束 |
| 同一问题的互补步骤 | 同reference中分条放，只有原文支持时才给执行顺序 |
| 相似主题但不同条件/动作 | 保留不同规则及明确分支，不合成万能建议 |
| 无法裁决的冲突 | 标记review，不自行挑“更强”版本 |
| 无法安全合并/独特卡 | verbatim保留，由程序原样复制正文 |

例如“缺少量词前提”与“已有前提但触发失败”可以放在可相互区分的导航区域，
但不能合成“遇到量词问题就改trigger”。这是方法示意，不是本次已生成的卡内容。

## 必须通过的验收

- Router分配ID集合恰好等于78卡ID集合，每卡一个primary family；链接无悬挂。
- 每卡case都被主要路由或带条件跨链接覆盖；来源短摘录必须能在对应原文找到。
- family目录不能排除自己实际收纳的case；仅导航family必须有有效出链。
- 每family全部原卡在Reducer覆盖表中；merged规则逐条claim绑定来源ID。
- Reduce后case到rule映射完整，跨组链接能解析；缺失/含糊case不得当成已覆盖。
- coverage齐全只是结构条件，仍须检查被合并掉的限定条件、Why和Avoid没有丢失。
- verbatim内容由程序从冻结输入复制，不让模型重抄时改字。
- 路由描述只描述适用边界，不能把新的执行策略塞进顶层目录。
- `needs_review`或`blocked`输出不自动部署；通过独立原文对照后才能冻结候选。
- 保留请求/返回/usage/审查记录于运行根目录，未通过候选不基于validation成绩挑选。
- 程序计算并验证哈希/计数，独立源题支持由provenance做集合运算，不让模型猜。
- 在线仍由原actor自主选择reference，不添加额外检索模型或强制读取规则。

## 已授权的主目录精简阶段

`compact_index_system.md`只接收已经生成的family路由信息，输出37条短入口描述。
模型仍为DeepSeek V4 Pro/max，不重新分组、不reduce正文、不读取评测任务。
每项150ASCII字符上限，程序保证一项一行、ID全覆盖及主文件总字节不超过flat control。
完整边界留在未改动的reference正文。原始响应和格式校验保存，主文件前缀、reader、
reference内容/manifest逐字节比对；本步骤不授权启动评测。
