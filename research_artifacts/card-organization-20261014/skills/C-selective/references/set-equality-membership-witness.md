# Set equality by membership extensionality and witnesses

## Scope

- Consult when: Goal is equality of sets/set images or a sequence-set view after removal
- Consult when: No direct matching library lemma
- Consult when: Membership equivalence and witness indices are required
- Not for: Direct library lemma already applies with available premises
- Not for: Membership extensionality is not the missing step

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 002 is broadly triggered by set/image equality but its concrete body uses image/union witnesses. 049 specifically needs duplicate-free sequence removal and shifted indices. Select by that structure; do not assume the image-union recipe proves arbitrary set equalities.

<a id="rule-general-set-image-equality-witness"></a>
- [rule-general-set-image-equality-witness](set-equality-membership-witness--rule-general-set-image-equality-witness.md): Set/image equality; concrete image-union witness case.
  - When: Set/image equality lacks a direct lemma and reverse membership fails; the original body develops the image-of-union case.
  - Avoid: A matching library lemma already closes the goal; do not assume its image-union details fit a different set operation.

<a id="rule-no-duplicate-sequence-removal-set-equality"></a>
- [rule-no-duplicate-sequence-removal-set-equality](set-equality-membership-witness--rule-no-duplicate-sequence-removal-set-equality.md): Set view after duplicate-free sequence removal.
  - When: Removing an index from a duplicate-free sequence must equal removing that element from its set view.
  - Avoid: Duplicates are possible or the removed element occurs at another index.

Read: `python3 reference_read.py set-equality-membership-witness --rules ID [ID ...]`

Whole reference: `python3 reference_read.py set-equality-membership-witness --full` or [set-equality-membership-witness--full.md](set-equality-membership-witness--full.md).
