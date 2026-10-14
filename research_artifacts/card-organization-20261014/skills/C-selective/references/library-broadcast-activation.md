# Activate installed library broadcast axiom groups in proof body

## Scope

- Consult when: Pointwise proof is stuck on facts about an installed library operation
- Consult when: The relevant broadcast axiom group exists in the installed library and open definitions are available
- Not for: Relevant broadcast axiom group is absent in installed version
- Not for: Bringing it in causes unintended instantiation of unrelated facts

## Rules

- [Activate installed library broadcast axiom groups in proof body](#lb-broadcast-activation-verbatim)

<a id="lb-broadcast-activation-verbatim"></a>
## Activate installed library broadcast axiom groups in proof body

Source cards: card-078

**Trigger:** A library-typed pointwise proof is stuck because facts about the library operation are not being used, even though the operation is defined in the installed standard library.
**Action:** Inspect the installed library definitions and explicitly bring the relevant broadcast axiom group into scope inside the proof body. Use the available open definitions and broadcast axioms directly with case analysis on the relevant boolean predicate, rather than adding new axioms or assumptions.
**Why:** Verus broadcast axiom groups are not automatically available in every proof body; enabling the group exposes trusted library facts that close the pointwise case split. This preserves soundness and avoids weakening the proof with new trusted bodies.
**Validate:** Rerun Verus after adding the broadcast use and case analysis; the previously unproved pointwise assertion should verify, followed by Lynette passing.
**Avoid when:** The relevant group or axiom is not present in the installed version, or bringing in the group causes unintended instantiation of unrelated facts. Existing trusted declarations are background and do not authorize adding new trusted bodies.

- Distinguish from [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge invokes a matching lemma; broadcast route explicitly brings a trusted axiom group into proof scope for case analysis.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Direct bridge invokes a matching lemma; broadcast route explicitly brings a trusted axiom group into proof scope for case analysis.
