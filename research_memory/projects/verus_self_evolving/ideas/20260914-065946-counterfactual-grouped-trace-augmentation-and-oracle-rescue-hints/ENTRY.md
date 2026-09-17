# Counterfactual grouped trace augmentation and oracle rescue hints

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-09-14T06:59:46Z`
- status: `active`
- verdict: conditional GO for a train-only pilot; not yet a downstream method
  claim

## Objective contract

- Primary objective: learn a compact Verus skill or intervention policy that
  improves task-disjoint, within-budget verified solve rate and reduces total
  cost to the first verified proof.
- Scoreboard metrics: independently checked Verus plus Lynette solve rate,
  complete-ledger tokens including the hint agent, and time to first verified
  proof.
- Trusted diagnostics: verifier tier, exact verifier calls, error/action
  recurrence, candidate hashes, and frozen offline proof-progress labels.
- False progress: higher similarity to one final proof, 100% success on
  success-selected continuations, cleaner-looking traces, more skill cards, or
  lower actor tokens while ignoring hint-generation cost.
- Hard constraints: task-grouped splits; no fixed-test20 tuning; no final proof
  or hindsight progress target visible to a deployed actor/router; raw inputs
  remain read-only; generated runs remain below `VERUS_SKILL_RUN_ROOT`.

## Current board packet

- Incumbent: the reviewed two-task DeepSeek augmentation package has 24/24
  final Verus/Lynette passes and shows that no-reference continuations can find
  alternative proof routes, but it has only two independent tasks and no
  downstream SkillOpt result.
- Latest enabling result: verifier-gated Patch F1 and pruned-proof coverage can
  describe train trajectory plateaus and regressions at verifier-call
  granularity.
- Strongest negative evidence: final-proof similarity is reference-dependent,
  and a valid alternative proof can have near-zero similarity to the original
  endpoint. Existing R041 trace-distilled guidance also did not beat the H0/H1
  diagnostic, so more trace text is not a sufficient mechanism.
- Active blocker: the current proposal combines batch organization,
  obfuscation, rerunning, intervention timing, and oracle hints, making a
  positive result causally uninterpretable.
- Stale routes to ignore: optimizing information gain as a primary endpoint,
  training a router before card quality is established, or treating the
  recurring test20 as augmentation data.
- Budget class: slow-check. Live continuations and optimizer evaluations make
  independent task count more important than the nominal eight-trace batch.

## Assessment

The proposal contains a strong research kernel, but the useful claim is
narrower than "almost every trace can eventually verify." The defensible
hypothesis is:

> On train tasks with a known verified endpoint, a final-proof-aware teacher
> can convert a stalled prefix into a bounded, non-copying strategy hint; the
> resulting same-prefix rescue pairs can train a final-proof-blind hint policy
> or better-scoped skill that transfers to task-disjoint live repair.

The original universal recoverability assumption is not currently supported.
The 24/24 augmentation result is conditioned on two tasks, selected checkpoints,
and known successful endpoints; some checkpoints may already pass. Historical
Qwen runs also contain no-edit and unsolved trajectories. Recoverability must
therefore be measured as `recoverable@remaining_budget`, not assumed.

### Main hypothesis and competing explanations

- H1, useful mechanism: oracle hints identify a missing proof operation or
  route change that is inferable from observable verifier state, so a
  final-proof-blind policy can later reproduce part of the gain.
- H2, copying: the executor succeeds only because the hint leaks distinctive
  code, lemma names, witnesses, or proof structure from the final proof.
- H3, restart variance: any fresh continuation or generic "you are stalled"
  message performs similarly; the final proof adds no useful information.
- H4, path-metric artifact: the trigger selects points close to one surface
  form rather than genuinely stalled states, and alternative valid routes are
  misclassified.

## Related-work delta

This pass reused the repository's prior comparison with ReAct, Reflexion,
Voyager, LATS, AgentSpec, TACO, and VeruSAGE, and added a targeted primary-source
check around hindsight supervision, proof-trajectory granularity, verifier
feedback, and obfuscation.

| prior work | overlap | implication |
|---|---|---|
| STaR (2022) | regenerates rationales with the correct answer visible | final-answer-conditioned rationale generation is not novel by itself |
| Hindsight replay for theorem proving (2021) | relabels experience to learn from unsuccessful searches | hindsight use in theorem proving is established |
| Lean-STaR (2024/2025) | uses retrospective ground-truth tactics to synthesize thoughts | final-proof-aware synthetic reasoning is a close direct neighbor |
| DeepSeek-Prover-V1.5 (2024) | verifier feedback and diverse proof-path search | verifier-grounded exploration is established |
| Optimal data ordering for proof generation (2024) | shows proof-supervision order affects learning | grouped/logical ordering needs a matched random-order control |
| Segment-level theorem-proving supervision (2026) | extracts coherent proof segments and triggers goal-aware short rollouts | full-trace dumping is already challenged by stronger granularity choices |
| Hindsight Supervised Learning (2026) | an auxiliary LLM relabels completed agent trajectories | auxiliary hindsight teachers are established outside theorem proving |
| ClassEval-Obf (2025) | semantics-preserving identifier obfuscation exposes naming shortcuts | obfuscation is a diagnostic for cue dependence, not proof of memorization |
| Memorize or Generalize? (2025) | defines harmful memorization behaviorally under semantic rewriting | a clean-to-obfuscated accuracy drop alone is insufficient to establish memorization |

Novelty/value verdict: **incremental but valuable**. The ingredients exist
separately. The differentiated opportunity is a verifier-grounded causal data
unit: identical stalled prefix, controlled hint channel, independently verified
continuation, and a train-teacher/deployment-policy separation in Verus repair.
No strong novelty claim should be made before a broader paper-level survey.

## Candidate frontier

### C1. Grouped contrastive trace packs

- Family: infrastructure/data organization.
- Mechanism: compare random eight-trace batches with four task-matched pairs,
  keeping source traces and optimizer token exposure fixed.
- Strength: cheapest direct test of the current batching hypothesis.
- Limitation: can improve card contrast without solving intervention timing.
- Verdict: keep as the required batching baseline.

### C2. Oracle rescue augmentation

- Family: mechanism/data creation.
- Mechanism: at a frozen stalled prefix, a teacher sees the final proof and
  emits a bounded strategy hint; a fresh actor continues from the identical
  prefix without seeing the proof.
- Strength: creates causal same-state rescue pairs and tests upper-bound
  recoverability.
- Limitation: not deployable and highly vulnerable to answer leakage.
- Verdict: use only as a train-only teacher and upper-bound arm.

### C3. Distilled final-proof-blind hint policy

- Family: mechanism plus objective.
- Mechanism: learn or induce a hint rule from C2 rescue pairs using only
  deployable features: current code, verifier diagnostics, edit/error history,
  and token/call budget.
- Strength: converts hindsight supervision into a deployable policy and tests
  whether oracle information distilled into a general rule.
- Limitation: requires enough independent tasks; may collapse to generic
  restart advice.
- Verdict: selected direction after C1/C2 pilot gates pass.

Obfuscation is not a fourth main mechanism. Use it as an orthogonal diagnostic
and optional training perturbation after the clean causal comparison.

## Minimal staged experiment

### Stage 0: freeze labels and intervention semantics

Use only exact structured train trajectories with independently verified
endpoints. Define an offline teacher label over a window, for example:

```text
stalled_F(t) = verifier tier unchanged
               and progress_F gain <= epsilon
               and output tokens in window >= B
```

`progress_F` must remain verifier-gated and hindsight-only. Report sensitivity
to another valid endpoint or a small endpoint bank. Do not expose it to the
actor or the deployable trigger.

Define the online detector only from observable signals: unchanged verifier
error core, repeated `(error, edit)` motifs, lack of a newly verified helper,
candidate-hash churn, and token/call spend. Its agreement with `stalled_F` is a
calibration diagnostic, not the final objective.

The teacher hint should be structured as:

```text
diagnosed_blocker
target_subgoal
recommended_operation_class
why_current_route_is_stalled
```

It must contain no proof body, patch, witness expression, or copied source
span. Record all final-proof overlap and all identifiers newly introduced by
the teacher. The executor receives only this hint and the frozen prefix.

### Stage 1: same-prefix causal rescue pilot

Use at least eight independent train task groups, stratified across available
IR/AL/AC difficulty, with one frozen prefix per task. A 32-run diagnostic has
four matched arms per task:

1. fresh continuation, no hint;
2. token-length-matched generic stall notice;
3. prefix-only critic hint;
4. final-proof-aware bounded teacher hint.

Use the same actor, temperature, remaining wall-time/token budget, tools, and
starting source. A direct-final-proof arm may be run separately as an upper
bound but must never be mixed into deployable training claims. One sample per
arm is diagnostic; any apparent gain requires independent task-clustered
replication.

Primary outcomes are within-budget dual-verifier solve, total actor plus hint
tokens, and time/tokens to first verified proof. Secondary outcomes are rescue
rate, intervention rate, verifier calls, unique valid candidates, and route
diversity. Analyze tasks as the independent units; eight traces are not `n=8`
when they come from the same base task.

### Stage 2: eight-trace SkillOpt batching test

Treat eight as an engineering batch size, not a scientific unit. Form each
contrastive batch as four independent task pairs:

```text
(same prefix, control continuation)
(same prefix, oracle-rescued continuation)
```

Compare against a random eight-trace batch under identical source material,
optimizer calls, prompt tokens, and output budget. Balance which task and arm
occupies each position across repetitions. Evaluate the resulting skills on
task-disjoint live repairs; card count, wording quality, or offline similarity
alone cannot select the winner.

### Stage 3: obfuscation and deployment transfer

Apply only verifier-preserving transformations with recorded inverse maps:

- alpha-renaming of local identifiers;
- whitespace/comment normalization;
- safe helper reordering or equivalent surface rewrites only when fresh Verus
  and Lynette both pass.

Use a clean/obfuscated cross matrix on task-disjoint evaluation. A performance
drop measures naming/surface-cue dependence, not memorization by itself. A
stronger behavioral memorization test requires a semantics-changing
counterfactual specification with its own independently verified endpoint;
simple renaming cannot supply that claim.

Finally distill C2 hints into C3 using only observable prefixes, and test
whether the no-final-proof policy retains a meaningful fraction of the oracle
gain.

## Promotion and abandonment gates

Conditional pilot GO requires all of the following:

- oracle hints beat both restart and generic-message controls on task-clustered
  verified completion or cost to first pass;
- the gain remains after including teacher cost and excluding hints with proof
  overlap violations;
- grouped eight-trace skill induction beats random batching on task-disjoint
  live evaluation under matched budgets;
- a final-proof-blind policy preserves some oracle benefit without increasing
  verifier regressions or reducing solve rate.

Abandon or redesign if any of the following occurs:

- the oracle arm does not beat the generic/restart controls;
- success is explained by copied identifiers or proof fragments;
- benefits appear only on the same two source tasks;
- progress labels reverse materially under another valid endpoint;
- obfuscation gains do not transfer back to clean task-disjoint evaluation;
- token savings disappear after hint-agent and optimizer costs are counted.

## Quality gate

- novelty: 1/2 (known ingredients; differentiated causal Verus composition)
- falsifiability: 2/2
- feasibility: 2/2
- evidence quality: 2/2
- constraint fit: 2/2
- total: 9/10

Strongest objection: the method may only compress the exact final proof into a
hint and teach same-task shortcuts. The proposed same-prefix controls,
anti-copy audit, task-grouped split, alternate-endpoint sensitivity, and
final-proof-blind deployment arm are therefore constitutive tests, not optional
ablations.

## References

1. Zelikman et al. *STaR: Bootstrapping Reasoning With Reasoning*.
   arXiv:2203.14465, 2022. https://arxiv.org/abs/2203.14465
2. Aygun et al. *Proving Theorems using Incremental Learning and Hindsight
   Experience Replay*. arXiv:2112.10664, 2021.
   https://arxiv.org/abs/2112.10664
3. Lin et al. *Lean-STaR: Learning to Interleave Thinking and Proving*.
   arXiv:2407.10040, 2024/2025. https://arxiv.org/abs/2407.10040
4. Xin et al. *DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for
   Reinforcement Learning and Monte-Carlo Tree Search*. arXiv:2408.08152,
   2024. https://arxiv.org/abs/2408.08152
5. An et al. *Next-Token Prediction Task Assumes Optimal Data Ordering for LLM
   Training in Proof Generation*. arXiv:2411.00863, 2024.
   https://arxiv.org/abs/2411.00863
6. Xu et al. *Rethinking Supervision Granularity: Segment-Level Learning for
   LLM-Based Theorem Proving*. arXiv:2605.11905, 2026.
   https://arxiv.org/abs/2605.11905
7. Li et al. *Spinning Straw into Gold: Relabeling LLM Agent Trajectories in
   Hindsight for Successful Demonstrations*. arXiv:2607.04235, 2026.
   https://arxiv.org/abs/2607.04235
8. Le et al. *When Names Disappear: Revealing What LLMs Actually Understand
   About Code*. arXiv:2510.03178, 2025.
   https://arxiv.org/abs/2510.03178
9. Zhang et al. *Memorize or Generalize? Evaluating LLM Code Generation with
   Code Rewriting*. arXiv:2503.02296, 2025.
   https://arxiv.org/abs/2503.02296

## Decision and next action

Proceed only with Stage 0 and the bounded Stage 1 train-only pilot first. Do
not yet combine obfuscation, eight-trace batching, and learned routing in one
run. If the oracle teacher fails the matched rescue gate, stop before SkillOpt
training; if it passes, freeze the rescue-pair export contract and then run the
random-versus-grouped eight-trace comparison.

### Branch publication decision (2026-09-17)

- verdict: branch
- action: publish this plan on
  `feat/obfuscation-hindsight-replay-20260917`
- foundation: `d3b53a1`, the reviewed two-task DeepSeek augmentation commit
- reason: the new work depends on that augmentation evidence but changes the
  research mechanism and should not extend the completed publication branch
- next stage: freeze the Stage 0 data and leakage contract before implementing
  or launching continuations

No raw benchmark, sealed data, historical trace, or generated run directory
was modified during this assessment.
