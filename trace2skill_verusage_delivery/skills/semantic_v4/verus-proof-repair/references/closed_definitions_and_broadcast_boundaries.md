# Closed and Opaque Definition Boundaries

**Consult when:** A proof requires revealing an opaque definition with compute_only, or reveal/broadcast attempts are failing because a term is hidden behind a closed/axiomatic definition.

**Do not consult when:** The function is obviously open and the issue is a missing recurrence or insufficient invariant; revealing definitions will not help.

<a id="verus-global-032"></a>

## verus_global_032 — Use `assert ... by(compute_only)` to reveal opaque definitions early

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** When a proof is stuck because Verus is not automatically unfolding an opaque function whose body is needed to align an assertion or induction scheme.

**Obstacle:** Verus treats the relevant function body as opaque, so the proof state remains unreduced and later assertions or induction schemes are mismatched.

**Mechanism:** An `assert ... by(compute_only)` step forces Verus to reduce or expose the opaque definition, making the actual function behavior explicit and guiding a correct proof shape.

**Procedure:**
1. When function behavior is unclear and repeated assertions or induction steps do not match, suspect an opaque definition.
2. Before further proof attempts, use `assert ... by(compute_only)` on the specific instance that should reduce.
3. Use the revealed definition to align the next assertion, rewrite, or induction scheme.

**Why:** The source failure memory reports that this technique succeeded after many failed attempts, so it is retained as an early positive diagnostic for opaque definitions rather than as a general proof completion step.

**Check:** Confirm that `compute_only` actually exposes the expected body and does not fail with a closed-function error; if it fails, the boundary is closed and a different path is needed.

**Avoid or stop:**
- Do not use for a closed definition when Verus reports it cannot reveal the function.
- Do not treat `compute_only` as a substitute for proving a missing bridge relation when the unfolded body is not the real obstacle.

<a id="verus-global-033"></a>

## verus_global_033 — Stop reveal/broadcast attempts when closed or axiomatic definitions hide triggers

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** When a proof needs to connect a goal term expressed through a closed definition to a lemma or broadcast trigger, or when it needs the internal definition or equational behavior of a spec function or axiom, especially when reveal, reveal_with_fuel, or broadcast use is being attempted.

**Obstacle:** Closed spec/ghost definitions and axiomatic or non-recursive functions block direct unfolding and trigger visibility, so reveal fails, broadcast lemmas do not fire, and repeated fuel tweaks cannot expose the missing fact.

**Mechanism:** Broadcast lemmas only match direct trigger terms in the proof context; terms hidden behind closed or axiomatic definitions cannot expose the trigger. The correct move is to determine early whether the relevant spec function is open or closed/axiomatic, stop repeated reveal or fuel attempts on closed definitions, and pivot to externally visible structural properties or a dedicated equational lemma.

**Procedure:**
1. Identify the exact spec function whose internal definition or equational behavior is needed.
2. Test whether reveal(...) or reveal_with_fuel(...) exposes that definition; if it reports a closed-function, axiomatic, or opaque error, mark the definition as a closed boundary and stop repeating that attempt.
3. Before introducing a broadcast lemma, confirm that its trigger term is directly visible in the goal or known facts, not merely buried under an unevaluated closed-definition application.
4. When the trigger is hidden, do not rely on the broadcast lemma; look for a visible rewrite, a dedicated equational lemma, or another route that uses only externally available structural properties.
5. Avoid restructuring the same impossible injectivity or equality approach around the closed definition, and do not keep tuning fuel further.
6. If no visible route is available, stop rather than repeating failed reveal or broadcast strategies; treat any alternative bridge as unverified until confirmed by the verifier.

**Why:** Failure records from the marshal serialization trajectory show a closed definition could not be revealed and a broadcast lemma was ignored because its trigger was hidden behind that closed definition. Additional failure-derived evidence from Verus extra filter lemmas shows repeated reveal_with_fuel and axiom-broadcast attempts over inaccessible axiomatic/non-recursive definitions. This pattern avoids long iterations on unachievable proofs over inaccessible definitions and redirects effort to viable structural reasoning.

**Check:** Verify that the relevant trigger term appears syntactically in the goal or an active assertion; if it does not, do not expect broadcast-group lemmas to apply. Also confirm that no closed or axiomatic definition is still hiding the needed term before relying on reveal or broadcast as a proof dependency.

**Avoid or stop:**
- Do not assume explicit assertions or helper lemmas automatically bridge a closed definition if the same closed terms are still hidden from the verifier.
- Do not present an unverified proposed remedy from a failed trajectory as verifier-confirmed success.
- Do not use broadcast or reveal as automatic fixes without confirming what facts they supply.
- Do not apply to open recursive definitions where unfolding is expected to help.
