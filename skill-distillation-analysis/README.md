# Skill Distillation Research Analysis

本目录汇总本项目截至 2026-07-22 的 skill learning、knowledge distillation 与
Verus proof-repair trace 研究。

## 阅读顺序

1. [PLAN.md](PLAN.md)：本轮交付范围、证据边界与验收标准。
2. [RESEARCH_SYNTHESIS.md](RESEARCH_SYNTHESIS.md)：综合结论、现有工作定位、
   可发表创新门槛与下一步路线。
3. [PAPER_MATRIX.md](PAPER_MATRIX.md)：论文全名、作者、机构、链接、接收状态、
   skill 载体和创新点。
4. [FAILURE_PATH_ANALYSIS.md](FAILURE_PATH_ANALYSIS.md)：Qwen3.6-27B 与 Codex
   在三样例实验及 closest-failure 样例上的逐路径审计。

## 一句话结论

本项目不应继续把“从 trace 写出更漂亮的 skill prompt”作为主要创新。最有区分度的
路线是：利用 Verus verifier 做因果效用验证与组件 credit assignment，把通过验证的
task-state-specific skill 先外置，再研究如何针对不同学生模型编译和内化。

## 数据边界

- 原始数据树 `${VERUS_SKILL_DATA_ROOT}` 只读；本轮没有修改、移动或复制原始 trace。
- 完整运行日志仍只位于 `${VERUS_SKILL_RUN_ROOT}`。
- 本目录只保存人工审阅后的紧凑结论、公开论文元数据和运行指针，不保存 raw trace、
  token 明细表、完整日志或个人凭据。
