# Verification Process, Soundness, and Proof-Maintenance Hygiene

**Consult when:** The task requires disciplined in-place editing, complete Verus feedback, empty-body checks, helper independence, forbidden-assumption audits, smallest-obligation isolation, or post-verification cleanup.

**Do not consult when:** The proof is already hygienic and only a specific mathematical bridge is missing; use the corresponding mechanism reference.

<a id="verus-global-081"></a>

## verus_global_081 — Edit the supplied target file in place for proof-annotation tasks

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Task names an existing source file for proof annotations; the proof has not yet been applied to that exact file.

**Obstacle:** Annotations are written to a separate or renamed file, so the required target remains unmodified and verifier success on the clone does not satisfy the task.

**Mechanism:** Make the provided target file the sole output artifact and apply all proof edits directly to it unless a separate artifact is explicitly requested.

**Procedure:**
1. Confirm the task's expected output file before creating any new file.
2. Open the provided target file and apply all proof annotations in place.
3. Avoid routing edits through `_verified.rs` or similarly renamed clones unless the task explicitly permits a standalone artifact.
4. After editing, inspect the diff or code-line changes against the original target to confirm the target itself changed.
5. If output requirements are ambiguous, ask for clarification before producing auxiliary files.

**Why:** Multiple trajectories failed because cloning the target file or writing only a separate verified file left the assigned file unchanged; in-place editing prevents this assignment mismatch.

**Check:** The final diff shows proof annotations inside the exact supplied target file, not only in a cloned or auxiliary file.

**Avoid or stop:**
- Tasks that explicitly ask for a standalone proof file or artifact rather than an in-place modification.
- Exploratory scratch work that is kept separate but later deliberately merged into the target.

<a id="verus-global-082"></a>

## verus_global_082 — Gate proof construction on complete Verus output before and after edits

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Before editing a proof target, after each non-trivial proof edit or transformation, and before declaring completion.

**Obstacle:** Edits are made blind, or a final success is declared from truncated, partial, or unreproduced verifier output.

**Mechanism:** Use Verus as a tight feedback loop: capture the original exact failure, re-verify after small changes, and require a complete reproducible 0-error report on the target before completion.

**Procedure:**
1. Run Verus on the unmodified target before writing proof annotations to capture the exact failed obligation or confirm that it already passes.
2. Run Verus after each focused edit or transformation to detect structural and proof regressions early.
3. Prefer small validated edits over large untested batches.
4. After the final proof is in place, inspect the complete Verus output and require 0 errors, not just a truncated or summarized success.
5. Re-run after final cleanup or another final check to confirm reproducibility.

**Why:** Successes across multiple trajectories came from first reading exact diagnostics and then validating edits with fresh runs; failures came from blind large edits or accepting truncated output as a pass.

**Check:** Every stage has recorded verifier feedback; the final 0-error output is complete and reproducible on the intended target.

**Avoid or stop:**
- Pure syntax or environment errors are excluded because they require build or configuration repair before proof verification.
- Verifier success with unsound assumptions still needs the separate forbidden-assumption audit skill.

<a id="verus-global-083"></a>

## verus_global_083 — Check whether an empty proof body already satisfies a definitional obligation

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** When a proof function is empty or minimal and the postcondition may reduce directly to a definitional equality.

**Obstacle:** The agent may add unnecessary proof steps or fail to notice that the original obligation is already verified.

**Mechanism:** Run Verus on the untouched source first; if the empty body verifies, stop; if it fails, use the exact diagnostic to build the required proof.

**Procedure:**
1. Run Verus on the original file before editing the proof body.
2. If the original empty body verifies successfully, accept it and avoid adding proof work.
3. For direct definitional equivalences, test the minimal empty body before writing manual proof blocks.
4. If verification fails, switch to exact diagnostic and proof construction.

**Why:** Several successes showed that empty or definitional proof bodies can already discharge the obligation, so a preliminary run avoids unnecessary annotations.

**Check:** Verus passed on the original or minimal empty body before any unnecessary proof step was added.

**Avoid or stop:**
- Non-trivial obligations where empty-body verification fails.
- Cases where a later dependency still needs auditing.

<a id="verus-global-084"></a>

## verus_global_084 — Complete helper lemma proofs independently before depending on them

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** When introducing or reusing a helper lemma whose body is empty, comments-only, recursive without closing the induction, or not independently verified.

**Obstacle:** Unproven helper lemmas propagate postcondition failures to every call site or fake a proof if their emptiness is not caught.

**Mechanism:** Treat each helper lemma as its own proof unit, provide concrete proof steps, verify it in isolation, and only then call it from larger proofs.

**Procedure:**
1. State the exact ensures clause for the helper lemma.
2. Fill its body with assertive steps, case splits, arithmetic, or calls to already verified lemmas.
3. Verify the helper alone with a small concrete instance before relying on it.
4. If the helper cannot be independently proved, change its specification or remove it instead of leaving it empty.
5. At each call site, ensure the callee's concrete body is actually verified.

**Why:** Failures repeatedly showed that empty or insufficient helper bodies created cascading errors and blocked the main proof from making progress.

**Check:** Each helper lemma verifies independently with a non-empty body before the main proof can claim success.

**Avoid or stop:**
- Trivial definitional lemmas where an empty body legitimately verifies.
- Pre-existing trusted lemmas whose verified body is already established.

<a id="verus-global-085"></a>

## verus_global_085 — Audit proof dependencies, reject forbidden assumptions, and report unsolvable specification gaps

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** When a proof uses or plans to use `external_body`, `unimplemented!()`, `assume`, `admit`, new axiom functions, or trait methods with opaque or external concrete bodies and task rules forbid them, or when repeated compliant proof attempts cannot close an obligation and a new axiom or unsound assumption appears to be the only route.

**Obstacle:** Verus reports success even though an unchecked assumption carries the central proof obligation; or, after a failed search, the agent rationalizes an axiom or submits a forbidden artifact instead of reporting the true specification gap.

**Mechanism:** Prohibit forbidden trust primitives when disallowed, inspect concrete lemma and trait-method implementations before relying on them, audit the final dependency chain for verifier-checked bodies, and when a fact is missing enumerate the exact premise, audit existing contracts, invariants, verified lemmas, and induction/definitional alternatives, then report the specification gap rather than silently introducing forbidden support.

**Procedure:**
1. Re-read task constraints for prohibitions on `external_body`, `assume`, `admit`, `unimplemented!()`, and new axioms.
2. Before invoking a trait method or helper lemma, inspect its concrete implementation and classify `external_body` or `unimplemented!()` as an unchecked assumption.
3. If repeated compliant proof attempts cannot close an obligation, write down the specific missing fact that would close the stuck goal.
4. Check existing trait contracts, invariants, sortedness or determinism properties, and verified lemmas for that fact; attempt compliant alternatives such as structural induction or definitional unfolding.
5. Do not add new axiom functions, empty ext-equal lemmas, or external-body placeholders to close a proof gap.
6. If the premise is still absent, record the precise specification gap.
7. After Verus success, audit the proof's critical dependency chain to confirm each lemma has a verifier-checked body.
8. If a temporary forbidden artifact was used, revert it and complete a concrete proof path; if no compliant proof exists, report the limitation or request permitted support instead of adding an axiom or submitting a forbidden artifact.

**Why:** Failures occurred because proofs were accepted only when central obligations depended on unchecked external-body lemmas or new axioms, and because agents concluded an axiom was necessary without exhaustively checking existing properties, then submitted forbidden axioms instead of exposing the real missing premise.

**Check:** The final proof contains no forbidden assumption artifacts, every critical lemma in the dependency chain has a verifier-checked body, and the required missing premise is either found in the existing specification or explicitly reported as a gap, never silently assumed.

**Avoid or stop:**
- Tasks that explicitly permit axioms, new axiomatic support, or `external_body` in the trusted base.
- Pre-existing language or toolchain trust primitives outside the assignment rules.
- Cases where the missing fact is present but hidden and must be discovered by deeper proof search.

<a id="verus-global-086"></a>

## verus_global_086 — Isolate the smallest failing obligation and decompose or pivot when stuck

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** When a postcondition or invariant remains unproved after multiple edits, or when a proof block is large and the verifier failure is not yet isolated.

**Obstacle:** Cycles of small patching, speculative helper lemmas, strategy thrashing, or repeated edits that do not address the exact blocked conjunct.

**Mechanism:** Capture the exact failed conjunct; probe it with an explicit `assert`; decompose into small independent subgoals; and redesign or pivot when incremental patches repeatedly fail.

**Procedure:**
1. Read the exact failing postcondition conjunct or invariant location before adding new lemmas.
2. Insert a minimal explicit `assert` for the stuck fact to confirm the blocked obligation.
3. Split the main proof obligation into small, independently assertable subgoals.
4. When a single lemma call or monolithic assertion fails, assert intermediate equalities between it and the target conclusion.
5. If multiple small tweaks do not close the gap, stop patching and redesign the invariant or proof strategy.

**Why:** Many failed trajectories shared the pattern of editing the same large assertion repeatedly or switching strategies without ever refining the one atomic fact the verifier could not prove.

**Check:** The proof proceeds through explicit intermediate assertions, and any failed strategy is either refined around the blocked assertion or replaced by a redesigned plan.

**Avoid or stop:**
- Simple obligations that solve with one direct proof step.
- Already-focused proofs that need only one additional lemma.

<a id="verus-global-087"></a>

## verus_global_087 — Remove redundant assertions after successful verification

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** After a proof verifies successfully and contains extra manual assertions that duplicate facts already established by existing lemma calls.

**Obstacle:** Redundant proof steps remain in the verified lemma, making maintenance harder without increasing soundness.

**Mechanism:** Use Verus success as a baseline, identify assertions that duplicate already-proven facts, delete only those, and re-run Verus.

**Procedure:**
1. Verify the full proof to create a trusted baseline.
2. Identify assertions that duplicate facts already provided by existing lemma calls or invariants.
3. Remove only redundant steps while preserving necessary intermediate facts.
4. Re-run Verus to confirm the proof still verifies.

**Why:** The observed successful trajectory kept reasoning minimal by deleting an assertion already covered by an element-by-index lemma, then re-verified to preserve soundness.

**Check:** The cleaned proof still verifies with 0 errors and contains only necessary reasoning steps.

**Avoid or stop:**
- Do not remove assertions that encode necessary intermediate facts.
- Do not simplify before a successful baseline verification exists.

<a id="verus-global-088"></a>

## verus_global_088 — Write a complete proof in one self-contained edit when the structure is clear

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** When the required proof structure is already clear from the definitions and a single complete annotation is likely to verify immediately.

**Obstacle:** Incremental partial edits would add unnecessary debugging cycles for an already clear proof.

**Mechanism:** Construct the entire proof body in one self-contained edit and run Verus immediately; only fall back to diagnostic decomposition if that run fails.

**Procedure:**
1. Read the initial file and failure log to understand definitions and required reasoning.
2. Draft the full proof annotation in a single edit.
3. Run Verus immediately to confirm correctness.
4. If the first run fails, switch to the verifier-feedback and decomposition loop to isolate the gap.

**Why:** The observed success came from a single self-contained edit that verified immediately; this is efficient when the proof structure is already clear.

**Check:** The single self-contained edit verifies on the immediate Verus run, confirming the proof structure was clear.

**Avoid or stop:**
- Complex or unclear obligations that need iterative diagnosis and decomposition.
- Do not confuse this self-contained edit with writing proofs only in a cloned file.
