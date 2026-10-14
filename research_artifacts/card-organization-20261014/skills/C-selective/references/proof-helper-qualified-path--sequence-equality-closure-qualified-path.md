# Qualified proof-only helper/macro references

## Scope

- Consult when: Proof helper, macro, or closure is reported out of scope
- Consult when: Adding a top-level import would survive deghosting and cause a safety comparison difference
- Consult when: The item is exposed under a fully qualified path
- Not for: Difference is a real executable or contract change
- Not for: Fully qualified path is not the installed path

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
