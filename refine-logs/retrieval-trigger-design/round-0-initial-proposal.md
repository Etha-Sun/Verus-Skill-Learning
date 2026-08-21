# Verus Memory Index, Retrieval Trigger, and Card Design: Initial Proposal

## 1. Problem Anchor

- **Bottom-line problem:** 为 Verus proof-repair agent 设计一个可审计的 domain-specific memory system，明确怎么建索引、什么时候搜索、什么时候注入、如何测量和减少召回损失，以及 memory card 的机器表示。
- **Must-solve bottleneck:** 当前系统既可能在需要现有 lemma、Verus 规则或历史 proof transition 时没有查 memory，也可能把无关的 global guidance 注入简单任务。前者是 recall failure，后者是 context toxicity。单独优化向量相似度无法解决 trigger miss、scope/type incompatibility、stale version 和 agent 不使用结果。
- **Non-goals:** 不承诺绝对 100% recall；不把 file summary 当主检索单元；不把所有 verifier failure 都解释为缺知识；不让 memory 绕过 Verus/Lynette；不在无 live held-out 证据时声称提高 solved rate 或 token efficiency。

## 2. Evidence-Grounded Normal Failure Patterns

### 2.1 Infrastructure and state failures: do not trigger proof memory

1. Verus command unavailable, permission denied, transport timeout, missing candidate.
2. Diagnostic belongs to a stale candidate hash or wrong revision.
3. Tool output is truncated, misparsed, or only exposes pass/fail without full diagnostics.
4. Context/state handoff loses source constraints or previous verifier progress.

These failures route to `HARNESS_RECOVERY`, not to lemma/proof memory. Local
R041 failure-path evidence shows that missing interactive Verus feedback was a
first-order confound: high-level proof insight did not compensate for an
unavailable verifier loop.

### 2.2 Knowledge-addressable proof failures

1. **Symbol/API gap:** unknown or hallucinated symbol; wrong namespace,
   visibility, arity, type, mode, generic bound, or precondition.
2. **Postcondition/assertion bridge gap:** target fact is named but the
   intermediate logical bridge is missing.
3. **Quantifier gap:** missing forall/exists instantiation, witness, or usable
   trigger term.
4. **Case split gap:** enum/transition/option/structural branch is missing.
5. **Loop gap:** invariant is not initially true, not preserved, or too weak
   for exit; required function precondition was not copied into an isolated
   loop invariant.
6. **Bounded arithmetic gap:** machine integer overflow/underflow, casts,
   bit-vector vs mathematical integer interpretation, nonlinear arithmetic.
7. **Opacity/recursion gap:** closed spec function, missing `reveal`, wrong
   fuel, missing decreases argument, or mismatched induction scheme.
8. **Extensionality/representation gap:** sequence/set/map equality,
   serialization/view/refinement bridge, index-offset correspondence.
9. **Invariant/liveness gap:** state transition preservation, omitted changed
   component, fairness or recurrence premise.
10. **SMT resource gap:** rlimit/timeout caused by quantifier explosion or a
    proof surface that should be decomposed, after infrastructure is known to
    work.

### 2.3 Behavioral failures: trigger recovery or negative memory

1. Same normalized diagnostic and same proof-shape action recur twice without
   reducing the target-error frontier.
2. New errors exceed removed errors, or a previously verified obligation
   regresses.
3. The candidate introduces `assume`, `admit`, `external_body`, `axiom`,
   specification weakening, executable-code changes, or an illegal helper.
4. Agent reports success while Verus/Lynette evidence disagrees.
5. Agent keeps searching for nonexistent APIs despite compiler suggestions or
   exact symbol evidence.

## 3. Index Architecture

### 3.1 Canonical store

Use one typed canonical store, initially SQLite, with immutable source
provenance and content hashes. JSONL is the portable interchange format.
Markdown is only a rendered human view.

Core entities:

```text
artifact(
  artifact_id, artifact_type, repo_id, commit_sha, verus_version,
  source_path, source_span, content_hash, safety_status, provenance
)

symbol(
  symbol_id, fq_name, short_name, kind, mode, visibility,
  parameter_types, return_type, requires_shape, ensures_shape,
  module_path, artifact_id
)

edge(
  src_symbol_id, edge_type, dst_symbol_id
)

state_signature(
  state_id, candidate_hash, diagnostic_family, diagnostic_code,
  diagnostic_span_fingerprint, target_decl_fingerprint,
  local_spec_fingerprint, motif_set, previous_error_delta
)

memory_card(
  card_id, card_type, version, status, parent_ids,
  trigger_json, applicability_json, action_json, effect_json,
  negative_scope_json, evidence_json, utility_json
)
```

### 3.2 Retrieval views

Every artifact/card is projected into multiple indexes:

1. **Exact symbol index:** fully-qualified/short names, compiler suggestions,
   signature tokens and diagnostic identifiers.
2. **Sparse lexical index:** SQLite FTS5/BM25 over names, requires/ensures,
   comments, normalized diagnostics, aliases and card trigger text.
3. **Typed dependency graph:** import/call/spec/lemma/trait/type edges with
   directed and bounded reverse traversal.
4. **Structural fingerprint index:** normalized AST/spec/diagnostic-span
   shapes; identifiers alpha-normalized except rare domain anchors.
5. **Verifier-transition index:** pre-state signature plus action family to
   replay-validated diagnostic delta.
6. **Facet/bitmap index:** repository, commit, Verus version, module,
   visibility, proof/spec/exec mode, error family, motif, safety and status.
7. **Optional dense/late-interaction index:** semantic expansion channel only;
   it cannot override accessibility, type, version or safety gates.

The file is the ingestion/invalidation boundary. Retrieval units are symbol,
spec block, proof block, dependency edge, verifier transition and memory card.

### 3.3 Candidate generation and ranking

```text
query state
  -> high-recall union from exact + FTS + graph + structure + transition
  -> hard validity gates
  -> family-specific ranking
  -> diversity/contribution selection
  -> zero-to-three injected cards
```

Hard gates:

```text
repository/version valid
AND symbol accessible
AND mode/type/arity compatible
AND safety status allowed
AND card status active or shadow
AND negative scope not matched
```

Ranking should be lexicographic in the MVP:

1. exact diagnostic/error family;
2. exact or unifiable target/spec shape;
3. required symbol/signature overlap;
4. dependency-graph distance;
5. replay evidence and held-out non-harm;
6. lower prompt cost.

Do not start with one opaque weighted score. Log every channel rank and every
filter reason so false negatives can be attributed.

## 4. Search Trigger and Injection Gate

### 4.1 Separate two decisions

`SEARCH` means cheaply produce and log a candidate pool. `INJECT` means spend
context budget and steer the agent. Search should favor recall; injection
should favor precision and safety.

### 4.2 Mandatory state machine

```text
G0 HARNESS_GATE
  if no candidate-hash-bound complete Verus diagnostic:
      HARNESS_RECOVERY

G1 INITIAL_STATIC_LOOKUP
  exact symbols + dependency context for target declaration
  no strategy card unless a specific state trigger matches

T1 FIRST_SEMANTIC_FAILURE
  search diagnostic-family, span, target spec, accessible premise channels

T2 SYMBOL_FAILURE
  search exact/alias/signature/compiler-suggestion channels immediately

T3 ERROR_FAMILY_TRANSITION
  re-query when normalized error family or target span changes

T4 PLATEAU
  re-query recovery and anti-pattern cards after two equivalent diagnostics
  with no target-frontier reduction

T5 REGRESSION_OR_UNSAFE
  suppress positive strategy cards; inject rollback/safety card

T6 MANUAL_REQUEST
  agent may request a typed search with stated missing information
```

### 4.3 Trigger alternatives

#### A. Always retrieve at every verifier step

- Highest trigger recall and easiest baseline.
- Expensive and likely to inject irrelevant memory unless search/injection are
  separated.

#### B. Deterministic event/FSM rules

- Observable, versionable and auditable; best MVP.
- Can over-trigger and needs explicit normalization of equivalent diagnostics.

#### C. Agent self-trigger

- Agent calls `memory.search` when it believes it lacks a lemma, API or proof
  pattern.
- Cheap to add, but trigger recall is not reliable because a model often does
  not know which knowledge it lacks.

#### D. Learned value-of-retrieval router

- Predicts marginal benefit of search/injection from proof-state features.
- Labels require paired no-memory/retrieval or oracle-retrieval outcomes;
  false-negative and threshold-transfer risks make it unsuitable as the only
  gate initially.

#### E. Hybrid router

- Mandatory deterministic triggers for first semantic error, symbol failure,
  plateau, error-family transition and safety regression.
- Optional agent request and learned router for additional retrieval.
- Recommended target architecture.

## 5. Recall Contract

Absolute recall cannot be guaranteed. The system instead measures a recall
funnel:

```text
R0 card/index coverage
R1 trigger recall
R2 query-construction recall
R3 candidate-union Recall@K
R4 post-filter valid Recall@K
R5 reranked Recall@K/MRR
R6 injection recall
R7 agent-use recall
```

For a replayable successful historical transition, define the oracle as the
smallest card/premise/action required to reproduce its verifier improvement.
Each evaluation state records where that oracle was lost.

### 5.1 Offline evaluation

- task-disjoint and near-code-disjoint replay states;
- `coverage`: oracle card exists and is valid for the frozen version;
- trigger recall and false-trigger rate;
- per-channel and union Recall@1/5/20/50 before filters;
- false-negative filter audit by filter reason;
- MRR/nDCG after ranking;
- injection rate, cards and tokens injected;
- alpha-renamed identifier, diagnostic-wording and version perturbations;
- hard-negative sets: lexically similar but inaccessible, wrong direction,
  unmet preconditions, stale version, or historically harmful cards.

### 5.2 Live evaluation

- strict Verus + Lynette success;
- Expected Cost to Success;
- unsafe/regression rate;
- harmful retrieval rate versus matched H0;
- realized search/injection rate and latency;
- oracle-retrieval upper bound and no-retrieval lower bound.

The primary recall target for the MVP is the pre-filter candidate union. Use
large cheap K there, then let typed validity gates and a small injection budget
control precision.

## 6. Memory Card Format

### 6.1 Storage decision

- Canonical: validated JSON conforming to a versioned JSON Schema.
- Bulk transport: JSONL, one card per line.
- Human review: deterministic Markdown rendering from the canonical JSON.
- Never use Markdown-only cards as the source of truth.

### 6.2 Shared header plus typed payload

```json
{
  "schema_version": "0.1",
  "card_id": "verus.transition.invoke_lemma.8byte_prefix.v1",
  "card_type": "transition",
  "version": 1,
  "status": "shadow",
  "parents": [],
  "scope": {
    "repo_id": "frozen-repo",
    "commit_sha": "<sha>",
    "verus_version": "0.2025.07.12.0b6f3cb"
  },
  "trigger": {
    "error_families": ["assertion_failure", "postcondition_failure"],
    "motifs": ["serialization", "sequence_extensionality"],
    "diagnostic_span_shapes": ["eq(serialized(x),serialized(y))"],
    "required_symbols": ["spec_u64_to_le_bytes"],
    "progress": {"max_equivalent_failures": 2}
  },
  "applicability": {
    "modes": ["proof"],
    "required_facts": ["serialized_x_eq_serialized_y"],
    "forbidden_matches": ["spec_edit", "exec_edit"]
  },
  "retrieval_views": {
    "exact_terms": ["lemma_auto_spec_u64_to_from_le_bytes"],
    "lexical_aliases": ["8-byte prefix", "length prefix", "offset extensionality"],
    "graph_anchors": ["spec_u64_to_le_bytes"],
    "structural_fingerprints": ["seq_extensionality_with_fixed_prefix"]
  },
  "action": {
    "kind": "invoke_lemma_then_extensionality",
    "template": [
      "invoke an accessible byte-conversion lemma with type-checked arguments",
      "prove payload equality pointwise at fixed_offset + i"
    ]
  },
  "expected_effect": {
    "remove_error_families": ["assertion_failure"],
    "next_state": "payload_extensionality_only"
  },
  "negative_scope": [
    "Do not invent an external_body helper.",
    "Do not change requires, ensures, or executable code."
  ],
  "evidence": {
    "source_run_ids": ["<run-id>"],
    "pre_state_hashes": ["<hash>"],
    "replay_status": "pending",
    "lynette_status": "pass"
  },
  "utility": {
    "strict_success": {"success": 0, "failure": 0},
    "target_error_reduction": {"success": 1, "failure": 0},
    "matched_token_delta": null
  },
  "lifecycle": {
    "created_at": "2026-08-05T14:00:32-05:00",
    "last_validated_at": null,
    "superseded_by": null
  }
}
```

### 6.3 Card types

Use a typed union, not one free-text card:

1. `premise`: existing lemma/API fact, signature, requirements and direction.
2. `transition`: proof-state trigger, action and expected diagnostic delta.
3. `anti_pattern`: observed harmful action, matched state and recovery.
4. `repository_convention`: project-local proof idiom or representation bridge.
5. `toolchain`: version-specific syntax, diagnostic and official guidance.

## 7. Recommended MVP

1. Freeze one repository, commit, Verus version and one error family.
2. Build SQLite canonical store plus exact, FTS5, graph and structural
   indexes; omit dense retrieval initially.
3. Extract only exact, replayable single-edit lemma transitions.
4. Implement deterministic FSM triggers and separate search/injection logs.
5. Evaluate H0, always-search/no-injection, FSM retrieval, always-inject and
   oracle retrieval on task-disjoint states.
6. Require full recall-funnel attribution before tuning ranking weights.

## 8. Open Design Decisions for Review

1. Should initial static lookup inject accessible dependency summaries before
   the first verifier failure, or only make them available as tool results?
2. Is plateau defined by two equal normalized diagnostics, or by no reduction
   in a dependency-aware error frontier?
3. Should anti-pattern cards bypass the normal top-k and be mandatory when a
   forbidden diff is detected?
4. Is JSON Schema plus SQLite sufficient for the first implementation, or is
   a dedicated graph database justified at the anticipated repository scale?
