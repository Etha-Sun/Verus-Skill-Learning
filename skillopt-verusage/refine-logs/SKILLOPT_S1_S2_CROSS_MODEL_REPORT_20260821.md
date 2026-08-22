# SkillOpt S1/S2 跨模型测试报告

> 状态：实验运行中草稿。GLM final-aligned 与 Qwen BF16 尚未填入；完成独立审计前请勿引用本文件中的结论。

日期：2026-08-21

## 1. 研究问题

在冻结的 VeruSAGE test-20 上，比较同一个 actor 在三种输入条件下的结果：

- `blank`：不提供 skill 目录；任务要求仍由相同的 Codex prompt/AGENTS 提供。
- `S1`：SkillOpt 第一次通过 selection gate 的 skill。
- `S2`：第二次通过 gate、也是最终 retained best 的 skill。

核心 estimand 是同一 actor、同一任务、同一 harness 下由 skill 条件引起的 paired outcome 变化。不同模型之间的绝对分数不是 skill 的因果比较。

## 2. 冻结对象与判分

| 对象 | 冻结值 |
|---|---|
| test split | 20 tasks；AL 7、AC 6、IR 7；5 个历史 Claude-failed case |
| test items SHA-256 | `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42` |
| blank SHA-256 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| S1 SHA-256 | `fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab` |
| S2 SHA-256 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` |
| Codex CLI | 0.147.0；binary SHA `cb0a1556...a40` |
| actor generation limit | 每题 600s；valid timeout 不重跑；独立 final check 另有 120s 上限 |
| hard solved | `input.rs` 未改变，且 final Verus 与 Lynette 均通过 |

每个条件只运行一次，因此所有 score 与 transition 都是 paired observations，不是稳定性或方差估计。actor 即使在 600s 时被终止，只要留下的 candidate 在独立 final check 中同时通过 Verus 与 Lynette，仍按 SOLVED 计分。

## 3. Actor 设置

| Actor | Transport | Reasoning | Context | Task workers | API cost basis |
|---|---|---|---:|---:|---|
| GPT-5.6 Sol | native Responses through Codex | max | 1,048,576 | 1 | local quota |
| DeepSeek V4 Pro | native Responses through Codex | high | 1,048,576 | 1 | DeepSeek ledger；无 usage 的失败请求单列 unknown |
| GLM-5.3 | Responses -> Chat bridge | max + thinking enabled | 1,048,576 | 1 | Z.AI ledger；无 usage 的失败请求单列 unknown |
| Qwen3.8-27B BF16 | Responses -> local vLLM Chat bridge | xhigh + thinking preserved | 262,144 | 1 | $0 API；报告 4-GPU hours |

GLM 采用 reference 的串行设置，正常单 turn 输出上限为 8,192，只有 upstream 明确返回 `finish_reason=length` 才使用 131,072 retry；transport error 不扩充输出。Qwen 使用 official checkpoint revision `1d4bf0f...60c0`、BF16、TP=4、4×L40S、vLLM 0.19.1，并在正式运行前要求真实 runtime provenance 与 one-task smoke 同时通过。

## 4. Legacy/project-profile July-Verus 诊断结果

下表的 GPT/DeepSeek 三臂内部 prompt byte-identical，因此适合做各 actor 内的
trajectory case study；但它们使用 project prompt、262K context、并且 blank
workspace 中含1-byte 空 `SKILL.md`，不能与 reference-aligned GLM/Qwen 混成
四模型主表。最终主表将由当前运行中的 reference-aligned 重跑替换。

| Actor | blank | S1 | S2 | blank -> S1 | S1 -> S2 | blank -> S2 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 18/20 | 18/20 | 17/20 | 0 | -1 | -1 |
| DeepSeek V4 Pro | 13/20 | 11/20 | 13/20 | -2 | +2 | 0 |
| GLM-5.3 | pending | pending | pending | pending | pending | pending |
| Qwen3.8-27B BF16 | pending | pending | pending | pending | pending | pending |

## 5. Legacy performance、runtime 与 cost

### 5.1 全部 20 题的 operational result

| Actor | Skill | Solved | Mean / median actor time | Timeouts | API requests | Input/prompt tokens | Output tokens | Cost | Cost/task |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | blank | 18/20 | 205.94 / 126.71s | 1 | local | 8,760,922 | 145,066 | local quota | local quota |
| GPT-5.6 Sol | S1 | 18/20 | 177.16 / 105.01s | 0 | local | 9,653,665 | 138,015 | local quota | local quota |
| GPT-5.6 Sol | S2 | 17/20 | 205.54 / 99.59s | 1 | local | 10,036,223 | 131,720 | local quota | local quota |
| DeepSeek V4 Pro | blank | 13/20 | 370.12 / 337.86s | 7 | 537 | 20,700,806 | 365,718 | $1.598398 | $0.079920 |
| DeepSeek V4 Pro | S1 | 11/20 | 356.62 / 448.72s | 9 | 433 | 17,079,934 | 367,487 | $1.395085 | $0.069754 |
| DeepSeek V4 Pro | S2 | 13/20 | 341.01 / 242.59s | 8 | 465 | 18,673,223 | 327,435 | $1.393428 | $0.069671 |
| GLM-5.3 | blank | pending | pending | pending | pending | pending | pending | pending | pending |
| GLM-5.3 | S1 | pending | pending | pending | pending | pending | pending | pending | pending |
| GLM-5.3 | S2 | pending | pending | pending | pending | pending | pending | pending | pending |
| Qwen3.8-27B BF16 | blank | pending | pending | pending | pending | pending | pending | $0 API | pending GPU-hours |
| Qwen3.8-27B BF16 | S1 | pending | pending | pending | pending | pending | pending | $0 API | pending GPU-hours |
| Qwen3.8-27B BF16 | S2 | pending | pending | pending | pending | pending | pending | $0 API | pending GPU-hours |

### 5.2 共同 solved tasks 的 paired efficiency

| Actor | Comparison | Common solved | Before -> after mean time | Before -> after mean cost |
|---|---|---:|---:|---:|
| GPT-5.6 Sol | blank -> S1 | 18 | 177.50 -> 182.26s | local quota |
| GPT-5.6 Sol | S1 -> S2 | 17 | 164.39 -> 186.29s | local quota |
| GPT-5.6 Sol | blank -> S2 | 17 | 160.08 -> 186.29s | local quota |
| DeepSeek V4 Pro | blank -> S1 | 11 | 217.53 -> 155.67s | $0.04746 -> $0.03061 |
| DeepSeek V4 Pro | S1 -> S2 | 10 | 158.63 -> 127.64s | $0.03135 -> $0.02815 |
| DeepSeek V4 Pro | blank -> S2 | 11 | 230.47 -> 138.88s | $0.04962 -> $0.03000 |

共同 solved 子集只回答“两个条件都能解出的题上是否更快/更省”；它不能抵消 regression，也不能与各自不同的 solved 子集均值混用。

## 6. Trajectory 机制分析

### 6.1 GPT

blank 与 S1 解出完全相同的 18 题。S1 的全题均时下降不是共同成功题更快，而主要来自对两个 July-Verus infrastructure blocker 更快停止：blank 分别用 323.13s、600.60s，S1 用 174.59s、87.94s；18 个共同成功题反而从 177.50s 小幅增加到 182.26s。

S2 唯一回退是 `e0ff80bd8ec2d2c26eb9`。blank 与 S1 都通过已有 liveness lemma 建立较短 bridge 并 solved；S2 写出 198 行手工 `Step` case split，在 preservation premise 仍失败时超时。它没有遵守 skill 自己的 representative-arm 与 checkpoint 规则。因此这是 instruction compliance 失败的直接证据，而不是新增规则在逻辑上错误的证据。

### 6.2 DeepSeek

- `a31...`：S1 的 `/tmp` probe、非规定 verifier 与顶层 import 路线超时；S2 将 `==>` 改为 skill 明确要求的 `implies`，用 fully-qualified proof macro 保持 Lynette 安全，251.31s solved。属于与 S2 规则直接吻合的 gain。
- `22fb...`：blank/S1 都在错误的 fold 形状和多个 probe 中超时；S2 只绑定一次 closure，并按真实定义使用 `drop_last/last` 递归，482.50s solved。属于 exact higher-order shape 的强机制吻合。
- `2532...`：blank/S1 浏览库后 candidate 未改变；S2 留下 +38/-3 proof patch，Codex 虽在 600s 被终止，但 final Verus+Lynette 均通过。属于实际产出 candidate 的 gain，但不是 runtime gain。
- `548...`：blank/S1 均 solved；S2 写了额外 helper，却把目标 proof body 留空并且没有恢复 checkpoint，600.94s regression。
- `318...`：blank 用匹配 `Seq::filter` 定义的真实 induction solved；S1 使用错误的 `first/skip` 形状，S2 留下无关 probe，两者都超时。说明 learned skill 对“短 bridge”的偏好不能替代必须的 induction fallback。
- official-Verus `f24...`：blank 通过已有 sibling lemma 仅加8行 solved；S1/S2 反而改写原有 uninterpreted `view` specification，最终未验证且违反 proof-only boundary。它是 extensional-bridge 策略偏置的直接负例。

完整客观证据笔记位于 `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/report-s1-s2-20260821/trajectory_analysis_notes_zh.md`。

## 7. Legacy Verus 版本校正

July 主表保留固定 `/20` denominator。`f24cf9...` 与 `826687...` 另外使用 official VeruSAGE Verus 做 fresh actor rerun；“校正后”数字是另外18题的 July outcome 加这两题的 official fresh outcome，不是完整 official-Verus test-20 rerun。

| Actor | Skill | July raw /20 | Official two | Targeted hybrid /20 |
|---|---|---:|---:|---:|
| GPT-5.6 Sol | blank | 18 | 1/2 | 19 |
| GPT-5.6 Sol | S1 | 18 | 1/2 | 19 |
| GPT-5.6 Sol | S2 | 17 | 1/2 | 18 |
| DeepSeek V4 Pro | blank | 13 | 1/2 | 14 |
| DeepSeek V4 Pro | S1 | 11 | 0/2 | 11 |
| DeepSeek V4 Pro | S2 | 13 | 0/2 | 13 |
| GLM-5.3 | blank/S1/S2 | pending | pending | pending |
| Qwen3.8-27B BF16 | blank/S1/S2 | pending | pending | pending |

## 8. 与另一份 cross-provider 结果的边界

作者侧结果的 test-20 顺序与题号高度吻合，但其第二条件是 `native official baseline` skill tree，不是我们的 S1 或 S2。GLM 本轮对齐其串行、Codex 0.147、max reasoning、prompt 结构、600s 与 Chat bridge 设置；仍需保留三个差异：同版本字符串的 July Verus binary SHA 不同，当前 Codex 使用 `workspace-write` 而 reference 在外层 namespace 中使用 `danger-full-access`，以及 learned S1/S2 是单个 SKILL.md 而非 native baseline skill tree。Qwen 本轮为 BF16，作者侧为 FP8，必须作为不同 precision 条件报告。

## 9. 暂定结论

待 GLM、Qwen 与最终独立审计完成后填写。
