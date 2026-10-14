# Explicit triggers for quantifier inference failures

## Scope

- Consult when: Verus cannot infer triggers for a quantified assertion, choose, or witness term; cards 018/057 also cover a separately diagnosed missing antecedent
- Not for: Only a low-confidence trigger note remains after successful verification
- Boundary: A missing-antecedent-only case is not card-034's trigger-only case; it remains within cards 018/057's stated coverage
- Not for: A genuinely missing logical premise, rather than trigger selection or antecedent availability

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 034 focuses on trigger inference only. 018 and 057 also cover independently diagnosed missing antecedents; 018 emphasizes witness/entailment terms, 057 state/suffix terms. An assertion trigger error can match all three. 018 retains a source Action/Validate wording tension; no exclusive split is claimed.

<a id="original-card-018"></a>
- [original-card-018](trigger-inference-annotation--original-card-018.md): Trigger/antecedent coverage with witness or entailment terms.
  - When: Assertion/witness choice has a trigger-inference error or a quantified proof lacks its antecedent; witness/entailment terms are this rule's focus.
  - Avoid: Neither diagnostic present or a real premise missing; the source's Action/Validate wording tension remains.

<a id="original-card-034"></a>
- [original-card-034](trigger-inference-annotation--original-card-034.md): Trigger-only coverage for assertion or choose.
  - When: Verus cannot infer triggers for a quantified assertion or witness choice.
  - Avoid: Only a successful-proof trigger note remains; a missing-antecedent-only case is outside this rule's trigger.

<a id="original-card-057"></a>
- [original-card-057](trigger-inference-annotation--original-card-057.md): Trigger/antecedent coverage with state or suffix terms.
  - When: A universal assertion has a trigger-inference error or lacks its implication antecedent; quantified state/suffix terms are this rule's focus.
  - Avoid: A new logical premise is needed; warning cleanup after success is not evidence of required proof repair.

Read: `python3 reference_read.py trigger-inference-annotation --rules ID [ID ...]`

Whole reference: `python3 reference_read.py trigger-inference-annotation --full` or [trigger-inference-annotation--full.md](trigger-inference-annotation--full.md).
