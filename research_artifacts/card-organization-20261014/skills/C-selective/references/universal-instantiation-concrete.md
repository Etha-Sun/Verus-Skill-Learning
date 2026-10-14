# Instantiate an available universal fact at a concrete term

## Scope

- Consult when: A whole-sequence, entailment/validity, or temporal universal fact is available but not used at a concrete index, execution, or term
- Consult when: No trigger-inference diagnostic is present, or local aliases hide the matching form
- Not for: A trigger-inference error requires explicit trigger annotation
- Not for: The failure is a missing antecedent inside a quantified proof block

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 037 specializes an available sequence fact at an in-bounds index; 058 an available entailment at one execution; 076 stability facts at a recursive helper with alias-sensitive matching. This is fact instantiation, not a general trigger-inference repair.

<a id="card-037-whole-sequence-element-helper"></a>
- [card-037-whole-sequence-element-helper](universal-instantiation-concrete--card-037-whole-sequence-element-helper.md): Whole-sequence fact missing at one index.
  - When: A whole-sequence validity/range premise is available but an element assertion at the loop index fails.
  - Avoid: The index is not in bounds or the element property does not follow.

<a id="card-058-entailment-implication-concrete"></a>
- [card-058-entailment-implication-concrete](universal-instantiation-concrete--card-058-entailment-implication-concrete.md): Entailment premise inactive at one execution.
  - When: An entailment/validity premise exists but asserting its conclusion at a concrete execution fails.
  - Avoid: Mismatching execution type or implication surface form.

<a id="card-076-alias-inline-trigger-instantiation"></a>
- [card-076-alias-inline-trigger-instantiation](universal-instantiation-concrete--card-076-alias-inline-trigger-instantiation.md): Alias facts miss quantified stability precondition.
  - When: A recursive helper fails stability after always-facts reached a suffix through local aliases.
  - Avoid: Aliases do not affect matching or trusted quantified facts are absent.

Read: `python3 reference_read.py universal-instantiation-concrete --rules ID [ID ...]`

Whole reference: `python3 reference_read.py universal-instantiation-concrete --full` or [universal-instantiation-concrete--full.md](universal-instantiation-concrete--full.md).
