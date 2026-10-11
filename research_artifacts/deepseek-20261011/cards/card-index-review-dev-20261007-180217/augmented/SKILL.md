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

- card-001: A proof obligation is a known algebraic property about library types, such as mapping over a union of sets, and an installed library already provides a lemma whose conclusion matches that obligation.
- card-002: The proof goal is equality of sets or set images, no existing library lemma can directly discharge it, and the verifier fails on a naked quantified membership equivalence or on a case split that merely asserts the reverse containment.
- card-003: A proof obligation asks to show that two structured values have equal views under assumptions that both values are marshalable and their serialized representations are equal; an existing trait or generated instance already promises view equality under those assumptions.
- card-004: A proof function has an empty or incomplete body and its postcondition is equality of two records that contain a function-valued projection field; a premise already gives pointwise equality of that projection for every index. Verus reports only the postcondition unsatisfied.
- card-005: The same pointwise function-equality premise is available, but a direct equality assertion on the function values is not discharged by the verifier, and helper names for function equality are unavailable or rejected.
- card-006: Inside a proof block, a quantified assertion or lemma call fails even though the body appears to have the needed antecedent. Verus diagnostics warn that the implication form in that quantified proof assertion does not assume the antecedent for the body.
- card-007: A top-level temporal goal, such as eventually reaching a stable state under a transition system, has an empty or weak proof body and direct application of weak fairness or leads-to does not close the postcondition.
- card-008: A generic helper has established that an action eventually fires after every point, but the desired existential post-state does not follow. The verifier reports that the post-state existence or the lifted eventual-state assertion failed.
- card-009: The proof already has an existential witness for a raw state predicate at an absolute shifted index, but the assertion that the lifted state predicate eventually holds on the current suffix still fails.
- card-010: Verus reports an unsatisfied temporal postcondition requiring a specification to entail that a state predicate holds at every point in the future, while the relevant proof function body is empty.
- card-011: The invariant is about messages in a network multiset, and transition cases update the network by removing at most one received message and adding a multiset of newly sent messages.
- card-012: The controller-step preservation case needs to rule out the possibility that the target controller sends a request to its own external system.
- card-013: A helper that reasons about a nondeterministic state-machine result fails on an assertion equating the computed result with the transition of one manually chosen enabling step, especially when several steps share the same precondition and the choice is not unique.
- card-014: A proof function must establish a nested always property of an execution, the body is empty, and the surrounding rules define a helper that shifts an always guarantee to any suffix of the execution.
- card-015: Newly added proof code produces Verus errors that a method name is being taken as a field, or a struct field is being called as a method; alternatively, quantified assertion bodies warn or fail because an implication antecedent is not being assumed.
- card-016: A temporal logic proof obligation must show that one existential state condition leads to another, and trusted per-witness lemmas already relate the corresponding individual messages but the verifier cannot connect the quantified statement-level conditions.
- card-017: A proof obligation states that a set produced by folding over a finite input set is finite, and the proof body is empty, causing a postcondition failure.
- card-018: An assertion or witness selection in a proof body fails because the verifier reports that it cannot infer quantifier triggers, or it warns that the weak implication does not assume its antecedent inside an assertion proof.
- card-019: An attempt to unfold a spec function with no decreasing clause using fuel-based revealing is rejected.
- card-020: A proof obligation is an equality between a logical predicate and the conjunction of that predicate with another predicate, under an assumption that the first predicate entails the second. The proof body is empty or only attempts the final equality directly.
- card-021: A direct assertion about the length of a closed serialization function fails, or attempting to reveal that function is rejected because it is closed. The fixed-width serialization length is needed for downstream bounds.
- card-022: Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions. Concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.
- card-023: A proof block for a quantified implication fails to use its antecedent, so later index-bound or quantified facts are unavailable inside the block. Warnings may state that the antecedent is not being assumed.
- card-024: Verus verifies the proof, but the proof-only safety comparison reports a difference because a proof-import-like directive was left at module scope.
- card-025: A proof obligation requires a property to hold at every suffix of an execution, and the available premise states that an always-form of a lifted action is satisfied by that execution. An existing proof helper already unfolds the always form into suffix-wise satisfaction.
- card-026: The goal is to prove that a compound temporal formula is stable, and that formula is a conjunction of an always-step property and several universally quantified fairness or action obligations. The direct goal fails or is too large to discharge at once.
- card-027: While proving stability for a fairness obligation whose action has already been specialized to a fixed controller or identifier, the verifier reports mismatched types in a universal quantifier, expecting a payload type but the binder uses the full action-input tuple.
- card-028: A newly introduced pointwise equality proof on a record containing a function-valued field fails, either because the field is accessed like a method, or because the verifier cannot infer a trigger for the universal pointwise equality.
- card-029: A proof obligation is an equality between two temporal predicates and the body is empty or cannot discharge the postcondition, while existing helper rules already describe commuting a universal temporal quantifier and moving the always construct across that quantifier.
- card-030: A liveness proof reaches a phase-descent lemma whose premise uses the next phase index, while the base liveness lemma concludes the all-phase assumption bundle. Verus rejects the first descent with a precondition about the next phase predicate unless an equality between the recursive phase accumulation and the all-phase bundle is established.
- card-031: A final liveness theorem has an empty or partial body and its postcondition is a desired-state leads-to current-state property, while invariant derivation lemmas, stability lemmas, a base liveness lemma, phase-descent lemmas, and a condition unpacking helper already exist.
- card-032: A temporal leads-to goal has source or intermediate states that contain an existential over messages or other witnesses, while existing helper lemmas prove the property only for one specific witness at a time.
- card-033: Two temporal predicates must be proved equal, where at least one side is an existential temporal predicate combined with another predicate, and the source context provides a predicate-equality rule and a witness-introduction rule.
- card-034: Verus reports that it could not automatically infer triggers for a quantified assertion or choose expression used to select a witness.
- card-035: Verus reports that a while loop must have a decreases clause, while the loop counter starts at zero and increments until it reaches a collection length.
- card-036: After termination is accepted, a call inside a loop fails a precondition or assertion that depends on the enclosing function's assumptions, even though those assumptions were true at function entry.
- card-037: A whole-sequence validity or range property is available, but an assertion about one element at the loop index fails because the quantified assumption is not instantiated automatically.
- card-038: Verus passes, but Lynette reports that the candidate differs from the input in executable code despite all intended changes being ghost or proof-only.
- card-039: A recursive proof function has an empty or insufficient body and cannot establish a temporal property at an arbitrary natural offset.
- card-040: While writing a recursive helper for natural-number induction, Verus reports a type mismatch when assigning the predecessor of a natural index, because subtraction produces an integer type rather than a natural.
- card-041: A while loop over an unapproved prefix mutates an output packet sequence by appending one element per iteration, and after adding a termination measure the verifier still reports that the final set-equality postcondition, a loop-body invariant, or a nested match arm fail.
- card-042: The proof checker reports success, but the proof-only comparison reports that the generated executable code differs from the input file.
- card-043: A proof function has an empty body and must show that two datatype values with equal abstract views have equal marshalability predicates.
- card-044: The packaged existing-lemma chain fails to instantiate, or no view-equal specification bridge is available, for a proof that equal abstract views imply equal marshalability.
- card-045: A proof function has an empty or incomplete body and its postcondition asks for validity of a stable property over a large left-associative conjunction where every conjunct is an always-wrapped temporal predicate already available in the same file.
- card-046: An executable deserializer or constructor returns a value in a success branch, but the postcondition still fails because the new value's specification-level representation is not connected to the input value, even though the file already has a trusted round-trip lemma or axiom relating a reconstructed value back to its input under a previously checked condition.
- card-047: The proof function has an empty body and a postcondition that a conjunction of always-lifted state predicates is stable under temporal rules; equivalent stability and conjunction proof objects are already present in the file.
- card-048: A proof function has a missing body and a postcondition that a fold-computed set equals the image of a finite source set under a supplied function; the fold is defined by recursion on finite cardinality.
- card-049: A proof obligation asks to show that the set view of a sequence after removing an index equals the set view of the original sequence with the element at that index removed, and the sequence is known to have no duplicates.
- card-050: A proof-only set-equality argument verifies in Verus, but the generated-code safety comparison reports that the files differ or that a disallowed macro change was detected.
- card-051: A leads-to transitivity proof has an empty body and only its postcondition fails, while the surrounding helper lemmas for entailment, always, eventually, implication application, witness selection, execution equality, and backward eventual propagation are already declared as trusted background.
- card-052: A proof verifies but emits a low-confidence automatic trigger note or a warning about implication inside a universal assertion.
- card-053: A length-prefixed serialization injectivity proof needs a fixed-size header fact and sequence equality, but directly asserting the header length fails because a closed encoding spec function is opaque, and invoking a sequence-equality helper too early also fails.
- card-054: A function returning a ghost aggregate is required to prove that its contained sequences are all empty and that a sequence-derived set is empty, but its body returns an arbitrary or otherwise unconstrained witness.
- card-055: Verus reports that a proof-only helper or macro is not in scope, and simply adding a top-level import may later make Lynette report a deghosted source difference.
- card-056: A proof function body is empty and Verus reports only the final entailment or leads-to postcondition unproved; the obligation is a universal relationship over cluster states or execution suffixes.
- card-057: Verus reports that it cannot automatically infer triggers for a universal assertion, or warns that an implication used inside a quantified assertion does not assume the antecedent in the proof body.
- card-058: A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed.
- card-059: Verus reports a failed recommendation or precondition about an uninterpreted conversion when ghost code extracts a field through an unwrap, while the surrounding entailment is still unproved.
- card-060: Verus compile errors say a struct field is not a method when a stored spec function is applied directly to an argument in a proof.
- card-061: A temporal proof branch reduces to an existential reachability obligation and requires a witness index, but constructing the index manually is difficult.
- card-062: Verus reports an empty or incomplete proof body for a temporal stability postcondition, and the target predicate is a finite conjunction of always-lifted state predicates.
- card-063: A proof obligation requires showing that a left fold over the concatenation of two sequences equals the concatenation of the two separate folds, and a direct assertion or unfolding does not close the proof.
- card-064: A proof obligation about folding a concatenated sequence can be approached by splitting the concatenated sequence at the boundary between the two original parts.
- card-065: Verus complains that a proof/ghost macro is not in scope, and adding a top-level import would survive deghosting and later cause the proof-only safety comparison to report that the files are different.
- card-066: In a generic proof, an empty sequence argument triggers a type-inference error, or a sequence length is used where an integer index is expected and produces a natural-versus-integer mismatch.
- card-067: You need to prove equality of two sequence expressions, especially an equivalence that holds after adding the same suffix to both sides, and the proof body is empty or the equality is not discharging.
- card-068: A sequence-equality closure mechanism is reported as not in scope, or the only easy way to bring it into scope is a new top-level import that the proof-only safety comparison rejects.
- card-069: A proof block inside a universal assertion depends on the implication antecedent, and Verus reports an inner assertion failure or warns that the top-level implication in such an assertion does not assume the antecedent in the body.
- card-070: A postcondition asserts equality between two spec-level function or temporal objects constructed by applying the same operator once versus twice, and the proof body is empty or only this postcondition fails.
- card-071: A Verus postcondition requires validity of a stable form of a conjunction of always-lifted state predicates, and the proof body is empty.
- card-072: A first attempt applies the always-stability rule to an already-lifted temporal conjunct, and the subsequent conjunction-stability rule reports precondition failures.
- card-073: A concrete initializer's postcondition depends on an abstract initial-state relation that requires a ghost history field to be empty, while that ghost field is currently sourced from an unconstrained arbitrary value.
- card-074: Verus reports a precondition not satisfied for a helper call inside a quantified assertion whose body contains an implication, or warns that the implication antecedent is not assumed in the assertion body.
- card-075: Verus emits a compile error saying a public spec-function-valued field has no method with that name when it is used with call-like dot syntax.
- card-076: A recursive or induction helper call fails its quantified stability precondition after always-style facts were propagated to a suffix, even though the needed facts were asserted through local aliases.
- card-077: A proof postcondition is an equivalence between two universal formulas with different bodies, such as a filtered-size condition and a no-such-element condition, and direct chaining does not close it.
- card-078: A library-typed pointwise proof is stuck because facts about the library operation are not being used, even though the operation is defined in the installed standard library.
