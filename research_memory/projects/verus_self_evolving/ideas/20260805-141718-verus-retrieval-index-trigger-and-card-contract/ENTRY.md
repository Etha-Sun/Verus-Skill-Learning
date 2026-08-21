# Verus Retrieval Index, Trigger, and Card Contract

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-08-05T14:17:18-05:00`
- status: `active`

## Question

How should a Verus-specific memory index be built, when should the agent search
or receive memory, how can recall loss be measured without leakage, and what
should a memory card contain?

## Decision

Use files as ingestion/invalidation boundaries, not retrieval units. The broad
substrate indexes typed declarations/specifications, analyzer-derived
dependencies, normalized verifier states and replay-certified transitions.

The implementation-ready research MVP is narrower:

> Search a frozen bank of train-derived `invoke_lemma` transition cards
> invisibly after every valid candidate-hash-bound Verus checkpoint. A
> separate deterministic policy injects at most one validation-promoted,
> type-valid, structurally anchored card or abstains.

This removes search-trigger false negatives during the recall study without
unconditionally steering the agent.

## Failure Routing

Three top-level observable routes are mandatory:

1. `HARNESS_INVALID`: permission/transport failure, missing or stale-hash
   diagnostic, missing candidate, incomplete tool result. Do not query proof
   memory.
2. `VERIFIER_RESOURCE_SYMPTOM`: valid Verus rlimit/timeout. Run a bounded
   controlled resource/profiler probe before calling it a knowledge gap.
3. `SEMANTIC_PROOF_FAILURE`: valid syntax/type/precondition/assertion/
   postcondition/invariant/trigger/other proof diagnostic. Query typed memory.

Behavioral events (`NO_OP`, unchanged candidate, state change, repeated
equivalent state, frontier regression and unsafe diff) separately govern
requery, injection, rollback and abstention.

## Minimal Index

SQLite tables:

```text
symbols
dependencies
transitions
cards
card_symbol_projection
card_state_projection
```

Candidate channels:

1. exact name/signature/compiler-suggestion lookup;
2. FTS5/BM25 over card and state projections;
3. analyzer-derived accessible dependency traversal.

Every substrate hit must project explicitly to a `card_id`. Exact symbol hits
are not counted as transition-card recall unless the correct card survives
that projection.

## Recall Contract

Exact declaration/edge/card projection coverage can be mechanically tested on
a frozen snapshot. Useful semantic memory recall cannot be absolutely
guaranteed.

Use `VALID / INVALID / UNKNOWN` filter semantics; reject only mechanically
invalid candidates. Unknowns stay visible for audit but are not injectable.

Freeze near-code-disjoint `D_train / D_val / D_eval`:

- `D_train` builds frozen `B_train` shadow cards;
- `D_val` alone promotes `B_active` and freezes normalization, binding,
  filtering, ranking and injection;
- `D_eval` never updates the system.

For eval state `s`, construct the oracle independently of retrieval:

```text
O_train(s)
  = frozen train cards whose deterministic type-valid binding replays on s
    with strict Verus+Lynette success or strict diagnostic-frontier subset,
    without safety/frontier regression
```

Report `R-1`, the fraction of high-fidelity eval states with a nonempty
train-bank oracle, before conditional coverage/search/filter/rank/injection/use
recall. The withheld eval exact action is an isolated ceiling only.

## Memory Card

Canonical form is versioned JSON/JSONL in SQLite, with deterministic Markdown
for human review and a 50-120-token agent rendering. The MVP card contains:

```text
card_id, card_type, status
provenance_identity
retrieval_fingerprint
fully-qualified lemma signature/requires/ensures
deterministic binding rule
structural anchor rule
exclusion_conditions
safety_constraints
validation-only activation evidence
```

Per-run evidence, utility and lineage remain separate ledgers. Source replay
creates `shadow`; only non-source validation improvement with zero harmful
valid bindings can create `active`.

## Independent Review

The focused `research-refine` process scored:

- Round 1: `6.38 / 10`, REVISE;
- Round 2: `7.69 / 10`, REVISE;
- Round 3: `9.06 / 10`, READY, no blocking issues.

Canonical artifacts:

- `refine-logs/retrieval-trigger-design/FINAL_PROPOSAL.md`
- `refine-logs/retrieval-trigger-design/REVIEW_SUMMARY.md`
- `refine-logs/retrieval-trigger-design/round-3-review.md`

## Claim Boundary

RAG-Verus, KVerus, Rango and LeanDojo/ReProver already cover much of hybrid
retrieval, dependency knowledge, evolving-state retrieval and accessibility.
The broad index is substrate. The focused research claim is verifier-grounded
transfer-opportunity and earliest recall-loss attribution plus selective
top-one injection, conditional on leakage-safe live results.

No solved-rate or token-efficiency improvement is claimed. R042 remains
incomplete.

## Next Action

Before implementing a general memory platform:

1. freeze one repository/version/error family and disjoint splits;
2. enumerate 10-20 exact single-edit `invoke_lemma` transitions;
3. replay them and construct minimal shadow cards;
4. build exact + FTS5 + accessible-dependency card retrieval;
5. run H0, search/no-injection, selective injection, always injection and
   isolated ceiling arms;
6. stop the skill-system claim if strict utility does not improve without
   safety/frontier regression.

## Data Safety

All corpus and historical run artifacts were read only. No raw or sealed data
was modified, moved or copied into the repository. This entry contains only
reviewed compact conclusions and pointers.

