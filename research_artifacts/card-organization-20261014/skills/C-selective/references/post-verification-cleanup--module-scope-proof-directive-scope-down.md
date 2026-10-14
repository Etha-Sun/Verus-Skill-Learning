# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

<a id="module-scope-proof-directive-scope-down"></a>
## Module-scope proof-import-like directive after successful verification

Source cards: card-024

**Trigger:** Verus verifies the proof, but the proof-only safety comparison reports a difference because a proof-import-like directive was left at module scope.

**Action:** Move that directive into the bodies of the proof functions that require it, rather than keeping it at module scope. Verify with the standard proof checker and then rerun the safety comparison.

**Why:** A module-level proof-import-like directive can be observed by the safety comparison as a change to the generated interface, whereas the same directive scoped inside a proof-function body is contained in ghost proof code and does not alter the comparison.

**Validate:** Both the proof checker and the proof-only safety comparison pass after scoping the directive into proof-function bodies.

**Avoid when:** The directive cannot legally appear inside a function body or is required by multiple proofs in a way that cannot be partitioned.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route responds to an active trigger-inference failure; this route only cleans up warnings or deghosted-code differences after verification.

- Distinguish from [proof-helper-qualified-path](proof-helper-qualified-path.md): Qualified-path route prevents an import from surviving deghosting before conclusion; post-verification route repairs an already reported difference or warning.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Use trigger-inference annotation when Verus reports an active trigger-inference failure or a failing quantifier; this post-verification route only cleans up a low-confidence automatic-trigger note after the proof already verifies.

- Related [proof-helper-qualified-path](proof-helper-qualified-path.md): Use the qualified-path route during proof construction to prevent a top-level import from surviving deghosting; this cleanup route repairs an already reported post-verification difference or warning.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use the set-equality membership/witness route to construct set equality when no direct lemma applies; post-verification cleanup handles proof-only imports/macros once the set-equality proof already verifies but the comparison reports a difference.
