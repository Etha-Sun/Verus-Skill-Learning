# Research Proposal: Verifier-Grounded Transition Memory for Verus Agents

## Problem Anchor

- **Bottom-line problem:** 判断“从每个 Verus 文件提取 memory，再搭建一个高度 domain-specific 的 RAG”是否是好的 skill-system 设计，并给出不限于 embedding/vector search 的 Verus 检索方案。
- **Must-solve bottleneck:** 当前 agent 不是普遍缺少更多文本，而是在特定 proof state 下无法及时找到可访问、签名兼容、对当前 verifier obligation 真正有帮助的 lemma、proof pattern 或下一步动作；无选择地注入全局 memory 可能增加 token、误导编辑并引入 safety regression。
- **Non-goals:** 不把全文向量库本身包装成研究创新；不让检索器替代 Verus/Lynette；不在没有 leakage-safe live rerun 的情况下声称提高 solved rate 或 token efficiency；不立即加入 SFT/RL、多 agent 或复杂自进化。
- **Constraints:** 原始与 sealed 数据只读；新运行输出只写入 `VERUS_SKILL_RUN_ROOT`；禁止 exact-task/reference-proof leakage；R041 global H2 已给出负面定性信号；R042 frontier held-out evaluation 尚未完成；系统必须允许“不检索/不注入”。
- **Success condition:** 在 task/project-held-out live Verus repair 中，相对无 memory、文件摘要 RAG 和 embedding-only RAG，系统提高 strict Verus+Lynette success 或降低 Expected Cost to Success，且 unsafe edit rate 不增加；离线 premise/transition retrieval 指标只能作为诊断。

## Technical Gap

现有证据否定了一个朴素假设：把历史经验压成更多通用文字并不自动产生 skill。R041 的全局 trace-distilled H2 在三个 H0-frozen 案例上为 4/9，通过数低于 H0/H1 的 5/9，同时 token、wall time 和 safety 更差。失败路径显示，当前状态往往已经收缩到一个具体 obligation，例如“找到 bytes library lemma”或“完成 offset extensionality”，但全局摘要仍提供宽泛建议。

外部工作也使“Verus RAG”本身不再新颖。RAG-Verus 已研究 repository-level context retrieval；KVerus（ASE 2026）已组合 dependency-aware program analysis、semantic lemma indexing 和 error-driven refinement。LeanDojo/ReProver 进一步表明 formal retrieval 的关键不是纯语义相似，而是可访问 premise 与 hard negatives；Lean 的 graph-augmented premise selection 也显示 dependency relation 可提供额外信号。

因此缺口不是“缺少一个 Verus vector database”，而是：

1. 静态 repository knowledge 与动态 verifier transition 没有被清楚区分；
2. 检索单位常是文档/chunk，而不是带 precondition、expected observation、negative scope 和 verifier evidence 的操作；
3. 检索器通常优化相似度或 premise recall，而不是 live strict utility；
4. 系统缺少 abstention：没有高置信、可验证候选时仍向 prompt 塞入 memory；
5. 失败经验常被丢弃，无法检索“不要做什么”和“哪个方向会保持同一错误”。

## Candidate Routes

### Route A: Minimal typed hybrid retrieval

用 deterministic parsing、symbol/scope filtering、BM25、dependency-graph traversal 和 verifier-state matching 构建无训练 MVP。优点是可审计、实现小、能直接测试“文件摘要是否必要”；缺点是与 KVerus 的静态知识库部分高度接近，论文新颖性有限。

### Route B: Verifier-grounded transition memory

把历史轨迹分割为 `S_i -> A_i -> S_{i+1}`，候选 memory 是经过 held-out live validation 的 state-to-action operator，带 negative scope、预期 verifier delta 和 abstention。静态 repository retrieval 只负责提供可访问 premises；主要研究对象是“何时调用哪个 operator，以及何时不调用”。优点是直接响应本项目负结果并区别于纯静态 Verus RAG；风险是需要高保真 transition 数据和昂贵 live credit assignment。

### Choice

选择 Route B 作为方法主线，但先用 Route A 作为最小基础设施和强基线。不要把二者描述成两个平行贡献：静态 hybrid retrieval 是 substrate，validated transition retrieval 才是主贡献。

## Method Thesis

- **One-sentence thesis:** Verus skill memory 应当是一个以当前 verifier-grounded proof state 为 query、以可达 premises 和已验证 state-to-action transitions 为对象、能够检索负证据并主动 abstain 的 typed retrieval controller，而不是每文件一个自由文本摘要的向量库。
- **Why this is the smallest adequate intervention:** 它只改变知识的单位、检索协议和 promotion gate，不修改 base model、不训练新 generator、不重写 agent scaffold。
- **Why timely:** 直接建立在 formal premise retrieval、structured agent memory 和 repository-level Verus RAG 之上，同时利用 Verus 独有的 exact verifier delta 做 selection/credit signal。

## Contribution Focus

- **Dominant contribution:** verifier-grounded transition memory：从轨迹中抽取、验证并检索带 applicability/negative scope 的 `state -> action -> expected verifier transition` operator。
- **Supporting contribution:** 多通道、结构约束优先的 Verus retrieval substrate，用于提供可访问 lemma/project context。
- **Explicit non-contributions:** 新 embedding 模型；通用 GraphRAG；全文 memory extraction prompt；参数蒸馏；整个 self-evolving agent framework。

## Proposed Method

### Complexity Budget

- **Frozen/reused:** 原有 VeruSAGE/Codex agent loop、Verus、Lynette、trace schema、ATLAS failure taxonomy、现有 motif extractor。
- **New trainable components:** MVP 为 0；后续最多一个 utility reranker/router。
- **Intentionally excluded:** SFT/RL、multi-agent planner、learned graph encoder、自动修改 harness、全量 raw trace prompt injection。

### Memory Object Model

#### Layer 0: Canonical source facts

每个文件只生成结构化 `file card`，不把自由文本摘要当主要检索单元：

- repository/project/module/version/hash；
- imports、namespaces、visibility；
- functions/lemmas/types/traits 及签名；
- `requires`/`ensures`/invariants/decreases；
- spec/proof/exec mode；
- lemma calls、reveal/fuel、quantifier/trigger；
- verified status 和 Verus version。

真正进入检索的是 declaration、proof block、spec clause 和 dependency edge，而不是整份 file summary。

#### Layer 1: Static proof substrate

- vstd/API declarations and official examples/tests；
- current repository 的 lemma/spec/call/import graph；
- verified sibling proofs and project conventions；
- Verus versioned diagnostics/toolchain notes；
- proof motifs：quantifier、sequence/map/set、arithmetic/bitvector、induction、serialization、refinement、state machine、temporal/liveness。

#### Layer 2: Dynamic transition memory

每个 memory item：

```yaml
id: ...
preconditions:
  error_family: ...
  goal_signature: ...
  available_symbols: [...]
  motif: ...
action:
  kind: lemma_route | assertion_bridge | trigger | reveal | invariant | case_split
  ordered_steps: [...]
expected_observation:
  verifier_delta: ...
failure_indicators: [...]
negative_scope:
  forbidden_edits: [...]
  incompatible_signatures: [...]
evidence:
  source_transition_hashes: [...]
  heldout_validation: ...
utility:
  strict_solve_delta: ...
  expected_cost_delta: ...
  unsafe_delta: ...
version:
  verus: ...
```

只有 exact 或高置信 verifier-anchored transitions 可进入 validation；`narrative_only` 只能作为低信任候选来源。

### Runtime Query

查询不是一段用户问题 embedding，而是：

```text
Q_t = {
  current code slice + symbol table,
  failing obligation/error family/location,
  normalized goal/hypothesis signature,
  imports and accessible declarations,
  motif/project/version,
  previous actions and verifier deltas,
  remaining token/tool budget
}
```

### Candidate Generation: Beyond Embeddings

1. **Exact/symbol retrieval:** identifier、lemma 名、error span、compiler suggestion、namespace、type 名。
2. **Sparse lexical retrieval:** BM25/FTS over normalized verifier messages、signatures、docstrings、proof snippets；保留 Verus/Rust rare tokens。
3. **Scope/type filtering:** import visibility、declaration-before-use、proof/spec/exec mode、argument/return type、generic bounds、requires compatibility。
4. **Dependency graph retrieval:** import/call/lemma/spec/trait graph上的 k-hop、shortest path 或 personalized PageRank；从 current symbol 和 goal heads 出发。
5. **Structural matching:** AST/goal fingerprint、quantifier shape、trigger pattern、loop invariant form、sequence extensionality、opaque/reveal/fuel、bitvector/arithmetic operators。
6. **Motif/facet retrieval:** SQL/filter by project、motif、error family、Verus version、safety status、success tier。
7. **Transition-case retrieval:** 匹配 `(state signature, error family, action history)` 与历史成功/失败 transition；优先 error delta 相符的 cases。
8. **Negative retrieval:** 返回同签名下曾导致 unchanged error、unsafe edit、spec modification 或 obsolete API 的 anti-pattern。
9. **Optional semantic channel:** embedding/late-interaction 仅用于 lexical/structural channel recall 不足时补召回。
10. **Iterative retrieve-execute-refine:** 执行一个小动作后，以新 verifier state 重写 query；不一次检索整条 proof。

### Fusion, Reranking, and Abstention

初版使用可解释分数：

```text
score =
  exact_symbol
  + signature_compatibility
  + graph_proximity
  + error_family_match
  + motif_match
  + validated_transition_utility
  - version_mismatch
  - unsafe_or_negative_evidence
  - context_token_cost
```

先 hard-filter 不可访问/签名不兼容项，再做 reciprocal-rank fusion。Top candidates 由小型 LLM/cross-encoder 做 pairwise rerank 是可选后续，不应是 MVP 前置。

若没有候选同时满足可达性、兼容性、最低 evidence 和 token budget，返回 `ABSTAIN`。检索结果默认只注入一个 operator、最多若干必要 premise signatures；agent 可忽略建议并继续自由探索。

### Retrieval Timing

只在以下 decision points 触发：

- 首次 verifier failure 后需要定位 premise；
- 相同 normalized error 连续重复；
- error count 不变或出现回退；
- 当前 obligation 明确切换到新 motif；
- agent 主动请求 library/project context。

安全规则（禁止 bypass/spec edit）始终执行，但普通 skill 不做硬 gate。

### Writeback and Lifecycle

1. 新经验先进入 candidate buffer；
2. exact verifier state、patch、next diagnostics、Lynette 和 cost 完整时才可抽 operator；
3. 同来源任务只允许去重/合并，不作泛化证据；
4. 在 `D_skill_val` 上做 paired live rollout；
5. 只有 strict utility 非负、unsafe 不升且 negative scope 明确时 promotion；
6. 版本变更触发 revalidation 或降级；
7. failed/unsafe transition 写入 negative memory，不覆盖正 memory。

### Why This Is a Skill System Rather Than Plain RAG

普通 RAG 只回答“什么文本相似”；本系统还定义：

- skill 的 typed interface；
- applicability 和 negative scope；
- verifier-grounded promotion/demotion；
- runtime trigger 与 abstention；
- error-driven iterative use；
- version、cost、安全和 provenance lifecycle。

因此 RAG 是 skill selection/execution 的一个部件，不是 skill system 的完整定义。

## Failure Modes and Diagnostics

- **File summaries erase proof structure:** 对照 free-text file memory 与 declaration/graph index；若 summary 不增益则删除。
- **Exact-task leakage:** 按 normalized task/code/project family 去重，reference proof 不进入 query，报告 project-held-out。
- **Retrieval toxicity:** 必须有 no-retrieval arm、wrong-memory arm、negative-memory arm和 token budget sweep。
- **Static relevance but no actionability:** 分开报告 premise recall 与 live strict utility。
- **Graph hub bias:** 限制高出度通用节点，按 relation type 加权。
- **Version drift:** 所有 items 带 Verus/toolchain hash，过期项默认不注入。
- **Conflicting memories:** 保留正负 evidence 与适用域，不靠 LLM 自由合并。
- **Trace fidelity gaps:** exact/heuristic/narrative provenance 分层；只有 exact 可直接 promotion。

## Novelty and Elegance Argument

本方法不以“Verus + RAG”为 novelty，因为 RAG-Verus 和 KVerus 已覆盖该空间。可辩护的新颖点只可能是：把 verifier-anchored transition 作为 skill 单位，用 held-out paired rollouts 做 utility credit assignment，并让 negative scope/abstention 成为一等公民。静态 hybrid retrieval 是必须击败的 substrate，而不是论文主张。

## Claim-Driven Validation Sketch

### Claim 1: Structured hybrid retrieval is a better substrate than file-summary/vector RAG

- **Minimal experiment:** 从 held-out proof states 查询实际后续使用的 premise/operator。
- **Baselines:** no retrieval；raw neighboring files；free-text per-file memory + embedding；BM25-only；embedding-only；static hybrid。
- **Metrics:** accessible premise Recall@k/nDCG；invalid/inaccessible rate；context tokens；下一个 verifier delta。
- **Expected evidence:** hybrid 提高 accessible recall、减少无效候选；若只改善 offline recall 而 live 无效，则只保留为工程组件。

### Claim 2: Validated transition memory improves live repair without safety regression

- **Minimal experiment:** 在同一 frozen model/harness 上，对 project/task-held-out cases 做 paired repeated live runs。
- **Arms:** H0；static hybrid；static + unvalidated extracted memories；static + validated positive transitions；static + positive/negative transitions + abstention。
- **Metrics:** strict Verus+Lynette solve/Pass@k；Expected Cost to Success；tokens/wall/tool iterations；unsafe edits；retrieval acceptance；error-delta trajectory。
- **Expected evidence:** 完整方法相对 static hybrid 改善 strict utility；若增益来自 exact-task或只减少失败长度，则判失败。

### Claim 3: Abstention and negative scope prevent retrieval toxicity

- **Minimal experiment:** wrong-skill、out-of-domain、version-mismatch 和 tempting-bypass stress cases。
- **Ablations:** 去掉 abstention；去掉 negative memory；去掉 scope/type hard filters。
- **Metrics:** unsafe rate、regression rate、unnecessary context tokens、false retrieval rate。
- **Expected evidence:** 安全/回退显著减少，且正常 cases 的 solve 不下降。

## Experiment Handoff Inputs

- **Must-prove claims:** live strict utility，而非相似度；negative scope/abstention 的必要性。
- **Must-run ablations:** file summary vs declaration graph；embedding-only vs hybrid；static vs transition；positive-only vs positive+negative；always-retrieve vs abstain。
- **Critical splits:** `D_trace` / `D_skill_val` / `D_test`，再加 project-held-out 和 Verus-version split。
- **Highest-risk assumptions:** 高保真 transitions 足够；现有 parser 能恢复所需状态；validation 成本可接受；与 KVerus 的差异足够清楚。

## MVP Implementation Plan

1. 用 Lynette/verus-analyzer/轻量 parser 建 declaration table 和 import/call/lemma graph。
2. 用 SQLite FTS5/BM25 + graph adjacency + metadata filters 建 static retriever；不训练 embedding。
3. 从已有 exact verifier-anchored traces 建一个小型 transition registry，先人工审核 20-50 items。
4. 实现 query router、hard filters、fusion、token packer 和 `ABSTAIN`。
5. 先做 offline oracle-premise/next-transition evaluation；只有通过后做小型 live paired pilot。

## Compute & Timeline Estimate

- **GPU:** MVP index/query 为 0 GPU；可选 reranker 评估使用现有 API/模型。
- **Data/annotation:** 20-50 个 transition 人工或双重审核；静态代码只读解析。
- **Timeline:** 约 1 周完成 static MVP 和 offline harness，1 周完成 transition registry 与 live pilot；具体取决于 verifier-state fidelity 和 rerun budget。
