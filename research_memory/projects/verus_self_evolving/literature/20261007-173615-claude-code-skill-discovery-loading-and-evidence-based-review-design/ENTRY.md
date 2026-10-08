# Claude Code skill discovery loading and evidence based review design

## Scope

2026-10-07 官方资料调研：结合用户刚讨论的 retrieve，同时核查 Claude Code
skill 发现/加载与质量 review。只研究和提方案，不安装插件、不改代码或卡库、
不调用收费模型。对照[现有卡片/trace 审查](../../notes/20261007-140333-completed-campaign-figures-and-card-action-evidence-audit/ENTRY.md)。
专用 memory/bash_exec 接口不可用，使用已有仓库记忆和文件工具归档替代。

## Sources

| source | link | why it matters |
|---|---|---|
| Claude Code skills | [官方产品文档](https://code.claude.com/docs/en/skills) | invocation、description、lifecycle、listing、eval |
| Agent Skills architecture | [Anthropic engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | metadata/body/resources 渐进加载 |
| Authoring practices | [官方开发文档](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | discovery 描述、正文结构、模型适配 |
| Official skill-creator | [官方插件源码](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/skill-creator/skills/skill-creator/SKILL.md) | 正/负触发、baseline、人工 review、迭代 |
| Trigger evaluator | [run_eval.py](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/run_eval.py) | Claude CLI 和早期 Skill/Read 检测 |
| Output/trace grader | [grader.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/agents/grader.md) | 全 transcript、实际产物、逐条证据 |
| Description optimizer | [run_loop.py](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/skill-creator/skills/skill-creator/scripts/run_loop.py) | 开发 split 与版本选择边界 |
| Evaluation workflow | [Agent Skills guide](https://agentskills.io/skill-creation/evaluating-skills) | clean context、old/without、成本和反馈 |

来源为调研时读取的 current/main，不宣称已 pin Claude Code 闭源生产实现。
本项目实际部署以此前 hash-bound frozen artifacts/trace 为依据。

## Method Patterns

### 发现与加载：官方可确认的公开机制

- 常规会话先提供名称/描述，模型根据任务决定调用，正文随后进入上下文；
  附加文件按需要再读取。没有依据将其描述成某个隐式 embedding 排序器或
  固定 top-k 检索器；也不能保证每次都触发正确。
- 正文读过仍留在后续上下文。当前 Claude Code 对相同内容的再次调用采用
  简短已加载提示，变化内容才另加；不是调用后彻底零 token 成本。
- 描述应同时说明用途和何时用。官方没有统一要求只能10/20词，metadata
  字数只是近似指导。不能声称 Claude 单个描述必定比我们26/32词 Trigger 短。
- 当前 Code 文档对 description listing 有总预算，超量可去掉一些描述只留
  名称。该有损策略不宜照搬我们的完整索引/自主选择契约；长度数字与产品
  版本相关，不机械移植到 DeepSeek。

### Review：触发与效果分开

官方 skill-creator 使用应触发和不应触发的真实例，重点包括共享关键词但
不适用的 near-miss。任务质量则用干净上下文的 with/without 或新/旧版本
对照，记录 token、时间、输出断言和人工反馈；可做版本 blind A/B。
它是辅助工作流，不是每个已安装 skill 都自动具备语义正确性保证。

官方 grader 读完整 transcript 和实际产物，为每条断言寻找具体证据，
并检查预设断言没涵盖的事实/过程/质量声明。不信 actor 自称已完成，也不
把文件存在等同正确。对本项目，Verus/Lynette 仍是正确性主判据，LLM review
辅助解释使用机制；读取、实际采用和因果收益必须分开。

## Takeaways For This Project

我们已实现 card body 按需读取，不需要重新发明这一层。主要差距是重复
title/Trigger、路由描述与完整前提耦合、规则重叠和独立触发审查不足。
本地对应代码为 `card_bank.py` 的 `AUTONOMOUS_RETRIEVAL_INSTRUCTIONS`、
`_index_entry` 和 `build_bundle`。

建议最小迁移路线（未实施）：

1. 先修 title==Trigger 的重复渲染。保持所有 ID 可见，保留现有卡内容，
   冻结旧部署用于比较。该项无需重新学习。
2. 新版区分简短 routing description 与完整 Trigger/Action/Why/Validate/
   Avoid when。短描述只用于发现，读取后核对完整语义前提；不能直接硬截断
   长 Trigger。如需模型生成，仍走 native SkillOpt 输出链并记录证据。
3. 训练侧开发截面做“值得查阅/不适用/可选”审查：真实 trigger inference
   error vs 已成功 warning；固定宽度序列化 vs 普通 closed map view；已有
   matching helper vs 没有 helper。测 near-miss/漏选，不将读率最大化。
4. Trace review 留前提→实际动作→验证变化→拒绝/失败反例，offline sidecar
   保留来源，不把训练参考答案泄漏进 actor 提示。
5. 后续如用户授权，旧/新版同卡库对照仅改变索引/加载接口，单独检查上下文
   大小、匹配、实际应用、600s完整 episode 成功、验证与成本。继续自主选择，
   不强制 top-k、次数或人工选卡。当前 validation 已用于分析，不能反复调后
   冒充独立确认性数据；开发数据和封存终测分离。

不必把78张卡变成78个插件、不必引入向量库或完整HTML平台才能开始。
下一步为用户确定实施范围；当前仅新增文献/设计记录并更新索引。

## Gaps / Risks

- 依赖 `claude -p`/Skill tool 的脚本不是 DeepSeek harness 的直接测量工具。
  `run_eval.py` 的早期检测对先用其他工具的路径会快速退出，本项目应根据
  完整轨迹的真实成功 body read 判断，并记录晚读/拒绝/部分采用。
- `run_loop.py` 虽然不把内部 test 分数传给描述改写模型，但最终按该分数
  选择 best_description；因此内部 held-out 是版本选择开发数据，不是终测。
  不能把 sealedtest20 放入循环。
- 格式正确、建议正确、值得查阅、实际有效是不同指标。多个合理解法时
  不读某张可用卡不自动构成任务失败或硬性漏检。
- 官方通用开发文档与较新产品文档对内建 eval 工具可用性的表述不同步，
  应区分 API 与 Code 产品，不用旧的一句话概括所有环境。
- 官方工程经验不能证明 DeepSeek 上省 token 或提高 solved rate。主结果
  保持 inconclusive；本轮无代码/卡库/旧结果修改、无收费请求、无 raw-data
  写入或 sealed-test 读取。Local memory fallback，无图谱完成声明。
