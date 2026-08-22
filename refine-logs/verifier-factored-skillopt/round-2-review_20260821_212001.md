# Round 2 Review

**Reviewer**: same independent GPT-5.5 xhigh thread
**Overall**: 7.10/10
**Verdict**: REVISE
**Anchor**: preserved

## Scorecard

| Axis | Score |
|---|---:|
| Problem Fidelity | 9 |
| Method Specificity | 7 |
| Contribution Quality | 6 |
| Frontier Leverage | 8 |
| Feasibility | 6 |
| Validation Focus | 8 |
| Venue Readiness | 6 |

## Blocking Findings

1. `CardTemplate` 与 checkpoint-specific `CardInstantiation` 尚未分开；带 source hash、concrete symbol、byte range 的 card 不可能跨 checkpoint 泛化。
2. V-FACE 的 `ADMIT / REJECT / UNKNOWN` 决策规则未冻结。
3. exposure ITT 的随机化单位、hard outcome 顺序、ROPE 与 prospective target 需要唯一化。
4. Generic replay baseline 必须写成可执行协议；compiler gate 只验证工程可行性，不能证明 admission claim。

## Review Conclusion

修订已足以进入 compiler feasibility gate，贡献也已聚焦；但 top-tier novelty 仍是 PARTIAL，且 READY 必须等待 prospective 证据。
