# SkillOpt S1/S2 跨模型正式评测报告

> 状态：四种 actor 的 blank/S1/S2 正式矩阵与两道 official-Verus 修正实验均已完成；
> 独立完整性审计 PASS。

日期：2026-08-21

## 1. 问题与比较对象

本实验在固定 VeruSAGE test-20 上，对每个 actor 比较三个条件：

- `blank`：不提供 skill 目录；
- `S1`：SkillOpt 第一次通过 selection gate 后接受的 skill；
- `S2`：第二次通过 gate 后接受、也是本轮演化最终保留的 skill。

核心比较是同一个 actor、同一道题、同一个 harness 下的 paired difference。
不同 actor 的绝对分数只能描述模型表现，不能用于估计 skill 的因果效应。

## 2. 冻结实验契约

| 对象 | 冻结值 |
|---|---|
| test split | 20 题；Anvil 7、Action Controller 6、IronKV 7；其中5题为历史 Claude-failed |
| test items SHA-256 | `81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42` |
| blank SHA-256 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| S1 SHA-256 | `fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab` |
| S2 SHA-256 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` |
| Codex CLI | 0.147.0；binary SHA-256 `cb0a1556...b73a40` |
| 主表 Verus | July-2025 binary SHA-256 `27bd3d40...52a3bd` |
| 修正实验 Verus | official VeruSAGE `ddc66116` binary SHA-256 `737048da...66e2d` |
| Lynette | SHA-256 `bcdd8e1b...deb11` |
| actor budget | 每题生成最多600秒；valid timeout 不重跑；final check 单独执行 |
| hard solved | `input.rs` 未改变，且独立 final Verus 与 Lynette 都通过 |
| repetition | 每个 actor×skill×task 仅一次 retained rollout |

blank 与 skill 条件使用同一条 common task contract。唯一必要的 prompt 差异是：
blank 明确说明没有 skill；S1/S2 要求先读取提供的 `SKILL.md`。S1 与 S2 的 task
prompt SHA 相同，仅 skill 文件 SHA 不同。

## 3. Actor 与 transport

| Actor | Codex-facing / upstream | Reasoning | Context | Task worker | 费用口径 |
|---|---|---|---:|---:|---|
| GPT-5.6 Sol | native Responses / native Responses | max | 1,048,576 | 1 | local quota |
| DeepSeek V4 Pro | native Responses / native Responses | high | 1,048,576 | 1 | 完整 bridge ledger；另做统一低峰价归一化 |
| GLM-5.3 | Responses / Chat bridge | max + thinking | 1,048,576 | 1 | 完整 Z.AI bridge ledger |
| Qwen3.8-27B BF16 | Responses / local vLLM Chat bridge | xhigh + preserved thinking | 262,144 | 1/arm | API $0；报告实验占用 GPU-hours |

GLM 的最终 blank/S1/S2 使用同一 bridge SHA-256
`b7f3d067...600c4a`。该实现保留 reasoning/tool history，并且只有上游明确返回
`finish_reason=length` 时才将单次输出上限从8,192扩展到131,072；HTTP 429 或
transport error 不触发扩展。

Qwen 使用共享本地服务：4×L40S、BF16、TP=4、262,144 context、seed 0、
`max-num-seqs=4`、Qwen3 reasoning parser 与 Qwen3-Coder tool parser。实际进程
路径名指向 `vllm-0.19.1-env`，但没有独立捕获 `vllm --version`，因此0.19.1只作为
环境路径证据而非已独立验证的软件身份。服务进程和 `/models` 已存档；由于共享 checkpoint 目录权限不可读，
revision 无法从本账户独立复核，不能写成已验证的 commit identity。正式的
no-skill、S1、S2 三个条件同时运行，但每个条件内仍为一个 task worker；三个条件的调度配置相同，不代表
共享服务上的实际负载相同。

这偏离了预注册 Qwen 计划中的 owned service、三个条件串行不重叠和 revision 可核验
要求。共享服务竞争可能改变600秒内的搜索进度与 timeout score，因此 Qwen 数字是
有效的实际执行结果，但不是原计划或作者 FP8 arm 的严格复现。另有一项历史
metadata 缺陷：240个 main 与24个 official retained `run_manifest.json` 的 `stage`
都沿用了 `auxiliary_dev_fidelity_smoke`，而 arm-level `run_contract.json` 正确写明
held-out purpose。历史 raw manifest 保持不变；生成器已修复为后续正式评测显式写
`formal_held_out_evaluation`。

## 4. July-Verus test-20 主结果

### 4.1 Performance 与 runtime

这里的 runtime 是 retained 顶层 attempt 的 runner wall time，包括该 attempt
timeout 后的 final check，但不包含被归档 attempt 或 provider cooldown。归档
attempt 的已知 usage/cost 仍进入4.2节的完整 ledger 费用。

| Actor | Skill | Solved | 项目分布（AC/AL/IR） | Claude-failed | Mean / median time | Timeouts |
|---|---|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | blank | 18/20 | 6/6, 7/7, 5/7 | 3/5 | 175.22 / 67.52 s | 1 |
| GPT-5.6 Sol | S1 | 17/20 | 5/6, 7/7, 5/7 | 2/5 | 210.85 / 119.27 s | 2 |
| GPT-5.6 Sol | S2 | 17/20 | 5/6, 7/7, 5/7 | 2/5 | 171.58 / 91.30 s | 1 |
| DeepSeek V4 Pro | blank | 14/20 | 2/6, 7/7, 5/7 | 1/5 | 314.58 / 252.29 s | 6 |
| DeepSeek V4 Pro | S1 | 14/20 | 2/6, 7/7, 5/7 | 1/5 | 310.06 / 282.33 s | 6 |
| DeepSeek V4 Pro | S2 | 14/20 | 2/6, 7/7, 5/7 | 1/5 | 282.50 / 201.92 s | 6 |
| GLM-5.3 | blank | 15/20 | 3/6, 7/7, 5/7 | 1/5 | 314.52 / 262.12 s | 6 |
| GLM-5.3 | S1 | 15/20 | 3/6, 7/7, 5/7 | 1/5 | 255.48 / 142.67 s | 4 |
| GLM-5.3 | S2 | 16/20 | 4/6, 7/7, 5/7 | 1/5 | 180.40 / 107.43 s | 2 |
| Qwen3.8-27B BF16 | blank | 3/20 | 2/6, 1/7, 0/7 | 0/5 | 546.60 / 600.59 s | 16 |
| Qwen3.8-27B BF16 | S1 | 5/20 | 2/6, 1/7, 2/7 | 0/5 | 533.45 / 600.58 s | 15 |
| Qwen3.8-27B BF16 | S2 | 6/20 | 2/6, 2/7, 2/7 | 0/5 | 515.48 / 600.61 s | 15 |

GPT、DeepSeek 和 GLM 的差异集中在 AC：这些 actor 的所有条件都解出 AL 7/7，
并在 July binary 下均为 IR 5/7。GLM S2 的净涨点来自一个普通 AC case，不来自
历史 Claude-failed 子集。Qwen 的变化则来自 AL 与 IR；三种条件均未解出5道
历史 Claude-failed case。

### 4.2 Token 与已知计量费用

`已知计量费用` 从完整 bridge ledger 汇总，包含最终 retained attempt 以及因
provider/fidelity 异常被归档并重跑、且 provider 返回了 usage 的 attempt；这些
额外调用不能从实验花费中删除。少数 transport/IncompleteRead/HTTP error 没有
usage，其实际 billing 未知，因此表中美元数是已知费用下界，不是最终账单上界。
GPT 不把 local quota 伪报成零美元。

| Actor | Skill | Requests | Input / prompt tokens | Output tokens | Reasoning tokens | Retained / archived known cost | 已知计量费用 | 已知计量费用/task |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | blank | local | 9,772,943 | 113,077 | 55,369 | local quota | local quota | local quota |
| GPT-5.6 Sol | S1 | local | 10,486,714 | 116,098 | 56,886 | local quota | local quota | local quota |
| GPT-5.6 Sol | S2 | local | 10,169,714 | 115,242 | 55,972 | local quota | local quota | local quota |
| DeepSeek V4 Pro | blank | 801 | 39,311,402 | 398,237 | 282,404 | $3.61431 / $0.62638 | $4.24068 | $0.21203 |
| DeepSeek V4 Pro | S1 | 631 | 31,956,812 | 362,612 | 258,598 | $1.94223 / $0.04930 | $1.99152 | $0.09958 |
| DeepSeek V4 Pro | S2 | 775 | 37,424,907 | 382,596 | 277,601 | $1.63241 / $0.41348 | $2.04589 | $0.10229 |
| GLM-5.3 | blank | 577 | 22,217,736 | 236,552 | 114,362 | $6.13919 / $1.75238 | $7.89157 | $0.39458 |
| GLM-5.3 | S1 | 624 | 25,058,295 | 229,364 | 116,004 | $7.86209 / $0.56251 | $8.42460 | $0.42123 |
| GLM-5.3 | S2 | 418 | 15,594,338 | 163,822 | 79,746 | $5.29431 / $0.14464 | $5.43895 | $0.27195 |
| Qwen3.8-27B BF16 | blank | 272 | 6,376,473 | 304,153 | 未单列 | API $0 | API $0 | API $0 |
| Qwen3.8-27B BF16 | S1 | 315 | 7,670,652 | 276,209 | 未单列 | API $0 | API $0 | API $0 |
| Qwen3.8-27B BF16 | S2 | 251 | 5,352,643 | 274,689 | 未单列 | API $0 | API $0 | API $0 |

DeepSeek blank 全部发生在高峰价，S1 混合了高峰与低峰，直接美元差不能归因于
skill。把 no-skill、S1、S2 三个条件的 token ledger 全部重算为同一低峰价后，分别为
$2.12034、$1.81314、$2.04589。S2 的 clean retained cost 最低，但 fidelity
重试使它的已知计量费用高于 S1。DeepSeek blank 与 S2 各有一次
IncompleteRead partial stream 没有 provider usage；对应 billing 未知且不在美元
合计中。

本报告所含正式 main + official-two 的已计量 API
已知支出下界为 $35.33997：DeepSeek $9.21704、GLM $26.12293。若把 DeepSeek 全部按
统一低峰价重算，则 DeepSeek 为 $6.91832、两家合计为 $33.04124。GPT 使用
local quota，Qwen API 为 $0；二者不能并入美元总和。Qwen 的 no-skill、S1、S2 主实验共同占用的
共享4-GPU TP 服务窗口为10,995.54秒，即12.22 service-window GPU-hours。该值由
run-directory birth time 到最后一个 retained main-result mtime 重建；由于服务
同时承载 official 补跑和其他用户请求，这不是可独占归因的增量 GPU-hours。Qwen
bridge 不单列 reasoning tokens，其 thinking 消耗包含在 completion 语义中。之所以
重建 timing，是因为外层 launcher 在66个 retained 结果和各 arm summary 全部落盘
后，于 timing 收尾阶段报 shell parse error；当前脚本 `bash -n` 通过，actor 结果未
受该 post-result closure failure 影响。

GLM 的 $26.12293 不是单个20题条件的费用，而是 no-skill、S1、S2 三个20题主实验
（合计 $21.75512）与三个条件各自对 official-two 的补跑（合计 $4.36780）之和，
共66次 task rollout，平均已知计量费用约 $0.39580/task。三个主实验共发出1,619次
迭代请求并累计报告62,870,369个输入 token；Codex 每轮工具调用都会重新发送不断
增长的对话前缀，所以这不是6,287万个互不重复的 token。主实验中 provider/fidelity
异常后归档的已计量请求贡献约 $2.45953。GLM 计价档案为 cache-hit input
$0.26/M、cache-miss input $1.40/M、completion $4.40/M；因此即使大部分前缀命中
缓存，大量多轮请求仍会产生明显费用。

### 4.3 共同 solved tasks 的 paired efficiency

| Actor | Comparison | Common solved | Mean time before → after | Mean cost before → after |
|---|---|---:|---:|---:|
| GPT-5.6 Sol | blank → S1 | 17 | 112.68 → 151.63 s | local quota |
| GPT-5.6 Sol | S1 → S2 | 16 | 141.65 → 127.23 s | local quota |
| GPT-5.6 Sol | blank → S2 | 17 | 125.52 → 148.50 s | local quota |
| DeepSeek V4 Pro | blank → S1 | 14 | 191.25 → 180.89 s | $0.05205 → $0.04554（统一低峰价） |
| DeepSeek V4 Pro | S1 → S2 | 14 | 180.89 → 143.15 s | $0.04554 → $0.03841（统一低峰价） |
| DeepSeek V4 Pro | blank → S2 | 14 | 191.25 → 143.15 s | $0.05205 → $0.03841（统一低峰价） |
| GLM-5.3 | blank → S1 | 14 | 212.49 → 135.67 s | $0.15724 → $0.19731 |
| GLM-5.3 | S1 → S2 | 15 | 163.86 → 118.03 s | $0.25960 → $0.16649 |
| GLM-5.3 | blank → S2 | 15 | 217.50 → 104.61 s | $0.17440 → $0.13116 |
| Qwen3.8-27B BF16 | blank → S1 | 2 | 433.43 → 406.22 s | API $0 |
| Qwen3.8-27B BF16 | S1 → S2 | 3 | 309.45 → 255.65 s | API $0 |
| Qwen3.8-27B BF16 | blank → S2 | 3 | 368.38 → 270.58 s | API $0 |

共同成功子集只回答“两个条件都成功的题上，搜索是否更快/更省”。它不能抵消
score regression，也不能替代全部20题的 operational result。这里的 mean cost
来自 retained 顶层 per-task usage，只比较共同成功题，不含 archived retries；
因此它与4.2节完整 ledger 的已知计量费用不是同一口径。

## 5. Outcome transitions

| Actor | blank → S1 | S1 → S2 | blank → S2 |
|---|---|---|---|
| GPT-5.6 Sol | `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` regression，净 -1 | `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` gain + `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` regression，净 0 | `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` regression，净 -1 |
| DeepSeek V4 Pro | 无变化 | 无变化 | 无变化 |
| GLM-5.3 | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` gain + `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` regression，净 0 | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` gain，净 +1 | `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` gain，净 +1 |
| Qwen3.8-27B BF16 | `AL__push_to_set_seq_to_set_insert`、`IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive`、`IR__host_impl_v__make_send_only_event_results` gain + `AL__always_to_current` regression，净 +2 | `AL__leads_to_by_borrowing_inv`、`AL__always_to_current`、`IR__delegation_map_v__impl3__values_agree` gain + `AL__push_to_set_seq_to_set_insert`、`IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive` regression，净 +1 | `AL__leads_to_by_borrowing_inv`、`IR__host_impl_v__make_send_only_event_results`、`IR__delegation_map_v__impl3__values_agree` gain，净 +3 |

## 6. Official-Verus 两题修正

`IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` 与 `IR__single_delivery_model_v__impl2__send_single_cmessage` 在 July binary 下存在 fixture/version 兼容问题。主表仍保留
冻结的 `/20` denominator；另外在 official VeruSAGE Verus 上对这两题做 fresh
actor rerun。`Targeted hybrid` 是18题 July outcome 加两题 official fresh
outcome，不是完整 official-Verus test-20 rerun。

| Actor | Skill | July raw | Official two | Targeted hybrid |
|---|---|---:|---:|---:|
| GPT-5.6 Sol | blank / S1 / S2 | 18 / 17 / 17 | 2/2 / 2/2 / 2/2 | 20 / 19 / 19 |
| DeepSeek V4 Pro | blank / S1 / S2 | 14 / 14 / 14 | 1/2 / 0/2 / 1/2 | 15 / 14 / 15 |
| GLM-5.3 | blank / S1 / S2 | 15 / 15 / 16 | 1/2 / 1/2 / 0/2 | 16 / 16 / 16 |
| Qwen3.8-27B BF16 | blank / S1 / S2 | 3 / 5 / 6 | 0/2 / 0/2 / 0/2 | 3 / 5 / 6 |

GLM 的 July S2 涨点在 hybrid 中被 official `IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` 回退抵消，因此 no-skill、S1、S2 都为
16/20。这也说明版本修正不能只对 no-skill 做：skill 会改变同一道修正题的搜索
路线。

### 6.1 与作者侧 baseline grid 的差异

作者侧 July-Verus no-skill 分数为 DeepSeek 13/20、Qwen FP8 5/20、GPT
18/20、GLM 16/20；其第二条件是完整 `native official baseline` skill tree，
分数为15/20、4/20、17/20、16/20。我们的 reference-aligned no-skill 当前为
DeepSeek 14/20、Qwen BF16 3/20、GPT 18/20、GLM 15/20。因此 GPT 完全相同，
DeepSeek 高1题、GLM低1题、Qwen低2题；这些差异不能仅凭 single rollout 归因，
尤其 Qwen 的 BF16/FP8、共享 checkpoint identity 和服务栈并不相同。

作者第二列不能与我们的 S1/S2 直接比较：treatment 不是同一 skill；作者 Qwen
为 FP8 而本实验为 BF16；两边 July Verus 的版本字符串相近但 binary SHA 不同；
作者在外层隔离 namespace 中使用 Codex `danger-full-access`，本实验由 Codex
直接使用 `workspace-write`；绝对 verifier 路径也使 prompt bytes 不同。GLM 的
model alias、无显式 decoding seed 和一次 rollout 还保留随机性。这里已对齐的
部分包括 test manifest、Codex 0.147 binary、600秒、worker=1、reasoning/context、
Chat history/tool ID 语义和 normal/length-retry 输出预算。

## 7. Trajectory 原因分析

以下只引用候选 diff、工具动作、verifier diagnostic、usage 和最终状态；不引用
或推断模型私有 chain-of-thought。由于每题每条件只有一次 rollout，这些是机制
证据，不是稳定因果估计。

### 7.1 GPT-5.6 Sol

`AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` 在 blank 中用90行 proof 建立实际 state requirements、pointwise
message predicate、已有 equivalence lemma 和 `invariant_n!`，519.19秒通过。
S1 改走141行手工 `Step` case split，在600秒预算结束时 preservation obligation
仍未关闭，最终 Verus fail；这是 blank→S1 的唯一 regression。

S2 在同题使用 exact `implies` 和较小的 named `partial_spec` bridge，488.79秒
恢复成功；该 rollout 的路线与 S2 新增规则一致。但 `AC__vreplicaset_controller__proof__liveness__resource_match__lemma_from_after_receive_ok_resp_to_send_create_pod_req` 中，
blank/S1 都调用现有 domain lemma 处理两个困难 step；S2 却扩展所有 `Step`
variant，并把最难的 APIServer/Controller 分支留成裸 assertion，最终超时失败。
因此 S1→S2 的总分打平来自一涨一跌，不是稳定无影响。

### 7.2 DeepSeek V4 Pro

no-skill、S1、S2 成功解出的题目集合完全相同，skill 没有扩大 retained capability。效率变化仍有明确
异质性：

- `IR__delegation_map_v__impl3__values_agree` 在 no-skill、S1、S2 中都使用同一类 loop invariant。blank 用517.37秒、56 requests；
  S1 用137.43秒、17 requests；S2 用307.54秒。该 S1 rollout 的搜索更短，但
  没有产生能力涨点。
- `AL__leads_to_by_borrowing_inv` blank 直接实例化两个已有 entailment lemma，177.36秒完成；S1
  展开更多 execution/index quantifier，364.34秒才关闭同一目标。规则更多并不
  保证路线更短。
- `AC__vreplicaset_controller__proof__helper_invariants__proof__lemma_eventually_always_no_other_pending_request_interferes_with_vrs_reconcile` 在 no-skill、S1、S2 中均失败；S2 写出更大的 temporal skeleton，仍缺 domain-specific
  temporal implication。exact-shape 指导不能替代缺失的领域 bridge。
- `AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` 的 S2 首次 attempt 留下 Verus+Lynette 均通过的候选，但 Responses
  流以 `IncompleteRead` 结束、无 clean terminal event，因此按预注册 fidelity
  规则归档为 `V0_INVALID`。clean retry 未解出。这说明 S2 路线可能有效但方差
  很大；不能把 invalid success 算进 performance，也不能删除其 $0.21019 花费。

### 7.3 GLM-5.3

`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_list_pods_request_returns_ok_list_resp_containing_matching_pods` 是 blank→S1 的 gain：blank 在602.49秒留下153行仍不完整的 uniqueness/
cardinality proof；S1 用 ObjectRef key injectivity 和 no-duplicates bridge 在
558.54秒通过。S2 保留该涨点，并把时间降到502.87秒。它与 S1 的 contract-first
和 extensional-bridge 规则一致，但仍是接近 timeout 的昂贵成功。

`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` 展示了“有规则但执行不稳定”。blank 用两个 resource-map branch 和
双向 membership witness 在287.73秒解出；S1 只写一个没有 witnesses 的 set
equality assertion，215.98秒失败。S2 则用133行明确处理 delete/update 两个
branch、两个 membership 方向和 finite-cardinality bridge，在301.53秒恢复。
因此 S1→S2 的 +1 是对同一个 extensional strategy 的更完整执行，而不是添加
task-specific lemma。

在 score 不变的题上也有明显效率作用：`AL__leads_to_shortcut_temp` blank 用37行手工 temporal
semantics 并在600.63秒才通过；S1 只调用三个现有 lemma，229.78秒完成。
`IR__delegation_map_v__impl3__values_agree` 的 S1 虽然最终 proof 与 blank 类似，却产生约10倍费用；S2 又用同一
小 invariant 在92.48秒完成。这些反向例子说明单次 runtime/cost 具有明显搜索
方差，不能仅凭逻辑 patch 大小推断费用。

在 official `IR__marshal_ironsht_specific_v__impl2__lemma_serialize_injective` 上，blank/S1 都调用现有 sibling serialization lemma 并
通过；S2 改走更底层的 vector injectivity，只证明了 `to_vec().view_equal`，没有
bridge 回目标 `self.view_equal`，因此失败。这个被审阅 rollout 选择了底层
exact/extensional 路线而没有执行更靠前的 contract-first 原则；单次结果不能证明
S2 文本稳定地造成这种偏置。

### 7.4 Qwen3.8-27B BF16

`AL__leads_to_by_borrowing_inv` 中 blank/S1 均失败、S2 成功，三个条件都达到600秒
截止。blank/S1 只实例化两个 premise，却没有把局部 `p` 与推导出的 `inv`
显式合成 `p.and(inv)`，最终 Verus fail。S2 命名 `p_and_inv`；虽然外层仍写
`==>`，但在 proof body 中显式分支检查 antecedent，并在每个 suffix 下依次建立
`inv`、`p_and_inv` 和 eventuality，留下同时通过 Verus/Lynette 的 checkpoint。
这与 S2 新增的 named predicate 以及“显式建立或分支处理 antecedent”指导一致。

第4题 `AL__push_to_set_seq_to_set_insert` 则是 blank/S2 失败、S1 成功。S1 只调用一行现有
`lemma_push_to_set_commute`，clean V2 retry 在207.08秒通过；S2 写六行 pointwise
set extensional proof，却卡在 `push` membership assertion，没有回退到已有 contract。
因此它是 contract-first 的正例；该 S2 rollout 则选择 extensional 路线而未执行
S1 原则，不能据一次 rollout 断言是 S2 文本稳定压制了该原则。S1 的首次同解
attempt 因原始 trace 缺一个 tool-completion event
被严格归档，clean retry 独立复现后才计入 score。

`IR__verus_extra__lemma_seq_fold_left_sum_len_int_positive` 中 S1 新增一个按序列长度递归的局部 helper，利用
`lemma_fold_left_split` 关闭非负性，520.05秒通过；blank 和 S2 都没有留下有效
编辑并超时。因此这是结构归纳策略的成功实例，但不是 S2 新增规则的受控反例：
S2 比 S1 多出的文字并未否定归纳，single rollout 的搜索方差仍是合理解释。

`IR__host_impl_v__make_send_only_event_results` 中 blank 把 `ghost(...)` 当成字段表达式，212.56秒以 type error 结束；
S1/S2 都直接构造 `EventResults { recvs, clocks, sends, ios }`，分别115.92秒和
166.53秒通过。这里的有效模式是先读返回值 postcondition，再构造字段逐一匹配的
ghost value，属于通用的 contract-first 策略。

`AL__always_to_current` 是 S1 的唯一 blank→S1 regression。blank 先得到 suffix-0 上的 `p`，
再调用已有 `execution_equality` bridge，238.28秒通过；S1 直接断言
`ex.suffix(0) == ex`，600秒后仍失败。S2 恢复调用该 bridge，211.32秒通过。
这个恢复符合“语义等价先找小 bridge”的共同规则，但 blank 也能找到同一路线，
所以不能把它专属于 S2 新增文本。

`IR__delegation_map_v__impl3__values_agree` 中 blank 把 `int` cast 写入 executable loop 的 decreases，S1 又遗漏
invariant/decreases 子句所需标点；两者最终都停在 parser/type error。S2 写出合法
的 quantified invariant 和 `decreases hi + 1 - i`，317.12秒通过。由于 loop
invariant 指导在 S1 已存在，这更像规则执行质量和搜索方差，而不是 S2 delta 的
直接因果证据。

两个在 no-skill、S1、S2 中共同成功的 AC stable-tie case 也呈现异质性：`AC__vreplicaset_controller__proof__liveness__spec__invariant_since_phase_iv_is_stable` 的
blank/S1/S2 为583.24/445.66/430.32秒，`AC__vreplicaset_controller__proof__liveness__spec__invariant_is_stable` 为283.62/366.78/170.10秒。
S2 在两题都更快，但 S1 一快一慢；这与共同成功子集的均值方向一致，同时再次
说明一次 rollout 的 runtime 不能逐题稳定归因。两道 official-Verus IR 修正题在
三种条件下均为0/2，未给 Qwen 主表增加分数。

## 8. 当前结论与边界

1. S1/S2 不是模型无关的单调增益。GPT 的 blank→S2 为 -1；DeepSeek 为0；GLM
   为 +1；Qwen BF16 为 +3。GLM S2 同时改善 score、runtime 和已知计量 API cost；
   Qwen S2 同时提高 score、降低 mean runtime、requests 和 prompt tokens，但其
   费用是共享本地 GPU 服务窗口，不能与 API 美元成本直接比较。
2. DeepSeek 的 score tie 隐藏了效率变化；GLM S1 和 GPT S1→S2 的 tie 都隐藏了
   一涨一跌；Qwen S1→S2 的净 +1 隐藏了三涨两跌。因此只报 aggregate score 会
   遗漏机制。
3. 被审阅的成功案例与 contract-first、双向 membership witness、匹配真实定义的
   recursion/quantifier shape 和保留已验证 checkpoint 等模式一致；被审阅的失败
   案例常伴随未执行这些规则、过度展开 step arms、或忽略已有 domain lemma。
   这是 post-hoc case evidence，不是这些规则的独立 ablation。
4. test-20 只含一次 rollout，无法估计方差。`AC__vreplicaset_controller__proof__liveness__api_actions__lemma_get_then_delete_matching_pod_request_deletes_matching_pod_and_returns_ok` 的多次 diagnostic/fidelity
   retry 已直接显示同一模型、skill、题目可以在 solved 与 unsolved 间变化；Qwen
   多个无法由 S1→S2 文本差直接解释的转移也应按探索方差谨慎解读。
5. author 侧 `with-native-official-baseline` 使用完整官方 skill tree，不是本实验的
   S1/S2；其 Qwen 为 FP8，而本实验为 BF16。两组结果不能把第二条件直接等同。

## 9. 可复核产物

- 机器可读汇总：`$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/aggregate-live/matrix.json`
- July 主表状态变化：`$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/aggregate-live/transitions.csv`
- July 主表每题结果：`$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/aggregate-live/per_task.csv`
- 详细轨迹证据：`$VERUS_SKILL_RUN_ROOT/skillopt-verusage/report-s1-s2-20260821/trajectory_analysis_notes_zh.md`
- 冻结预注册计划（B3 实际偏离已在文件末尾对账）：
  `skillopt-verusage/refine-logs/EXPERIMENT_PLAN_20260821_002906.md`
- 实际执行与进度：`skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`

## 10. 独立完整性审计

二轮只读 reviewer 最终 verdict 为 **PASS**，没有剩余实质性 must-fix。审计独立
确认24个正式 arm 和264条 retained 结果完整（240 main + 24 official）；198条
bridge-backed 结果均显式 `provider_valid=true`；164个 SOLVED 全部同时通过
Verus 与 Lynette；97条 V1、167条 V2；source manifest 均匹配冻结输入。

reviewer 还复算了 matrix、240条 July `per_task.csv`、20条 transition、official-two
与 targeted hybrid，并验证 fail-closed fault injection 会拒绝不完整状态、重复或
错误 ID、缺失 provider validity、V0 fidelity、输入变化和缺失双 verifier。独立
回归测试为 Codex harness 46/46、SkillOpt/bridge 80/80。

PASS 只适用于本文明确披露的证据范围：single rollout、Qwen shared-service/B3
偏离、未知 billing 下界、targeted hybrid 非完整 official test-20，以及历史 stage
metadata 缺陷仍然是结论边界。
