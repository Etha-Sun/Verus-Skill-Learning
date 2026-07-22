# Research Contract: Hands-Off Trace Distillation

## Selected Idea

- **Description**: 从成功 frontier-agent Verus repair trajectories 中蒸馏
  短、可复用、verifier-grounded 的 proof-repair knowledge，并在相同 agent
  scaffold 下测量它能否保持 solved rate、降低 uncached inference cost，或
  帮助 local Qwen3.6-27B 缩小到 frontier baseline 的差距。
- **Immediate gate**: 在正式 R041 prompt distillation 前，先建立独立的
  30-task Qwen capability map，并冻结 pass、near_miss、stalled 三档诊断任务。
- **Selection rationale**: 当前 one-task Qwen smoke 只证明 harness 可运行，
  不能区分模型能力、任务难度和 context/scaffold failure。先测能力分布能避免
  用单一失败任务设计后续对照。

## Core Claims

1. **Primary claim C1**: 在 project-held-out live evaluation 中，冻结的
   trace-derived knowledge 能在 solved-rate non-inferiority 约束下减少 total
   uncached tokens per solved task。
2. **Supporting claim C2**: 同一冻结 knowledge 能改善 local 27B 的
   solve-cost frontier，并缩小它与 frontier no-knowledge baseline 的差距。

## Anti-Claims To Rule Out

- **A1 prompt-length confound**: H2 必须优于长度匹配的 H1 generic control。
- **A2 task leakage**: distillation、calibration、dev 和 sealed test 在 task、
  normalized source hash 与 near-code group 层面隔离。
- **A3 early-stop artifact**: token 少但 solved rate、安全性或 verifier progress
  下降不算成功。
- **A4 cherry-picked case study**: 三档任务只用于机制诊断；selected-case
  结果不能替代完整 held-out evaluation。

## Data Contract

- Raw datasets 与 sealed data 始终只读。
- Generated outputs 只写 `VERUS_SKILL_RUN_ROOT`；repo 只保留计划、测试、
  compact summary 与 durable pointers。
- **R040 distillation source**: 30 条成功 train traces，15 Anvil + 15 IronKV，
  30 个唯一 normalized tasks/sources。
- **R040A calibration source**: effective train manifest 映射到各项目
  `unverified/` 下的 canonical original task，另选 30 题，15 Anvil +
  15 IronKV；必须存在 standard trace 的 paired verified artifact，并由当前
  Verus 与 Lynette 对 canonical source 重新确认 security-valid；model 只看到
  canonical source。
- R040A 与 R040 在 normalized task id、normalized source hash 和
  7-token-shingle Jaccard >=0.90 层面均不重合。
- MA/NR sealed content 不得用于 selection、distillation、calibration 或
  threshold tuning。

## Calibration Contract

1. CPU preflight resolve 并约束所有 source/verified/R040 文件位于允许的
   train directories，重新计算 physical hashes；验证 standard paired
   verified artifact 当前通过 Verus+Lynette、canonical source 不能已经通过 Verus，并用冻结的
   Qwen tokenizer 记录 32,768 context eligibility。
2. R040B 在冻结 30 tasks 上只跑 H0，每题一次，固定 Qwen3.6-27B、Copilot
   CLI、prompt、tools、permissions、timeout 和 context budget。
3. 对预声明的边界候选补两次 repetition。若 provider 无显式 seed control，
   只能称 repetition。
4. 在查看 H1/H2 outcomes 前冻结：
   - `pass`: 至少 2/3 security-valid solved；
   - `near_miss`: 0/3 solved，但至少 2/3 proof-safe 且有 verifier-grounded
     局部进展，严格定义为 candidate target-error count 下降；total verified
     count 上升不算 progress；
   - `stalled`: 0/3 solved，至少 2/3 完成 candidate、Verus 和 Lynette 检查，
     但没有上述 verifier progress。
5. candidate 缺失、tool failure、timeout 或 context exhaustion 归入
   `infrastructure_failure`，不能解释为 reasoning failure。
6. 每档优先选择 3 tasks；每档只有 1 task 时只形成 qualitative smoke。
7. R040B 一次 screen 后按预声明类别最多选择 5 题/类补两次 repetition；
   required results 或 task/source/prompt/model hashes 不完整时禁止写 frozen
   tiers，聚合目录禁止覆盖。

## Method And Controls

- H0: original hands-off prompt，无额外 knowledge。
- H1: 与 H2 长度控制在 provider-reported input delta ±5% 的 generic Verus
  建议，不读取 R040 traces。
- H2: 仅由 R040 traces 生成的 <=800-token frozen global prompt。
- H2 不能为 calibration task 编写 task-specific oracle hint。
- 同一 task/condition 使用相同 scaffold、budget、tools、source snapshot 和
  safety checks；所有 task cost 与失败尝试都进入主 denominator。

## Metrics

- Primary quality: security-valid solved rate（Verus 0 errors + Lynette pass +
  无 bypass/exec semantic change）。
- Primary cost: total uncached input + output tokens / security-valid solved
  tasks，包含所有失败任务成本。
- Secondary: tokens/task、wall time、tool/Verus/checker calls、timeouts、
  candidate presence、illegal-edit rate、context exhaustion、GPU-hours。
- Calibration diagnostics: tier occupancy、repetition stability、source-to-
  candidate verifier diagnostics。文本 edit distance 只能辅助，不能定义
  “near answer”。
- Information gain 只保留为 secondary offline ranking/diagnosis signal。

## Decision Gates

- **GO R040B**: 30 tasks audit pass、sealed reads 0、R040 exact/near overlap 0、
  model-free harness sanity pass、4-GPU backend available。
- **GO R041A**: tiers 与 hashes 已冻结，H1/H2 prompts 已冻结。
- **STOP/branch local contrast**: 30 tasks 全 stalled、全 context-ineligible，
  或 tiers 在 repetitions 中不稳定；先修正 task pool/scaffold/context route。
- Calibration 失败不自动否决 train-only R041；它只否决当前 local contrast
  设计。
- 最终 method claim 仍要求 leakage-safe held-out R042-R053 live evidence。

## Status

- [x] M0 corpus/leakage/harness integrity complete
- [x] R040 30-trace distillation source frozen
- [x] R040A 30-task calibration set frozen
- [ ] R040B Qwen H0 screen complete
- [ ] R040C-R040D repetitions and tiers frozen
- [ ] R041 H1/H2 prompts distilled and frozen
- [ ] R041A tiered local contrast complete
- [ ] R042-R044 held-out frontier dev gate complete
- [ ] Confirmatory sealed evaluation complete
