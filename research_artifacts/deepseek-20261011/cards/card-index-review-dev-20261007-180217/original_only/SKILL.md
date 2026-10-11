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
Check Trigger and Avoid when against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
Cards are fallible advice, not proof. Briefly identify a consulted card's ID
and why it applies or why you decline it in your progress message. Do not
bulk-read cards.json or modify library files. Reading is optional and uses the
normal task time and context budget.

## Card index

- card-001: The verifier reports that a proof goal equating a mapped union with a union of mappings is not satisfied from an empty or weak proof body.
- card-002: The verifier reports a structural equality postcondition for two concrete values while the preconditions include marshalability and serialization equality, and the proof body is empty.
- card-003: A quantified assertion verifies, but Verus prints a low-confidence note about an automatically chosen trigger.
- card-004: A proof goal requires equality of two small records, and the only remaining obstacle is that a function-valued field inside that record must be shown equal from a pointwise equality premise that is already available.
- card-005: The target is a temporal leads-to or always property expressed through entailments and weak fairness, and the proof body is empty or relies on high-level temporal rules without pointwise support.
- card-006: Verification stalls inside temporal helper proofs with universally or existentially quantified formulas over executions or natural indices, especially when trigger annotations are placed on large conjunctions or when the formula uses a logical implication whose antecedent is not available in the body.
- card-007: A temporal entailment requires proving that a state predicate holds at every position under a specification that entails initial and next-step properties.
- card-008: An invariant over a collection of in-flight messages must be preserved across a step that removes one optional message and adds a collection of messages.
- card-009: A global message invariant must be preserved even when messages can be produced by several state machines.
- card-010: Inside a universally quantified assertion proof block, the intended antecedent facts are unavailable and Verus warns that the implication does not assume its antecedent.
- card-011: Verus proof code fails with method-resolution or attempted-method errors after calling state-machine operations.
- card-012: A proof asserts equality between a machine's next-result and the transition of a chosen witness, and that assertion fails even after case splitting on the witness.
- card-013: A proof obligation requires showing that an already established always fact remains true at every suffix, forming a nested always statement.
- card-014: Verus reports a failed postcondition or failed precondition in a temporal leads-to proof where the source and target state predicates differ by an existential witness, and the proof is supposed to be composed from existing per-witness leads-to lemmas but the solver cannot directly prove the bridge entailments.
- card-015: A finite set fold or map fold operation is defined recursively by choosing an arbitrary element and recursing on the set with that element removed, and a companion proof obligation such as finiteness of the fold result has an empty proof body that fails its postcondition.
- card-016: A proof obligation asks for equality between a predicate and the conjunction of that predicate with another predicate, while the only premise is that the first predicate entails the second.
- card-017: A pre-existing generic fold induction lemma does not prove a concrete fold bound because the lemma conclusion retains a symbolic function argument, and the concrete fold assertion remains unproven or produces a type mismatch.
- card-018: A needed specification function is marked closed, and attempting to unfold it with a reveal statement is rejected.
- card-019: A structural predicate for a container is a conjunction of quantified facts over one representation, while the available precondition provides quantified facts over a different but related representation of the same data.
- card-020: A verification goal requires showing that a temporal safety property is stable, and that property is a conjunction of an always-step condition with universal weak-fairness constraints.
- card-021: A proof of execution suffix composition fails either with a missing-trigger diagnostic or with a postcondition failure after pointwise equality.
- card-022: A proof body is empty and must prove a universal property over execution suffixes from an assumption that an always-wrapped action property holds.
- card-023: A phase-by-phase liveness proof needs a next-phase premise expressed with a recursive phase predicate, but the available base-liveness conclusion gives an equivalent expanded all-phase conjunction; the first descending lemma call fails its precondition for that missing next-phase fact.
- card-024: An equality proof involving a recursively defined temporal predicate fails the equality lemma's mutual-entailment precondition even though the two sides look equivalent.
- card-025: A postcondition asserting equality between a distributed always over a quantified implication and an implication over distributed always over the inner predicate is not automatically discharged for opaque temporal predicates.
- card-026: A temporal leads-to proof obligation starts from a state predicate that hides an existential choice over a message or response, while the available lower-level lemmas are stated for a single concrete message.
- card-027: The proof goal is an equality between an existential over a predicate conjoined with another temporal predicate and the corresponding temporal existential conjoined separately with that same predicate, in a setting with an extensional equality lemma and a witness-introduction helper.
- card-028: A Verus function contains a while loop over an indexed collection, the loop is missing a decreasing measure, and a call inside the loop fails a precondition that is already guaranteed by the function's own requires clauses.
- card-029: A function body contains an arbitrary ghost result placeholder, and Verus fails a postcondition that must hold for every returned ghost sequence, including the failure branch.
- card-030: A proof function has an empty body and must prove a natural-number indexed postcondition that follows from quantified step, never, and next hypotheses about suffixing an execution.
- card-031: A while loop initially fails only because it lacks a decreases clause. After adding that clause, the loop body still reports that postconditions or loop invariants are not satisfied, even though the required facts were established just before the loop.
- card-032: An empty proof body fails a postcondition that two values' marshalability or serialization validity must agree whenever their abstract views are equal.
- card-033: The verifier reports mode errors, such as a proof function being called outside a proof context or a ghost-only numeric type appearing in executable code, after adding proof lemmas to a loop or function.
- card-034: Verus reports success, but the proof-only safety comparison reports that the de-ghosted executable code differs from the input.
- card-035: An empty proof function must prove that a large temporal invariant, expressed as a conjunction of always-applied subpredicates, is stable. The initial Verus error points to that function's postcondition.
- card-036: A deserialization postcondition fails in the successful parse branch: the returned object must be marshalable, sorted when required, bounded in serialized size, and its serialized form must equal the consumed byte segment. The required facts are spread across an inner deserializer contract, a sortedness test, a constructor postcondition, and a proof-mode lemma.
- card-037: Verus reports that a function cannot be called with proof mode while the current context is exec mode.
- card-038: A proof function has an empty body and its postcondition requires a temporal property to be valid and stable, where that property is a finite conjunction of always-wrapped state predicates.
- card-039: A proof obligation relates a recursive fold over a finite set to the built-in set image operation, and the current proof function body is empty, causing a postcondition failure.
- card-040: A proof obligation requires that removing an element from a duplicate-free sequence yields exactly the set obtained by removing that element from the sequence's set view, and the solver cannot close the resulting set equality on its own.
- card-041: An empty proof body cannot discharge a transitivity-style entailment for an always-eventually relation, even though the context provides trusted unfold and application lemmas for the modalities.
- card-042: After a proof-only change verifies successfully, the deghosted-code safety comparison reports that files are different, and the candidate contains a top-level import of a proof-only helper macro.
- card-043: A proof obligation requires showing that equality of two serialized byte sequences implies equality of the original values, where the serialization format is a fixed-size length prefix followed by the raw payload and the word-to-bytes conversion is opaque.
- card-044: A proof-only function returns a ghost wrapper around a concrete result and has field-level postconditions, but the body uses an arbitrary or unfinished placeholder so those field equalities cannot be discharged.
- card-045: A proof must conclude a temporal entailment from a hypothesis that is itself a validity assertion over all executions, and a generic transitivity statement over temporal predicates stalls or fails to instantiate.
- card-046: The goal requires showing a condition that mentions a generic state constructor weaker than a concrete one, and a ghost-code extraction from an uninterpreted deserializer fails because the success constructor cannot be proved.
- card-047: A quantified assertion for all executions or states reports either a warning that the implication body does not assume the antecedent, or an automatic trigger inference failure.
- card-048: A well-founded temporal leads-to rule has multiple always-entailment premises and must prove a leads-to entailment; an empty body or direct global reasoning stalls.
- card-049: A proof helper needs to show two execution objects are equal, but either a field-versus-method access error occurs or a pointwise quantifier has no inferred trigger.
- card-050: A proof obligation requires showing that folding a sequence-combining operation over the concatenation of two sequences equals combining the fold results of the two sequences, where the combining operation is associative.
- card-051: A proof obligation requires showing stability of a temporal predicate that is expressed as a conjunction of several always-lifted state predicates.
- card-052: A proof macro such as a sequence-equality rewriter is needed, and the natural first attempt is a module-level import so the macro can be used by its short name.
- card-053: Verus reports a parser error such as an expected closing parenthesis inside a proof assertion that contains nested higher-order fold or function-application expressions.
- card-054: A proof obligation is an equivalence between two sequence values where one side appends a common suffix to both sequences.
- card-055: A proof obligation is equality between two higher-order spec functions or temporal predicates whose definitions quantify over executions and suffix positions.
- card-056: A universal assertion over executions, or another domain, has an implication target and the proof body needs to assume the antecedent to establish the consequent.
- card-057: A proof-only edit adds a top-level import solely to use an assertion macro, and the proof-only safety comparison reports that the files are different.
- card-058: A proof function has an empty body while its postcondition requires validity of a temporal stability property built as a conjunction of stable lifted state predicates.
- card-059: A function's postcondition fails because its constructed result must satisfy an initial-state relation, and one ghost component of that result is initialized with an arbitrary or nondeterministic value.
- card-060: An assert-forall proof block needs to use the antecedent of an implication before calling a helper, and the verifier reports a missing precondition for that antecedent.
- card-061: A helper lemma has a universal premise about every index, but a call to that helper fails with a precondition not satisfied, and earlier local definitions introduced names for repeated expressions.
- card-062: The goal is a global temporal entailment involving leads-to, always, and next-preservation, and the initial empty proof only reports a failed postcondition.
- card-063: A proof fails to show that a filtered container has size zero if and only if no element satisfies both membership and a condition.
