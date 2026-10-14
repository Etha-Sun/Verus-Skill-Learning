# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

## Rules

- [Restore original executable call, binding, branch, and return shape after a proof-only comparison difference](#exec-shape-deghost-restore)
- [Module-scope proof-import-like directive after successful verification](#module-scope-proof-directive-scope-down)
- [Proof-only imports/macros in a verified set-equality argument](#qualified-proof-helper-set-equality-no-import)
- [Post-verification automatic-trigger and implication-warning cleanup](#post-verification-trigger-implication-warning-cleanup)

<a id="exec-shape-deghost-restore"></a>
## Restore original executable call, binding, branch, and return shape after a proof-only comparison difference

Source cards: card-038, card-042

**Trigger:**
- The proof checker/Verus reports success, but Lynette or the proof-only/deghosted executable comparison reports that the generated executable code differs from the input.
- For card-038, this difference occurs despite all intended changes being ghost or proof-only.

**Action:**
- When the difference involves the executable call/return surface, preserve the original executable call structure, including local borrow bindings and the exact shape of the final returned value; keep the original ghost return identifier if one was already present; do not change a ghost binding from spec type to an execution wrapper in ways that alter the deghosted return expression.
- When the difference involves executable-shape edits, review and revert local variable renaming, added unreachable or alternate branches, intermediate executable bindings, and reordered executable statements; capture the original parameter's abstract view in a ghost variable if a later pattern match would otherwise shadow it, while keeping the executable bound name and control flow identical.
- Put all new reasoning inside ghost annotations or separate proof blocks, and move only new mutations into proof blocks so they do not survive deghosting.

**Why:**
- Verification success does not imply only ghost code changed. The safety comparison checks deghosted executable code and can be sensitive to how ghost bindings appear in the executable surface; changes that survive ghost erasure are not proof-only and are rejected even when logically equivalent, because the requirement is to preserve the executable program rather than merely a semantically equivalent version.

**Validate:**
- Rerun both the proof checker and the proof-only comparison after restoring the original structure/identifier. Success is Verus/proof verification with zero errors and an empty/clean comparison output.

**Avoid when:**
- The proof genuinely requires changing an executable binding, return shape, branch, intermediate binding, name, or statement order. Do not force an incompatible surface shape or rely on semantic equivalence alone when the comparison is required; find a ghost-only way to state the relationship or reconsider the proof strategy rather than altering run-time code.


<a id="module-scope-proof-directive-scope-down"></a>
## Module-scope proof-import-like directive after successful verification

Source cards: card-024

**Trigger:** Verus verifies the proof, but the proof-only safety comparison reports a difference because a proof-import-like directive was left at module scope.

**Action:** Move that directive into the bodies of the proof functions that require it, rather than keeping it at module scope. Verify with the standard proof checker and then rerun the safety comparison.

**Why:** A module-level proof-import-like directive can be observed by the safety comparison as a change to the generated interface, whereas the same directive scoped inside a proof-function body is contained in ghost proof code and does not alter the comparison.

**Validate:** Both the proof checker and the proof-only safety comparison pass after scoping the directive into proof-function bodies.

**Avoid when:** The directive cannot legally appear inside a function body or is required by multiple proofs in a way that cannot be partitioned.

<a id="qualified-proof-helper-set-equality-no-import"></a>
## Proof-only imports/macros in a verified set-equality argument

Source cards: card-050

**Trigger:** A proof-only set-equality argument verifies in Verus, but the generated-code safety comparison reports that the files differ or that a disallowed macro change was detected.
**Action:** Remove proof-only imports and macro invocations that survive deghosting. Prefer fully qualified proof-only helper references rather than adding a use; if a set-equality macro is used, invoke it by its full path without importing it. Alternatively replace the macro with a direct quantified membership assertion and a built-in set-extensionality assertion, which avoids extra proof-only imports entirely.
**Why:** Verification success does not imply that only executable code changed. In these traces, a top-level proof-only import or macro invocation inside the verified scope was retained by the deghosted comparison, causing a false difference even though the proof was correct.
**Validate:** Run both tools after the adjustment. In the supplied traces, Lynette changed from failure to success once the proof-only import was removed or the helper invocation was fully qualified, while Verus continued to verify.
**Avoid when:** The comparison reports a real executable or contract difference, such as modified signatures or specifications; fully qualifying a proof helper will not fix an actual contract change.

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
