# 三目标 IG 实验独立完整性审计

**日期**：2026-07-14  
**审阅者**：GPT-5.5 xhigh，独立只读审阅  
**总体结论**：`WARN`  
**完整性状态**：机械与算术完整，但属于小规模 offline likelihood proxy，不是 downstream agent 改善评估

## A. Target 来源：WARN

- action 来自 trace 中 observed demonstrator action：`ig_probe.py:537-548`。
- patch 是 prefix code 与最终 verified code 的确定性 diff：`ig_probe.py:455-525,581-598`。
- full proof 来自最终 verified `.rs`：`ig_probe.py:566-578`。
- evidence 只使用当前 prefix 的 error、历史 action/error、verifier 文本和 prefix code window：`ig_probe.py:726-749`。

没有发现未来 patch 或 final proof 泄漏。历史中可能出现与当前 action 相同的旧 action，这是合法 prefix history，但会成为 action-label-in-context 混杂。评估应分类为 `self_supervised_proxy`，而不是 `real_gt`。

## B. Metric：WARN

- `artifact - baseline` 的 logprob 方向和 nats-to-bits 转换正确：`logprob_scorer.py:748-766`。
- token boundary 和跨 chunk next-token 处理有实现及测试：`logprob_scorer.py:198-270`、`test_logprob_scorer.py:129-170`。
- specific IG 正确实现为 evidence raw IG 减去五类 matched controls 均值：`three_target_analysis.py:133-164`。
- 实际 backend 是 HF，不是 vLLM；正式报告已更正。
- 本轮 `candidate_count=1`，未执行 22-way candidate-normalized action distribution。

## C. 文件与算术：PASS

- cases 126 行、aggregates 126 行、token scores 1,499,498 行。
- 矩阵严格为 6 states × 3 targets × 7 artifacts。
- token score 行数等于 `2 × 749,749`，对应 baseline 与 artifact-conditioned 两种条件。
- action、patch、full-proof spot check 的逐 token logprob 和与 aggregates 一致。
- target/control 汇总可由底层结果重算，报告哈希与 `summary.json` 一致。

## D. 执行路径：WARN

已执行 exact scoring、126 个 case checkpoints、三目标分析、CSV、PNG/PDF。没有发生截断，最大序列 78,392 < 131,072。

未实际触发 resume（`resumed_case_count=0`），也未执行 action candidate distribution。它们有实现或接口，但不属于本轮结果证据。

## E. Scope：WARN

报告只覆盖 3 traces / 6 states，且没有 solved rate、live-agent tokens、trajectory improvement 或 held-out project split。任何泛化、self-evolving agent 提升或 repair efficiency claim 均不受支持。

## F. Controls：WARN

- `empty_container` 已正确排除在 matched controls 外。
- evidence 与五类正式 controls 均 exact token matched。
- action 对 irrelevant 的均值差为 -0.5398 bits，只赢 2/6；对 shuffled 只赢 3/6。
- patch 对 irrelevant 赢 5/6，但对 shuffled 的 mean difference 为 -3.0562 bits。
- full proof 对 irrelevant 与 shuffled 均赢 6/6。

## 支持的结论

1. 三种 target likelihood probe 已在相同 6 states 上完成。
2. raw/specific IG 算术与逐 token 记录有效。
3. full-proof evidence 在此 pilot 中稳定胜 irrelevant 与 shuffled controls。
4. action IG 仍受 irrelevant/shuffled 上下文混杂。

## 需要限定或不支持的结论

- “evidence 改善 action selection”：不支持。
- “patch 稳定胜 shuffled”：不支持，结果混合。
- 泛化、solved-rate、token efficiency、live repair 改善：未评估。

完整只读审阅输出保存在：`.aris/traces/experiment-audit/20260714_run01/reviewer_output.md`。
