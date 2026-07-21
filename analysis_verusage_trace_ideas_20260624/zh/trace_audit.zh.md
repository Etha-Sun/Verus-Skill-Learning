# Trace 审计

## 检查的数据面

通过脚本和抽样检查了以下本地文件：

- 30 个顶层 `*_analysis_results.csv`。
- 23 个顶层 `*_action_counts.csv`。
- 4 个 `all_batch_results-*` 模型 batch 文件夹。
- 2,996 个 `verus-repair.log` 文件。
- 代表性的 `llm-prompts/*.txt`、`reasoning/*.txt` 和 `fix-v*-success-*` 文件。

机器可读摘要在 `tables/` 中。

## 定量发现

### 1. 失败远比成功昂贵

来自 20 分钟 batch summaries：

| model | avg verified tokens | avg non-verified tokens | ratio |
|---|---:|---:|---:|
| claude | 110,999 | 1,010,949 | 9.1x |
| claude-s4 | 125,725 | 998,522 | 7.9x |
| gpt5 | 64,134 | 256,202 | 4.0x |
| o4mini | 107,696 | 558,247 | 5.2x |

因此，防止失败循环和 proof generation 同样重要。

### 2. 难点具有明显 project-family 特征

20 分钟 verified rates：

| project | claude | claude-s4 | gpt5 | o4mini |
|---|---:|---:|---:|---:|
| AC | 37% | 21% | 27% | 19% |
| NR | 58% | 55% | 48% | 30% |
| OS | 61% | 53% | 44% | 37% |
| NO | 97% | 100% | 83% | 72% |
| MA | 84% | 75% | 72% | 62% |

`AC`、`NR`、`OS` 应该使用不同于 `NO`、`MA`、`AL` 的 routing、context compaction 和 retrieval policy。

### 3. 重复 action loop 很常见

从 2,996 个解析过的 logs 中：

- `AssertFail` 是主要 target error。
- `PostCondFail` 是第二常见 target error。
- 1,010 个日志中，同一个 primary action 至少重复 8 次。

典型高循环模式：

- `seqsetmap` 在 `OS__slinkedlist__...remove_helper*` 上重复 19 次。
- `induction` 在 `VE__regular__repetition__...prefix_secure_helper` 上重复 19 次。
- `instantiate_forall` 在 `AL__tla_forall...` 上重复 18-19 次。
- `uselemma` 在 `NR__extra__aligned...` 上重复 17-19 次。

### 4. 跨模型分歧暴露可复用 proof plans

来自 `tables/top_100_cross_model_disagreements.csv` 的例子：

- `AC__...lemma_from_after_receive_create_pod_resp_to_receive_create_pod_resp.rs`
  - `gpt5`：约 340k tokens verified。
  - `claude-s4`：约 3.37M tokens failed。
- `OS__kernel__create_and_share_pages__impl0__share_mapping.rs`
  - `gpt5`：约 231k tokens verified。
  - `claude`/`claude-s4`：约 1.94M/2.64M tokens failed。
- `NR__impl_u__wrapped_token__impl2__register_failed_map.rs`
  - `gpt5`：约 160k tokens verified。
  - `claude`/`claude-s4`/`o4mini`：约 0.95M-1.61M tokens failed。

这直接说明数据集中存在可复用的成功 proof structure，但没有跨 run/跨模型迁移。

## 定性发现

### AC temporal proofs 需要结构，而不是更多 generic examples

在抽样的 AC liveness lemma 中，GPT-5 成功识别出 proof 需要：

- 从 in-flight OK response 中提取 existential witness；
- 使用两个 phase-progress lemmas；
- 使用 leads-to transitivity/composition。

失败的 Claude-S4 trace 在 20 次尝试中反复 `postcondition_repair` 和 `uselemma`。它只接受了一次 repair，并在日志中消耗约 5.58M input tokens。

prompt 包含完整 code 和 generic vstd examples。vstd token-similarity examples 大多是 sequences/sets/pow2，不是 Kubernetes temporal proof structure。这说明 Verusage-specific helper-lemma graph 比 generic token-similar snippets 更有价值。

### Local repair success 可能误导

一个 repair 可以移除 target `PostCondFail`，但引入一个持续存在的 `AssertFail`。如果 controller 只看 local target-error improvement，就可能接受会增加后续搜索成本的变更。

### Prompt 成本主要来自 input 重复

对大 AC prompts，单次 input prompt 可超过 180k characters 和 40k-60k input tokens。很多失败 run 会重复几十次。这让 compact proof-state memory 和 prompt deltas 比单纯控制 output length 更有希望。

