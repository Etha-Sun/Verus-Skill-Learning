# Avoid ghost extraction of uninterpreted conversion results

## Scope

- Consult when: Ghost code extracts a field through an unwrap of an uninterpreted conversion
- Consult when: Verus reports failed recommendation/precondition about that conversion
- Consult when: Only the surrounding open spec definitions/predicates are needed
- Not for: Proof genuinely depends on a property of the conversion result not captured by open predicates

## Rules

- [Avoid ghost extraction of uninterpreted conversion results](#card-059)

<a id="card-059"></a>
## Avoid ghost extraction of uninterpreted conversion results

Source cards: card-059

**Trigger:** Verus reports a failed recommendation or precondition about an uninterpreted conversion when ghost code extracts a field through an unwrap, while the surrounding entailment is still unproved. **Action:** Remove the ghost extraction of the conversion result. Reason at the spec level using the open definitions and predicates around that opaque value. Local bindings of the same predicate forms are acceptable, but do not call the uninterpreted conversion in ghost code as if its success were known. **Why:** The uninterpreted conversion has no body proving its success in ghost code, while the proof only needs the logical relationship expressed by the open closures and predicates. **Validate:** Re-run Verus; the failed recommendation should disappear, leaving only the real target obligation, which should then be closed by the entailment bridge. **Avoid when:** The proof genuinely depends on a property of the conversion result that is not captured by the existing open predicates; then the missing premise must be supplied separately, not bypassed.

- Distinguish from [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque function route exposes a definition through counterpart/connector; this route removes an unsupported ghost extraction instead.

- Related [opaque-spec-function-facts](opaque-spec-function-facts.md): Opaque function route exposes a definition through counterpart/connector; this route removes an unsupported ghost extraction instead.
