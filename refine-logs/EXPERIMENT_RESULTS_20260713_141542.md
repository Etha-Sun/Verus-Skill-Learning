# Control-Null Action Information-Gain Pilot

**日期**：2026-07-13  
**结论**：工程完整性通过；预注册方法门槛失败；按计划停止 patch/full-proof 与扩展实验。

## 实验问题

检验 VeruSAGE trajectory 中的 decision-time verifier evidence 是否真的为当前修复 action 提供 state-specific information，而不是仅由额外文本、长度、Verus 风格、历史 action 或 option 位置造成概率变化。

## 设置

- 数据：3 条最终 verified 的 Claude hands-on traces，抽取 6 个 locally accepted action states。
- 模型：本地 `<model-root>/QwQ-32B`，vLLM tensor parallel 4。
- 目标：trace 中实际执行且局部 accepted 的 action；它是 demonstrator label，不等价于全局最优 action。
- action space：固定 22 类，每个 state 使用确定性随机 option mapping。
- prompt：`chat_direct`，跳过 QwQ 默认 `<think>` 前缀；测量 reasoning-suppressed forced-choice proxy。
- 每个 state：1 个 evidence、5 个 token-exact matched controls、1 个仅诊断 wrapper effect 的 `empty_container`，共 42 cases。
- non-empty intervention token delta：按 state 分别为 124、160、144、125、124、157；每个 state 内完全一致，无 padding。

## 对照含义

| artifact | 要排除的混淆 |
|---|---|
| `cross_trace_same_error` | 只有 error type/Verus 风格相似，但不是当前 state |
| `cross_trace_any` | 任意其他 trace 的 verifier evidence |
| `block_shuffled` | 保留词汇和代码块，破坏结构顺序 |
| `counterfactual_error` | 保留格式，替换为错误的 verifier diagnosis |
| `irrelevant_archive` | 与 proof repair 无关的档案管理文本，测额外长文本本身的影响 |
| `empty_container` | 只测 artifact wrapper；不参与 primary null mean |

`irrelevant_archive` 是构造意义上的 negative control，不可能预先保证模型概率变化为零或负。它的价值正是检测“无关文本也能涨分”；本轮它的 mean conditional PMI 为正，说明 raw positive IG 不能被当作相关性证据。

## 主要结果

| artifact | mean decision PMI (bits) | positive states |
|---|---:|---:|
| evidence artifact | -0.1922 | 3/6 |
| cross-trace same-error | -0.4236 | 2/6 |
| cross-trace any | -0.5454 | 3/6 |
| block shuffled | +0.4855 | 3/6 |
| counterfactual error | +0.1824 | 3/6 |
| irrelevant archive | +0.3794 | 3/6 |
| empty container | +0.1192 | 4/6 |

Primary metric：

```text
specific_gain(state)
  = PMI(evidence)
  - mean(PMI(five matched controls))
```

| metric | result | predeclared requirement |
|---|---:|---:|
| mean specific gain | **-0.2079 bits** | > 0 |
| positive specific states | **2/6** | >= 4/6 |
| evidence wins vs same-error | **3/6** | >= 4/6 |
| evidence wins vs shuffled | **2/6** | >= 4/6 |
| evidence wins vs irrelevant | **2/6** | >= 4/6 |

所有 GO 条件失败。个别 state 有增长，但 evidence 没有稳定超过 matched null，不能支持“当前 artifact 改善 action selection”。

## 测量有效性发现

- 22-way 内部概率归一化误差不超过 `6.7e-16`，PMI 算术正确。
- 但 A-V 候选 token 的原始下一 token 总概率质量仅为 `5.00e-12` 至 `3.96e-10`，median `8.36e-11`。
- 六个 evidence case 的 raw target-token IG 全为负，均值 `-2.2796 bits`。
- 因此当前 decision PMI 只能解释为“条件于模型必须输出 A-V 中一个字母”的 forced-choice proxy，不能解释为 QwQ 的自然 action policy。

## 审计与停止决定

- 19 个 unit/leakage/integrity tests 全部通过。
- 42 cases、1,848 token score rows、hash、token delta、option mapping 和 target consistency 均通过复算。
- evidence construction 不读取当前 target action、当前 attempt 后日志或 final proof；历史 action 属于 decision-time 信息，但 3/6 later states 的历史中出现过当前 action，仍是 attribution confound。
- 独立 Codex 审计 verdict：`PASS_WITH_LIMITATIONS`；predeclared GO：`FAIL - STOP`。

所以本轮不运行 patch/full-proof IG，也不扩大 trace 数量。下一步应先修复 measurement interface：让模型以高概率进入可评分 action channel，或直接评分真实 agent-generated action/reasoning，再重新构造能与 controls 分离的 artifact。

## 产物

- cases：`verus-self-evolve-scaffold/runs/control_null_ig_20260713/action_cases.jsonl`
- analysis：`verus-self-evolve-scaffold/runs/control_null_ig_20260713/r025_six_states/analysis/`
- audit：`refine-logs/EXPERIMENT_AUDIT_20260713_140634.md`
- cases SHA256：`d209d5a2a32e66b25addaa2af8705d1b12e96cfca7736aa79ff502fae7491d55`
- aggregates SHA256：`9aa992a136d25f993e60766b31ef5009b2bf9007f4131d3e5b7f2314dc3e7f82`
