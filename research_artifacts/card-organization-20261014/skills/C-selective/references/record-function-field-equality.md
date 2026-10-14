# Record equality with function-valued fields

## Scope

- Consult when: Goal is equality of records containing function-valued projection fields
- Consult when: Pointwise premise is available or built-in extensional equality is needed
- Not for: Pointwise premise is incomplete
- Not for: No function-valued field is involved

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 004 addresses the remaining record-equality goal from full pointwise agreement; 005 is explicitly conditioned on direct function equality failing and unavailable/rejected helper names. Distinguish the observed proof state, not two different mathematical premises.

<a id="rule-card-004"></a>
- [rule-card-004](record-function-field-equality--rule-card-004.md): Record equality from full pointwise field agreement.
  - When: Record equality is the failing postcondition and every index of a function-valued field already agrees.
  - Avoid: Agreement covers only some indices or other record fields are not known equal.

<a id="rule-card-005"></a>
- [rule-card-005](record-function-field-equality--rule-card-005.md): Direct function-value equality remains unproved.
  - When: Full pointwise agreement exists but direct function equality and guessed helpers fail.
  - Avoid: No installed extensional equality relation or incomplete pointwise agreement.

Read: `python3 reference_read.py record-function-field-equality --rules ID [ID ...]`

Whole reference: `python3 reference_read.py record-function-field-equality --full` or [record-function-field-equality--full.md](record-function-field-equality--full.md).
