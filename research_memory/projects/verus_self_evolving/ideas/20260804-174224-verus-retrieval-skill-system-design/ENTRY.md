# Verus Retrieval Skill System Design

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-08-04T17:42:24-05:00`
- status: `active`

## Question

Is extracting memory from each Verus file and building a highly
domain-specific RAG system a good skill-system design, and what should be
retrieved beyond embeddings or vector similarity?

## Decision

Per-file extraction is a useful ingestion and caching boundary, but a file
summary should not be the primary retrieval unit. Static knowledge should be
indexed at declaration, specification, proof-block, and dependency-edge
granularity. A static Verus hybrid retriever is a useful system substrate and
baseline, not a complete skill system or a sufficient research contribution.

The recommended research mechanism is:

> Replay-validated selective lemma-transition retrieval: a historical
> `invoke_lemma` action becomes retrieval-eligible only when it can be replayed
> on the exact saved pre-state and reproduce the verifier improvement, passes
> scope/type/mode and Lynette checks, and is non-harmful on task-disjoint
> validation states; otherwise the router abstains.

## Evidence

Local evidence:

- The R041 global trace-distilled H2 prompt was 4/9 versus 5/9 for H0/H1 on
  three diagnostic cases, used more session tokens, and was Lynette-safe in
  only 6/9. This is a negative candidate, not a population effect estimate.
- The Qwen arm also had a verifier-access confound, so R041 cannot establish
  that global memory is generally harmful or that transition retrieval works.
- Motif-aware offline rules had much lower false-stop risk than generic rules,
  supporting domain-specific structured features while not proving live gain.
- The full trace audit permits exact transition learning only from the
  high-fidelity subset; summary-only and narrative-only logs must not be
  promoted as exact state transitions.

Closest work:

- RAG-Verus: `https://arxiv.org/html/2502.05344`
- KVerus (ASE 2026): `https://arxiv.org/html/2605.03822`
- LeanDojo/ReProver: `https://arxiv.org/abs/2306.15626`
- Rango: `https://arxiv.org/abs/2412.14063`
- Text-plus-graph premise selection:
  `https://arxiv.org/html/2510.23637`

These works already cover repository metadata, static code/lemma retrieval,
dependency structure, accessible premises, evolving-state retrieval, and
verifier-driven refinement. The novelty boundary must therefore stay on
replay attribution, held-out promotion, and selective action-or-abstain.

## Verus Retrieval Substrate

Useful non-vector channels:

1. exact symbol/name and compiler-suggested lemma lookup;
2. FTS/BM25 over rare identifiers, signatures, specifications, and normalized
   diagnostics;
3. import/visibility, proof-spec-exec mode, arity, type, generic-bound, and
   precondition filtering;
4. import/call/spec/lemma/trait dependency traversal;
5. AST, diagnostic-span, spec-shape, quantifier/trigger, invariant, and proof
   motif matching;
6. metadata filtering by repository, motif, error family, Verus version,
   safety status, and provenance;
7. exact verifier-state transition matching and negative/harmful-action
   evidence;
8. iterative retrieve-run-Verus-requery rather than one-shot context packing;
9. optional embeddings only as a supplementary recall channel.

## MVP Contract

- one frozen repository and Verus version;
- one error family;
- one action family: `invoke_lemma`;
- exact single-edit verifier intervals only;
- 10-20 reviewed operators and 10-20 task-held-out states as a kill-gate
  feasibility pilot;
- deterministic conservative abstention, not statistical risk calibration;
- lexicographic utility: safety, strict success, then Expected Cost to Success;
- no cross-project or population-effect claim.

Full proposal:

- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/REVIEW_SUMMARY.md`

## Next Action

Before implementing a broad RAG system, enumerate exact single-edit
lemma-invocation transitions in one frozen repository snapshot and test whether
they replay. If the replay and live kill gates fail, stop expanding the memory
taxonomy and retain the result as Verus RAG engineering/negative analysis.

## Data Safety

No raw or sealed dataset was modified, moved, copied, or committed. This entry
contains only reviewed compact conclusions and public literature pointers.
