# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.

Use the current Verus diagnostic as the primary signal. Before editing, classify
the failure (precondition, postcondition, invariant entry/exit, quantifier,
arithmetic, type/mode/scope, or termination), inspect the implicated context,
and choose the narrowest matching VeruSAGE action. When choosing an approach to an unfamiliar obligation, or when its premises or
scope change, match the current state against the card index before expanding
the proof attempt. Reuse applicable guidance or read a plausible match; a clear
local correction can proceed directly. Prefer an existing lemma or a
small local assertion over duplicating a proof. Re-run Verus after a meaningful
change; if the same failure repeats, change the proof strategy rather than
repeating the same edit. Accept a candidate only when Verus verifies it and the
proof-only safety comparison passes.

## On-demand proof repair cards

An optional card library is available in this workspace. The complete index
below lists every card's title and trigger. You decide whether, when, and which
cards to read based on your current proof state; no retrieval ranking or fixed
card count is imposed. Read any indexed card by ID:

    python3 card_read.py new-001

You may read additional cards, decline their advice, or continue without them.
Reconsider earlier card choices or a no-match decision when the obligation changes.
Check applicability and rejection conditions against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
Turn applicable advice into a small proof step and check the intended obligation.
Cards are fallible advice, not proof. Briefly identify a consulted card’s ID and connect its advice to the current
obligation and available premises. Distinguish applying its route from borrowing
a general technique; check the premises needed for the step you actually take,
and decline advice that requires unavailable premises. Do not
bulk-read cards.json or modify library files. Reading is optional and uses the
normal task time and context budget.

## Card index

- new-001: Recursive accumulator finiteness — Empty/new recursive proof over finite input. Inspect branch relations; require finite input and, in recursive branches, a proved reduced result or justified smaller-input recursion.
- new-002: Packet-loop precondition/local assertion — Check whether the required per-element fact is available at this call's index and endpoint. Inspect invariant support versus unapplied facts; a sequence-level fact elsewhere is insufficient.
- new-003: Forward-preservation helper precondition fails — The missing premise is its universal invariant/next step at suffixes of the base execution. Check that exact contract and scoped step; another temporal goal without this failed call is not this route.
- new-004: Set-image membership equivalence — Assertion failure for image-of-union versus union-of-images, with sets/map in scope. Inspect the active direction's source witness; bind one only from justified image membership/existence, not an assumed relation.
- new-005: Final entailment still open after pointwise/temporal-lifting reasoning — Check whether those steps are proved or merely attempted, and expose the full hypothesis instance at the required execution. A justified source-satisfaction scope and derivable connection are required; temporal vocabulary alone is insufficient.
- new-006: Goal: prove temporal stability of a conjunction — An empty/incomplete proof must establish stability for conjoined lifted state predicates using matching local rules. Merely having a stability premise for a different goal does not match. Inspect wrappers and all composition premises.
- new-007: Closed little-endian serialization — Reveal rejected or length proof blocked by the closed body; bytes module available. Inspect permitted open definitions, connector consequences or byte-width facts; stop without a justified length/transfer route.
- new-008: Empty-body temporal equality postcondition — Inspect existing equality helpers requiring pointwise mutual entailments, including predicate-family arguments. Check each direction locally; reject mismatched types/premises or an unjustifiable direction.
- new-009: Missing trigger in an execution-equality helper premise — Projection syntax is repaired; the open goal is pointwise execution equality at an arbitrary index. Inspect legal existing call/projection terms. A missing trigger in another quantified proposition does not match this route.
- new-010: Failed inner assertion needs an out-of-scope implication antecedent — In quantified entailment reasoning, compare the needed premise with the actual proof scope, then inspect justified branching. An implication warning alone, with no dependent failed assertion, does not establish this match.
