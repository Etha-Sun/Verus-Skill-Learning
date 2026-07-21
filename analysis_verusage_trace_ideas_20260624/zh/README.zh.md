# Verusage Trace Idea Brief 中文版

日期：2026-06-24

这个文件夹是一个独立分析产物。它没有修改原始的 `result-*`、`all_batch_results-*` 或 `claude_sonnet_gpt5/` 数据。

## 输出类型

这是一个偏算法/系统优化的 idea brief，不是论文级 novelty package。当前目标是从本地 agent 轨迹、trace、prompt 和结果 CSV 中提取 Verusage 特有的方向，用来提升 agent 能力或降低 token 消耗，同时保持现有数据集和评测契约不变。

## 主要结论

最强的下一步方向是：

**Verusage trace-distilled proof skeleton cache with a repetition gate。**

核心观察是：很多失败并不只是任务本身难。对同一个 Verusage 文件，一个模型常常能用少得多的 token 验过，而另一个模型会消耗几百万 token 后仍失败。本地日志显示了大量重复 action loop，例如 `postcondition_repair -> assert fail -> uselemma -> 同样的 postcondition/assert fail`，经常持续 20 次尝试。这说明数据集中存在可复用的 proof plan 和负面的 loop signature，但当前 agent 没有足够紧凑地表示和使用它们。

## 关键本地证据

- `all_batch_results-*` 中每个模型有 849 条 20 分钟 breakdown 任务记录。
- `all_batch_results-*` 中有 2,996 个 `verus-repair.log` 文件。
- 工作区中有 65,370 个 `reasoning/*.txt` 文件和 104,759 个 `llm-prompts/*.txt` 文件。
- 在 20 分钟结果中，non-verified 样本的平均 token 明显高于 verified 样本：
  - `claude`：verified 平均 125,725 tokens，non-verified 平均 998,522 tokens。
  - `claude-s4`：verified 平均 125,725，non-verified 平均 998,522。
  - `gpt5`：verified 平均 64,134，non-verified 平均 256,202。
  - `o4mini`：verified 平均 107,696，non-verified 平均 558,247。
- `AC`、`NR`、`OS` 是主要 token sink，成功率也明显低于 `NO`、`MA`、`AL`、`VE`。
- 在所有解析过的日志中，`AssertFail` 是最主要的 target error，其次是 `PostCondFail`。
- 1,010 个日志中，同一个 primary action 至少重复 8 次，这是直接的 token 节省机会。

## 文件

- `objective_contract.zh.md`：目标、约束、false-progress signals。
- `current_board_packet.zh.md`：从本地数据重建出的当前状态。
- `trace_audit.zh.md`：定量和定性的 trace 发现。
- `literature_survey.zh.md`：紧凑的相关工作 grounding。
- `limitations.zh.md`：瓶颈图。
- `candidates.zh.md`：bounded idea slate 和打分。
- `selected_idea.zh.md`：最终选择的 idea handoff。
- `pre_idea_drafts.zh/`：严肃候选的 challenge memo。
- `tables/`：从本地结果文件生成的机器可读 CSV 摘要。

