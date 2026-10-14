# Compound temporal stability via existing stability and conjunction rules

## Scope

- Consult when: Target is a stable compound temporal predicate such as a conjunction of always-lifted predicates and/or finitely many universal fairness components
- Consult when: Existing stability, conjunction, or stabilization proof objects/macros are available
- Not for: Target is not a finite conjunction of always-lifted or similarly stable predicates
- Not for: Required local rules or proof objects are absent or incompatible

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** Universal fairness/action conjuncts distinguish the first entry. The next two cover overlapping always-conjunction goals with different available helpers; neither excludes the other. The extra-wrapper entry is a specific failed-call diagnosis, not a required stage.

<a id="compound-stability-universal-components"></a>
- [compound-stability-universal-components](compound-stability-existing-rules--compound-stability-universal-components.md): Compound stability with universal obligations.
  - When: An always-step conjunct is combined with universal fairness or action obligations.
  - Avoid: Missing component premises or unproved conjunction-stability rule.

<a id="always-conjunction-per-conjunct-stability"></a>
- [always-conjunction-per-conjunct-stability](compound-stability-existing-rules--always-conjunction-per-conjunct-stability.md): Always-conjunction with pairwise stability helpers.
  - When: The target is a left-nested conjunction of always predicates and matching always/conjunction helpers are available.
  - Avoid: Unavailable helpers or incompatible predicate shapes/nesting.

<a id="existing-stabilization-proof-object-lifted-conjunction"></a>
- [existing-stabilization-proof-object-lifted-conjunction](compound-stability-existing-rules--existing-stabilization-proof-object-lifted-conjunction.md): Always-conjunction with a local proof object or macro.
  - When: The target is a finite always-lifted conjunction and a matching local proof object or macro accepts its lifted arguments.
  - Avoid: Absent/incompatible proof objects or wrong predicate lifting level.

<a id="always-stability-extra-wrapper-precondition"></a>
- [always-stability-extra-wrapper-precondition](compound-stability-existing-rules--always-stability-extra-wrapper-precondition.md): Extra always wrapper in a helper precondition.
  - When: A conjunction-stability precondition fails after an already wrapped predicate was given to always-stability.
  - Avoid: The exact contract expects that wrapper shape or other premises are missing.

Read: `python3 reference_read.py compound-stability-existing-rules --rules ID [ID ...]`

Whole reference: `python3 reference_read.py compound-stability-existing-rules --full` or [compound-stability-existing-rules--full.md](compound-stability-existing-rules--full.md).
