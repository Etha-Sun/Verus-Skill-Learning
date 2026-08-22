# SkillOpt Verus failure-driven V-FACE proposal

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-08-21T21:39:56-05:00`
- status: `complete`

## Objective

Use the completed SkillOpt self-evolution lineage and cross-model test failure
trajectories to identify the task-specific bottleneck, generate alternatives,
run bounded offline pilots, audit novelty, and freeze the smallest credible
next method and experiment gate.

## Evidence Reviewed

- Self-evolution selection: S0 13/20, E1 14/20, E2 12/20, E3 15/20,
  E4 14/20, plus four slow/repair candidates.
- Cross-model blank/S1/S2 valid solved counts: GPT 18/17/17, DeepSeek
  14/14/14, GLM 15/15/16, Qwen 3/5/6.
- Concrete trajectories covering over-expansion, missing semantic bridges,
  unexecuted correct guidance, wrong existing-lemma selection,
  parser/type/ghost-mode failures, invalid harnesses, and incomplete provider
  terminals.
- Recent closest work on skill evolution/retrieval, context attribution,
  executed replay, and formal proof retrieval.

The inspected test-20 was used only for post-hoc mechanism diagnosis. It is no
longer eligible for method selection or confirmatory evaluation.

## Offline Pilots

Generated outputs live under:

`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/idea-discovery-skillopt-verus-20260821_210659/pilots/`

1. Whole-skill routing ceiling: NEGATIVE. The oracle union of nine existing
   candidates is 15/20, equal to the best fixed candidate; whole-document
   routing has zero development headroom.
2. Structured trace compaction: narrowly POSITIVE. 180 trajectory summaries
   preserve required ledger fields while reducing selected evidence from
   51,692,832 to 96,996 bytes (532.94x). This does not establish semantic
   sufficiency for the optimizer.
3. Naive near-miss constructibility: WEAK. Only 1/8 mixed-outcome tasks has a
   mechanically visible success-only lemma contrast, making action
   compilation the primary feasibility risk.

No GPU or live actor experiment was launched.

## Result

The main bottleneck is not lack of an ordinary reference retriever. SkillOpt's
whole-document action and whole-trajectory scalar outcome confound:

- environment/tool validity;
- whether a local proof action is technically valid;
- whether the actor adopts a presented action;
- whether exposure causes unrelated proof-search drift.

The selected Phase-0 idea is V-FACE. It freezes three typed proof-action
templates, separates cross-checkpoint `CardTemplate` from checkpoint-local
`CardInstantiation`, collects Build-only forced-edit validity and randomized
exposure evidence, and predicts admission on independent evaluable pairs.
Adoption is telemetry, not a causal mediator. `NON_INSTANTIABLE` pairs are
compatibility statistics only and cannot improve decisive coverage.

Independent novelty review rated the core verifier-mediated atomic-artifact
increment PARTIAL (5/10); abstention/contraindication and checkpoint schemas
were rejected as standalone novelty. Four independent method reviews improved
the proposal from 6.10 to 8.00/10. The final verdict is design-frozen for
Phase 0, empirically REVISE.

## Canonical Artifacts

- `idea-stage/IDEA_REPORT.md`
- `idea-stage/IDEA_REPORT.html`
- `idea-stage/docs/research_contract.md`
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `refine-logs/REVIEW_SUMMARY.md`
- `.aris/traces/novelty-check/2026-08-21_run01/`
- `.aris/traces/research-review/2026-08-21_run02/`

## Caveats

- No prospective compiler or admission result exists.
- Novelty remains partial and may resolve to a formal-skill audit/benchmark.
- The 533x compression is engineering feasibility, not evidence that semantic
  optimizer judgment is preserved.
- Existing test-20 and prior 40+20 development data cannot support a new
  confirmatory claim.
- Do not claim solved-rate, token-efficiency, causal-credit, or no-regression
  improvement.

## Decision / Next Step

Run only R001-R005 from `refine-logs/EXPERIMENT_TRACKER.md`: unused-pool
inventory, contamination/split audit, and the 30-checkpoint CPU compiler gate.
The gate requires at least 18/30 instantiable checkpoints, at least 90 percent
blind semantic correctness among instantiated edits, 100 percent Lynette
fidelity, and at most 5 percent out-of-region or unrelated edits. If it fails,
stop optimizer/retrieval work and publish the extractor failure taxonomy.

Raw and sealed data remained read-only and unmodified. All generated pilot
outputs were written only below `VERUS_SKILL_RUN_ROOT`; only reviewed compact
reports, contracts, and pointers were stored in this repository.
