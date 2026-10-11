# Pilot trace audit and scale decision

Parent: completed24episode Executive development pilot, same two arms/common TASK.
Question: are residual/improvement paths interpretable and safe enough to broaden
the matched comparison without tuning? Scope: all24saved CLI traces,1020saved
candidate snapshots and24final candidates. Full census for trusted-block checks
and command flags; case rubric below covers all4actor timeouts, bothbodyreaders
and the short-lemma-chain positive case. No new model/solver calls for this audit.

## Observable findings

- Supplied trusted blocks: zero exact block changes in saved snapshots/finals.
  Initial audit regex missed a stacked attribute on generated_name_is_unique in
  b9e; Astra independently supplemented its check. Fixed parser and added test,
  regenerated audit includes all5trusted blocks in each of4b9e episodes. This is
  saved-snapshot coverage, not every transient edit or full Rust AST certification.
- Operational commands:9episodes flagged. Toolchain/binary introspection and
  PATH printing occur; actors also create/read private /tmpscratch or compiler
  logs. Flags mix actual contract deviations and paths requiring interpretation.
  No sensitive-path pattern flags observed; this is not a complete syscall audit
  or a guarantee of no unrecorded access. No read of reference/sealed sources
  observed in reviewed commands. Keep proof validity separate from access claims.
- aded revised repeat0 timeout: final proof includes a pointwise DeMorgan helper
  but the reverse quantified direction remains empty, two failed assertions in
  final tool return. Repeated vstd searches and toolchain inspection do not close
  the concrete lambda/trigger bridge. Revised repeat1 passes; initial repeats
  show opposite outcomes. This remains unstable, not a repaired class of problems.
- aded initial repeat1 timeout: repeated assertion failures persist despite VIR/
  SMT diagnostic exploration. This is a real unresolved proof, not slow card IO.
- 9b9f initial repeat0 timeout: repeated quantified-antecedent warnings, auxiliary
  diagnostics and repeated same failures persist. Revised repeat0 explicitly
  reads006/058 and implements antecedent branches plus full implication-form
  instances, eventually passes. It still makes an initial missing-parentheses
  error, then corrects it; diagnostic-first does not eliminate every syntax error.
- b9e initial repeat1 timeout: late diagnostics show postcondition failures, final
  saved candidate passes terminal validation after actor cutoff. Revised repeat1
  passes within budget at591.9s and uses scratch experiments; this is a narrow
  budget-margin improvement, not a dramatic newly solved proof or strict-scope
  certified success. Both arms perform toolchain exploration in this task.
- a23a revised repeat0: actual reads020/029/056/058/077, progress message identifies
  missing entailment instantiation and explicitly cites058; code diff adds full
  implication-form satisfaction before its conclusion. Final verification passes.
  This is observed card-consistent application, not proof of causal benefit
  against an otherwise identical no-card run.
- 3ce revised repeat0: final diff calls the two existing supplied contracts and
  concludes the target in a short chain; both original trusted blocks unchanged.
  This corresponds to the intended policy,44.5s versus178.0s in initial repeat0;
  both arms already pass under common corrected TASK, so no scope-fix causal claim.

## Evidence and decision

External VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-full-20261010-YUSsK2/
pilot_audit/{audit.json,dev_*.diff}. audit.json hashes1093original evidence files;
all hashes checked unchanged. Prior regex audit retained in pilot_audit_v1/,
not overwritten. Source script scripts/audit_executive_pilot.py, coverage test
tests/test_full_executive_validation.py. Rubric: actual verifier diagnostics,
saved candidate diff, trusted-block equality, command scope, consulted-card
message corroborated by code; do not infer hidden reasoning or causal effects.

No reference leakage/trusted-background mutation blocker identified within this
inspection scope. Broaden matched development comparison to all validation20
without editing prompts/cards/runner; retain operational limitations and audit
new traces. Fresh80episodes, separately report pilot6/remaining14 and repeats.
Do not claim augmentation efficacy, generalization or strict operation compliance.
