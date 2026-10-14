# Weak-fairness liveness decomposed into pointwise lemmas

## Scope

- Consult when: Top-level temporal goal is weak-fairness/eventual stable state under transitions
- Consult when: Direct weak fairness or leads-to fails
- Consult when: Pointwise action precondition, firing outcome, and preservation can be proved
- Not for: A needed pointwise implication cannot be proved
- Not for: Step space is too large to case-split effectively

## Rules

- [Weak-fairness liveness decomposed into pointwise lemmas](#rule-wfpl-card-007)

<a id="rule-wfpl-card-007"></a>
## Weak-fairness liveness decomposed into pointwise lemmas

Source cards: card-007

**Trigger:** A top-level temporal goal, such as eventually reaching a stable state under a transition system, has an empty or weak proof body and direct application of weak fairness or leads-to does not close the postcondition.

**Action:** Prove separate pointwise lemmas: desired state implies the relevant action precondition, an action firing yields the desired post-state, and every concrete transition step preserves the post-state under the available invariants. Then combine those lemmas with reusable generic temporal lifting helpers for lead-to and stable behavior.

**Why:** Isolating pointwise implications lets the solver handle the state-machine transitions case by case and reduces the temporal quantification to known reusable steps. This avoids trying to prove invariance over arbitrary unfiltered transitions.

**Validate:** Each helper and the final lemma should verify. Run Verus to confirm the expected number of verified functions and zero errors, then run the safety comparison tool.

**Avoid when:** A needed pointwise implication cannot be proved from the available invariants, or the step space is too large to case-split effectively. Do not weaken the top-level specification to make the proof pass.

- Distinguish from [final-liveness-helper-chain](final-liveness-helper-chain.md): Final-liveness route assembles already-declared invariant/stability/phase helpers; weak-fairness route first creates pointwise action lemmas.

- Related [final-liveness-helper-chain](final-liveness-helper-chain.md): Final-liveness route assembles already-declared invariant/stability/phase helpers; weak-fairness route first creates pointwise action lemmas.

- Related [temporal-entailment-pointwise-lifting](temporal-entailment-pointwise-lifting.md): Weak-fairness route creates action precondition/outcome/preservation lemmas; this route lifts a single pointwise/per-suffix implication to a temporal goal.
