# Round 1 Refinement

## Problem Anchor

- **Bottom-line problem:** 判断“从每个 Verus 文件提取 memory，再搭建一个高度 domain-specific 的 RAG”是否是好的 skill-system 设计，并给出不限于 embedding/vector search 的 Verus 检索方案。
- **Must-solve bottleneck:** 当前 agent 不是普遍缺少更多文本，而是在特定 proof state 下无法及时找到可访问、签名兼容、对当前 verifier obligation 真正有帮助的 lemma、proof pattern 或下一步动作；无选择地注入全局 memory 可能增加 token、误导编辑并引入 safety regression。
- **Non-goals:** 不把全文向量库本身包装成研究创新；不让检索器替代 Verus/Lynette；不在没有 leakage-safe live rerun 的情况下声称提高 solved rate 或 token efficiency；不立即加入 SFT/RL、多 agent 或复杂自进化。
- **Constraints:** 原始与 sealed 数据只读；新运行输出只写入 `VERUS_SKILL_RUN_ROOT`；禁止 exact-task/reference-proof leakage；R041 global H2 已给出负面定性信号；R042 frontier held-out evaluation 尚未完成；系统必须允许“不检索/不注入”。
- **Success condition:** 在 task/project-held-out live Verus repair 中，相对无 memory、文件摘要 RAG 和 embedding-only RAG，系统提高 strict Verus+Lynette success 或降低 Expected Cost to Success，且 unsafe edit rate 不增加；离线 premise/transition retrieval 指标只能作为诊断。

## Anchor Check

- **Original bottleneck:** 当前 state 下缺少行动相关、可访问且安全的 Verus knowledge，不是一般性上下文不足。
- **Why preserved:** revised method 直接决定哪个历史 atomic action 能在当前 state 被安全实例化，以及何时 abstain。
- **Rejected drift:** 不把目标改成建立最全的 Verus knowledge graph、训练最强 embedding、或重做通用 RAG benchmark。

## Simplicity Check

- **Dominant contribution:** counterfactually replay-validated selective transition retrieval。
- **Components removed or demoted:** file card、BM25、dependency graph、versioned knowledge 全部降为复用 substrate/baseline；删除支持性贡献。
- **Rejected complexity:** GNN、cross-encoder、RL、SFT、多 agent、全 motif/action ontology。
- **Smallest adequate route:** 一个 error family、两类 atomic action、exact single-edit transitions、deterministic ranking 和 risk-calibrated abstention。

## Changes Made

### 1. Made transition extraction executable

- **Reviewer said:** schema 没有定义 state equivalence、credit assignment、operator abstraction 和 instantiation。
- **Action:** 限制为可恢复 pre/post state 的 exact single-edit interval；定义 observable state tuple、atomic actions 和 replay gate。
- **Impact:** 只有可独立重放并重现 verifier delta 的动作才进入 memory。

### 2. Removed pseudo-novel static retrieval claims

- **Reviewer said:** KVerus/RAG-Verus/LeanDojo 已覆盖大部分 static substrate。
- **Action:** static retrieval 只作为 KVerus-like baseline；论文主张只围绕 replay validation + calibrated selectivity。
- **Impact:** novelty boundary 更清楚。

### 3. Reduced validation and timeline

- **Reviewer said:** 三个 claims 和大量 baseline 造成 expansion，时间估计过于乐观。
- **Action:** 只保留一个主机制实验和一个必要性消融；MVP 限制为 10–20 operators/states。
- **Impact:** 形成可执行 kill gate。

## Revised Proposal

# Research Proposal: Replay-Validated Selective Transition Retrieval for Verus

## Problem Anchor

- **Bottom-line problem:** 判断“从每个 Verus 文件提取 memory，再搭建一个高度 domain-specific 的 RAG”是否是好的 skill-system 设计，并给出不限于 embedding/vector search 的 Verus 检索方案。
- **Must-solve bottleneck:** 当前 agent 不是普遍缺少更多文本，而是在特定 proof state 下无法及时找到可访问、签名兼容、对当前 verifier obligation 真正有帮助的 lemma、proof pattern 或下一步动作；无选择地注入全局 memory 可能增加 token、误导编辑并引入 safety regression。
- **Non-goals:** 不把全文向量库本身包装成研究创新；不让检索器替代 Verus/Lynette；不在没有 leakage-safe live rerun 的情况下声称提高 solved rate 或 token efficiency；不立即加入 SFT/RL、多 agent 或复杂自进化。
- **Constraints:** 原始与 sealed 数据只读；新运行输出只写入 `VERUS_SKILL_RUN_ROOT`；禁止 exact-task/reference-proof leakage；R041 global H2 已给出负面定性信号；R042 frontier held-out evaluation 尚未完成；系统必须允许“不检索/不注入”。
- **Success condition:** 在 task/project-held-out live Verus repair 中，相对无 memory、文件摘要 RAG 和 embedding-only RAG，系统提高 strict Verus+Lynette success 或降低 Expected Cost to Success，且 unsafe edit rate 不增加；离线 premise/transition retrieval 指标只能作为诊断。

## Technical Gap

作为工程方案，Verus-specific hybrid retrieval 是合理且已有强先例；作为研究贡献，它已被 RAG-Verus、KVerus、Rango、LeanDojo/ReProver 和 graph premise selection 大量覆盖。现有空白更窄：

> 历史 repair action 是否只有在原状态重放后确实重现 verifier improvement、并在 held-out applicability states 上满足风险门槛时，才应成为可检索 skill？

R041 H2 只提供一个动机性负信号：当前全局 distilled prompt 在三个诊断案例上未显示改善并带来成本/安全回退，且存在 verifier-access confound。它不能证明 memory 一般无效；它提示 retrieve-or-abstain 值得被直接测试。

## Method Thesis

**Counterfactually replay-validated selective transition retrieval:** 历史动作只有在 exact pre-state 上独立重放并重现 verifier delta，且在独立 validation states 上达到 harmful-retrieval 风险门槛时，才允许被检索、实例化或触发；否则 router 返回 `ABSTAIN`。

## Contribution Focus

- **Only claimed mechanism:** replay validation + selective applicability/abstention over atomic verifier transitions。
- **Reused substrate:** KVerus-like symbol/dependency metadata、FTS/BM25、current repository/vstd lemma records。
- **Not claimed:** file summary、hybrid retrieval、dependency graph、version awareness、verifier loop 或 knowledge writeback 本身。

## MVP Scope

- 一个 repository snapshot；
- 一个 Verus/toolchain version；
- 一个 error family，例如 failed assertion 或 missing/applicable lemma；
- 两类 action：`invoke_lemma` 与 `add_assertion`；
- 只接受 exact code states、exact verifier output、single successful edit；
- 10–20 个经过人工审核的 operators；
- 10–20 个 task-held-out live states；
- 不训练 embedding/reranker/GNN。

## Observable State

不声称获得 Verus 未公开的 SMT proof goal。状态只由可观测字段构成：

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

Normalization 只做 alpha-renaming、literal bucketing 和 syntax-preserving canonicalization；不得删除 type、mode、quantifier 或 operator 信息。

## Transition Fidelity Gate

从 verifier-anchored interval 提取 `(S_i, edit, S_{i+1})`。候选必须满足：

1. pre/post code snapshot hash 可恢复；
2. interval 内恰有一个成功 edit；
3. edit 只修改 proof-only 区域；
4. pre/post Verus diagnostics 与相应 code hash 绑定；
5. Lynette 可独立运行；
6. 不含 bypass/spec/exec 修改；
7. 在保存的 pre-state 重放 edit 后，Verus/Lynette 重现原结果。

multi-edit、zero-edit、summary-only、narrative-only 和 unverified-tail 全部排除。

## Atomic Operator Extraction

第一版只允许：

```text
invoke_lemma(
  fully_qualified_name,
  formal_parameter_types,
  required_preconditions,
  argument_binding_pattern
)

add_assertion(
  normalized_expression_AST,
  required_local_facts,
  insertion_region
)
```

LLM 只充当 typed operator instantiator：根据当前 accessible symbols 产生 bindings。随后做静态检查：

- symbol 可访问；
- proof/spec/exec mode 合法；
- arity/type/generic bounds 兼容；
- required preconditions 可由当前 local facts 表达；
- insertion region 位于 proof-only 区域。

输出固定 JSON；executor 只把该对象翻译成一条局部建议或补丁候选，不注入历史全文。

## Replay Validation

对来源 transition：

1. 在 immutable pre-state 重放抽取出的 atomic operator；
2. 独立运行 Verus；
3. 独立运行 Lynette；
4. 比较 normalized diagnostic multiset、target error 和安全状态；
5. 只有 action 单独重现预期 improvement 才标记 `replay_valid=true`。

这不是完整因果证明，但它排除了 multi-edit credit 混淆和“成功轨迹中无关动作”。

## Retrieval and Abstention

static substrate 先提供 accessible candidates。transition router 只用 lexicographic ranking：

```text
hard gate:
  accessible AND type_compatible AND replay_valid AND safe
rank:
  same error family
  > same diagnostic-span AST shape
  > same local spec shape
  > same required-symbol signature
  > lower context/action token cost
```

不使用未校准的加权总分。

在 `D_skill_val` 上对候选 applicability 做 paired rollout，得到 signed utility evidence：

```text
utility = strict_success_delta
          - lambda * cost_delta
          - mu * unsafe_delta
```

选择 threshold，使 harmful retrieval rate 的预设置信上界低于 `alpha`。样本不足、兼容性失败或 threshold 未通过时返回 `ABSTAIN`。

## Why This Is More Than File-Level RAG

文件仍可作为 ingestion boundary，但不是 retrieval unit。static facts 至少拆为 declaration/spec/proof block。skill 则是经过 replay 的 atomic transition operator。完整 skill system 还包括：

- applicability interface；
- executable validation；
- signed utility evidence；
- retrieve-or-abstain policy；
- provenance、version 和 safety lifecycle。

如果不实现这些机制，“每文件 memory + vector RAG”应被定位为有用工程基线，而不是 skill learning。

## Validation

### Block 1: Main mechanism

- **A:** KVerus-like static retrieval。
- **B:** static + raw state-matched historical transitions。
- **Method:** static + replay-validated selective transitions。
- **Control:** static + same-token shuffled operator。
- **Split:** source task/project family 与 test 隔离；reference proof 永不可见。
- **Primary metrics:** strict Verus+Lynette success；Expected Cost to Success；unsafe regression。
- **Secondary diagnostics:** retrieved operator execution rate、target error delta、context tokens。

### Block 2: Necessity

在同一 paired live matrix 中：

- remove replay validation；
- always retrieve（remove abstention）。

不另起新的 claim；premise Recall@k 只作为 appendix diagnostic。

`ECTS` 预先冻结为有限预算内所有 matched attempts 的总成本除以 strict successes；若 zero success，报告预算上界和 failure rate，不用无穷值隐藏结果。

## Kill Gate

只有同时满足以下条件才扩大范围：

1. static + raw transitions 不优于或明显弱于 method；
2. method 在相同 context/token budget 下改善 strict utility；
3. 增益不来自 exact-task/template leakage；
4. 去掉 replay validation 后 harmful retrieval 增加；
5. 去掉 abstention 后 unsafe/regression 增加；
6. verifier/tool access 与 harness fidelity 全部通过。

若失败，停止扩展 memory taxonomy，把结果定位为 Verus RAG engineering/negative analysis。

## Timeline

- **Week 1:** fidelity gate、single-edit extraction、replay harness。
- **Week 2:** atomic abstraction、typed instantiation、static compatibility checks。
- **Weeks 3–4:** matched live pilot、audit 和 kill decision。

跨 error family、project 和 Verus version 只在 kill gate 通过后进行。
