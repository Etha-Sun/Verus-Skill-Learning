# Secondary Method Review

Reviewer: separate Codex agent context, same model family. The requested legacy GPT-5.5 reviewer was unavailable. No spending authority. The reviewer did not independently verify all external papers. Text below is preserved verbatim from the two responses.

## Initial review

**Verdict: REVISE; ready for a zero-model-call diagnostic audit.** The direction is worthwhile, but the first experiment should be simpler and its causal claim narrower. This is a same-family secondary Codex review, not independent cross-family assurance; the requested legacy GPT-5.5 reviewer was unavailable.

| Dimension | Score |
|---|---:|
| Problem fidelity | 9 |
| Method specificity | 7 |
| Contribution quality | 6 |
| Frontier leverage | 8 |
| Feasibility | 7 |
| Validation focus | 6 |
| Venue readiness | 5 |
| Weighted overall | **7.1/10** |

These are qualitative planning judgments, not evidence of scientific validity.

**1. The bottleneck remains a hypothesis.** The local results establish uncertain benefit from augmentation and cards, not deficient long-trace analysis. The 31/40→32/40 comparison could reflect extraction, insufficient diversity, retrieval, execution, or ordinary variation. The reported 5997 case is particularly useful: explicit syntax advice existed, yet the agent still made repeated parse errors. Better extracted rules may therefore fail because runtime execution ignores or misapplies them. Conversely, the 3310 bridge example supports the value of identifying the right missing premise, but does not establish that a particular card caused its discovery. Keep “long traces overwhelm analysis” as a falsifiable motivation, not the paper’s established premise.

**2. The method currently combines several possible interventions.** Verifier-boundary segmentation, state reconstruction, contrasts, applicability conditions, and transfer admission each could change results. Moreover, “test transfer before admitting broad applicability” has no operational rule yet. Do not build a leave-one-task-out admission controller in the first pilot. Start with one intervention: **replace narrative trace inputs with evidence-linked pre-state/action/post-feedback records, while keeping the existing distiller and deployment interface fixed**. Treat applicability fields as a common output contract for every extraction arm, rather than a treatment-only advantage. Defer replay and transfer-gated admission.

**3. Five-fold cross-fitting is premature.** It multiplies independently generated skill banks, lineage audits, extraction budgets, and failure points before showing the proposed representation helps. It also cannot guarantee family-disjoint transfer merely because folds contain different task IDs. Start with a single locked training split. Five folds become worthwhile only if the small test reveals a plausible effect and a stable pipeline.

**4. Repaired78 cannot be a common core on training targets.** Excluding target raw traces is insufficient: target-specific information can survive in original SkillOpt cards, consolidated text, indexes, repaired descriptions, augmentation descendants, final solutions, and prompt choices. Repaired78’s provenance must be excluded on training-held-out targets, not merely described. The “initial global core” needs the same ancestry audit. Use only task-agnostic baseline instructions whose provenance is acceptable, and regenerate learned banks from the permitted source pool. If lineage cannot be established, do not label that arm leakage-safe. On validation, train-only ancestry prevents direct source overlap, but repeated validation-driven prompt or card repair still creates adaptive development bias.

**5. Offline differences cannot isolate extraction from runtime use.** A blinded audit can assess evidence fidelity and applicability, but it does not prove deployed utility. Even with a fixed actor and reader interface, new cards can change which documents the actor reads and how it reasons. A live comparison therefore estimates the **end-to-end effect of the extraction recipe under a fixed deployment policy**, not a pure extraction effect. Record uptake and misapplication as diagnostics. Avoid a factorial extraction×retrieval campaign until there is a positive result worth decomposing.

**6. Novelty is not established.** The proposal correctly acknowledges close work, but the actual differentiator still needs method-level comparison. Segmentation, contrastive reflection, structured memories, and verifier feedback are insufficient individually. I have not independently verified the cited papers in this review; their titles and claimed mechanisms must not be treated as confirmed by my assessment. A credible eventual distinction could be grounded, auditable action evidence with demonstrably fewer unsupported or inapplicable lessons and better budgeted transfer.

**Minimal first pilot**

- Lock **32 source training tasks and 8 held-out training tasks** from the existing train40. Choose membership before candidate results using declared project/outcome/trace-length criteria and a deterministic rule. Preserve all val20 and test20 from this pilot.
- Audit duplicates and dependency families. If the 32/8 split cannot be family-disjoint, call the result task-held-out transfer within the existing distribution; do not imply family-level generalization.
- Generate source-only banks for **three extraction recipes**: native SkillOpt, ordinary chunk-and-merge, and evidence-record analysis. Match teacher model, total extraction allowance, final skill budget, available source evidence, and deployment interface. Direct long-context analysis can be the offline diagnostic comparator; do not silently give it less source information.
- Evaluate **four arms**: no learned memory plus those three banks, on the same 8 targets, one fresh repeat each: **32 actor episodes**, each capped at 600 seconds. This is an engineering screen, not confirmatory evidence.
- Declare the actual extraction call/token ceiling and API dollar ceiling before launch. Eight tasks cannot support a statistical “no solved loss” guarantee; the proposed gain/token thresholds are development heuristics.
- Account for all physical attempts, extraction expense, failures, and timeouts. Never select on successful-pair efficiency alone.

**Approved now in methodological terms:** preserve the brief, inventory provenance and snapshots, verify evaluator contracts, prepare the deterministic split manifest, and specify matched arms without model calls. **Not approved by this review:** paid extraction or solver execution, full cross-fitting, validation expansion, or test access. Those require an explicit launch budget/scope from the user; a reviewer verdict supplies no spending permission.

**Drift warning:** none if the project remains about transferable experience from traces. Improving stopping behavior alone could be useful, but would be a different primary contribution.

**Simplification:** one split, one evidence representation intervention, one frozen deployment interface; postpone replay, admission controllers, and cross-domain experiments. **Modernization:** none needed.

## Narrowed-proposal review

**READY_FOR_DIAGNOSTIC.** The narrowed proposal preserves the research objective and removes the main unnecessary complexity. The 32-episode screen is sufficiently specified as a proposed later scope: 8 training-held-out targets × 4 arms × 1 repeat, fixed 600-second actor budget, common deployment settings, matched B2/M interfaces, and explicit financial ceilings. It is not yet dispatch-ready.

Before any model calls, resolve these concrete blockers:

1. **Freeze actual membership and lineage.** Record the 8 target IDs, donor IDs, all excluded descendants/cards/solutions, and the provenance of B0’s fixed guidance. Task-specific knowledge in shared baseline instructions would contaminate every arm. Reduced donor counts are acceptable if explicitly frozen.
2. **Freeze operational budgets.** Specify per-arm extraction input/output tokens, calls, consolidation allowance, actual model identifiers/settings, and treatment of oversized inputs. State whether the preliminary direct/chunk/verifier diagnostic is included in each arm’s allowance or separately charged; avoid accidentally giving M extra analysis.
3. **Implement budget enforcement before dispatch.** USD15 is a proposed cap, not a cost estimate. Outstanding concurrent requests can overshoot a simple “stop when ledger reaches limit” rule. Reserve a bounded allowance for requests already in flight, or stop launching sufficiently before the ceiling.
4. **Confirm evidence and evaluator readiness.** Restore approved data/output paths, check snapshot coverage, and verify that source-only skill generation works without relaxing the historical production wrapper’s constraints.
5. **Specify partial-run interpretation.** If the dollar cap interrupts the experiment, retain all attempts but do not compare unmatched completed subsets as if the full four-arm screen had finished.

The planned additions correctly narrow interpretation: live outcomes estimate the end-to-end extraction-recipe effect under fixed deployment, and a non-family-disjoint split supports within-distribution task-held-out conclusions.

Minor wording correction: 2.67 hours is an idealized execution estimate, not a wall-clock upper bound.

This check supplies methodological assessment only. It does not authorize spending, establish novelty, or certify that the proposed mechanism will improve performance.
