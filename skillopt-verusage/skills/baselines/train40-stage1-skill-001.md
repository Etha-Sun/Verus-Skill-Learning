# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.

Use the prescribed Verus command on the untouched candidate as the primary signal. Before editing, classify the failure as precondition, postcondition, invariant entry/exit, quantifier, arithmetic, type/mode/scope, termination, or infrastructure/toolchain; inspect only the implicated context and choose the narrowest matching VeruSAGE action. If unchanged source fails before proof verification because of crate or macro resolution, a missing dependency, or a wrapper/tool failure, do not repair imports, crate aliases, executable declarations, or configuration in the candidate. Preserve the source and report the infrastructure blocker unless a permitted workspace tool provides the fix. Prefer an existing lemma or a small local assertion over duplicating a proof. Before unfolding a definition, inspect the target and nearby proof functions, then form a short chain of lemma contracts whose `ensures` match the goal. Instantiate them with named local predicates and use equality, entailment, or transitivity for syntactic bridges. Pre-existing `external_body` items may be used through their contracts, but must not be removed, rewritten, or reproved. Unfold temporal or collection definitions only after a concrete lemma chain fails.

For quantified proofs, mirror existing trigger terms rather than guessing new ones. Use `assert forall |x| ... by { ... }` when the body needs `x`. Bind closures to named spec locals before triggering applications because triggers cannot contain lambdas, `let`, quantifiers, or `choose`. Supply a concrete witness for every existential. In loops, carry each quantified precondition needed by the body as an invariant and instantiate it at the current index. Re-run Verus after a meaningful change; if the same failure repeats, change proof strategy rather than repeating the edit. Accept a candidate only when Verus verifies it and the
proof-only safety comparison passes.

When semantic equality does not match syntactically, prove a small bridge first. For sets, sequences, spec functions, predicates, executions, or structs, establish the relevant extensional facts—membership equivalence, equal lengths and pointwise indices, pointwise equality, or field equality—then close with `=~=`, an existing extensionality rule, or enclosing value equality. Normalize equivalent expression shapes such as nested suffixes, open-spec wrappers, or concatenation offsets before reusing a fact.

## Bounded Iteration

Test one hypothesis per edit and retain the last preservation-safe candidate that parses with the smallest diagnostic set. Immediately revert parser, type, trigger, or safety regressions. Before the time budget expires, restore the best preservation-safe checkpoint and run Verus followed by the proof-only comparison.

<!-- SLOW_UPDATE_START -->
<!-- SLOW_UPDATE_END -->
