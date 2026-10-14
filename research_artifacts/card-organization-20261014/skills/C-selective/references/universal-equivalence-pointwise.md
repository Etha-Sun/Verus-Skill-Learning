# Universal formula equivalence by pointwise facts and triggers

## Scope

- Consult when: Goal is equivalence between two universal formulas with different bodies
- Consult when: Direct chaining fails
- Consult when: Installed library facts/open definitions can prove pointwise equivalence
- Not for: Bodies are already syntactically equivalent or a direct assertion closes the goal
- Not for: Required library axioms/definitions are unavailable

## Rules

- [Universal formula equivalence by pointwise facts and triggers](#rule-card-077)

<a id="rule-card-077"></a>
## Universal formula equivalence by pointwise facts and triggers

Source cards: card-077

**Trigger:** A proof postcondition is an equivalence between two universal formulas with different bodies, such as a filtered-size condition and a no-such-element condition, and direct chaining does not close it.
**Action:** Prove a pointwise equivalence for an arbitrary element using the installed library facts and open definitions. Then either assert the universal equivalence with explicit valid multi-trigger patterns on each side's function-call or field projection, or avoid fragile trigger lifting by introducing two directional lemmas with requires and case-splitting the main goal into each direction.
**Why:** The verifier cannot connect the two universal bodies without a pointwise bridge. Explicit triggers must be function calls, field accesses, or arithmetic operators, not logical equalities; directional lemmas with requires avoid reliance on quantifier instantiation when equality terms are invalid triggers.
**Validate:** Rerun Verus; the target postcondition should be verified. Run Lynette for proof-only safety.
**Avoid when:** The universal bodies are already syntactically equivalent or a direct assertion closes the goal; or the needed library axioms and definitions are not available or trusted. Do not add a pointwise lemma if it duplicates an existing trusted lemma already proving the equivalence.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): This route first proves pointwise equivalence and then chooses triggers or directional lemmas; trigger route only annotates an existing quantifier.

- Distinguish from [library-broadcast-activation](library-broadcast-activation.md): Broadcast route activates trusted library axioms; universal-equivalence route proves a pointwise extensional bridge.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): This route first proves pointwise equivalence and then chooses trigger annotations or directional lemmas; trigger-inference-annotation only annotates an existing quantifier.

- Related [library-broadcast-activation](library-broadcast-activation.md): Library-broadcast-activation brings trusted library axiom groups into proof scope; this route proves a pointwise extensional bridge from installed library facts/open definitions.

- Related [direct-existing-lemma-bridge](direct-existing-lemma-bridge.md): Use direct-existing-lemma-bridge when an existing trusted lemma/trait contract already proves the equivalence; use this family only when no such lemma exists and a pointwise bridge must be established.
