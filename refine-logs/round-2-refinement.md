# Round 2 Refinement

## Problem Anchor

- **Bottom-line problem:** 判断“从每个 Verus 文件提取 memory，再搭建一个高度 domain-specific 的 RAG”是否是好的 skill-system 设计，并给出不限于 embedding/vector search 的 Verus 检索方案。
- **Must-solve bottleneck:** 当前 agent 不是普遍缺少更多文本，而是在特定 proof state 下无法及时找到可访问、签名兼容、对当前 verifier obligation 真正有帮助的 lemma、proof pattern 或下一步动作；无选择地注入全局 memory 可能增加 token、误导编辑并引入 safety regression。
- **Non-goals:** 不把全文向量库本身包装成研究创新；不让检索器替代 Verus/Lynette；不在没有 leakage-safe live rerun 的情况下声称提高 solved rate 或 token efficiency；不立即加入 SFT/RL、多 agent 或复杂自进化。
- **Constraints:** 原始与 sealed 数据只读；新运行输出只写入 `VERUS_SKILL_RUN_ROOT`；禁止 exact-task/reference-proof leakage；R041 global H2 已给出负面定性信号；R042 frontier held-out evaluation 尚未完成；系统必须允许“不检索/不注入”。
- **Success condition:** 在 task/project-held-out live Verus repair 中，相对无 memory、文件摘要 RAG 和 embedding-only RAG，系统提高 strict Verus+Lynette success 或降低 Expected Cost to Success，且 unsafe edit rate 不增加；离线 premise/transition retrieval 指标只能作为诊断。

## Anchor Check

- 原始问题保持不变；MVP 只将 success condition 中的第一阶段证据限制为 frozen repository 内 task-held-out。
- 跨项目结论被明确推迟，不把 FQ lemma reuse 误写成 domain-general transfer。

## Simplicity Check

- 唯一机制：replay-validated selective lemma-transition retrieval。
- 唯一 action family：`invoke_lemma`。
- MVP abstention 是 deterministic/conservative，不声称小样本风险校准。
- utility 为词典序约束，不含任意权重。

## Revised Proposal

# Research Proposal: Replay-Validated Selective Lemma-Transition Retrieval for Verus

## Problem Anchor

- **Bottom-line problem:** 判断“从每个 Verus 文件提取 memory，再搭建一个高度 domain-specific 的 RAG”是否是好的 skill-system 设计，并给出不限于 embedding/vector search 的 Verus 检索方案。
- **Must-solve bottleneck:** 当前 agent 不是普遍缺少更多文本，而是在特定 proof state 下无法及时找到可访问、签名兼容、对当前 verifier obligation 真正有帮助的 lemma、proof pattern 或下一步动作；无选择地注入全局 memory 可能增加 token、误导编辑并引入 safety regression。
- **Non-goals:** 不把全文向量库本身包装成研究创新；不让检索器替代 Verus/Lynette；不在没有 leakage-safe live rerun 的情况下声称提高 solved rate 或 token efficiency；不立即加入 SFT/RL、多 agent 或复杂自进化。
- **Constraints:** 原始与 sealed 数据只读；新运行输出只写入 `VERUS_SKILL_RUN_ROOT`；禁止 exact-task/reference-proof leakage；R041 global H2 已给出负面定性信号；R042 frontier held-out evaluation 尚未完成；系统必须允许“不检索/不注入”。
- **Success condition:** 在 task/project-held-out live Verus repair 中，相对无 memory、文件摘要 RAG 和 embedding-only RAG，系统提高 strict Verus+Lynette success 或降低 Expected Cost to Success，且 unsafe edit rate 不增加；离线 premise/transition retrieval 指标只能作为诊断。

## Research Judgment

“每文件 memory + domain RAG”是合理的 engineering baseline，但不是完整 skill system，也不是足够新的研究贡献。`file` 应是 ingestion boundary，不是 retrieval unit；static facts 至少拆到 declaration/spec/proof-block。最小可研究机制是：

> 历史 `invoke_lemma` action 只有在 exact saved state 上重放后独立重现 verifier improvement，并在 frozen repository 内 task-held-out validation states 上显示非有害 utility，才成为 retrieval-eligible；否则返回 `ABSTAIN`。

## Closest-Work Boundary

- RAG-Verus/KVerus：复用其 repository metadata、dependency/static lemma retrieval 思路。
- LeanDojo/ReProver：复用 accessibility/filtering discipline。
- Rango：承认 state-adaptive premise/proof retrieval 已存在。
- 本方案只研究 historical action attribution、held-out promotion 和 selective action-or-abstain。

## MVP Contract

- one frozen repository snapshot；
- one Verus/toolchain version；
- one error family；
- one action family：`invoke_lemma`；
- exact code snapshots + exact Verus diagnostics；
- single-edit verifier intervals；
- 10–20 reviewed operators and 10–20 held-out states only for feasibility/kill-gate evidence；
- no calibrated-risk or population-effect claim from this pilot；
- no cross-project claim。

## Observable State

```text
S = (
  error_family,
  diagnostic_span_AST,
  target_decl_signature,
  normalized_local_spec_shape,
  accessible_symbol_signatures,
  previous_error_delta
)
```

所有字段来自 code、diagnostic 和 symbol analysis；不声称恢复 SMT internal goal。

## Fidelity and Replay Gate

候选 transition 必须具有：

1. exact pre/post snapshot hashes；
2. exactly one successful proof-only edit；
3. bound pre/post Verus diagnostics；
4. no spec/exec/bypass change；
5. independent Lynette result；
6. replayed edit on immutable pre-state reproduces the target diagnostic improvement and safety result。

不满足者不进入 operator pool。

## Operator

```text
invoke_lemma(
  fully_qualified_name,
  formal_parameter_types,
  required_preconditions,
  argument_binding_pattern,
  expected_diagnostic_delta
)
```

冻结 LLM 只生成 argument bindings；symbol/type/mode/scope checker 必须全部通过。输出为 fixed JSON 和一条局部 suggestion，不注入历史 proof。

## Selective Retrieval

### Hard eligibility

```text
accessible
AND type_compatible
AND replay_valid
AND proof_only_safe
AND same_error_family
```

### Lexicographic ranking

```text
same diagnostic-span AST shape
> same local spec shape
> same required-symbol signature
> lower graph distance
> lower context cost
```

### Deterministic conservative abstention

MVP 只有在所有 hard gates 通过，且 candidate 在 task-disjoint validation states 上至少没有出现 safety regression、并出现一次 strict improvement 或稳定 target-error reduction 时才允许 retrieval；否则 `ABSTAIN`。

这只是 pilot promotion rule，不称为 statistical calibration。若 kill gate 通过，再按预先给定的 harmful-rate 上界和置信度计算所需 `D_skill_val` 样本。

## Utility Order

不使用 \(\lambda,\mu\)。候选比较按词典序：

1. **Safety constraint:** zero additional Lynette/spec/exec/bypass regression；
2. **Primary:** strict Verus+Lynette success；
3. **Secondary:** Expected Cost to Success；
4. **Diagnostic only:** target error delta、retrieval acceptance、context tokens。

## Evaluation

同一 frozen harness/model、paired seeds、相同 context budget：

- **A:** KVerus-like static lemma retrieval；
- **B:** static + raw state-matched historical lemma actions；
- **Method:** static + replay-validated selective lemma actions；
- **Control:** static + same-token shuffled lemma action。

Necessary ablations in the same matrix:

- remove replay gate；
- always retrieve instead of abstain。

Split only claims task-held-out transfer inside the frozen repository. Exact/near code、task identifier 和 reference proof 均隔离。每个 condition 使用预先冻结的重复次数；pilot 只决定是否值得扩大，不支持 population effect。

## Kill Gate

继续扩展必须满足：

1. replay success and harness fidelity complete；
2. method 在相同 budget 下优于 raw-transition arm 的 strict utility；
3. no safety regression；
4. no exact/near-task leakage；
5. remove-replay 或 always-retrieve 至少一个明显增加 harmful actions；
6. 结果不是仅由缩短失败轨迹造成。

若失败，停止扩展 action taxonomy，并将系统定位为 domain-specific Verus RAG engineering，而不是 validated skill learning。

## Implementation Sequence

1. Week 1: enumerate exact single-edit lemma transitions and replay them。
2. Week 2: implement typed binding、scope/type checks、lexicographic retrieval 和 abstention。
3. Weeks 3–4: run and audit the frozen paired pilot。
4. Only after GO: add assertion/trigger/invariant operators, larger validation, cross-family and cross-project abstractions。
