# Temporal property at arbitrary natural offset by induction

## Scope

- Consult when: Property must hold at an arbitrary natural offset or suffix index
- Consult when: Induction on the natural index is structurally appropriate
- Consult when: Extensional execution equality principle is available
- Not for: Property is not inductive over chosen index
- Not for: No pointwise/extensional equality principle for base/step bridges

## Rules

- [Temporal property at an arbitrary natural offset by induction](#card-039-verbatim)

<a id="card-039-verbatim"></a>
## Temporal property at an arbitrary natural offset by induction

Source cards: card-039

**Trigger:** A recursive proof function has an empty or insufficient body and cannot establish a temporal property at an arbitrary natural offset.
**Action:** Add a recursive helper with a decreases clause on the natural index. In the base case, prove that the zero-offset suffix equals the original execution by using an existing extensional equality lemma rather than a bare equality assertion. In the inductive case, instantiate the universal transition assumptions at the predecessor index, derive the property at the successor, and, if the goal index differs from the successor expression, bridge them with the same extensional equality lemma before carrying the property across that equality.
**Why:** Induction on the natural index matches the structure of the property; extensional equality of execution-like values is not automatically derived from directly asserting equality, so the supplied pointwise-equality lemma supplies the missing logical premise.
**Validate:** Rerun Verus; the recursive helper and the original proof function should verify, and Lynette should report only proof-only differences.
**Avoid when:** The property is not inductive over the chosen index, or no pointwise or extensional equality principle is available to justify the execution equalities needed for the base and step cases.

- Distinguish from [temporal-suffix-shift-helper](temporal-suffix-shift-helper.md): Induction route uses a recursive helper with decreases; suffix-shift route uses an existing helper directly.

- Related [temporal-suffix-shift-helper](temporal-suffix-shift-helper.md): Induction route uses a recursive helper with decreases; suffix-shift route uses an existing helper directly.
