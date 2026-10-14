# Quantified proof-block antecedent and binder scope failures

## Scope

- Consult when: Proof block, assert-forall, or helper precondition fails inside quantified implication
- Consult when: Diagnostic says antecedent not assumed or facts disappear because binder was shadowed by a fresh symbol
- Not for: Failure is a trigger-inference diagnostic
- Not for: Needed logical premise is genuinely absent, not a scope or antecedent problem

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** All three can match a helper failure caused by a missing antecedent. The merged rule surveys that diagnostic; 023 additionally covers a shadowed bound symbol; 074 focuses on a helper call inside the implication. These are overlapping focuses, not three distinct error classes.

<a id="missing-antecedent-quantified-proof"></a>
- [missing-antecedent-quantified-proof](quantified-proof-antecedent-binder-scope--missing-antecedent-quantified-proof.md): Missing-antecedent diagnostic: general coverage.
  - When: An inner assertion or lemma fails with a missing-antecedent diagnostic inside a quantified implication.
  - Avoid: Antecedent already available, a different premise missing, or a trigger-inference-only failure.

<a id="quantified-binder-scope-verbatim"></a>
- [quantified-binder-scope-verbatim](quantified-proof-antecedent-binder-scope--quantified-binder-scope-verbatim.md): Missing antecedent with binder/available-bound context.
  - When: A quantified proof cannot use antecedent-dependent bounds/facts; the rule also covers a bound symbol shadowed by a fresh one.
  - Avoid: Bounds genuinely absent or no binder/antecedent issue; implication syntax is version-sensitive.

<a id="helper-precondition-implication-branch-verbatim"></a>
- [helper-precondition-implication-branch-verbatim](quantified-proof-antecedent-binder-scope--helper-precondition-implication-branch-verbatim.md): Missing antecedent at a helper-call precondition.
  - When: A helper inside a quantified implication fails its precondition, or that assertion warns its antecedent is not assumed.
  - Avoid: Changing specification requires/ensures, or a goal already discharged by a supplied case lemma.

Read: `python3 reference_read.py quantified-proof-antecedent-binder-scope --rules ID [ID ...]`

Whole reference: `python3 reference_read.py quantified-proof-antecedent-binder-scope --full` or [quantified-proof-antecedent-binder-scope--full.md](quantified-proof-antecedent-binder-scope--full.md).
