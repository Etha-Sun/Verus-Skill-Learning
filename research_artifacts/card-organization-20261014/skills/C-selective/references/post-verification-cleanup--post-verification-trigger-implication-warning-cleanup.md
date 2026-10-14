# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

<a id="post-verification-trigger-implication-warning-cleanup"></a>
## Post-verification automatic-trigger and implication-warning cleanup

Source cards: card-052

**Trigger:** A proof verifies but emits a low-confidence automatic trigger note or a warning about implication inside a universal assertion.
**Action:** After the proof is already verified, accept the automatic trigger on the proof-only quantified assertion, or rephrase a bare implication in the assertion as either the built-in implication relation or an explicit conditional guard. This step is only warning cleanup, not proof construction.
**Why:** These messages are emitted even when verification succeeds. Accepting automatic triggers silences the note but does not change instantiation behavior; rephrasing the implication makes the intended containment of the antecedent explicit.
**Validate:** Re-run Verus and confirm the same number of verified functions and zero errors, with the warning gone; keep Lynette passing.
**Avoid when:** The goal is to make a failed quantifier or implication pass by changing trigger selection or implication handling; a warning cleanup is not evidence that trigger changes will help a failing proof.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route responds to an active trigger-inference failure; this route only cleans up warnings or deghosted-code differences after verification.

- Distinguish from [proof-helper-qualified-path](proof-helper-qualified-path.md): Qualified-path route prevents an import from surviving deghosting before conclusion; post-verification route repairs an already reported difference or warning.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Use trigger-inference annotation when Verus reports an active trigger-inference failure or a failing quantifier; this post-verification route only cleans up a low-confidence automatic-trigger note after the proof already verifies.

- Related [proof-helper-qualified-path](proof-helper-qualified-path.md): Use the qualified-path route during proof construction to prevent a top-level import from surviving deghosting; this cleanup route repairs an already reported post-verification difference or warning.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use the set-equality membership/witness route to construct set equality when no direct lemma applies; post-verification cleanup handles proof-only imports/macros once the set-equality proof already verifies but the comparison reports a difference.
