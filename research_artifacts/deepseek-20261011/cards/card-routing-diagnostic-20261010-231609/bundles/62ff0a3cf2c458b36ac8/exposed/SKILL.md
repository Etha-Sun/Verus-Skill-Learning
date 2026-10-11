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

## Optional proof repair advice

The following cards are fallible advice. Check Trigger and Avoid when before use; you may decline them. Normal verification and safety rules apply.

card-001
**Trigger:** A proof obligation is a known algebraic property about library types, such as mapping over a union of sets, and an installed library already provides a lemma whose conclusion matches that obligation.
**Action:** Before constructing a manual case analysis, inspect the installed library definitions for a lemma with the same conclusion. If one exists, invoke that lemma in the proof body with arguments matching the current obligation and let the verifier close the postcondition.
**Why:** Existing verified library lemmas have already handled witness extraction and extensional reasoning. Reusing such a lemma is narrower and faster than re-proving the same property. In the observed set-image union task, every continuation that selected the direct library lemma verified on the first attempt.
**Validate:** Run the verifier and confirm zero errors; run the proof-safety comparison and confirm it passes. Check that only the proof body changed and no signatures or specifications were modified.
**Avoid when:** The installed library has no lemma matching the goal, the lemma requires additional premises not currently available, or the lemma uses an equality form that the verifier cannot connect to the present postcondition.
