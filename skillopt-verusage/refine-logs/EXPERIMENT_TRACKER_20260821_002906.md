# SkillOpt S1/S2 补充实验 Tracker

更新时间：2026-08-21 02:53 CDT

| Run ID | Milestone | Purpose | System / Variant | Split | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| R201 | M0 | GLM reference parity check | GLM bridge + Codex 0.147 | one training smoke | MUST | COMPLETE | `3a77a3e4e72edf600e2a` solved；155.13 s；Verus+Lynette PASS；24/24 calls；$0.223253 |
| R202 | M0 | Qwen environment parity check | Qwen3.8-27B BF16 | one training smoke | MUST | BLOCKED | reasoning 字段已修正；runtime `/models`、vLLM command、4-GPU snapshot 已加入 formal gate；xinyueh 的 orphan vLLM PID 1896375 仍占满4×L40S |
| R203 | M1 | legacy diagnostic S1 | GPT-5.6 Sol + S1 | test-20 | MUST | COMPLETE | project profile 18/20；内部 blank/S1/S2 prompt byte-identical，但不与 reference GLM/Qwen 混表 |
| R204 | M1 | legacy diagnostic S1 | DeepSeek V4 Pro + S1 | test-20 | MUST | COMPLETE | project profile 11/20；$1.395085；provider errors 0；不与 reference 主表混表 |
| R203R | M1 | reference-aligned matrix | GPT-5.6 Sol × blank/S1/S2 | test-20 + official two | MUST | RUNNING | direct-path propagation 已修复；真实 blank smoke 77.65s solved/V2/双 verifier PASS；formal 使用 `retryfix` IDs |
| R204R | M1 | reference-aligned matrix | DeepSeek V4 Pro × blank/S1/S2 | test-20 + official two | MUST | RUNNING | worker=1，1M context，high，prompt SHA `d0b663...`，blank skill absent，complete ledger |
| R205 | M2 | diagnostic S1 test | GLM-5.3 + S1 | test-20 | MUST | COMPLETE | 15/20；$4.999686；20/20 provider-valid；bridge SHA 与最终矩阵不同，不用于严格 skill-only delta |
| R206 | M2 | diagnostic S2 test | GLM-5.3 + S2 | test-20 | MUST | RUNNING | 8/20 complete，7 solved；ledger $1.652201；零 provider error/429；运行中 bridge 已加载旧 SHA |
| R206B | M2 | aligned no-skill test | GLM-5.3 + blank | test-20 | MUST | QUEUED | S2 后串行；将加载修复后 bridge SHA |
| R205R | M2 | final aligned S1 rerun | GLM-5.3 + S1 | test-20 | MUST | QUEUED | 与 final S2/blank 使用同一修复后 bridge SHA |
| R206R | M2 | final aligned S2 rerun | GLM-5.3 + S2 | test-20 | MUST | QUEUED | 当前 diagnostic chain 完成后重跑，最终主表仅用该结果 |
| R207 | M3 | formal no-skill | Qwen3.8-27B BF16 + blank | test-20 | MUST | BLOCKED | 等待 owned GPU service；reference task worker=1 |
| R208 | M3 | formal S1 | Qwen3.8-27B BF16 + S1 | test-20 | MUST | BLOCKED | R207 后运行 |
| R209 | M3 | formal S2 | Qwen3.8-27B BF16 + S2 | test-20 | MUST | BLOCKED | R208 后运行 |
| R210 | M4 | verifier-version correction | all models × blank/S1/S2 | two IR items | MUST | RUNNING | official `ddc66116`，与 July 主表分开；GPT/DeepSeek 已完成 |
| R211 | M5 | result analysis | blank/S1/S2 paired | test-20 | MUST | TODO | performance/runtime/cost + traj causes |
| R212 | M5 | integrity audit | independent reviewer | all artifacts | MUST | TODO | real_gt verifier-grounded；scope WARN expected |

## Execution incident 2026-08-21 01:50 CDT

GLM S2 的旧 partial run 在首个请求遇到 HTTP 429 后，错误使用了仅供
`finish_reason=length` 的 131072-token retry budget。该 run 未产生 retained
task result，raw artifact 与 $0.0932732 spend 均保留。bridge 已修复为 transport
error 立即上抛；21/21 focused tests 通过。正式 S2 从新 run ID
`fixed-test20-glm-s2-reference-retryfix-20260821` 重新开始。

## Verification update 2026-08-21 02:02 CDT

- Bridge/experiment suite: 78/78 unit tests pass.
- Codex harness suite: 46/46 unit tests pass.
- Shell syntax and Python bytecode compilation checks pass.

## Independent audit correction 2026-08-21 02:24 CDT

- Qwen3.8 tool history 按 reference contract 使用 `reasoning`，不再误用
  GLM/DeepSeek 的 `reasoning_content`。
- Chat transport/model/usage 错误现在在抛出前写入 ledger；未知 provider
  花费保持 `null`，避免把未记录请求误报为零花费。
- 修复后测试：SkillOpt/bridge 79/79，Codex harness 46/46，总计 125/125。
- 修复后 bridge SHA：
  `b7f3d067bc6efcb7644f5ee3ff2f296ef8a5f1a65ec15e08e4cbf0c4f3600c4a`。
- 因 GLM 当前 S2 已在旧进程中运行，它与既有 S1 均作为 diagnostic evidence；
  final GLM S1/S2 将在同一修复后 SHA 下重跑，防止桥接实现成为混杂变量。
- Qwen formal gate 还要求真实服务运行时 provenance：`/models` response、
  含 BF16/TP=4/262144 context 的实际 vLLM process command、以及恰好4张 GPU
  的快照。仅有静态 `model_identity.json` 不足以启动正式矩阵。

## Cross-model parity correction 2026-08-21 02:49 CDT

- 旧 GPT/DeepSeek 三臂的实际 TASK/user prompt 均为 SHA `13a4598...`，所以
  各 actor 内的 legacy paired comparison 有效；但 blank workspace 含1-byte
  `SKILL.md`，profile 也不是 reference cross-provider contract。
- 新主表改用与 GLM/Qwen 相同的 reference contract：prompt SHA
  `d0b663...`、blank skill absent、worker=1、1M context（Qwen 仍按其
  reference 使用262K）、600s。GPT/DeepSeek 三臂与 official two 校正已启动。
- launcher check-only 明确验证 GPT/DeepSeek 的 profile、prompt、skill absence、
  worker、context 和 verifier identity；全套测试仍为 79/79 + 46/46。

## GPT direct-path incident 2026-08-21 02:53 CDT

首个 GPT reference run 暴露出 direct evaluator 没有继续传递
`actor_contract_profile` 与 `condition_skill_present`：contract JSON 正确，但实际
workspace 仍为 project layout。该 run 在1个 retained result后立即终止，并以
`ABORTED.md` 标记，不能进入任何结果表。

修复后真实 one-task smoke 的 workspace 只有 `AGENTS.md`、`TASK.md`、
`candidate.rs`、`input.rs`；manifest 明确 `skill_present=false`，1M context，
prompt SHA `d0b663...`。任务 77.65s solved，V2 trace，Verus+Lynette PASS。
回归测试新增 direct reference blank 的参数传播/skill absence 检查；当前测试为
80/80 + 46/46。formal GPT 从新 `retryfix` run ID 重启。

## Frozen identities

| Object | SHA-256 |
|---|---|
| test items | `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42` |
| blank | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| S1 | `fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab` |
| S2 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` |
| local July Verus | `27bd3d402d05a19c1915b33ae5d04e3a64599d18f0738970586755c53552a3bd` |
| official Verus | `737048da2e41eabe9b3b0594edb11da6593358b8d55f8dcd270de539acd66e2d` |
| Lynette | `bcdd8e1b1fc407bfd415814f2791af91f1ac30c2af9ee0085ae97b4fd38deb11` |
