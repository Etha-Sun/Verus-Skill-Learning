# Direct reuse of an existing lemma or trait bridge

## Scope

- Consult when: A library lemma matches an algebraic goal, or the goal connects serialization, view equality, and marshalability
- Consult when: The selected direct route has a matching installed/declared lemma or trait contract with available premises
- Not for the direct route: Its matching lemma, premises, or required equality connection are unavailable
- Boundary: Cards 003/043 also describe conditional constructor fallbacks; failure of a direct bridge does not exclude those original fallback cases

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 003 and 043 have different premise-to-goal directions. The library-lemma entry is a general option and may also match either case; it is not a third mutually exclusive goal. Constructor fallback remains conditional in the original specialized bodies.

<a id="installed-library-lemma-direct"></a>
- [installed-library-lemma-direct](direct-existing-lemma-bridge--installed-library-lemma-direct.md): Existing library lemma matches the goal.
  - When: A library lemma has the required algebraic conclusion and available premises.
  - Avoid: No matching lemma, missing premises, or incompatible equality form.

<a id="original-card-003"></a>
- [original-card-003](direct-existing-lemma-bridge--original-card-003.md): Marshalable + equal serialization to equal views.
  - When: Both values are marshalable, serialized representations agree, and an existing trait/instance promises view equality.
  - Avoid: Trait unavailable or its view relation cannot imply the required structural equality.

<a id="original-card-043"></a>
- [original-card-043](direct-existing-lemma-bridge--original-card-043.md): Equal abstract views to equal marshalability.
  - When: The premise is abstract-view equality and the goal is equality of marshalability predicates.
  - Avoid: The goal has a different proof direction; an uninstantiable direct bridge requires the original conditional fallback.

Read: `python3 reference_read.py direct-existing-lemma-bridge --rules ID [ID ...]`

Whole reference: `python3 reference_read.py direct-existing-lemma-bridge --full` or [direct-existing-lemma-bridge--full.md](direct-existing-lemma-bridge--full.md).
