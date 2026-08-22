# SkillOpt S1/S2 补充实验 Tracker

更新时间：2026-08-21 13:18 CDT

| Run ID | Milestone | Purpose | System / Variant | Split | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| R201 | M0 | GLM reference parity check | GLM bridge + Codex 0.147 | one training smoke | MUST | COMPLETE | `IR__verus_extra__set_map_union` solved；155.13 s；Verus+Lynette PASS；24/24 calls；$0.223253 |
| R202 | M0 | Qwen environment parity check | Qwen3.8-27B BF16 | one training smoke | MUST | COMPLETE | 真实 Codex→bridge→Qwen→Verus/Lynette smoke：28/28 provider calls clean、input unchanged、两项 final check 均执行；blank 在600s未解出（Verus fail、Lynette pass），因此仅通过 operational gate，不把能力失败误判为 harness 失败；共享 checkpoint revision 因权限不可独立读取 |
| R203 | M1 | legacy diagnostic S1 | GPT-5.6 Sol + S1 | test-20 | MUST | COMPLETE | project profile 18/20；内部 blank/S1/S2 prompt byte-identical，但不与 reference GLM/Qwen 混表 |
| R204 | M1 | legacy diagnostic S1 | DeepSeek V4 Pro + S1 | test-20 | MUST | COMPLETE | project profile 11/20；$1.395085；provider errors 0；不与 reference 主表混表 |
| R203R | M1 | reference-aligned matrix | GPT-5.6 Sol × blank/S1/S2 | test-20 + official two | MUST | COMPLETE | July blank/S1/S2 = 18/17/17；S1→S2 为 `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` gain + `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` regression；official two 在 no-skill、S1、S2 中均为 2/2；local quota |
| R204R | M1 | reference-aligned matrix | DeepSeek V4 Pro × blank/S1/S2 | test-20 + official two | MUST | COMPLETE | July blank/S1/S2 = 14/14/14，三个条件成功解出的题目集合完全相同；S2 $2.045890（retained $1.632406、archived $0.413484），mean/median 282.50/201.92s；official two 为 1/2、0/2、1/2 |
| R205 | M2 | diagnostic S1 test | GLM-5.3 + S1 | test-20 | MUST | COMPLETE | 15/20；$4.999686；20/20 provider-valid；bridge SHA 与最终矩阵不同，不用于严格 skill-only delta |
| R206 | M2 | diagnostic S2 test | GLM-5.3 + S2 | test-20 | MUST | COMPLETE | 14/20；Claude-failed 1/5；375 requests；$4.301793（retained $4.218167，archived $0.083626）；零 provider error；旧 bridge，仅用于诊断 |
| R206B | M2 | aligned no-skill test | GLM-5.3 + blank | test-20 | MUST | COMPLETE | 15/20（Claude-failed 1/5），6 timeout；577 ledger requests（549 metered、28 HTTP 429 无 usage）；known cost $7.891566（retained $6.139188、archived $1.752379）；最后一题在两次 provider-invalid attempt 后冷却并以 clean a03 retained |
| R205R | M2 | final aligned S1 rerun | GLM-5.3 + S1 | test-20 | MUST | COMPLETE | 15/20，与 blank 持平；`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` gain 与 `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` regression；mean/median 255.48/142.67s；$8.424601（retained $7.862093、archived $0.562509） |
| R206R | M2 | final aligned S2 rerun | GLM-5.3 + S2 | test-20 | MUST | COMPLETE | 16/20，S1→S2 仅 `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` gain、无 regression；mean/median 180.40/107.43s；$5.438955（retained $5.294313、archived $0.144641）；相对 blank 净 +1 且更快、更便宜 |
| R207 | M3 | formal no-skill | Qwen3.8-27B BF16 + blank | test-20 | MUST | COMPLETE | 3/20；AC/AL/IR=2/1/0；mean/median 546.60/600.59s；272 requests；API $0 |
| R208 | M3 | formal S1 | Qwen3.8-27B BF16 + S1 | test-20 | MUST | COMPLETE | 5/20；AC/AL/IR=2/1/2；mean/median 533.45/600.58s；315 requests；API $0 |
| R209 | M3 | formal S2 | Qwen3.8-27B BF16 + S2 | test-20 | MUST | COMPLETE | 6/20；AC/AL/IR=2/2/2；mean/median 515.48/600.61s；251 requests；API $0；blank→S2 净+3 |
| R210 | M4 | verifier-version correction | all models × blank/S1/S2 | two IR items | MUST | COMPLETE | official `ddc66116`，与 July 主表分开；GPT=2/2、2/2、2/2；DeepSeek=1/2、0/2、1/2；GLM=1/2、1/2、0/2；Qwen=0/2、0/2、0/2 |
| R211 | M5 | result analysis | blank/S1/S2 paired | test-20 | MUST | COMPLETE | 四模型 performance/runtime/cost、全部 outcome transitions 与机制证据已写入最终中文报告 |
| R212 | M5 | integrity audit | independent reviewer | all artifacts | MUST | COMPLETE | 二轮只读审计 PASS；24 arms / 264 retained；164 solved 均双验证；46/46 + 80/80 tests |

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

- 旧 GPT/DeepSeek 的 no-skill、S1、S2 三个条件使用的 TASK/user prompt 均为 SHA `13a4598...`，所以
  各 actor 内的 legacy paired comparison 有效；但 blank workspace 含1-byte
  `SKILL.md`，profile 也不是 reference cross-provider contract。
- 新主表改用与 GLM/Qwen 相同的 reference contract：prompt SHA
  `d0b663...`、blank skill absent、worker=1、1M context（Qwen 仍按其
  reference 使用262K）、600s。GPT/DeepSeek 三个条件与 official two 校正已启动。
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

## GLM retry cooldown intervention 2026-08-21 05:18 CDT

GLM blank 第20题的 attempt-01 出现2个 HTTP 429，attempt-02 开头又出现9个
HTTP 429；两次均因此不具备进入 performance 的 provider-validity。evaluator 没有
安全的 live ledger-error cancellation 接口。为避免 attempt-02 结束后立刻启动并
污染最后一次 clean retry，暂停 evaluator 父进程 PID 2701328；无效子进程自行
收尾后冷却120秒，再由 `skillopt_glm_retry_cooldown` 自动恢复父进程。归档尝试的
已知和 unknown cost 全部保留；retained performance 只取最终 provider-valid
attempt。未修改 timeout、actor prompt、skill、model 或 verifier。

## GLM S1 retry cooldown intervention 2026-08-21 07:11 CDT

Final-bridge S1 第12题 `AL__always_implies_to_leads_to` 的 attempt-01 出现7个 HTTP
429。该 attempt 在246.11秒内留下双验证通过的 candidate，但因 provider ledger
不干净被正确标为 `V0_INVALID`；$0.278074 已知费用保留在归档账本中。为避免
evaluator 立即启动同样受限流污染的 retry，暂停父进程，仅让当前子任务收尾，
随后冷却120秒并恢复。attempt-02 启动后的前3个请求均为 clean metered calls。
未修改 prompt、skill、model、600秒预算、reasoning、worker 或 verifier。

## DeepSeek S2 trace-fidelity retry 2026-08-21 07:41 CDT

S2 的 `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` attempt-01 在600秒截止时留下 Verus 与
Lynette 均通过的 candidate，但最后一个 native Responses 流发生
`IncompleteRead(177698 bytes read)`，导致该 attempt 有1个 provider error、无
Codex terminal event，按冻结契约标为 `V0_INVALID`。其65个已计量请求和
$0.210185 已归档；evaluator 自动启动 clean attempt-02。没有修改 task、skill、
prompt、模型、timeout 或 verifier；最终 performance 只取 provider-valid
retained attempt。已知计量 cost 保留两次有 usage 的调用，但 partial stream 的
provider billing 未知，因此不是账单上界。

## Qwen post-result launcher closure 2026-08-21 12:56 CDT

Qwen 的 no-skill、S1、S2 三个 main 条件已各写入20个 retained 顶层结果和 `summary.json`，official
补跑也已在三个条件中各写入2个结果与 summary；随后外层 tmux launcher 在 timing 收尾处以
shell parse error 退出。launcher 文件在09:32启动后于09:45发生过 mtime 变化，
当前版本 `bash -n` 通过，因此最可能是运行中脚本文本变化影响了 shell 后续读取；
该解释是 provenance inference，不作为 actor 结果事实。所有66个 retained 结果
已独立复核：provider-valid、input unchanged，所有 SOLVED 同时通过 Verus 和
Lynette。缺失 timing 由 run-directory birth time 到最后一个 main result mtime
重建为10,995.54秒，对应12.22个共享 service-window GPU-hours，并明确不把它写成
exclusive/incremental GPU usage。

Qwen 实际执行偏离预注册 B3：使用其他用户拥有的 shared service、revision 无法
读取，三个 main arm 并发而非串行不重叠。共享竞争可能影响600秒内的搜索进度与
timeout score；实际结果保留，但不称作 B3 原计划或作者 FP8 arm 的严格复现。
所有264个 selected formal `run_manifest.json` 还继承了错误 stage
`auxiliary_dev_fidelity_smoke`；arm-level contract 的 held-out purpose 正确，历史
raw manifest 不回写。生成器现已支持显式 stage：formal test 写
`formal_held_out_evaluation`，training 写 `skillopt_training_rollout`；相关26个
targeted unittest 与编译检查通过。

最终回归为 SkillOpt/bridge 80/80、Codex harness 46/46。fail-closed 聚合器已在
真实12个 main arm 和12个 official arm 上通过，并用删除一个 retained ID 的临时
副本完成 negative test；该副本未触碰真实 run artifact。Qwen launcher 当前
`bash -n` 通过。

## Final independent audit 2026-08-21 13:18 CDT

二轮 reviewer verdict 为 PASS，无剩余实质性 must-fix。独立复核24个正式 arm、
264条 retained、198条 bridge provider-valid、164个 Verus+Lynette 双通过 solve、
97条 V1 与167条 V2；matrix、July CSV、official-two/hybrid 和全部费用口径一致。
single-rollout、Qwen shared-service/B3 偏离、unknown billing、非完整 official hybrid
和历史 stage metadata 均作为非阻塞 caveat 保留。

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
