# Refinement Report

**Problem**: SkillOpt formal proof skill credit/admission。
**Date**: 2026-08-21
**Rounds**: 4
**Final score**: 8.00/10
**Verdict**: REVISE empirically; design-frozen for Phase 0。

## Outputs

- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Idea report: `idea-stage/IDEA_REPORT.md`

## Score Evolution

| Round | Fidelity | Specificity | Contribution | Frontier | Feasibility | Validation | Venue | Overall |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9 | 6 | 5 | 7 | 5 | 5 | 4 | 6.10 |
| 2 | 9 | 7 | 6 | 8 | 6 | 8 | 6 | 7.10 |
| 3 | 9 | 8 | 7 | 8 | 7 | 8 | 6 | 7.70 |
| 4 | 9 | 9 | 7 | 8 | 7 | 8 | 7 | 8.00 |

## Method Evolution Highlights

1. Replaced an invalid causal decomposition with forced technical validity, randomized exposure ITT and adoption telemetry.
2. Introduced the decisive `CardTemplate → STATIC_INSTANCE → post-decision execution` firewall.
3. Removed runtime retrieval/calibration from the initial claim and froze a non-degenerate prospective admission rule.

## Pushback and Drift Log

- Rejected adding RL, GNN, learned retriever, Shapley or more patch families before compiler evidence.
- Rejected calling abstention, contraindication or proof-state retrieval separate novelty.
- Rejected using the already-inspected test set for any gate.

## Remaining Weaknesses

Novelty is only PARTIAL; compiler feasibility, label stability, sufficient evaluable pairs, ≥40% coverage and equal-budget advantage are untested. These cannot be solved by another design round.

## Raw Reviewer Responses

Full forensic responses are stored under:

- `.aris/traces/novelty-check/2026-08-21_run01/`
- `.aris/traces/research-review/2026-08-21_run02/`

## Next Step

Execute R001–R005 only. If the compiler gate fails, stop optimizer/retrieval work and publish the failure taxonomy.
