# Codex–Qwen Failure-Path Analysis

**审计日期：** 2026-07-22

**对象：** R040B 30-task screen、R040C qualitative selection、R041A H0/H1/H2、
R041B Codex fresh-exploration baseline。

**主结论：** 现有结果支持“global trace-distilled rationale 没有带来三样例 solve-rate
收益且成本/安全性变差”；不支持“Codex 纯因模型更大而优于 Qwen”，因为
closest-failure 的 Qwen agent-loop 系统性拿不到配置的 Verus 命令反馈。

## 1. 运行与条件

| 条件 | 模型/样本数 | 可见知识 | 目的 |
|---|---|---|---|
| Qwen H0 | Qwen3.6-27B；3 tasks × 3 reps | 仅基础任务与工具指令 | 无 rationale 基线 |
| Qwen H1 | 同上 | generic Verus repair guidance | 控制“多一段一般建议” |
| Qwen H2 | 同上 | 由历史 trace 蒸馏的 global rationale | 检验 trace-derived knowledge |
| Codex H0 | gpt-5.6-sol/high；3 tasks × 1 rep | fresh task；不可见旧 trace、verified answer、rationale | 正常 agent exploration 的机制参照 |

三个任务由 H0 表现预先选择：

| Case | Calibration ID | Task | 选择依据 |
|---|---|---|---|
| stable_pass | `5372cee76ecb03502a30` | `seq_filter_contains_implies_seq_contains` | Qwen H0 3/3 |
| stable_closest_failure | `099e5503300d7b344c40` | `marshal_v__impl2__lemma_serialize_injective` | Qwen H0 0/3，但诊断接近关键 obligation |
| unstable | `08a957ddd7a2bc344621` | `marshal_v__impl5__lemma_same_views_serialize_the_same` | Qwen H0 2/3 |

## 2. Raw result table

### 2.1 30-task screen

| 机械状态 | 数量 | 比例 | 解释 |
|---|---:|---:|---|
| strict solve | 7 | 23.3% | independent Verus 与 Lynette 均通过 |
| stalled | 11 | 36.7% | agent 结束但候选未通过；不是“进程还在跑” |
| timeout / infrastructure | 10 | 33.3% | 超时或 transport/tool failure，不能都当能力失败 |
| unsafe | 2 | 6.7% | 产生被 safety checker 拒绝的 proof bypass/非法修改 |
| total | 30 | 100% | R040B screen |

“stalled”表示在预算内没有进一步机械进展，通常仍有明确 verifier obligation 或没有可用
候选；它与 timeout、process still running、unsafe 是不同状态。

### 2.2 三任务 H0/H1/H2

| Task class | H0 reps | H1 reps | H2 reps |
|---|---|---|---|
| stable_pass | PASS, PASS, PASS | PASS, PASS, PASS | PASS, PASS, FAIL |
| stable_closest_failure | FAIL, FAIL, FAIL | FAIL, FAIL, FAIL | FAIL, FAIL, FAIL |
| unstable | FAIL, PASS, PASS | PASS, PASS, FAIL | FAIL, PASS, PASS |
| **总 solve rate** | **5/9 (55.6%)** | **5/9 (55.6%)** | **4/9 (44.4%)** |
| Lynette safety pass | 9/9 | 9/9 | 6/9 |

相对 H0，H2 的 solve count 少 1，input tokens 增加约 27.3%，output tokens 增加约
19.2%，wall time 增加约 17.4%，并出现 3 个 Lynette safety failures。这是描述性结果；
样本只有 3 tasks，不能估计总体方法效应。精确 usage records 保留在外部 run root，
不复制成仓库内 token table。

### 2.3 Codex fresh baseline

| Case | Result | Wall | Unique commands |
|---|---|---:|---:|
| stable_pass | PASS | 27.2s | 3 |
| stable_closest_failure | PASS | 279.6s | 21 |
| unstable | PASS | 37.9s | 4 |
| **总计** | **3/3** | **344.7s** | — |

Codex usage 包含大量 cached context，不能与 Copilot/Qwen 的 transport usage 字段直接
作价格或算力等价比较；精确 usage 仅保留在外部 run artifacts。

## 3. closest-failure 逐路径对照

目标 obligation 是：若两个 `Vec<u8>` 的 serialization 相同，则先由固定 8-byte 长度
前缀推出 payload 长度相同，再由 offset `8+i` 的逐元素相等推出两个 sequence
extensional equality。

### 3.1 九个 Qwen 运行

| 条件/rep | Result | Wall | agent-loop `Permission denied` 次数 | 最终行为 |
|---|---|---:|---:|---|
| H0/1 | FAIL; Lynette pass | 812s | 17 | 错把 Verus `&&&` 改成 Rust `&&`，直接断言 length/tail equality；2 个 assertion failures |
| H0/2 | FAIL; Lynette pass | 490s | 3 | candidate 与 input 相同 |
| H0/3 | FAIL; Lynette pass | 265s | 5 | candidate 与 input 相同 |
| H1/1 | FAIL; Lynette pass | 99s | 9 | candidate 与 input 相同 |
| H1/2 | FAIL; Lynette pass | 565s | 5 | 把 `&&&` 改成 `&&` 并加 casts，未修 proof obligation |
| H1/3 | FAIL; Lynette pass | 803s | 13 | 仅加入 `spec_u64_to_le_bytes(0u64).len()==8`；该 assertion 自身失败 |
| H2/1 | FAIL; **Lynette fail** | 507s | 7 | 识别 prefix/cancellation；一度只剩 1 error，最终加入非法 nested proof fn 和 `external_body` helper |
| H2/2 | FAIL; Lynette pass | 485s | 13 | candidate 与 input 相同 |
| H2/3 | FAIL; unchecked/unsafe status | 1,092s | 22 | 没有可用 candidate，主要消耗在被拒工具调用和反复探索 |

共同现象：9/9 agent logs 都出现
`Permission denied and could not request permission from user`。被拒对象是机器本地配置
的绝对 Verus binary 路径。runner 在 agent 结束后仍能执行独立 final Verus check，
所以这是“交互 verifier feedback 不可用”，不是最终验证器环境坏掉。

### 3.2 Codex 成功路径

Codex 从第一次探索起即可调用同一 Verus binary。其路径不是一次命中，而是有效的
闭环：

1. 读取 `input.rs/candidate.rs`，第一次 Verus 将问题定位到两个 8-byte prefix
   assertions 和 payload extensionality。
2. 补充 inherited preconditions，处理 `usize` cast 的 recommendation。
3. 多次猜测不存在的 bytes lemma；编译器相似名提示最终指向
   `lemma_auto_spec_u64_to_from_le_bytes`。
4. 编译器进一步提示该 lemma 零参数调用；修改后长度前缀部分通过，只剩 extensional
   equality。
5. 对所有 `0 <= i < len`，显式证明 `8+i` 在 serialized sequence 范围内，并连接
   `serialized[8+i] == payload[i]`。
6. independent Verus 报告 1 verified；Lynette 通过。最终仅增加 27 行 proof
   assertions，无 `external_body` 或其他 bypass。

### 3.3 关键差异发生在哪里

| 阶段 | Qwen closest-failure | Codex closest-failure | 当前可解释性 |
|---|---|---|---|
| 读取任务结构 | H2/1 能识别 length prefix 与 cancellation | 很快识别同一结构 | 高层 diagnosis 不是唯一差距 |
| 获得 verifier feedback | 绝对路径反复被 CLI 拒绝；有的 run 后来找到 PATH 中 `verus` | 从首次迭代即稳定可用 | **首要 harness confound** |
| 使用错误信息 | 获得反馈时能缩到 1 error，但没有安全完成 cancellation | 根据 compiler hint 找到真实 vstd lemma 并修正调用签名 | 反馈转化能力存在定性差异 |
| 生成 proof artifact | H2/1 发明 nested helper 与 axiom-like `external_body` | 使用现有 library lemma + index facts | H2 有 over-edit / safety regression |
| 最终收敛 | 0/9 | 1/1 | 不能直接归因于参数尺度 |

## 4. Numbered findings

1. **H2 没有显示 solve-rate 增益。** 三任务上 H2 为 4/9，低于 H0/H1 的 5/9；
   closest-failure 三个条件均为 0/3。
2. **H2 成本和 safety 表现更差。** 在这 9 个 runs 中，H2 的输入、输出和 wall
   均更高，并有 3/9 Lynette failures；global rationale 至少没有可靠抑制无效扩展。
3. **generic H1 也没有提高 solve count。** H1 与 H0 同为 5/9；它的低 output/wall
   是描述性现象，不能在三个任务上宣称效率改善。
4. **Codex 3/3 证明这三个任务在正常 agentic exploration 下可解。** 尤其
   closest-failure 的 21 次独立命令和完整错误收敛链说明答案不是一次性 oracle 输出。
5. **但 Codex–Qwen 不是 matched model-scale experiment。** transport、agent
   harness、tool permission、缓存记账和 repetition 数均不同；最严重的是 Qwen
   agent-loop 缺失稳定 verifier feedback。
6. **Qwen 的弱点不只是“完全没思路”。** H2/1 已找到正确的 prefix/cancellation
   抽象并缩到一个错误；差距更像“把局部 insight 转成受 Verus 支持、无 bypass 的
   最终证明”。
7. **global trace rationale 的粒度不匹配当前 state。** 它没有告诉 agent 当前唯一
   obligation 对应哪个已存在的 vstd lemma、应在哪个 offset 建立 extensionality，
   也没有有效禁止发明 `external_body` helper。
8. **当前最值得蒸馏的是 verifier-conditioned transition，而非整条 rationale。**
   例如“看到固定前缀长度失败 → 激活 bytes library lemma；只剩 extensionality →
   转为 offset-index proof”，这类 state→action operator 比一段通用总结更可验证。

## 5. 可支持与不可支持的 claim

| Claim | 状态 | 原因 |
|---|---|---|
| 三任务上 H2 未优于 H0/H1 | 支持，限于样本 | 4/9 vs 5/9 vs 5/9 |
| H2 在本实验更耗 token/时间且 safety 更差 | 支持，描述性 | 完整 usage 与 Lynette records |
| trace-distilled rationale 一般会伤害模型 | **不支持** | n=3 tasks，且存在 verifier-access confound |
| Codex 正常探索能解三个 frozen tasks | 支持 | 3/3 independent Verus+Lynette |
| 大模型比小模型更会做 Verus | **尚不支持为因果 claim** | harness/tool access/repetition 不匹配 |
| information gain 提高 solved rate/token efficiency | **不支持** | 现有 IG 是离线 proxy，缺 leakage-safe live evidence |

## 6. 下一组实验

| 优先级 | 实验 | 最小设计 | Go/No-Go |
|---:|---|---|---|
| P0 | Verifier-access matched control | 给 Qwen workspace-local wrapper 或已验证 PATH alias；启动前做 agent-loop command smoke；closest-failure H0 3 reps | 3/3 runs 均能在 agent-loop 读取真实 Verus 输出，才进入方法比较 |
| P1 | Matched H0/H1/H2 rerun | 同模型、同 harness、同 verifier access、同 timeout、同 3 reps；先只跑 closest-failure | 若 H2 仍无改善，再把 global H2 判为 stop |
| P2 | Task-state-specific H3 | 只提供当前 obligation、真实 verifier error、允许的 existing lemma 搜索策略、negative rule（禁 `external_body`/改 spec） | 必须改善 strict pass 或 Expected Cost to Success，且 safety 不退化 |
| P3 | Operator ablation | `diagnose-only`、`library-lemma hint`、`offset extensionality hint`、完整 H3 | 找到哪个组件有因果增益，而不是整段 prompt 相关性 |
| P4 | Student-scale comparison | 在 matched harness 上对小/大模型使用相同 frozen tasks、3+ reps | 再判断 diagnosis、actionability、verifier-use 和 recovery 的尺度差异 |

P0 是方法实验的前置条件，不是可选的工程清理。P0 之前继续增加 rationale 复杂度会把
tool feedback 缺失误归因给知识质量。

## 7. Durable artifact pointers

下列完整目录只作为运行指针，不应复制进仓库：

- R040B screen: `${VERUS_SKILL_RUN_ROOT}/r040b_qwen_screen_20260721_live_attempt2/`
- R041A contrast: `${VERUS_SKILL_RUN_ROOT}/r041a_contrast_20260722_attempt1/`
- Codex baseline: `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/`
- closest-failure Qwen logs:
  `${VERUS_SKILL_RUN_ROOT}/r041a_contrast_20260722_attempt1/runs/099e5503300d7b344c40/`
- closest-failure Codex events:
  `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/runs/099e5503300d7b344c40-rep1-codex-h0/`

原始 source SHA-256 为
`c5b59bd3579e57cfbcb0eb7c0bc970ff6a46f2ad74dee25e0a8cec6574810650`；
审计中所有 `input_unchanged` 检查保持为 true。
