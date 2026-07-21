# 本地离线实验报告

脚本：`scripts/local_experiments.py`

输出：`outputs/`

## 1. 数据口径

只使用主批次：

```text
all_batch_results-cyy-*/results-batch_*/
```

不混入 `batch-results-benchmarks_verusys-sampled-unverified-*`，避免 sampled-unverified 额外批次污染主数据口径。

匹配结果：

- `results.csv` rows：2,996
- matched `verus-repair.log`：2,996
- verified：1,691
- non-verified：1,305
- effective total tokens：1,524,386,760

token 口径：`max(results.csv total_tokens, log parsed LLM tokens)`。原因是一些 TIMEOUT 的 `results.csv` token 为 0，但日志里实际存在大量 LLM 调用。

## 2. 实验 A：重复错误-动作 gate

方法：对每条 trace 按 attempt 解析：

- `Target error: VerusErrorType.X`
- `primary_action`
- attempt 内 input/output tokens
- final status

模拟 gate：当同一个 `(target_error, primary_action)` 在同一 trace 中第 `k` 次出现时停止。这个实验不是最终策略，只是估计 “重复循环是否有降耗信号”。

主要结果：

| threshold | nonverified gated | nonverified token saved | saved rate | verified false-stop |
|---:|---:|---:|---:|---:|
| 2 | 1305 / 1305 | 1,212,510,484 | 90.63% | 761 / 1691 |
| 3 | 1299 / 1305 | 1,076,004,993 | 80.43% | 424 / 1691 |
| 4 | 1286 / 1305 | 923,447,476 | 69.02% | 267 / 1691 |
| 5 | 1252 / 1305 | 776,366,321 | 58.03% | 178 / 1691 |
| 6 | 1198 / 1305 | 647,707,759 | 48.41% | 119 / 1691 |
| 8 | 969 / 1305 | 424,591,160 | 31.74% | 51 / 1691 |

解释：

- 阈值 2-4 太激进，虽然节省 token 很多，但会误杀大量最终 verified trace。
- 阈值 8 是更合理的第一版 gate：仍覆盖 74.25% non-verified trace，节省 31.74% non-verified effective tokens，verified false-stop 约 3.02%。
- 真实系统不应该直接 stop；更合理是 reroute：触发 skeleton retrieval、换 action family、降温、缩上下文、或交给 specialized repairer。

最高 token sink 例子集中在 OS/gpt5 的 TIMEOUT：

- `OS__process_manager__impl_new_container__impl0__new_container_with_endpoint.rs`：threshold=2 时估计可省 1,544,594 tokens。
- `OS__process_manager__impl_base__impl0__block_running_thread_and_change_queue_state.rs`：可省 1,526,129 tokens。
- `OS__pagetable__pagetable_impl_base__impl0__map_4k_page.rs`：可省 1,521,853 tokens。

这些例子说明 OS project 的大函数/复杂 proof 里，agent 会长时间重复 postcondition/assert/forall 类动作。

## 3. 实验 B：跨模型成功 skeleton 覆盖上界

方法：对每个失败 trace，检查同一个 `(project, file)` 是否被其他模型 verified。若存在，认为 exact-task skeleton cache 有一个可用上界。

结果：

- covered failed traces：517
- covered failed effective tokens：377,656,792
- total failed effective tokens：1,337,870,858
- 覆盖失败 token 约 28.23%

这个数字不是最终可实现收益，因为 exact-task cache 在严格 eval 中可能有数据泄露风险；它的意义是说明：同一个 Verusage task 的成功轨迹包含大量可迁移 skeleton 信息，而失败模型没有利用它。

更重要的是 non-exact retrieval sanity check：

- eval queries：517
- hit@1：0.9865
- hit@3：0.9923
- hit@5：0.9923

这里的 hit 定义很弱：用文件名 token + lemma token 检索其他成功 trace，检查检索到的 action sequence 是否和同 task 的成功 action set 有交集。它不能证明 retrieval 会修好 proof，但说明 action-level skeleton 检索信号非常强。

## 4. 实验 C：prompt/context cost audit

解析 `llm-prompts/*-input.txt`，共匹配：

- prompt groups：92
- prompt files：46,684

按 `over_100k` prompt 数排序，最重的组：

| model | project | status | prompt_count | mean bytes | over_100k |
|---|---|---|---:|---:|---:|
| o4mini | AC | TIMEOUT | 1245 | 167,379 | 1110 |
| claude-s4 | AC | FAILED | 1019 | 172,380 | 914 |
| gpt5 | AC | TIMEOUT | 891 | 188,380 | 865 |
| claude | AC | FAILED | 802 | 180,826 | 754 |
| claude-s4 | NR | FAILED | 1944 | 76,217 | 729 |
| gpt5 | NR | TIMEOUT | 1465 | 83,506 | 633 |
| o4mini | NR | TIMEOUT | 1897 | 75,737 | 622 |
| claude | NR | FAILED | 1418 | 79,186 | 530 |

结论：

- AC 是最明显的 prompt bloat project：失败/timeout prompt 大量超过 100k bytes。
- NR/OS 是第二梯队 token sink。
- prompt compaction 不应该全局平均做，而应该 project-aware：AC/NR/OS 先做，AL/MA 这种短 prompt 项目不是第一优先级。

## 5. 实验结论

本地实验支持三个可执行 claim：

1. **Repetition gate 有明确降耗空间**：阈值 8 是较稳的初始配置；更好的策略是 reroute 而不是 stop。
2. **Trace skeleton cache 有明确上界**：517 个失败 trace 有其他模型的 exact success，对应约 3.78 亿 failed effective tokens。
3. **Context compaction 应该按项目族做**：AC/NR/OS 是主要成本来源，尤其 AC 的 prompt bloat 非常稳定。

这些都满足 meeting 要求：grounded in Verusage，能出表，不依赖昂贵 API。

## 6. 补充实验：skeleton cache 与 reroute prior

我进一步导出了两个可直接接下一轮实验的产物：

- `skeleton_cache.jsonl`：1,691 条 verified trace，每条包含 project、file、lemma list、action sequence、error-action sequence、tokens 和 log path。
- `reroute_prior_threshold8.csv`：当失败 trace 在 threshold=8 触发重复循环时，查找同一 task 的其他模型成功轨迹，并取成功轨迹同位置动作作为 reroute prior；如果成功轨迹较短，则取其最后一个动作。

结果：

- reroute candidates：372
- top peer action 不同于当前重复 action：274
- different action rate：73.66%

解释：这进一步支持 “threshold=8 后不要继续原动作” 的策略。很多 AC/NR/OS 失败 trace 在 postcondition/assert/case-analysis/uselemma 中循环，而其他模型成功轨迹显示此时应该切到 `INSTANTIATE_EXISTS`、`USELEMMA`、`CASE_ANALYSIS` 等不同 action。

这不是最终 repair 策略，但它给出了一个可实现的 harness 改动：

1. 线上运行时检测 threshold=8。
2. 用 `(project, file tokens, lemma tokens, error prefix)` 检索 skeleton cache。
3. 如果 top skeleton 的同位置动作和当前重复动作不同，则 reroute 到该 action family。
4. 如果相同，则执行 context compaction 或 stop，避免继续烧 token。
