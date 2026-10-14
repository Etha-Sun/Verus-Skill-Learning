# Temporal always/suffix goals via existing shift or unfolding helpers

## Scope

- Consult when: Goal is a suffix-wise or always-derived property
- Consult when: An existing accepted unfolding/shift helper matches the available premise
- Consult when: Satisfaction, always, lifting, head, and next-state definitions are open enough
- Not for: Helper is absent or would require a new trusted body
- Not for: Current assumption does not match helper precondition

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 014 starts from a nested-always goal and a forward-shift helper. 025 starts from an always-lifted action premise and seeks suffix-wise action satisfaction with an unfolding helper. A larger proof may need both; match the current premise and goal.

<a id="nested-always-forward-shift-helper"></a>
- [nested-always-forward-shift-helper](temporal-suffix-shift-helper--nested-always-forward-shift-helper.md): Nested always with an existing suffix helper.
  - When: An empty proof must establish nested always and the context supplies a forward-shift helper.
  - Avoid: Missing helper, insufficient unfolding, or a mismatching assumption.

<a id="always-lifted-action-unfolding-helper"></a>
- [always-lifted-action-unfolding-helper](temporal-suffix-shift-helper--always-lifted-action-unfolding-helper.md): Always-lifted action to every suffix.
  - When: An always-lifted action premise must yield suffix-wise satisfaction and an unfolding helper exists.
  - Avoid: The helper is absent or not already accepted without a new trusted body.

Read: `python3 reference_read.py temporal-suffix-shift-helper --rules ID [ID ...]`

Whole reference: `python3 reference_read.py temporal-suffix-shift-helper --full` or [temporal-suffix-shift-helper--full.md](temporal-suffix-shift-helper--full.md).
