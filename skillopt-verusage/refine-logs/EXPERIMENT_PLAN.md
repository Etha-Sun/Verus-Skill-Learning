# SkillOpt S1/S2 跨模型补充实验计划

**问题**：在冻结的 VeruSAGE test-20 上，补齐 S1，并用参考设置复核 GLM 与 Qwen 的 SkillOpt skill 效果。
**方法主张**：只有在同一模型、同一 actor contract 下，blank、S1、S2 的 paired task outcome、runtime 和 cost 才能用于判断 skill transfer。
**日期**：2026-08-21

## Claim Map

| Claim | 为什么重要 | 最小可信证据 | 实验块 |
|---|---|---|---|
| C1：S1/S2 在 held-out test 上的影响依赖 actor | 这是 SkillOpt learned skill 是否跨模型可迁移的核心问题 | 每个模型固定 test-20，报告 blank/S1/S2 solved、paired transitions、runtime、tokens、cost | B1, B2 |
| C2：此前 GLM 低分主要受 actor/bridge/throughput setting 影响 | 若不先对齐，无法把 12/20 对 16/20 解释成模型能力差异 | 参考设置的串行 GLM S1/S2，且 429 等待接近零；与作者 no-skill 16/20 分开标注 provenance | B1, B3 |

**Anti-claim**：不能把不同 skill、不同 prompt、不同 Verus、不同并发或不同 Qwen precision 的分数合并成一个 skill delta。

## Paper Storyline

- 主表必须展示：每个 actor 的 blank/S1/S2 solved rate、paired gain/regression、mean/median runtime、timeout、tokens、requests 和 cost。
- 附录必须展示：GLM setting identity、July 与 official Verus 两题修正、Qwen BF16 服务身份、逐任务 outcome。
- 不做：新的 SkillOpt evolution、修改 S1/S2、使用 test outcome 选择新 skill、从单次 20 题声称稳定或普遍提升。

## 冻结实验对象

| Skill | 文件 | Bytes | SHA-256 |
|---|---|---:|---|
| blank | `skillopt-verusage/skills/blank.md`；参考模式中不创建 skill 目录 | 1 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| S1 | Epoch-1 accepted `steps/step_0001/candidate_skill.md` | 3,022 | `fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab` |
| S2 | retained best `best_skill.md` | 4,179 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` |

S1 使用 gate 实际评估并接受的 candidate；后续仅增加空 `SLOW_UPDATE` marker 的 3,075-byte 文件语义相同，但不作为正式身份。

## Experiment Blocks

### B1：GLM 参考设置复核

- Claim tested：C1、C2。
- Dataset：冻结 test-20，items SHA `81194e9c...c42`，单次重复。
- Compared systems：作者报告的 reference no-skill 16/20；本地 reference-aligned S1；本地 reference-aligned S2。
- Setup：GLM-5.3；串行；600s actor；120s final check；Codex 0.147.0；max reasoning；1,048,576 context；8192 normal output；仅在 `finish_reason=length` 时 131072 retry；1800s upstream timeout；不设置 temperature/top-p/seed；Chat non-stream；`thinking={type: enabled}`；仅 `exec_command`、`write_stdin`；保留 `reasoning_content`/`reasoning`。
- Verifier：主表使用 July 2025 Verus；两个 version-sensitive task 再用 official `ddc66116` 定向复核。
- Success criterion：20/20 provider-valid；无静默 length truncation；429 aggregate wait 接近零；skill 文件与 test hash 精确匹配。
- Failure interpretation：若仍低于作者 no-skill，保留 Codex/Verus binary SHA、model alias 时间和单次随机性为残余解释，不声称模型能力下降。
- Priority：MUST-RUN。

### B2：补齐 S1

- Claim tested：C1。
- Compared systems：GPT-5.6 Sol、DeepSeek V4 Pro、GLM-5.3、Qwen3.8-27B BF16。
- Dataset：同一冻结 test-20。
- GPT/DeepSeek：沿用各自已完成 blank/S2 的本地 semantic contract，仅新增 S1。
- GLM：使用 B1 reference-aligned S1。
- Qwen：与其 blank/S2 一起使用同一个 reference-aligned contract。
- Success criterion：每个 arm 20/20 provider-valid，skill SHA 锁定，输入不变，Verus+Lynette 独立评分。
- Priority：MUST-RUN。

### B3：Qwen 正式 blank/S1/S2

- Claim tested：C1。
- Model：官方 `Qwen/Qwen3.8-27B` revision `1d4bf0f...60c0`，BF16，TP=4，4×L40S，262,144 context，最多4 sequences。
- Contract：Codex 0.147.0，xhigh，reference prompt/AGENTS，8192→131072，1800s provider timeout，Chat non-stream，`enable_thinking=true`、`preserve_thinking=true`，仅 shell tools。
- Run order：blank → S1 → S2；参考 runner 每个 arm 内为1 task worker；arm 之间不重叠。vLLM 的 `max-num-seqs=4` 仅为服务容量，不作为 actor 并发度。
- Success criterion：模型 ID、weight revision、service config、tool history、usage、20/20 results 完整；不得使用或停止其他用户的服务。
- Failure interpretation：若 GPU 持续被占用，状态保持 BLOCKED，不借用其他用户 endpoint，也不把 smoke 当正式结果。
- Priority：MUST-RUN。

### B4：逐任务 skill 机制分析

- Claim tested：解释 C1 的方向和失败机制，而不是只看 aggregate score。
- 分组：blank→S1、S1→S2、blank→S2 的 gain、regression、stable solved、stable failed。
- Evidence：candidate diff、Verus/Lynette diagnostics、tool sequence、timeout position、最后有效 candidate；不暴露隐藏 chain-of-thought。
- 输出：每个模型一个 transition 表；每个非零 delta 至少审阅全部 gain/regression；持平模型抽查 skill 改变轨迹但不改变结果的任务。
- Priority：MUST-RUN。

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | 估计成本/时间 | 风险 |
|---|---|---|---|---|---|
| M0 | 配置和证据身份 | check-only、bridge unit tests、Codex 0.147、GLM/Qwen one-task smoke | 所有 hash/model/tool/usage 均匹配才进入正式 run | <30 min；smoke 少量 API | 配置漂移 |
| M1 | 快速补齐 S1 | GPT S1、DeepSeek S1 并行 | 20/20 valid | GPT local quota；DS 约 $1.3–2.0；约10–15 min | provider alias/随机性 |
| M2 | GLM 对齐 | GLM S1、S2、local blank 串行 | 每臂20/20 valid，429 等待近零 | 原估计约 $7–10/arm；实测后更新 | 串行慢、仍可能限流 |
| M3 | Qwen 三臂 | GPU 释放后 blank、S1、S2 | owned service + 真实 smoke PASS | $0 API；约6–12 L40S GPU-hours | 当前4 GPU被他人占用 |
| M4 | official Verus correction | 新增 arm 的两个 version-sensitive tasks | 结果有效并保持同 skill/model | 14 targeted tasks | 与 July 主表不是同一 condition |
| M5 | 分析和审计 | paired analysis、cost/runtime、独立 integrity review | 所有数字可追溯到 result/ledger | 约1–2 h | 单次20题不估计方差 |

## Compute and Data Budget

- 新增 actor executions：主矩阵最多 160（GPT S1 20、DeepSeek S1 20、GLM blank/S1/S2 60、Qwen blank/S1/S2 60），另加24个 official-Verus 定向任务（四模型 × 三 skill 条件 × 两题）。
- 预计新增 paid API：约 $16–22 GLM + $1.3–2.0 DeepSeek；GPT local quota；Qwen $0 API。
- 预计 Qwen：约6–12 L40S GPU-hours，具体取决于超时比例。
- 最大瓶颈：GLM 串行 wall time，以及4张 L40S 当前被另一用户的活跃 Qwen run 占用。
- Raw datasets 和 sealed data 保持只读；所有生成结果写入 `VERUS_SKILL_RUN_ROOT`。

## Risks and Mitigations

- 对方 Codex/Verus binary SHA 不可读：安装同一 Codex 版本，使用同版 July Verus，完整记录本地 SHA；结果标为 setting-aligned，不称 byte-identical。
- GLM 429：串行运行；若仍出现持续 429，暂停并加入全局 pacing，而不是让等待吞掉 task budget。
- Qwen GPU ownership：只在 GPU 释放并启动自己的服务后运行。
- Verus version：July 主表与 official targeted correction 分表汇报，不混合 denominator。
- 单次随机性：所有结论限定为 observed paired test-20 result，不使用“稳定”“普遍提升”。

## Final Checklist

- [ ] GLM documented settings 全部进入 manifest
- [ ] Qwen owned BF16 service 和真实 Codex tool smoke PASS
- [ ] GPT/DeepSeek S1 完成
- [ ] GLM S1/S2 完成
- [ ] Qwen blank/S1/S2 完成

## 2026-08-21 01:07 CDT 计划修订

- GLM 增加一个本地对齐 blank arm，原因是作者聚合分数不能替代同机 paired trajectory baseline。
- Qwen actor worker 从4修正为1；参考实现的 task loop 是串行，`max-num-seqs=4` 不是 task 并发设置。
- official-Verus 定向校正扩展到四模型的 blank/S1/S2 全部条件，以保持两版本表格完整。
- [ ] July 与 official Verus 分开报告
- [ ] performance、runtime、tokens、requests、cost 齐全
- [ ] gain/regression/stable trajectory analysis 完成
- [ ] 独立 experiment integrity audit 完成
