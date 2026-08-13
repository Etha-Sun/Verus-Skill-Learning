# Lemma Reuse, Helper Decomposition, and Library/Spec Inventory

**Consult when:** A proof should reuse existing helper/trait/source lemmas, needs a helper extraction, lacks a fold accumulator lemma, or is failing because a named/spec/trait property may be absent or private.

**Do not consult when:** The exact lemma exists and is available but the immediate issue is trigger selection, loop invariant, or syntax/environment errors.

<a id="verus-global-066"></a>

## verus_global_066 — Discharge top-level postconditions by invoking helper/lemma postconditions and asserting only necessary subgoals

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A top-level ensures/postcondition is a conjunction or follows from properties already proved by implementation helpers or named lemmas; the proof state contains those helper postcondition facts but the verifier does not automatically combine them into the target.

**Obstacle:** Opaque helper postconditions or lemma conclusions are not linked to the top-level spec.

**Mechanism:** Invoke the helpers/lemmas whose postconditions/conclusions match subgoals; expose only necessary intermediate assertions; if the target follows directly from lemma conclusions, keep the proof body minimal with lemma calls.

**Procedure:**
1. List sub-properties required by the top-level ensures.
2. Locate existing helper implementations or lemmas whose ensures/conclusions match those sub-properties.
3. Call those helpers/lemmas inside the proof block.
4. Assert the matching sub-properties only when the verifier needs them made explicit.
5. If the target postcondition follows directly from called lemma conclusions, omit redundant asserts and let Verus close the goal.

**Why:** Explicit calls bridge the helper assumptions to the top-level spec, avoiding reliance on opaque automation while still allowing minimal proofs when the conclusions already imply the goal.

**Check:** For success evidence: no missing helper postcondition assertions remain and the top-level postcondition verifies; for future reuse, compare the declared postcondition shape with the helper ensures before deciding to add assertions.

**Avoid or stop:**
- Do not use to prove facts about closed functions whose internal definition is inaccessible.
- Do not skip proving a helper lemma that does not already exist.
- Do not add redundant assertions when the lemma calls alone are explicit enough for the proof state.

<a id="verus-global-067"></a>

## verus_global_067 — Let a stronger precondition drive direct lemma instantiation without case splits

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** The current function precondition already guarantees a superset of what a helper lemma requires, such as a closed range where the lemma needs a half-open range.

**Obstacle:** The prover may appear to require a base case or recursive/exclusive-range call even though the stronger precondition already covers every lemma hypothesis.

**Mechanism:** Instantiate the helper lemma directly with the identical bounds already available from the stronger precondition, avoiding redundant case analysis.

**Procedure:**
1. Compare the current precondition with the helper lemma hypothesis.
2. Confirm that every hypothesis of the helper is implied by the current precondition.
3. Call the lemma immediately with the same arguments or bounds.
4. Do not decompose the range or introduce special cases unless the helper actually excludes an endpoint required by the goal.

**Why:** Redundant case splits often arise from underestimating the current precondition; direct instantiation keeps the proof simpler and more robust.

**Check:** The helper call verifies with the current bounds or arguments, and no missing case analysis remains.

**Avoid or stop:**
- Do not skip a base case if the helper genuinely does not cover an endpoint needed by the postcondition.
- Do not assume the precondition is stronger without checking the exact bound relation.

<a id="verus-global-068"></a>

## verus_global_068 — Replace external_body lemmas with explicit proof bodies using assertion chains

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A lemma is declared with #[verifier::external_body] and must become self-contained rather than relying on an external assumption.

**Obstacle:** The verifier accepts the lemma because its body is external, but the proof using it does not have the needed internal reasoning.

**Mechanism:** Locate the external_body lemma and rewrite it with a concrete proof body; use assert statements to connect the hypothesis to the required conclusions.

**Procedure:**
1. Find any lemma marked #[verifier::external_body].
2. Rewrite it as a normal lemma with an explicit proof body.
3. Use assert statements to chain the hypothesis, such as view_equal, to the required conclusions, such as is_marshalable and serialization equality.
4. Verify the new body without the external assumption.

**Why:** Converting an external assumption into explicit reasoning makes verification self-contained and less fragile.

**Check:** The formerly external_body lemma verifies with a concrete body and the downstream proof no longer depends on an opaque assumption.

**Avoid or stop:**
- Do not replace external_body with an unprovable concrete body if the required axioms are absent.
- Do not hide the missing proof under a different external assumption.

<a id="verus-global-069"></a>

## verus_global_069 — Refactor a stalled complex postcondition into smaller helper lemmas

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A direct proof body becomes littered with unprovable assertions or nested case splits, especially for complex serialization/prefix properties.

**Obstacle:** The main function is too tangled or is missing a key intermediate fact, so direct assertions remain unproven.

**Mechanism:** Extract the missing intermediate fact into one or more helper lemmas that can be proved separately, then instantiate them in the main proof.

**Procedure:**
1. Identify the key fact that the main proof cannot close.
2. Write a helper lemma for that fact, such as differing elements produce differing fold-left serializations.
3. Prove the helper using available structural lemmas or induction.
4. Replace the stuck low-level assertions in the main proof with calls to the helper lemma.
5. Iterate on helper proof separately rather than repeatedly editing the main proof body.

**Why:** This is a failure-derived recovery pattern: helper lemmas isolate the hard reasoning and often reveal the exact invariant the verifier needs, preventing a spiral of dead-end edits.

**Check:** The helper lemma verifies separately and the main proof closes with its call; validate in a future run since this cluster does not contain a confirmed success for the same trajectory.

**Avoid or stop:**
- Do not extract a helper if an existing lemma already covers the fact.
- Do not hide a missing trait or closed-definition assumption behind a helper without proving it.

<a id="verus-global-070"></a>

## verus_global_070 — Introduce a helper lemma to unpack fold_left accumulator semantics

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A property depends on the result of a fold_left-based function and needs to relate the full accumulated value to the prefix result plus the tail element.

**Obstacle:** The verifier does not automatically unfold the fold_left accumulator in a way that connects the full result to the list structure.

**Mechanism:** Prove a separate helper lemma that relates the full fold_left result to the prefix result and the last element, then use that equality in the main proof.

**Procedure:**
1. Identify the list decomposition, such as sets == prefix.push(last).
2. State an equality relating the full fold_left accumulator to the prefix accumulator and the tail element.
3. Prove the equality with induction or reduction rules.
4. Use the helper equality to reason about membership or other properties in the main lemma.

**Why:** Isolating the fold_left step makes the proof modular and avoids forcing the main lemma to repeatedly unfold list and accumulator structure.

**Check:** The helper lemma verifies and the main lemma closes by using its equality.

**Avoid or stop:**
- Do not use for fold functions whose accumulator relation is not expressible as a simple tail update.
- Do not unfold a closed or axiomatic fold definition if it cannot be revealed.

<a id="verus-global-071"></a>

## verus_global_071 — Inventory and validate source/vstd lemma availability before ad-hoc proof

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A proof appears to need a reusable property, or intends to rely on a named source/vstd/seq_lib lemma; the source file, trait bounds, project, exact lemma name, module path, privacy, or preconditions may not yet have been verified.

**Obstacle:** The agent writes ad-hoc assertions or invents new proof steps while existing reusable lemmas or specs remain undiscovered; or it repeatedly calls non-existent/private vstd functions by guessed names, causing compilation/proof errors and obscuring the real proof gap.

**Mechanism:** Before adding proof code, scan the source and available libraries for relevant annotated lemmas, spec functions, and trait-bound methods; verify the exact name, module path, signature, and availability of any library lemma before relying on it. Prefer existing reasoning over new ad-hoc proof; if a library lemma is unavailable, stop guessing and build a self-contained proof from known axioms or prove directly.

**Procedure:**
1. Read the entire source file and list relevant #[verifier::...] annotated items, proof fns, and spec definitions.
2. Grep the project or vstd sources for the relevant spec function name, lemma pattern, or module path.
3. Check trait bounds for reusable lemmas on the types involved.
4. Before invoking a named library lemma, search available sources or existing verified files for the exact name, module path, signature, and privacy.
5. If unsure, use a tiny test file to check that the candidate lemma exists and has the expected signature.
6. Confirm the signature, preconditions, and availability/status of any candidate lemma before invoking it.
7. If Verus reports the function as not found or private, stop generating name variants.
8. Use existing lemmas/specs as building blocks; if the library lemma is unavailable, build the needed property from known axioms or prove it directly.

**Why:** A systematic inventory and exact-name verification reveals reusable building blocks, avoids many stuck proof-editing cycles caused by missing known lemmas or specs, and shifts effort toward the real proof gap rather than guessed library API names.

**Check:** Every named lemma used resolves to an existing item in the current environment and its preconditions are satisfied; unresolved or invented lemma names are not used. A future run contains no unresolved vstd lemma names: library dependencies are either confirmed or replaced by a self-contained proof.

**Avoid or stop:**
- Do not assume a lemma exists just because its name suggests it should.
- Do not use an existing file lemma without checking whether its preconditions are satisfied.
- Do not skip proving a genuinely missing property after inventory shows it is absent.
- Do not treat this as verifier-confirmed success; it is recovery guidance from failed trajectories.
- Do not keep calling a failed lemma with minor name variations without checking the environment.

<a id="verus-global-072"></a>

## verus_global_072 — Recognize missing trait or spec properties before repeatedly restructuring a proof

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A proof depends on a property that is not supplied by the current trait or spec, and syntactic restructuring cannot close the logical gap.

**Obstacle:** The semantics require a connection, such as between view_equal and serialization lengths, but the trait supplies no such property.

**Mechanism:** Recognize the missing trait/spec property early and stop varying proof syntax; either supply an additional lemma/axiom or change the proof strategy.

**Procedure:**
1. Determine the exact property needed to complete the proof.
2. Inspect the trait bounds and spec declarations to see whether that property is available.
3. If the property is absent, do not keep introducing nested proof functions or helper restructurings that assume it.
4. Either add the missing lemma/axiom explicitly or change the proof to avoid requiring that property.

**Why:** This failure cause shows that repeated syntactic variations fail at the same semantic gap; recognizing the missing property prevents wasted effort.

**Check:** The required property is either explicitly supplied or no longer assumed by the proof strategy.

**Avoid or stop:**
- Do not present an unverified proposed remedy from this failed trajectory as verifier-confirmed success.
- Do not add an unsupported axiom unless it is valid and intended by the spec.

<a id="verus-global-073"></a>

## verus_global_073 — Use existing substructure, trait-bound, and structural lemmas before low-level sequence reasoning

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A composite or sequence/serialization proof is stalling on manual low-level index, subrange, or prefix assertions while relevant lemmas exist on trait bounds or in the file.

**Obstacle:** The verifier cannot close many direct low-level sequence equalities, but it can combine existing structural or trait-level lemmas if they are explicitly invoked.

**Mechanism:** Inspect trait bounds and the available structural lemmas; call sub-proofs for immediate substructures and chain their results into the composite property rather than performing manual index-based reasoning.

**Procedure:**
1. Identify the immediate substructures or component types of the composite goal.
2. Check trait bounds for lemmas on those substructures, such as symmetry or injectivity.
3. Find existing structural lemmas for serialization/prefix/equivalence relationships.
4. Invoke those sub-lemmas with the relevant instances and let the verifier combine their conclusions.
5. Avoid writing direct subrange equality or case-split assertions unless no existing lemma applies.

**Why:** This merges success and failure evidence: existing structural lemmas encapsulate the hard inductive relationships, so invoking them is more reliable than manual low-level sequence reasoning.

**Check:** The main proof closes through calls to existing sub-lemmas rather than unresolved manual index or subrange assertions.

**Avoid or stop:**
- Do not assume a trait-bound lemma exists without checking the trait declaration.
- Do not invoke a structural lemma if its preconditions are not satisfied.
- Do not use existing lemmas to hide a missing trait property.
