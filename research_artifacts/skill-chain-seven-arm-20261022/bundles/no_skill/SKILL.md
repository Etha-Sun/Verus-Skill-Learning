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
