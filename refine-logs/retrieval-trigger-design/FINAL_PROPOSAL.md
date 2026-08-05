# Verus Memory Index, Trigger, Recall, and Card Design

## Executive Decision

The recommended design is not “one summary per file plus vector search.”

Use a file as the ingestion and invalidation boundary, but index:

- declarations and typed signatures;
- requires/ensures/invariants and proof blocks;
- import/call/spec/lemma/type/trait dependency edges;
- normalized verifier states;
- replay-certified proof transitions.

For the research MVP, search a frozen bank of train-derived
`invoke_lemma` transition cards invisibly after every valid Verus checkpoint.
A separate deterministic policy injects at most one validation-promoted card
or abstains. This separation makes trigger recall measurable without forcing
irrelevant memory into the agent context.

## 1. Failure Patterns and Routing

### 1.1 Do not search proof memory

Route to `HARNESS_INVALID` when:

- Verus cannot be invoked, permission is denied, or transport fails;
- the diagnostic is incomplete or does not match the current candidate hash;
- a candidate is missing;
- tool output is stale, misparsed or belongs to another revision.

Local R041 evidence makes this gate mandatory: all nine Qwen closest-failure
logs had denied interactive Verus calls, while the successful Codex path used
iterative compiler/verifier feedback. Missing feedback is not missing proof
knowledge.

### 1.2 Treat resource symptoms separately

A hash-bound Verus `rlimit`/timeout is initially
`VERIFIER_RESOURCE_SYMPTOM`, not a semantic knowledge gap. Use a bounded,
predeclared same-code probe or quantifier-profiler run. Only a reproducible
quantifier/proof-complexity diagnosis may later query decomposition memory.
Resource handling is outside the first lemma-transition MVP.

### 1.3 Knowledge-addressable semantic failures

Useful facets, grounded in the local ATLAS taxonomy and official Verus
guidance, are:

| Observable family | Typical missing knowledge | Primary retrieval target |
|---|---|---|
| Unknown symbol, wrong namespace, arity/type/mode mismatch | Real accessible API or lemma | Exact symbol, signature, compiler suggestion, dependency neighbors |
| Precondition failure | Callee contract or bridge needed to establish `requires` | Lemma signature/spec and prerequisite graph |
| Assertion/postcondition failure | Missing intermediate bridge | State-matched lemma transition and nearby verified premise |
| Quantifier/trigger failure | Missing instantiation, witness, or matching term | Trigger guidance plus same-shape verified transitions |
| Case-analysis gap | Missing enum/transition/option branch | Sibling proof shapes and transition cases |
| Loop failure | Invariant establishment, preservation, or exit fact | Loop-specific contracts and invariant transitions |
| Overflow/cast/bit-vector failure | Machine vs mathematical arithmetic mismatch | Type-specific arithmetic facts and official tool guidance |
| Opaque/fuel/recursive failure | Reveal, fuel, decreases, or induction scheme | Accessible reveal/recursive lemmas and versioned guidance |
| Seq/Set/Map or serialization equality | Extensionality or representation bridge | Extensionality lemmas, offset/index bridge transitions |
| State invariant/liveness | Changed-component preservation or fairness premise | Invariant dependencies and state-machine proof transitions |

The 30-task Qwen calibration is not a population sample, but its first-run
final candidates illustrate the routing need: 7 passed and 23 failed; among
the mechanically readable primary final errors were nine postcondition
failures, three assertion failures, syntax errors, a trigger-coverage error,
and a trait-contract violation. Six failures had no usable primary final error,
mostly reflecting timeout/missing-result conditions that must not be pooled
with semantic failures.

### 1.4 Behavioral recovery events

Track these independently of semantic family:

```text
NO_OP
UNCHANGED_CANDIDATE
STATE_FINGERPRINT_CHANGED
FRONTIER_STRICTLY_IMPROVED
FRONTIER_REGRESSED
UNSAFE_DIFF
REPEATED_EQUIVALENT_STATE
```

`NO_OP`, an unchanged candidate, a new full state fingerprint, or two
equivalent failures are injection/requery signals. Regression or unsafe edits
force rollback and abstention. Safety cannot depend on retrieving a negative
card.

## 2. Concrete Index

### 2.1 Canonical SQLite store

```text
symbols
  fq_name, kind, proof/spec/exec mode, visibility,
  typed signature, requires, ensures, module, source hash, version

dependencies
  src_symbol_id, edge_type, dst_symbol_id

transitions
  pre/post state, added invoke_lemma action,
  full diagnostic frontier delta, source replay, Lynette result

cards
  minimal transition-card payload and activation status

card_symbol_projection
  card_id, lemma_symbol_id

card_state_projection
  card_id, error_family, normalized target/spec/diagnostic shapes
```

SQLite + FTS5 + adjacency tables are enough for the MVP. A graph database is
not justified.

### 2.2 Query state

```text
Q = (
  repo, commit, Verus version, candidate hash,
  target declaration and mode,
  normalized diagnostic family and AST span,
  normalized requires/ensures/invariant shape,
  accessible symbol signatures,
  previous action,
  pre/post diagnostic frontier delta,
  repeat/no-op/regression flags
)
```

Verus does not expose a Coq-like complete proof state. This is an observable,
hash-bound approximation; it must not be described as the internal SMT goal.

### 2.3 Candidate channels

First implementation:

1. exact name/signature/compiler-suggestion lookup;
2. FTS5/BM25 over card projections, lemma signatures/specifications and
   normalized diagnostics;
3. analyzer-derived accessible dependency traversal.

Each channel must return `card_id`, not merely a symbol. Exact or graph symbol
hits are joined through `card_symbol_projection`. Log substrate hits,
projected card IDs, channel ranks and projection reasons.

Use fixed quotas per channel, union and deduplicate. Exact hits occupy the
highest priority bucket; lower buckets may use fixed reciprocal-rank fusion.
Do not narrow the pool through a single dense top-k before exact and graph
channels run.

Later, only after the kill gate:

- structural AST/spec fingerprints;
- dense or late-interaction retrieval;
- additional premise/toolchain/anti-pattern card types;
- learned ranking or routing.

## 3. How Recall Is Protected and Measured

### 3.1 What can be guaranteed

For a frozen repository snapshot, tests can guarantee:

- every analyzer-resolved declaration is represented exactly once;
- every extracted explicit dependency edge round-trips;
- every card has valid source hashes, replay evidence and index projections;
- stale commit/version records are not silently current.

There is no absolute guarantee that every useful proof idea exists in memory
or is semantically retrievable. That requires empirical evaluation.

### 3.2 Avoid filter false negatives

Every filter returns:

```text
VALID | INVALID | UNKNOWN
```

Reject only mechanically proven `INVALID` candidates. Associated types,
generics, aliases, unresolved coercions and currently unproved preconditions
often produce `UNKNOWN`, not `INVALID`.

`UNKNOWN` candidates remain visible in search/filter recall audits but are not
injectable in the MVP. Injection requires a mechanically type-checked binding
and resolved structural anchor.

Split:

- `exclusion_conditions`: machine predicates making a card inapplicable;
- `safety_constraints`: globally forbidden edits if the card is used.

Report per-filter oracle loss and leave-one-filter-out rescue.

### 3.3 Leakage-safe oracle

Freeze near-code-disjoint `D_train`, `D_val`, and `D_eval`.

```text
B_train
  cards extracted only from D_train

O_train(s)
  train cards whose deterministic, type-valid binding independently replays
  on eval pre-state s and yields strict Verus+Lynette success or a strict
  subset of the prior normalized diagnostic frontier, with no safety or
  frontier regression
```

For a 10–20-card pilot, construct `O_train(s)` by exhaustive replay after
normal live eval logs have been sealed. It is independent of the retriever.
The withheld eval exact action is only an isolated ceiling; it never enters
the method card bank, thresholds or ordinary recall denominator.

### 3.4 Recall funnel

Over all high-fidelity eval states:

```text
R-1 transfer opportunity:
  fraction with nonempty O_train(s)

earliest loss:
  NO_TRAIN_ORACLE | INDEX | CANDIDATE_GENERATION |
  FILTER | INJECTABLE | RANK | INJECTION | USE_EFFECT
```

Conditional on nonempty `O_train(s)`, report:

- index coverage;
- search Recall@K;
- tri-state filter survival;
- active/type-valid/anchor-resolved survival;
- rank Recall@K;
- top-one injection recall;
- live reproduced effect.

Do not multiply marginal rates as if independent. Give every miss its earliest
loss stage. Always report `R-1`; otherwise excellent conditional recall can
hide near-zero transferable memory.

## 4. When the Agent Should Search

### Recommended research MVP

Run a cheap, invisible search after every valid verifier checkpoint, including
the initial one. The agent sees nothing until the separate injection policy
selects a card. This removes search-trigger false negatives and establishes
the recall ceiling.

### Trigger alternatives

| Scheme | Mechanism | Strength | Main risk |
|---|---|---|---|
| Always inject | Inject top card at every semantic checkpoint | High use and useful harm baseline | Context toxicity and ambiguous credit |
| Deterministic FSM | Inject on exact/unified state match, state change, no-op, repetition; abstain on regression | Auditable; recommended MVP | Conservative, may under-use |
| Agent self-trigger | Agent requests symbol, premise or pattern memory | Easy and flexible | Model may not know what it lacks |
| Learned utility router | Predict `P(benefit)-P(harm)` from matched outcomes | Can optimize use/cost | Needs enough paired data; threshold transfer |
| Hybrid | Mandatory deterministic events + agent request + learned optional route | Best production target | Not justified before MVP evidence |

The recommended sequence is:

```text
always invisible search + deterministic top-one injection/abstain
  -> add agent request
  -> add learned utility router only with matched labels
```

In a production optimization, static repository premise lookup can always run
before the first attempt, while transition/strategy injection remains
verifier-state-driven.

## 5. Memory Card Form

### 5.1 Representation layers

- canonical: versioned JSON Schema, stored as JSONL/SQLite;
- human review: deterministic Markdown rendering;
- agent context: a 50–120-token compiled card;
- evidence/utility histories: separate append-only ledgers.

Do not use Markdown-only cards as the source of truth.

### 5.2 Minimal MVP card

```json
{
  "schema_version": "0.1",
  "card_id": "invoke-lemma-0001",
  "card_type": "invoke_lemma_transition",
  "status": "shadow",
  "provenance_identity": {
    "repo_id": "<repo>",
    "commit_sha": "<sha>",
    "verus_version": "<version>",
    "source_path": "<path>",
    "pre_state_hash": "<hash>",
    "post_state_hash": "<hash>",
    "source_replay_id": "<id>"
  },
  "retrieval_fingerprint": {
    "error_family": "assertion_failure",
    "diagnostic_ast_shape": "<alpha-normalized-shape>",
    "target_decl_shape": "<normalized-shape>",
    "local_spec_shape": "<normalized-shape>",
    "required_symbol_signature": "<signature>"
  },
  "lemma": {
    "fq_name": "crate::module::lemma_name",
    "signature": "proof fn lemma_name(...)",
    "requires": ["..."],
    "ensures": ["..."]
  },
  "action": {
    "binding_rule_id": "typed-source-order-v1",
    "anchor_rule": "before_failing_assertion"
  },
  "exclusion_conditions": [],
  "safety_constraints": [
    "no_spec_edit",
    "no_exec_edit",
    "no_assume_admit_external_body_axiom"
  ],
  "activation": {
    "status": "shadow",
    "validation_policy_id": "strict-frontier-subset-v1",
    "validation_evidence_ids": []
  }
}
```

Source replay produces `shadow`, not `active`. Promotion happens only on
`D_val`: at least one non-source strict improvement, no harmful valid binding,
no new diagnostic, and no Lynette/spec/exec/bypass regression. `D_eval` never
updates activation.

Agent rendering:

```text
[invoke-lemma-0001]
WHEN: <matched normalized state>
DO: invoke <fully-qualified lemma> with <resolved typed binding>
AT: <resolved structural anchor>
EXPECT: remove a frontier diagnostic without adding one.
DO NOT: edit spec/exec code or use proof bypasses.
```

## 6. Evaluation and Kill Gate

Frozen arms:

1. H0;
2. always-search/no-injection;
3. deterministic selective top-one injection/abstain;
4. always top-one active-card injection;
5. isolated withheld exact-action ceiling.

Primary outcomes:

- strict Verus + Lynette success;
- Expected Cost to Success;
- unsafe and diagnostic-frontier regression.

Mechanism outcomes:

- `R-1` and earliest recall-loss stage;
- active-card and injection coverage;
- benefit/neutral/harm per injection;
- search/injection rate, context tokens and latency.

Stop the skill-system claim if selective injection does not improve strict
utility over H0/no-injection without safety/frontier regression. A negative
result can still localize whether the bottleneck is no transferable memory,
retrieval loss, overconservative promotion, or failure to use retrieved
actions.

## 7. Literature Boundary

- RAG-Verus already covers repository metadata, embedding retrieval,
  learned premise projection and dependency-graph retrieval:
  `https://arxiv.org/html/2502.05344`.
- KVerus already covers typed repository dependencies, semantic lemma
  indexing, version-aligned Verus knowledge and diagnostic-driven refinement:
  `https://arxiv.org/html/2605.03822`.
- Rango retrieves proofs and premises at every evolving Coq proof state using
  sparse retrieval:
  `https://arxiv.org/html/2412.14063`.
- LeanDojo/ReProver establishes accessibility filtering and hard negatives:
  `https://arxiv.org/abs/2306.15626`.
- Adaptive retrieval work shows why retrieval use, harm, thresholds and cost
  need separate accounting:
  `https://arxiv.org/html/2607.24010`.
- Official Verus guidance emphasizes complete verifier feedback, vstd/tests,
  cheat checking and common hard cases:
  `https://verus-lang.github.io/verus/guide/llmforverusproof.html` and
  `https://verus-lang.github.io/verus/guide/checklist.html`.

Therefore the broad index and trigger families are not the novelty. The
research claim must remain the verifier-grounded transfer-opportunity,
earliest-loss and selective-injection protocol, conditional on live results.
