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

card-006
**Trigger:** Inside a proof block, a quantified assertion or lemma call fails even though the body appears to have the needed antecedent. Verus diagnostics warn that the implication form in that quantified proof assertion does not assume the antecedent for the body.
**Action:** For a quantified proof assertion with the missing-antecedent diagnostic, use the dedicated proof implication operator named implies by the current Verus diagnostic, or explicitly branch on the antecedent before deriving the consequent. Check nested assertions separately; do not rewrite unrelated specification implications.
**Why:** Verus treats the two logical implication notations differently in asserted quantified proof bodies. The form that is not recognized as antecedent-assuming leaves the body without the needed hypothesis, causing failed lemma preconditions and assertions.
**Validate:** The previously failed preconditions or assertions should clear, and the full verification should reach the expected number of verified functions with zero errors. Run the safety comparison tool afterward.
**Avoid when:** The antecedent is already available or the failure needs another logical premise. The operator behavior was observed in Verus 0.2025.09.12.bb1f342; confirm the current diagnostic and language support rather than assuming the behavior in every version.

card-058
**Trigger:** A premise is an entailment or validity statement, and asserting only its conclusion does not activate the premise's universal quantifier; Verus reports the inferred assertion as failed. **Action:** Before using the premise at a concrete execution, assert the full implication-form satisfaction for that execution, not just the conclusion. Then apply the implication with the antecedent and conclude the right-hand side. This uses the existing universal hypothesis rather than adding any new trusted fact. **Why:** An entailment expands to a universal quantifier over executions, and SMT instantiation often needs the surface form of the implication applied to the chosen execution. **Validate:** Re-run Verus; the previously failing assertion should be discharged and the final target should close. **Avoid when:** The premise is not an entailment or validity over the same execution type, or the selected implication term does not match the premise's syntactic form; use a helper lemma or a different unfolding in that case.
