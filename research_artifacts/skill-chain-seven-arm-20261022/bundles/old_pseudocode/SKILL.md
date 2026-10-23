# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.

Use the current Verus diagnostic as the primary signal. Before editing, classify
the failure (precondition, postcondition, invariant entry/exit, quantifier,
arithmetic, type/mode/scope, or termination), inspect the implicated context,
and choose the narrowest matching VeruSAGE action. Prefer an existing lemma or a
small local assertion over duplicating a proof. Re-run Verus after a meaningful
change; if the same failure repeats, change the proof strategy rather than
repeating the same edit. Accept a candidate only when Verus verifies it and the
proof-only safety comparison passes.

## On-demand proof repair cards

An optional card library is available in this workspace. The complete index
below lists every card's title and trigger. You decide whether, when, and which
cards to read based on your current proof state; no retrieval ranking or fixed
card count is imposed. Read any indexed card by ID:

    python3 card_read.py card-001

You may read additional cards, decline their advice, or continue without them.
Check applicability and rejection conditions against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
Cards are fallible advice, not proof. Briefly identify a consulted card's ID
and why it applies or why you decline it in your progress message. Do not
bulk-read cards.json or modify library files. Reading is optional and uses the
normal task time and context budget.

## Card index

- card-002: card-002 — The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment — The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.
- card-017: card-017 — A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure — A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.
- card-022: card-022 — Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions — Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions. Concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.
- card-029: card-029 — A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier — A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier.
- card-037: card-037 — A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically — A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.
- card-058: card-058 — A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed — A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed.
- card-060: card-060 — Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof — Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof.
- card-062: card-062 — Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates — Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates.
- card-070: card-070 — A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails — A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.
- card-076: card-076 — A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases — A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.
