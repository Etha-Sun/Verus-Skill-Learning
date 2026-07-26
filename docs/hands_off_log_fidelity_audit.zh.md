# Hands-off 日志保真度审计

审计日期：2026-07-24

## 1. 结论

当前 hands-off corpus 没有一种日志格式同时完整保存：

1. task/system/user prompt；
2. 每次 tool call 的名称、参数和完整返回；
3. 每次代码编辑的 exact patch；
4. 每次 Verus 调用的命令、stdout、stderr 和 exit code；
5. provider 暴露的 thinking/reasoning token 数。

信息量最高的是 o4 的 JSONL event logs。它们基本完整保存 shell command、
`aggregated_output`、exit code、agent message 和 usage，也是唯一适合作为未来
canonical transcript 基础的现有格式。但是，它们的 `file_change` 事件只保存
path/kind，不保存 patch；也没有 thinking/reasoning token 字段。因此 o4 JSONL
仍然不是完整轨迹。

Sonnet 4、Sonnet 4.5 和 GPT-5 的 UI transcript 通常保存 tool call 名称、命令和
代码 diff。经过多格式抽样和折行修正后，共识别出 60,740 次带 diff box 的成功
`Edit`，其中 60,581 次（99.74%）显示的增删行数与标题完全一致，说明
**已经显示出来的 Edit diff 在行级上非常完整**。但另有 15,164 次成功
`Edit` 只有 `+N/-M` 摘要、没有 diff body，主要来自 Opus 4.5 和部分
Sonnet 4.5 no-lemma 格式。按所有 75,904 次成功 Edit 计算，60,581
（79.81%）行级完整，15,323（20.19%）压缩或不完全。此外 5,977 次
`Create` 全部不展开正文。

tool/verifier 返回仍大量折叠为 `↪ N lines...`。标准 Opus 4.5 的一大批日志只有
自然语言总结和 usage footer；详细 Opus/no-lemma 日志有 tool 轨迹，但 Edit
通常也是行数摘要而非 diff。

## 2. Scope

主审计范围是现有 M0 hands-off inventory 定义的：

```text
claude_sonnet_gpt5/verified-*/*/*.log
```

共 9,383 条：

| project directory | logs |
|---|---:|
| verified-anvil | 2,074 |
| verified-atmo | 1,895 |
| verified-ironkv | 1,273 |
| verified-memory-allocator | 911 |
| verified-node-replication | 247 |
| verified-nrkernel | 2,110 |
| verified-storage | 678 |
| verified-vest | 195 |

没有把 `all_batch_results-cyy-*` 纳入比例，因为它们是 VeruSAGE 多轮
error/action repair scaffold，不是本次所说的自由探索 hands-off agent。

`claude_sonnet_gpt5/` 另外有 440 个 `.log` 不符合上述 primary transcript
层级：101 个 HumanEval 日志，其余主要是 task 目录下的嵌套辅助/verifier log、
case study 或 whole-project 辅助日志。它们不是独立 hands-off trajectory，故不
进入分母。

## 3. 档位定义

为避免把“出现过一个标记”说成“完整保留”，采用以下档位：

| 档位 | 数量解释 | 保真度解释 |
|---|---|---|
| 所有样本都有 | 100% | 每条都有该字段；仍需另查内容是否被截断 |
| 大部分有 | 80%–99.99% | 可作常用字段，但必须处理缺失 |
| 少部分有 | 20%–79.99% | 不能作为统一轨迹字段 |
| 基本没有/不完整 | <20%，或格式本身有损 | 不应据此重建完整轨迹 |

## 4. 严格完整性重报

本节采用互斥的三种状态：

- **无压缩**：结构化保存完整参数、raw result、exit/status，并能按 event id 配对。
- **有记录但压缩/部分缺失**：有 tool/verifier/edit 对应痕迹，但使用
  `↪ N lines...`、行数摘要、自然语言总结、diff snippet 或 path/kind。
- **无可用记录**：没有足够信号确认该轨迹内容。

| 信息层 | 无压缩 | 有记录但压缩/部分缺失 | 无可用记录 |
|---|---:|---:|---:|
| Tool calls/results（trajectory-level） | 859（9.2%） | 7,588（80.9%） | 936（10.0%） |
| 所有 tool types（含 Edit） | 0（0%） | 8,447（90.0%） | 936（10.0%） |
| 可保证的 end-to-end incremental code history | 0（0%） | 8,169（87.1%） | 1,214（12.9%） |
| Verifier trajectory | 735（7.8%） | 7,860（83.8%） | 788（8.4%） |
| Usage totals | 860（9.2%） | 8,408（89.6%） | 115（1.2%） |
| Thinking/reasoning tokens | 0（0%） | 0（0%） | 9,383（100%） |

解释：

- 859 条是所有 started shell commands 都有 completed JSONL event 的 o4
  logs；另有 22 条 o4 JSONL 存在 unmatched started command，归入部分缺失。
- “所有 tool types”没有无压缩样本，因为 o4 `file_change` 也不含 edit args/patch。
- 上表的 code-history 行要求能证明所有文件写入都被捕获，因而仍是 0；这不等于
  UI 的每个 `Edit` 框都不完整。逐事件复核显示，带 diff box 的 `Edit` 几乎都
  是完整行级 diff；缺口主要是摘要型 Edit、初始 `Create` 和 o4 file_change。
- Verifier 的 735 条无压缩样本指 o4 JSONL 中存在结构化 Verus
  command/output/exit；另有 7,860 条只有 UI 调用、折叠结果或明确结果摘要。
  旧正则曾把普通自然语言中的 “Verus” 也算作 verifier call，现已排除。
- Usage 的 UI footer 常使用 `k`/`M` 和小数，属于 rendered/rounded；860 条 o4
  JSONL 保留整数 usage。两者都没有 thinking-token breakdown。
- 初始 system/user/task prompt 没有作为统一 transcript event 保存；运行脚本中
  经常能恢复 prompt，但不能当作 log 内无压缩记录。

代码还需要单独看最终状态：9,031（96.3%）条同时保留原始 `.rs` 和
`_verified.rs`，所以 **最终 net diff 是无压缩可恢复的**；这不能把 incremental
edit history 从 0% 提升为完整。

## 5. 全量字段覆盖

| 字段 | logs | coverage | 档位 | 完整性判断 |
|---|---:|---:|---|---|
| 可检测 tool-call marker | 8,447 | 90.0% | 大部分有 | 只表示出现 `Read/Edit/Run/$` 痕迹，不表示参数完整 |
| 任意 tool-result marker/payload | 8,402 | 89.5% | 大部分有 | 很多只是行数摘要 |
| 结构化 shell command/result logs | 881 | 9.4% | 基本没有 | 主要是 o4 JSONL；不覆盖完整 Edit patch |
| 全工具完整 call args + raw result | 0 | 0% | 基本没有 | 当前没有一种格式满足 |
| 有成功 code mutation event | 8,169 | 87.1% | 大部分有 | UI Edit/Create 或 o4 file_change；不等于 exact patch |
| 有 inline diff/patch | 5,252 | 56.0% | 少部分有 | 对带 diff box 的 `Edit`，行级内容几乎都完整；`Create` 不展开 |
| 有折叠输出 `↪ N lines...` | 6,489 | 69.2% | 少部分有 | 明确证明返回内容有损 |
| 有 explicit verifier result/error | 3,259 | 34.7% | 少部分有 | 其余多为折叠输出或自然语言声称 |
| 有 input/output/cache usage | 9,268 | 98.8% | 大部分有 | 不是 thinking token |
| 有 thinking/reasoning token 字段 | 0 | 0% | 基本没有 | provider token breakdown 未保存 |
| `.rs` 原始输入存在 | 9,358 | 99.7% | 大部分有 | 可恢复初始代码 |
| `_verified.rs` 文件存在 | 9,043 | 96.4% | 大部分有 | 文件名不自动等于 verifier success |
| 原始与 verified 两端都存在 | 9,031 | 96.3% | 大部分有 | 可恢复最终 net diff，不能恢复逐步 edit |

关键四项中，没有一项在全部 9,383 条日志中达到“所有样本都有且完整”。

### 5.1 Tool call 与返回

UI transcript 中 tool-call marker 的覆盖率很高，但不是 raw event log，也不能
据此声称完整保存了 tool name、arguments 和 result。7,104 条 UI
日志中：

- 7,104 条全部出现 tool-call marker；
- 7,059 条出现某种返回摘要/payload；
- 6,486 条至少一次把返回折叠为 `↪ N lines...`。

因此 UI logs 最多适合粗粒度分析“可能调用了哪类工具、调用顺序是什么”，不适合
恢复完整 call arguments，更不适合恢复“工具到底返回了什么”。例如 `Read file
(82 lines)` 没有保存 read result，`Edit file (+N -M)` 也不是完整 edit request。

o4 JSONL 共 882 条，其中 881 条有结构化 command events，记录了：

- 17,202 个 command started events；
- 17,180 个 command completed events；
- 15,525 个带非空 `aggregated_output` 的 completed commands；
- 4,149 次 completed Verus command，均有 exit/result event。

这类日志的 shell command/result fidelity 明显最好，但 `file_change` 不含 edit
arguments 或 patch，所以不能把它称为“所有 tool calls 完整”。22 个 started
command 没有 completed event，说明中断轨迹仍需显式处理。

### 5.2 Code edit

这里必须区分“带 diff box 的 Edit”、“只有摘要的 Edit”、“初始 Create”和
“整个轨迹”：

| code-edit 层级 | 复核结果 | 判断 |
|---|---:|---|
| 带 diff box 的成功 `Edit` | 60,581 / 60,740（99.74%）实际 `+/-` 行数与标题一致 | 几乎全部行级完整 |
| 只有 `+N/-M` 的成功 `Edit` | 15,164 / 75,904（19.98%）没有 diff body | 压缩记录 |
| 全部成功 `Edit` | 60,581 / 75,904（79.81%）行级完整 | 大部分完整，但不能泛化为 99.74% |
| 失败的 `✗ Edit` | 5,905 | 不算代码 mutation，单列 |
| UI `Create` 事件 | 0 / 5,977 展开正文 | 全部是行数摘要 |
| o4 `file_change` | 0 / 4,000 含 patch payload | 只有 path/kind |
| 原始/最终源码配对 | 9,031 / 9,383（96.3%） | 最终 net diff 可精确计算 |

因此，先前用“0% complete incremental edit history”概括 code edit 会让人误以为
diff 框本身也被大量截断，这是不准确的。更准确的说法是：

- **带 diff box 的 UI Edit：很完整。** 99.74% 的事件保留了标题所声明数量的
  新增/删除逻辑行。长行在终端宽度处换行，因此适合恢复代码语义和行级修改，
  但未必能 byte-for-byte 恢复原始 patch 中的空白。
- **摘要型 Edit：不完整。** Opus/no-lemma 常见
  `● Edit file +49 -8`，只知道修改规模，不知道代码内容。不能把带 diff box 的
  99.74% 完整率外推到这 15,164 次事件。
- **首次 Create：被压缩。** `Create file (+78)` 一类事件不显示那 78 行；
  如果重要代码只在创建时写入、之后没有再次出现在 Edit 中，单靠 transcript
  无法恢复。
- **整个增量轨迹：不能保证无损。** 882 条 o4 JSONL 中共有 4,000 个
  `file_change` events，但 patch-bearing event 为 0；UI 也没有文件系统级审计，
  因而不能证明没有经过 shell、重写或未显示的写入。
- **最终状态：大部分可无损恢复。** 9,031 条同时有原始 `.rs` 和
  `_verified.rs`，可计算完整最终净修改，但不能恢复中间错误版本、回滚版本和
  edit 顺序。

作为另一项交叉检查：在有 diff-box `Edit`、有源码配对且最终确有新增代码的
4,878 条日志中，3,161 条（64.8%）能在 transcript 某处逐字找到全部有意义的
最终新增行，3,376 条（69.2%）能找到至少 95%；其中位数是 100%。这个检索可能
命中 diff 之外的 read/verifier 回显，所以只作为“transcript 信息量”证据，不
把它等同于 edit payload 本身。

#### 代表日志回归测试

对六条不同格式日志做了人工/程序双重核对：

| sample | raw 行数 | 人工核对与统计器结果 |
|---|---:|---|
| Sonnet 4.5 `delegation_map_v__impl1_to_set.log` | 346 | 9 个 diff-box Edit 全部精确；1 个 Create 无正文；实际 `+/-` 逻辑行 100 |
| Sonnet 4 `host_model_next_get_request.log` | 1,805 | 44 个成功 Edit 全精确；4 个失败 Edit 单列；1 个 Create；实际修改行 612 |
| GPT-5 `clone_up_to_view.log` | 428 | 18 个成功 Edit 全精确；1 个 Create；实际修改行 97 |
| Opus no-lemma `process_received_packet_next.log` | 2,810 | 24 个 Edit 只有摘要，共声明 861 行修改但正文 0 行；另有 1 个失败 Edit |
| 标准 Opus `serialized_size.log` | 557 | 只有总结/usage，没有结构化 tool 或 edit body |
| o4 `vec_erase.log` | 80 个 JSONL event 行 | 31 行 command payload、891 行解码后的 result payload、14 个 file_change metadata；patch 0 行 |

回归测试发现并修复了四种旧统计误差：

1. `Edit (-N)` 的纯删除操作未被旧正则识别；
2. `✗ Edit` 被误算为成功 mutation；
3. Opus 的 `● Read/Run/Edit` 被误算为 narration；
4. 长文件名会把 `(+N -M)` 折到下一物理行，以及少数 log 在中间 usage footer
   后继续拼接第二段会话。

修正后，独立的 edit-event 统计器和 line-composition 统计器对全量 corpus 的
实际 `+/-` 逻辑行总数完全一致：都是 **1,833,283 行**，逐日志差异为 0。

#### 每类信息平均占用行数

以下平均数以全部 9,383 条日志为分母；“出现时平均”只在该类大于 0 的日志中
计算。UI 使用实际可见物理行；JSONL 的 command/output 使用 JSON 解码后的逻辑
行，因此 o4 的 payload 行数可以大于它的 raw JSONL 行数。

| 信息类 | 每条日志平均行数 | 出现的日志数 | 出现时平均行数 | 说明 |
|---|---:|---:|---:|---|
| raw log 物理行 | 595.1 | 9,383 | 595.1 | JSONL 的多行字符串仍只占一个 raw 行 |
| agent narration/message | 89.8 | 9,299 | 90.6 | 可见叙述，不是隐藏 thinking |
| tool call/command payload | 54.6 | 8,447 | 60.6 | 调用标题、命令及可见参数行 |
| tool result payload | 130.0 | 8,402 | 145.1 | UI 折叠结果只计一个 marker；o4 解码完整 output |
| code-edit 显示区域 | 353.8 | 7,431 | 446.7 | 含 diff context、边框和摘要标题 |
| 实际 `+/-` code lines | 195.4 | 5,252 | 349.1 | 只计 diff 中带 `+/-` 的逻辑行 |
| 摘要中声明但未显示的修改行 | 111.1 | 909 | 1,146.8 | Opus/no-lemma 等摘要型 Edit/Create |
| Create 摘要标题 | 0.64 | 5,412 | 1.10 | Create body 始终为 0 行 |
| o4 file_change metadata | 0.43 | 738 | 5.42 | path/kind event，不是 patch |
| verifier call payload | 31.1 | 8,159 | 35.8 | 是 tool-call 行的子集 |
| verifier result payload | 23.2 | 8,159 | 26.7 | 是 tool-result 行的子集 |
| usage footer/event | 5.04 | 9,268 | 5.11 | UI footer 或 JSON usage event |
| thinking-token 字段 | 0 | 0 | 0 | 完全没有 |

按模型族平均：

| family | logs | raw 行均值 / 中位数 | narration | tool call | tool result | edit 显示 | 实际 `+/-` | 摘要声明但缺失 | verifier result | usage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Opus 4.5 | 1,312 | 451.1 / 62 | 184.9 | 72.2 | 36.2 | 8.8 | 0 | 588.6 | 11.5 | 4.2 |
| Sonnet 4 | 1,966 | 870.0 / 451 | 89.5 | 49.5 | 21.3 | 664.8 | 382.0 | 0 | 12.1 | 5.9 |
| Sonnet 4.5 | 3,143 | 825.5 / 381 | 126.6 | 72.8 | 35.2 | 478.1 | 270.0 | 86.0 | 17.9 | 5.3 |
| GPT-5 | 1,884 | 269.2 / 157.5 | 2.3 | 31.6 | 17.3 | 210.9 | 96.7 | 0 | 7.5 | 6.0 |
| o4 JSONL | 882 | 48.1 / 44 | 9.0 | 21.5 | 1,113.5 | 0 | 0 | 0 | 120.6 | 1.0 |
| unknown/legacy | 196 | 703.5 / 400 | 64.2 | 66.1 | 23.8 | 516.1 | 262.3 | 0 | 11.4 | 7.3 |

这里的类别不是都互斥：verifier 是 tool 的子集，`实际 +/-` 是 edit 显示区域的
子集，不能把各列相加当作总行数。o4 的 raw 行数很少但 decoded result 行数最高，
正是 JSONL 保留完整多行输出的结果。

未来应把“完整 code edit”定义为每次 edit 都保存：

```text
before_sha256 + after_sha256 + exact unified diff
```

大文件或多轮编辑还应保存 content-addressed snapshot。

### 5.3 Verifier

UI transcript 中通常能看到 agent 调用了 Verus，但输出经常被折叠。只有
3,259/9,383 条出现 explicit `verification results::`、明确 verifier error 或
等价结果 payload。自然语言中的“Perfect, verification succeeded”不能代替原始
verifier result。

o4 JSONL 最接近完整：有 Verus 调用的 735 条日志中，command、output/exit 和
状态均结构化保存。它仍缺少统一记录的 Verus binary hash/version、cwd、timeout
和 stdout/stderr 分流。

有 5 条 GPT-5 日志检测到实际 command 将 Verus 输出重定向回外层 transcript
同名 `.log`。这会破坏或覆盖轨迹，应禁止。

### 5.4 Thinking tokens

0/9,383 条日志包含 `thinking_tokens` 或 `reasoning_tokens` 字段。

日志中经常有自然语言分析、`●` 段落或 JSONL `agent_message`，但这些是可见
assistant narration，不等于 provider 的隐藏 chain-of-thought，也不能推出
thinking token 数。现有 usage footer 只覆盖 input、output、cache read/write 等。

未来只能在 provider 明确暴露时记录：

```json
{
  "reasoning_tokens": 1234,
  "reasoning_content": null,
  "reasoning_availability": "token_count_only"
}
```

若 provider 不暴露，必须保存 `null/not_available`，不能把 output tokens 当成
thinking tokens。

## 6. 模型/格式差异

| family | logs | median bytes | tool calls | explicit verifier result | inline edit signal | 评价 |
|---|---:|---:|---:|---:|---:|---|
| o4 JSONL | 882 | 60,967 | 99.9% | 83.3% | 0% | tool/verifier 最完整；缺 patch/thinking |
| Sonnet 4 UI | 1,922 UI + 44 failures/mixed | 42,304 overall | 97.7% | 23.4% | 84.3% | diff 片段丰富，返回大量折叠 |
| Sonnet 4.5 UI/mixed | 3,143 | 24,202 | 99.9% | 37.6% | 66.1% | narration/tool 丰富，raw verifier 不稳定 |
| GPT-5 UI/mixed | 1,884 | 15,440 | 98.1% | 7.9% | 73.1% | 命令/编辑常见，verifier raw output 最弱 |
| Opus 4.5 mixed | 1,312 | 3,451 | 35.2% | 53.3% | 0% | 标准目录多为总结文本；no-lemma 子集较详细 |

Opus 4.5 必须按子目录再分：

- `results-opus45`、`results_adv-opus45` 等标准/advanced 目录的大量 log 只有
  自然语言总结和 usage，缺 tool/edit events；
- `results-nol-opus45`、`results_adv_nol-opus45` 多为详细 UI transcript，有
  tool sequence，但返回依然以摘要为主。

“日志字节数大”不自动等于“保真度高”。大 UI transcript 可能主要是 narration、
read-count 和折叠 diff；JSONL 较小也可能保存更完整的 command/exit/result。

## 7. 八个项目目录

项目目录本身不是主要决定因素；每个目录内部的 model/result family 才决定格式。

| directory | tool call | explicit verifier result | inline edit signal | `_verified.rs` exists |
|---|---:|---:|---:|---:|
| verified-anvil | 91.6% | 32.4% | 51.7% | 95.5% |
| verified-atmo | 91.6% | 42.8% | 66.6% | 97.5% |
| verified-ironkv | 89.6% | 31.6% | 59.6% | 97.4% |
| verified-memory-allocator | 90.2% | 28.3% | 52.4% | 99.9% |
| verified-node-replication | 88.3% | 36.0% | 52.6% | 99.6% |
| verified-nrkernel | 86.2% | 35.4% | 51.7% | 92.6% |
| verified-storage | 90.7% | 33.8% | 54.1% | 99.1% |
| verified-vest | 88.7% | 26.2% | 49.7% | 99.0% |

## 8. 推荐使用顺序

如果目标是蒸馏 hands-off agent 的真实决策过程：

1. 首选 `results-o4` / `results_adv-o4*` JSONL，研究 tool sequence 和 verifier
   feedback；同时用原始/verified 文件计算 net patch。
2. 第二选择 detailed Sonnet 4/4.5 UI logs，研究可见 rationale 和 edit strategy；
   verifier 反馈必须标记为 truncated/unknown。
3. GPT-5 UI logs 可用于 tool/edit action pattern，但不能假设保存了 verifier
   stdout。
4. 标准 Opus summary logs 只适合提取高层 proof rationale、usage 和最终 artifact，
   不适合 trajectory reconstruction。
5. 381-byte authentication errors、只有 verifier 单行或被同名重定向破坏的 log，
   应标为 incomplete，不能作为成功 hands-off trajectory。

## 9. 未来完整保留规范

建议 canonical run bundle：

```text
run/
  transcript.jsonl
  prompt/
    system.txt
    user.txt
    prompt_manifest.json
  edits/
    0001.patch
    0002.patch
    snapshots/<sha256>.rs
  verifier/
    0001.stdout
    0001.stderr
    0001.json
  artifacts/
    input.rs
    final.rs
  usage.json
  manifest.json
```

`transcript.jsonl` 每个事件必须有 monotonic sequence、timestamp、call id、tool name、
完整参数、cwd、stdout/stderr artifact hash、exit code、timeout 和 before/after
state hashes。大输出可以外置，但必须 content-addressed，不能只写
`N lines omitted`。

必须在写盘前做 secret redaction。结构扫描发现 187 条日志含凭据样式材料，均来自
o4 JSONL 捕获的完整 command output；本报告没有保存或复述匹配值。完整 raw tool
logging 与敏感信息防护必须一起设计。

## 10. 审计限制

- 这是结构保真度审计，不判断 proof 是否数学正确。
- `explicit verifier result` 是保守正则信号；可能漏掉非标准措辞，但不会把单纯
  narrative success 当成 raw result。
- `inline edit signal` 只表示出现过 diff-like text，不声称 diff 完整。
- `_verified.rs` 存在不等于 Verus 或 checker 成功；最终 status 仍应由独立
  verifier/checker record 决定。
- 对八个项目目录做了机械全量扫描；没有把任务代码内容复制进派生结果。
