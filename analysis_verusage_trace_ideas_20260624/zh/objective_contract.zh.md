# 目标契约

## 真实目标

在现有 Verusage 数据集和 verifier 契约下提升 agent 表现：

- 提高端到端 `VERIFIED` 率。
- 降低总 `input_tokens + output_tokens`。
- 在同一 repair budget 下减少 wall-clock time。
- 不引入新数据集，不使用人工标签，不削弱 Verus 检查，不用 `assume` 或 cheat 方式获得成功。

## 可信代理指标

- `all_batch_results-*/all_results_with_breakdown_20min.csv`：每个模型的 status、time、tokens、project。
- `*_analysis_results.csv`：任务级 verified flag、steps、action traces、added lines、versions。
- `*_action_counts.csv`：action 使用情况，以及部分文件中的 success counts。
- `verus-repair.log`：attempt 级 error、选择的 agent/action、候选接受/拒绝、LLM token calls。
- `llm-prompts/*.txt` 和 `reasoning/*.txt`：prompt 大小、previous-attempt 内容、reasoning plans。

## False Progress Signals

- 局部 action success 但最终没有 `VERIFIED`。日志显示 `fix-v*-success-*` 可能和最终 failed batch status 同时存在。
- 只降低 output tokens，但 full code 和 previous attempts 的 input-token replay 仍然巨大。
- 更多 attempts 或更多 candidates，但 repeated error signatures 没有减少。
- 某个 action 的 action-level success count 变好，但它只是把失败从 `PostCondFail` 移到重复 `AssertFail`。
- 把 exact-task memorization 当成模型能力。精确检索对工程有用，但模型训练/泛化 claim 需要 heldout task 或 family split。

## 硬约束

- 保持 Verusage tasks 和 verifier 不变。
- 如果评估泛化，不得在 heldout target patch 上训练。
- 不要把 final patch text 这类 leakage-prone labels 放进 heldout prompt。
- 优先选择可以先从现有 traces 离线验证、再做昂贵新 batch 的机制。

## 贡献类型

预期贡献类型：**Capability + Efficiency**。

问题重要性：Verusage 包含 repository-scale formal verification tasks，失败 agent 可能在重复 repair loop 上消耗几百万 tokens。

主要瓶颈：agent 没有紧凑复用自己 traces 中的成功 proof structure，也没有充分利用负面的 loop evidence。

目标增量：通过路由到 trace-derived proof skeleton，减少高成本失败循环，并提升 `AC/NR/OS` 类任务成功率。

