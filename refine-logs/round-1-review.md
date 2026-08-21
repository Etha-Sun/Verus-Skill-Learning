# Round 1 Review

<details>
<summary>Full independent reviewer response</summary>

## Senior Research Review

### Bottom line

方向有价值，但当前版本尚未形成足以支撑顶会论文的独立机制贡献。最强、也几乎唯一可辩护的研究点是：

> 从历史轨迹中构造“经反事实 replay 验证、可选择性 abstain 的 verifier-state-conditioned transition operators”。

其余静态 file card、scope/type filtering、dependency graph、semantic lemma retrieval、error-driven refinement、versioned knowledge、writeback，大部分已被 RAG-Verus、KVerus、LeanDojo/ReProver 和 graph premise selection 覆盖。若不把 transition 的抽取、因果验证、匹配与执行协议做实，这个方案会被评为“将合理的 Verus RAG 工程实践重新命名为 skill system”。

### Scores

| Dimension | Score | Assessment |
|---|---:|---|
| Problem Fidelity | 9/10 | 紧扣用户问题，并正确把核心瓶颈从“缺少文本”改为“当前 proof state 下缺少可用且有行动价值的知识”。 |
| Method Specificity | 6/10 | 数据结构和检索通道很具体，但真正的新机制——transition 的抽取、state 等价、credit assignment、operator 实例化和 abstention 校准——仍未定义到可实现程度。 |
| Contribution Quality | 5/10 | 静态 substrate 与最近工作高度重合；transition memory 的 schema 本身不构成机制创新，当前有明显 pseudo-novelty 风险。 |
| Frontier Leverage | 7/10 | verifier-as-critic、test-time retrieval/refinement、structured tool state 都用得自然；不需要强行加入 SFT/RL/GNN。 |
| Feasibility | 5/10 | 两周内完成 parser/graph、可靠 transition extraction、held-out live validation 和 promotion 明显低估工作量；现有轨迹 fidelity 也限制可用样本。 |
| Validation Focus | 6/10 | 指标方向正确，但三项 claim、十余个 baseline/ablation 已经形成实验扩张，且主因果对照尚不够清楚。 |
| Venue Readiness | 5/10 | 研究动机强，但与 KVerus 的机制边界尚不锐利，且没有主算法和初步 live evidence。 |

**OVERALL SCORE: 6.20/10**

**Verdict: REVISE**

不是 RETHINK：state-conditioned selective transition memory 是值得继续的方向。也远未到 READY：核心机制与最近工作的差异仍主要停留在 schema 和叙事层面。

### Closest-work overlap audit

KVerus 已具有 typed metadata dependency graph、signature/requires/ensures/module path、semantic lemma index、version-aligned toolchain knowledge、error triage、verifier-in-the-loop refinement 和 validated lemma writeback。RAG-Verus 已包括 code/informalization retrieval、function metadata、proof/spec/exec mode 与 dependency retrieval。LeanDojo/ReProver 已用 program analysis 确定 accessible premises 并构造 hard negatives。近期 Lean graph premise selection 已组合 text embeddings 与 heterogeneous dependency graph。

因此，真正可能区别最近工作的只能是：

1. 检索对象来自跨任务历史执行 transition，而不是静态 lemma/toolchain knowledge；
2. operator 在原状态上经过独立 replay 或 paired rollout，而非因一次轨迹成功就被收录；
3. router 优化 live utility，并提供校准过的 selective abstention；
4. operator 包含可执行 applicability boundary，而不仅是错误对应的提示。

### R041 H2 evidence correction

R041 只能证明当前特定 H2 prompt 是负面候选，并提示“是否、何时注入”比“压缩出更多全局建议”更值得测试。它不能证明 transition retrieval 有效，也不能证明 global memory 在正常 harness 下一般无效，因为样本只有三个诊断性选择案例，且 Qwen arm 存在 verifier-feedback availability confound。

### Required method fixes

将主算法缩为 single-edit replay-validated transition retrieval：

1. 状态只使用可观测 tuple：

   ```text
   S = (
     error_family,
     diagnostic_span_AST,
     target_decl_signature,
     local_spec_shape,
     accessible_symbol_signatures,
     previous_error_delta
   )
   ```

2. 第一版只接受一个 verifier interval 中恰有一个可恢复 edit 的 transition。
3. action 只允许可实例化 atomic template：`invoke_lemma`、`add_assertion`、`add_trigger`、`reveal` 或 `strengthen_invariant`。
4. 在保存的 pre-state 上重新应用 action，并独立运行 Verus/Lynette；只有 replay 重现预期 delta 才成为候选。
5. executor 只把 typed operator 翻译成一条局部建议，禁止自由拼接整段 historical proof。
6. 使用 lexicographic ranking，而不是未校准的任意线性权重。
7. 在 `D_skill_val` 上选择 abstention threshold，使 harmful-retrieval rate 的上置信界低于预设值。

把论文主张压缩为：

> Counterfactually replay-validated selective transition retrieval：历史动作只有在原状态重放后重现 verifier improvement，且在 held-out applicability states 上达到校准风险门槛时，才允许被检索和实例化。

删除 structured hybrid substrate 作为 supporting contribution、通用 GraphRAG 叙事、file-card extraction 的创新表述，以及“所有 failed transition 都是 negative skill”的表述。

### Feasibility fix

MVP 限制为一个 repository snapshot、一个 Verus version、一个 error family、两类 action、single-edit exact transitions、10–20 个审核 operator 和 10–20 个 task-held-out live states。第一周完成 fidelity gate/replay，第二周完成 retrieval/instantiation，随后一至两周完成 matched live pilot 和审计。

### Validation fix

保留两个验证块：

1. 主机制：KVerus-like static、static + raw historical transitions、static + replay-validated selective transitions、same-token shuffled control。
2. 必要性消融：去掉 replay validation、去掉 abstention。

主要指标只保留 strict Verus+Lynette success、Expected Cost to Success 与 unsafe regression。Premise Recall@k 仅作 diagnostic。

### Simplification Opportunities

1. 删除 structured hybrid retrieval 作为支持贡献。
2. 将 positive memory、negative memory 和 abstention 合并为一个 selective policy。
3. 首篇只覆盖一个 error family、两类 atomic action 和一个 toolchain snapshot。
4. 不先实现 embedding、cross-encoder、GNN 或 utility reranker。

### Modernization Opportunities

不需要额外 SFT、RL、multi-agent 或 learned graph encoder。冻结 LLM 充当 typed operator instantiator，Verus/Lynette 充当 executable critic，retrieval controller 充当 selective test-time policy。

### Drift Warning

NONE.

### Final verdict

**REVISE**

最小闭环：

```text
exact single-edit transition
→ replay reproduces verifier delta
→ abstract atomic operator
→ state-compatible instantiation
→ calibrated retrieve-or-abstain
→ project/task-held-out paired live utility
```

</details>
