# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

<a id="qualified-proof-helper-set-equality-no-import"></a>
## Proof-only imports/macros in a verified set-equality argument

Source cards: card-050

**Trigger:** A proof-only set-equality argument verifies in Verus, but the generated-code safety comparison reports that the files differ or that a disallowed macro change was detected.
**Action:** Remove proof-only imports and macro invocations that survive deghosting. Prefer fully qualified proof-only helper references rather than adding a use; if a set-equality macro is used, invoke it by its full path without importing it. Alternatively replace the macro with a direct quantified membership assertion and a built-in set-extensionality assertion, which avoids extra proof-only imports entirely.
**Why:** Verification success does not imply that only executable code changed. In these traces, a top-level proof-only import or macro invocation inside the verified scope was retained by the deghosted comparison, causing a false difference even though the proof was correct.
**Validate:** Run both tools after the adjustment. In the supplied traces, Lynette changed from failure to success once the proof-only import was removed or the helper invocation was fully qualified, while Verus continued to verify.
**Avoid when:** The comparison reports a real executable or contract difference, such as modified signatures or specifications; fully qualifying a proof helper will not fix an actual contract change.

- Distinguish from [trigger-inference-annotation](trigger-inference-annotation.md): Trigger route responds to an active trigger-inference failure; this route only cleans up warnings or deghosted-code differences after verification.

- Distinguish from [proof-helper-qualified-path](proof-helper-qualified-path.md): Qualified-path route prevents an import from surviving deghosting before conclusion; post-verification route repairs an already reported difference or warning.

- Related [trigger-inference-annotation](trigger-inference-annotation.md): Use trigger-inference annotation when Verus reports an active trigger-inference failure or a failing quantifier; this post-verification route only cleans up a low-confidence automatic-trigger note after the proof already verifies.

- Related [proof-helper-qualified-path](proof-helper-qualified-path.md): Use the qualified-path route during proof construction to prevent a top-level import from surviving deghosting; this cleanup route repairs an already reported post-verification difference or warning.

- Related [set-equality-membership-witness](set-equality-membership-witness.md): Use the set-equality membership/witness route to construct set equality when no direct lemma applies; post-verification cleanup handles proof-only imports/macros once the set-equality proof already verifies but the comparison reports a difference.
