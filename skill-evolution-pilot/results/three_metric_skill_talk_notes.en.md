# Three-Metric Skill Case Study: Talk Notes

## 1. Token cost: why R3-A helped and R3-C hurt

| Condition | Slot | Repeats | Verifier-safe | Primary uncached tokens / ETtS | Delta vs fresh H0 | Solver Verus calls | New helpers | Diff additions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fresh H0 | — | 3 | 3/3 | 87,312.7 | 0% | — | — | — |
| `local-proof-surface-cap` screen | R3-A | 1 | 1/1 | 61,232 | -29.87% | 2 | 0 | 139 |
| `three-fact-witness-note` screen | R3-C | 1 | 1/1 | 119,638 | +37.02% | about 6 | 4 | 302 |
| `local-proof-surface-cap` confirmation | R3-A | 3 | 3/3 | 82,391.0 | -5.64% | — | — | — |

- Direct good-versus-bad contrast: R3-A used 58,406 fewer tokens than R3-C, a 48.82% reduction.
- Both trajectories passed Verus, Lynette, and F3. The contrast is not produced by “failing faster.”
- The clearest textual difference is “every return path” versus “every false return.” A organizes the complete proof surface, including true-path coverage; C only reminds the solver about one local fact pattern.
- A imposes “the initial new-helper budget at zero.” C allows a helper once a fact appears twice, leaving an opening for the solver to grow a helper architecture.
- A also says “Repair only the reported local premise or syntax item.” This constrains post-verifier search. The C trajectory instead expands a local witness proof into four helpers.
- A/C/S reading: R3-A is a strong aggressive profile. Aggressive here means removing search freedom, not adding more proof advice. R3-C is concise and conservative, but its applicability assumption is wrong: the global proof architecture was not already settled.
- Generalization: the reusable atoms are the branch ledger, zero-helper first patch, and local-delta repair. The three witness facts—lower inclusion, strict upper inclusion, and abstract disagreement—are IronKV-specific.
- Meta-evolution: the meta-agent did turn R2's witness-completeness observation into a stronger R3 execution cap. That is useful candidate generation, but not validated evolution.
- Confirmation caveat: the three-run improvement is only 5.64%, smaller than H0's 12,908-token range. The result remains `inconclusive_within_h0_range`.
- Talk line: both skills know the witness facts; the cost difference appears when A turns those facts into an executable proof-surface budget.

R3-A source text. The generated file contains a duplicated rendering; this is its complete substantive policy block, preserved verbatim:

```markdown
# Local Proof-Surface Cap

## Applicable state

Use when a visible proof-only Boolean implementation can be related to its specification with existing contracts, local assertions, and constructive counterexamples.

## Ordered policy

1. Quietly compare immutable input and candidate. If identical, read only the candidate; inspect the target, relevant contracts, and checker wrappers once, then lock the commands.
2. Skip the untouched baseline when the visible body already exposes the failed postcondition and helper preconditions.
3. List every return path in a compact ledger. Name existing coverage facts for true paths and, for each false path, a witness with lower inclusion, strict upper inclusion, and abstract disagreement. Classify an exact upper endpoint as excluded.
4. Make one proof-only patch confined to the existing target body. Reuse supplied lemmas and keep the initial new-helper budget at zero. Cover every ledger row before invoking Verus.
5. Preflight quantified assertions, reveals, casts, endpoint strictness, and call preconditions.
6. Run Verus. Repair only the reported local premise or syntax item. Permit one helper only if the same fact is required at least twice and factoring it reduces total proof text.
7. At first success, run the policy checker once on the unchanged candidate and stop.

## Stop/self-disable condition

Self-disable if any ledger row needs semantics unavailable from visible contracts or if a local proof would duplicate a substantial derivation. Continue normal proof-safe solving without enforcing the cap.

## Predicted token-saving mechanism

This removes duplicate source context, an unnecessary baseline, large one-use helpers, and verifier turns over knowingly incomplete branches while keeping later candidate context small.

## Known failure risk

A strict locality bias can produce brittle SMT assertions or obscure a genuinely reusable invariant. The self-disable condition must take precedence over the size target.
```

R3-C source text. The generated file contains a duplicated rendering; this is its complete substantive policy block, preserved verbatim:

```markdown
# Three-Fact Witness Note

## Applicable state

Use when a Boolean proof plan is already clear but a false branch or excluded endpoint could be missed.

## Ordered policy

1. Read the checker wrappers and lock their exact commands. If input and candidate are identical, read only one full source.
2. Before editing, record for every false return one witness and three facts: lower inclusion, strict upper inclusion, and abstract-value disagreement. Check an exact upper endpoint separately.
3. Prefer existing lemmas and assertions inside the target body. Add a helper only for a fact reused at least twice.
4. Run a baseline only if the obligation is unclear. Otherwise make the local proof edit, run Verus, apply only the reported correction, then run the policy checker once and stop.

## Stop/self-disable condition

Self-disable when there is no constructive false path or when all three witness facts are immediate and need no reminder.

## Predicted token-saving mechanism

The small injection preserves the successful local-witness behavior while preventing duplicate reads, late endpoint discovery, and unnecessary helper growth.

## Known failure risk

This note supplies little architectural guidance when representation-to-spec transfer requires a substantial new proof.
```

## 2. Small-model benefit: no solve-rate gain, only lower damage from C

| Condition | Slot | Solved | Requests | Provider tokens | Delta vs H0 | Prompt | Completion | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H0 | — | 2/4 | 29 | 312,656 | 0% | — | — | — |
| `verus-contract-match-loop-r2` | R2-C | 2/4 | 29 | 321,998 | +2.99% | 305,732 | 16,266 | 9,640 |
| `verus-eight-plus-two-ladder-r2` | R2-A | 2/4 | 29 | 490,164 | +56.77% | 455,011 | 35,153 | 29,260 |

| Condition | Direct final state | Closest final state | Unstable final state | Hard final state | Avg new helper lemmas/run |
|---|---|---|---|---|---:|
| H0 | Solved | Compile-invalid, 1 error | Solved | Compiles, 47 verified / 1 logical error | 0.00 |
| R2-C | Solved | Compile-invalid, 2 errors | Solved | Compiles, 47 verified / 1 logical assertion error | 0.00 |
| R2-A | Solved | Compile-invalid, 4 errors | Solved | Compile-invalid, 1 unknown-prover error | 0.00 |

- Correct claim: R2-C is not a primary-metric winner. It is the least harmful complete skill.
- R2-C uses 168,166 fewer tokens than R2-A, a 34.31% reduction, but it still does not beat H0 or solve a new task.
- Proof progress: C preserves a compilable 47-verified/1-logical-error state on the hard task, while A ends on an unsupported prover name. Neither condition improves the solved subset, and neither closes the hard obligation.
- Helper count: all three conditions average 0.00 newly declared proof-function helpers per trajectory. The count is computed from the set difference between the immutable input and final candidate; the union over intermediate snapshots is also zero.
- Existing-lemma calls, assertions, and edits inside the target proof body are not counted as new helper lemmas.
- Therefore the C-versus-A token gap cannot be explained by helper proliferation. It is more consistent with repeated context, longer control reasoning, and compile-regression cycles.
- The clearest textual contrast is “Pick the lemma” → “at most one bridge” → “Run Verus immediately” versus A's ten-request phase schedule, `BEST` state, transition taxonomy, and decomposition controller.
- Both conditions use 29 requests. The token gap therefore reflects the amount of control state carried and regenerated per request, not merely the number of requests.
- C's “same outer operator” is an operational lemma-selection rule. Its “second failed bridge” is an observable stop condition.
- A's schedule looks disciplined, but the discipline exists only as prompt text. The host does not guarantee that the model restores the final compiling checkpoint.
- A/C/S reading: C better matches the small model's limited working memory. A is formally aggressive but cognitively expensive. A large structural DAG could create the same overload.
- Generalization: C may transfer when a visible lemma nearly matches the goal and only one quantified instance or representation bridge is missing. It is not sufficient for genuinely multi-layer correspondence.
- Meta-evolution: R2 learned to reduce the control burden introduced in R1, but this is damage control. R3-C is nearly unchanged in cost, and the solved subset never moves beyond H0.
- Talk line: the small model needs one grounded action plus host-enforced rollback, not a full agent controller rewritten as a skill.

R2-C source text:

```markdown
# One-Lemma Contract Match Loop

## Applicability
Use when the target postcondition is close to an in-scope lemma's `ensures` clause.

## Loop

1. Read the target and visible lemma contracts. Run Verus once. Keep the exact compiling proof body as `BEST`.
2. Pick the lemma whose `ensures` has the same outer operator as the goal. Prefer an exact contract match over an assertion you hope automation will prove.
3. Call that lemma and add at most one bridge:
   - instantiate its quantified result at the needed term;
   - call it separately for each component;
   - state one equality, bound, or cast already justified by the current requires; or
   - for an encoding, establish one field boundary and invoke the existing proof for that field.
4. Run Verus immediately.
5. If Verus passes, run the policy checker and stop. If a compile, type, recommendation, or unknown-name error appears, restore BEST. If the original logical error is unchanged, remove the bridge and try one different bridge class once.
6. After the second failed bridge, stop stacking facts. Preserve BEST and switch to semantic decomposition. Reserve the last two requests for Verus and the policy checker.

## Recovery
Use only identifiers visible in the task or an exact compiler suggestion. One missing name ends name guessing. A helper is forbidden until a concrete instance verifies and repeats. An assertion that merely repeats a precondition or the goal is no progress and must be removed.

## Verifier safety
Change proof code only. Preserve executable behavior, signatures, requires, ensures, and decreases. Never use assumptions, admissions, axioms, external bodies, or bypasses. Report success only when Verus and the policy checker pass on the same candidate.

## Negative scope
This loop does not solve genuinely multi-layer correspondence by itself and does not authorize external inspection, contract changes, executable edits, or policy-only success.
```

R2-A source text:

```markdown
# Eight-Plus-Two Reversible Verifier Ladder

## Applicability
Use for a proof-only Verus repair with at most ten model requests.

## Safety
Edit only permitted proof code. Preserve executable behavior, signatures, contracts, and decreases. Never add an assumption, admission, axiom, external body, or verification bypass. A solve requires both Verus and the policy checker to pass on the same candidate.

## Requests 1-8: work phase

1. Read the task, candidate, immutable input, and skill in one request. Write a private three-line inventory: exact goal; visible lemma ensures that share its outer shape; exact editable proof body.
2. Run Verus. Save `BEST` as the exact current proof body plus its compile status, verified count, and first diagnostic.
3. Choose exactly one move:
   - quantified implication: call the closest lemma, then instantiate it at the required witness;
   - conjunction or product: apply the matching lemma once per required component;
   - encoded concatenation: expose one field boundary with a visible bridge, prove the corresponding field encodings equal, then call existing field injectivity;
   - subset or nested interpretation: introduce one arbitrary witness and connect one semantic representation layer.
4. Make one reversible proof-only edit and run Verus immediately.
5. Classify the transition mechanically:
   - PASS: save BEST and stop substantive editing;
   - PROGRESS: the blocking diagnostic moved closer to the postcondition without new compile/type/recommendation failures; save BEST;
   - NO-PROGRESS: the same logical diagnostic remains; undo the edit before trying one different move;
   - REGRESSION: any syntax, type, recommendation, unknown-symbol, or increased independent-obligation failure; undo immediately to BEST.
6. Never guess a second spelling after an unknown identifier. Use only a name visible in the files or an exact compiler suggestion. Do not replace one guessed sequence or prover API with another.
7. After two equivalent logical diagnostics, restore BEST and change decomposition. For nested proofs, close one layer from witness selection to child or terminal fact before copying that verified pattern. For arithmetic, prove only the cast or bound required by the current semantic step.
8. Freeze the strongest compiling candidate. Add a helper only if one concrete instance already verifies and the identical obligation occurs again. Otherwise keep the concrete fact at its use site.

## Requests 9-10: protected checks

9. Run final Verus on the frozen candidate. Do not add a new idea in this request.
10. If request 9 regressed, restore BEST first and rerun Verus; then run the policy checker on that exact candidate. If Verus passed at request 9, run only the policy checker. Report a solve only if both pass.

## Recovery summary
Unknown symbol: revert, then use an exact visible or compiler-suggested name. Same diagnostic once: revert and change move. Same diagnostic twice: restore BEST and change decomposition. New helper failure: delete the helper. Never finish on a non-compiling edit when BEST compiles.

## Negative scope
This skill is not permission for broad refactoring, contract weakening, executable edits, external research, reference-proof inspection, or success claims based on policy safety alone.
```

## 3. Information Gain: S for pre, C for post

| Phase | Selected skill | Slot | Four-task macro IG | Important caveat |
|---|---|---:|---:|---|
| Pre | `dependency_bridge_map` | R1-S | +0.070516 | IronKV hard is negative; token-weighted pooled score is about -0.0587 |
| Post | `minimal_sufficient_rationale` | R1-C | +0.219801 | Hindsight summary after the proof already exists |

| R1-S pre task | IG, bits/target token |
|---|---:|
| Direct | +0.01539 |
| Marshal impl2 | +0.10306 |
| Marshal impl5 | +0.29008 |
| IronKV hard | -0.12647 |
| Unweighted macro | +0.070516 |
| Token-weighted pooled | about -0.0587 |

- Pre and post select different organization policies; there is no single overall InfoGain winner.
- R1-S's positive pre macro is driven by the two marshal tasks. It is a task-family specialist, not a general pre-memory result.
- R1-C is positive post-proof on all four tasks, but it is generated after solving. It supports memory compression, not live solve-rate or token-efficiency improvement.
- The clearest textual contrast is “root node,” “bridge edges,” and “topologically” for unresolved proof structure versus “smallest high-confidence set,” “only the mismatch,” and “five short lines” for a completed proof.
- A/C/S reading: S is a faithful representation of pre-proof dependency structure. C is a faithful minimal writeback policy. The profiles serve different phases.
- Strategy for pre: retrieve only the bridge/dependency card matching the current representation transition, and allow abstention.
- Strategy for post: retain the exact obligation, actually used lemma, decisive bridge, and verifier outcome; remove failed guesses and debugging history.
- Generalization: S may transfer to representation-heavy proofs, but the observed positive score is concentrated in the marshal family. C is more plausibly task-general as a post-proof schema, but only as a storage format.
- Meta-evolution: both winners are from R1. Mean post IG falls from about 0.2149 in R1 to 0.1805 in R2, and every R2 pre macro is negative. More sophisticated meta-analysis did not produce cumulative metric improvement.
- Talk line: pre memory should look like a map; post memory should look like a compressed index. Combining both into one global skill causes interference.

R1-S pre skill source text:

```markdown
# Dependency and Bridge Map for Verus Proofs

## Objective
Expose the topological structure of the proof: what each obligation depends on, which invariants connect layers, and which bridge closes each branch. Optimize only full-proof information gain.

## Applicability
Use when the target spans multiple abstractions or requires several helper facts, boundary cases, or implication directions.

## Negative scope
Do not reproduce the finished proof or task-specific identifiers. Do not add speculative nodes, chronological debugging narration, irrelevant warnings, or efficiency advice. For a direct corollary, use a minimal rationale instead.

## Required workflow
1. Create a root node for each target conjunct or implication direction. For a Boolean equality, create separate soundness and completeness roots.
2. Add premise nodes for requires clauses, recommendations, validity predicates, order laws, domain facts, length bounds, and branch guards.
3. Decompose each validity predicate into the invariant actually consumed by the proof. Distinguish structural invariants from semantic invariants.
4. Add bridge edges wherever adjacent nodes use different representations: component to aggregate, closed to exposed specification, encoded prefix to payload, index to key, stored value to abstract map value, local gap to global range, or branch guard to logical case.
5. For every bridge edge, identify a confirmed lemma, explicit quantified instantiation, witness, unfolding permission, injectivity argument, extensionality argument, or contradiction. An edge without such support is the current blocker.
6. Order helper lemmas topologically. Establish foundational order and membership facts first; then representation correspondence; then forward preservation; then converse or witness facts; finally branch assembly.
7. Make boundary nodes explicit: empty intervals, terminal sentinels, inclusive versus exclusive endpoints, equal indices, and the last stored element. State which invariant closes each.
8. Map executable branches to specification cases. True branches require constructive forward paths; false branches require a converse theorem or an internal counterexample witness.
9. After each verifier run, mark proven nodes and report only the lowest unresolved dependency. Do not treat downstream failures as independent until their prerequisites verify.

## Terminal repair summary
End with:
- Diagnosed obligation: root obligations and the last unresolved dependency.
- Key lemmas/invariants: a topologically ordered list of dependency nodes and roles.
- Decisive proof bridge: the critical representation or implication edge, followed by the branch-assembly chain.
- Verifier outcome: exact verification and structural-check results.
- Unresolved blocker: `none`, or the first unsupported edge in the dependency graph.
```

R1-C post skill source text:

```markdown
# Minimal Sufficient Proof Rationale

## Objective
Retain the smallest high-confidence set of facts sufficient to explain a complete Verus proof. Optimize reference-proof information gain, not brevity for its own sake, solve rate, or token cost.

## Applicability
Use for direct lemma applications, explicit quantifier instantiations, component-wise contract propagation, or a short confirmed representation-to-goal bridge.

## Negative scope
Do not compress away unresolved branch directions, required invariants, recommendations, casts, or representation boundaries. Do not list guessed APIs, routine tool failures, task identifiers, finished proofs, reference answers, or evaluator-only information.

## Required workflow
1. State the exact failing obligation in normalized form.
2. Select the strongest already-confirmed contract whose conclusion nearly matches the target.
3. Record only the mismatch between that conclusion and the target: a particular quantified instance, component decomposition, side condition, representation bridge, injectivity step, or extensional equality.
4. Prefer direct contract application over introducing a new helper. For composite values, invoke the component contracts and state how their conclusions reconstruct the composite property.
5. If the specification is closed or otherwise opaque, use only a verifier-confirmed bridge to an exposed representation; retain the representation fact it unlocks and discard failed name guesses.
6. Re-run the verifier. If new independent branches or invariants appear, stop using this profile and switch to a structural rationale.
7. Preserve a failed approach only when it identifies the unresolved blocker or establishes that a tempting bridge is unavailable.

## Terminal repair summary
End with five short lines:
- Diagnosed obligation: the target and the one missing step.
- Key lemmas/invariants: only those actually used, with their roles.
- Decisive proof bridge: one minimal implication chain.
- Verifier outcome: exact verification and structural-check results.
- Unresolved blocker: `none` or one precise missing fact.
```
