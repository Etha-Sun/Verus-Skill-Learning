# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

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


- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route responds to an active trigger-inference failure; this route only cleans up warnings or deghosted-code differences after verification.

- Distinguish from [proof-helper-qualified-path](proof-helper-qualified-path.md): Qualified-path route prevents an import from surviving deghosting before conclusion; post-verification route repairs an already reported difference or warning.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Use trigger-inference annotation when Verus reports an active trigger-inference failure or a failing quantifier; this post-verification route only cleans up a low-confidence automatic-trigger note after the proof already verifies.

- Related [proof-helper-qualified-path](proof-helper-qualified-path.md): Use the qualified-path route during proof construction to prevent a top-level import from surviving deghosting; this cleanup route repairs an already reported post-verification difference or warning.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use the set-equality membership/witness route to construct set equality when no direct lemma applies; post-verification cleanup handles proof-only imports/macros once the set-equality proof already verifies but the comparison reports a difference.
