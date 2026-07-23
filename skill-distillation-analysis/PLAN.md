# Analysis Plan

**状态：** complete

**冻结日期：** 2026-07-22

**任务类型：** 文献整合 + 既有实验审计；不启动新的 GPU/agent rollout。

## 目标与验收

| 步骤 | 产出 | 验收 |
|---|---|---|
| 1. 固定研究问题 | 本目录与证据边界 | 区分 skill extraction、validated skill 与 parametric distillation |
| 2. 核验文献池 | `PAPER_MATRIX.md` | 每篇包含全名、作者、affiliation、链接、状态、机制、创新 |
| 3. 审计现有实验 | `FAILURE_PATH_ANALYSIS.md` | 给出原始运行指针、逐条件结果、混杂因素、可支持/不可支持结论 |
| 4. 综合定位 | `RESEARCH_SYNTHESIS.md` | 回答“我们怎么做 distillation”“中稿靠什么创新”“下一步做什么” |
| 5. 研究记忆 closeout | `research_memory/CURRENT.md` + index | 当前结果、 caveat、next action 可被后续 agent 启动时恢复 |

## 研究问题

1. 相关工作中，经验被蒸馏成什么：rationale、自然语言规则、workflow、程序/API，
   还是模型参数？
2. 正式接收论文改变了什么学习单位、验证信号或更新机制？
3. 本项目当前的 H0/H1/H2 实验到底证明了什么，尚未证明什么？
4. Codex 与 Qwen 的差异发生在 trace 读取、错误定位、verifier 反馈利用、library
   lemma 选择，还是安全收敛？
5. 哪个最小下一步能消除现有混杂，并把工作从 prompt engineering 推进到方法创新？

## 冻结假设

- “中稿”仅指可由会议、期刊或官方 proceedings/OpenReview 状态核实的正式接收。
  arXiv、under review 和 Workshop 单列。
- 本文献池是与本项目直接相关的代表性核心池，不声称穷举整个知识蒸馏或 agent memory
  领域。
- L2–L5 是本项目用于研究决策的非官方创新强度标尺，不等同于会议评分。
- solve rate、verifier pass、token、wall time 和 safety 是主终点；information gain
  仅是离线二级代理。

## 可支持的交付级结论

- 现有三条件结果不支持“trace-distilled global rationale 提高 solved rate 或 token
  efficiency”。
- Codex 三样例 3/3 是机制样例，不是 solve-rate 估计，也不是纯粹的模型尺度因果效应。
- closest-failure 的 Qwen 运行存在交互期 Verus 命令被 CLI 拒绝的系统性混杂；在修复
  harness 前，不能把 0/9 与 Codex 1/1 直接解释为模型能力差异。
- 下一轮首要任务是 verifier-access matched control；通过后再测试 task-state-specific、
  verifier-grounded H3。

## 停止条件

本轮只做审计和文档化。不会：

- 修改 legacy/raw 数据；
- 重跑 Qwen 或 Codex；
- 根据 3 个任务宣称方法有效；
- 将未验证的 local rationale 称为 transferable skill；
- 将预印本写成正式接收论文。
