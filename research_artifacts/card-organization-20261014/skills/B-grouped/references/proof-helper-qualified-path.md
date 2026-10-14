# Qualified proof-only helper/macro references

## Scope

- Consult when: Proof helper, macro, or closure is reported out of scope
- Consult when: Adding a top-level import would survive deghosting and cause a safety comparison difference
- Consult when: The item is exposed under a fully qualified path
- Not for: Difference is a real executable or contract change
- Not for: Fully qualified path is not the installed path

## Rules

- [Fully qualified path for out-of-scope proof-only helpers and macros](#qualified-proof-helper-macro-path)
- [Sequence-equality closure qualified reference](#sequence-equality-closure-qualified-path)

<a id="qualified-proof-helper-macro-path"></a>
## Fully qualified path for out-of-scope proof-only helpers and macros

Source cards: card-055, card-065

**Trigger:**
- Verus reports that a proof-only helper is not in scope.
- Verus reports that a proof-only macro is not in scope.
- Verus reports that a proof/ghost macro is not in scope.
- Simply adding a top-level import may later make Lynette report a deghosted source difference.
- Adding a top-level import would survive deghosting and later cause the proof-only safety comparison to report that the files are different.

**Premises:**
- The intended helper or macro is exposed under a fully qualified usable form at the installed path; confirm the correct path from the compiler diagnostic or the installed library before editing.
- The item is a proof-only or proof/ghost item rather than a normal executable item.
- The helper does not produce executable artifacts that must remain after deghosting.

**Action:**
- Invoke the helper or macro through its fully qualified crate path at each use site instead of adding a top-level import.
- Confirm the correct path from the compiler diagnostic or the installed library before editing.
- If a type-inference diagnostic then appears on an empty sequence argument, annotate that empty sequence with the intended element type.

**Why:**
- A top-level import can remain in the compared Rust token stream after deghosting and cause a false behavior-preservation difference, whereas a fully qualified call inside the ghost body is more likely to disappear together with the proof code.
- Fully qualified macro invocations are ghost-only and deghost clean, whereas a top-level import can leak into the generated non-proof code and make the compared files differ.

**Validate:**
- Re-run Verus to clear the name-resolution error, then run Lynette or the proof-only safety comparison.
- If Lynette still reports a difference, inspect whether any added import or renamed ghost identifier survives deghosting and adjust accordingly.
- Remove any import and check that Verus passes with no remaining scope or type errors; the proof-only safety comparison should exit successfully.

**Avoid when:**
- The fully qualified path is not the installed path for the desired helper or macro, or the macro is not exposed in a fully qualified usable form.
- The helper produces executable artifacts that must remain; merely forcing a qualified path will not resolve the underlying availability or preservation issue.
- The surrounding build already contains the import harmlessly and the proof-only safety comparison passes with it.


<a id="sequence-equality-closure-qualified-path"></a>
## Sequence-equality closure qualified reference

Source cards: card-068

**Trigger:** A sequence-equality closure mechanism is reported as not in scope, or the only easy way to bring it into scope is a new top-level import that the proof-only safety comparison rejects.
**Action:** Invoke the existing sequence-equality mechanism through its fully qualified library path without adding a new top-level declaration. If the closure still fails, first supply the explicit length and elementwise obligations it requires, then invoke it once those obligations are available.
**Why:** A new top-level import changes the top-level declarations relative to the immutable input and can make the proof-only safety comparison report that the files differ. The fully qualified call uses the existing library path without adding a top-level declaration, while the closure mechanism still requires the underlying equality facts to be established.
**Validate:** Re-run Verus to ensure the scope error is gone and the proof verifies. Then run the proof-only safety comparison and require it to pass.
**Avoid when:** The required closure mechanism is not exported under the library root in the installed version, or the local comparison policy already accepts the top-level import and a different safe mechanism is needed.

- Distinguish from [post-verification-cleanup](post-verification-cleanup.md): Qualified-path route is chosen during proof construction to avoid a future deghosted difference; cleanup route handles an already verified proof with remaining warning/diff.

- Related [post-verification-cleanup](post-verification-cleanup.md): Qualified-path route is selected during proof construction to prevent an import from surviving deghosting before a comparison is run; post-verification-cleanup is used only after the proof already verifies and a warning or deghosted-code difference remains.

- Related [natural-integer-type-mismatch](natural-integer-type-mismatch.md): Natural/integer type route covers numeric and empty-sequence type mismatches generally. The empty-sequence annotation here is only a follow-up to a type-inference diagnostic after using a qualified proof/ghost macro path.
