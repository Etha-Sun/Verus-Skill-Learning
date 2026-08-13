# Quantifier Trigger Selection and Concrete Instantiation

**Consult when:** Verus reports missing/no-selected-trigger warnings, automatic trigger selection is preferred, or a quantified premise needs a concrete index-element assertion to instantiate.

**Do not consult when:** The quantifier body itself is unproved due to missing recursive lemmas or structural decomposition; trigger annotation will not close those gaps.

<a id="verus-global-029"></a>

## verus_global_029 — Explicitly annotate a forall predicate with #[trigger] to suppress missing trigger warnings

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Verus emits a missing or no-selected-trigger warning for a `forall` assertion, and the predicate or implication antecedent that should drive quantifier instantiation is textually identifiable.

**Obstacle:** The quantifier has no selected or stable trigger, so SMT may not know which terms should instantiate the `forall`, leading to trigger warnings and potentially unstable or absent instantiation.

**Mechanism:** Adding `#[trigger]` immediately before the intended predicate makes that predicate an explicit selected trigger pattern for the quantifier, suppressing ambiguity and giving the SMT solver a deterministic instantiation term.

**Procedure:**
1. Locate the `forall` assertion or quantifier that produces the Verus missing/no-selected-trigger warning.
2. Identify the positive predicate or implication antecedent that should drive instantiation, such as a set or sequence membership condition.
3. Annotate that predicate with `#[trigger]`, preserving the rest of the formula and proof structure.
4. Rerun Verus and confirm the trigger warning is eliminated and the proof still verifies.

**Why:** The merged trajectories all observed that explicit trigger annotations removed trigger-related warnings without requiring proof restructuring. The annotated predicate becomes the selected pattern the solver can match when a concrete occurrence appears.

**Check:** Rerun Verus after the edit. The targeted `forall` should no longer produce trigger-related warnings, and the surrounding verification should still pass.

**Avoid or stop:**
- Do not annotate a predicate that is not intended to drive instantiation; this can direct the solver away from needed instances.
- Do not add `#[trigger]` to an already stable, warning-free quantifier unless there is a concrete instantiation failure.

<a id="verus-global-030"></a>

## verus_global_030 — Insert #![auto] on forall quantifiers to let Verus choose triggers

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Verus suggests a trigger annotation for a `forall` expression, warns of missing triggers, or fails to instantiate an elementwise or range `forall` where automatic trigger selection is preferable.

**Obstacle:** A `forall` has missing, unstable, or overly rigid trigger selection. The solver either emits trigger warnings or does not instantiate the quantifier at the required concrete index or range occurrence.

**Mechanism:** `#![auto]` inside the quantifier delegates trigger selection to Verus/SMT automatic triggering, letting it choose appropriate instantiation patterns and fire the quantifier when matching terms arise in the context.

**Procedure:**
1. Find the `forall` quantifier that produced a missing-trigger warning, was suggested for trigger annotation, or failed to instantiate at the needed point.
2. Insert `#![auto]` inside the quantifier, before the body or range condition, such as `forall|i: int| #![auto] ...`.
3. Keep the logical statement unchanged; do not restructure the proof.
4. Rerun Verus and confirm trigger warnings are gone and any earlier quantifier-instantiation errors are resolved.

**Why:** The two success trajectories show that `#![auto]` both silences trigger warnings and, in the marshalling proof, enables automatic instantiation where elementwise equality is required. The remaining error-trajectory memory reports the same warning-eliminating recovery and is included as recovery evidence rather than as an additional clean success.

**Check:** After rerunning Verus, the `forall` should no longer have trigger-related warnings, and assertions depending on its instantiation should verify. If the proof remains open, inspect whether automatic triggering still matches the needed terms.

**Avoid or stop:**
- Do not use `#![auto]` on a quantifier whose automatic trigger selection is known to be explosive or divergent in the current context.
- Do not combine `#[trigger]` and `#![auto]` on the same quantifier without specifically testing that the resulting trigger behavior is the intended one.

<a id="verus-global-031"></a>

## verus_global_031 — Assert a concrete index-element equality to instantiate a quantified premise with an existing equality trigger

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A quantified premise contains an existing `#[trigger]` equality such as `g(i, a) == f(a)`, and the proof goal requires the same equality for a concrete index and concrete element from the current collection or map.

**Obstacle:** Even with a trigger on the premise, the solver may not automatically instantiate the quantified equality for the specific index and element needed to connect two collection or map transformations.

**Mechanism:** Writing an explicit assertion with a concrete occurrence of the left side, such as `g(index, element)`, matches the premise trigger. The quantifier is then instantiated for that pair, yielding the concrete equality and linking the elementwise expressions in the goal.

**Procedure:**
1. Identify a quantified premise whose trigger is already an equality over a function application such as `g(i, a) == f(a)`.
2. Identify the concrete index and concrete collection element needed by the current goal, for example `i` and `s[i]`.
3. Write an assertion of the same equality at that pair: `assert(g(i, s[i]) == f(s[i]))`.
4. Use the concretely instantiated equality in the surrounding proof to connect the map or sequence element being reasoned about.

**Why:** The explicit assertion creates a trigger-matching occurrence that forces the quantified premise to fire for the exact pair needed, bridging the gap between the quantified equivalence and the concrete elementwise equality in the goal.

**Check:** After the explicit assert, the subsequent proof should be able to use the concrete equality, and the surrounding goal should verify without needing induction or extensional rewriting to unfold the quantified premise.

**Avoid or stop:**
- Do not use this if the quantified premise lacks a matching trigger or its trigger is not the equality being asserted.
- Do not assert an unmotivated concrete pair unless the subsequent proof actually uses that pair; unnecessary trigger terms can cause additional instantiation.
