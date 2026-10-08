# Helper-inclusive case studies

Purposive contrasts, not a random prevalence estimate or hint experiments.
Use original IDs/call ordinals/events to resolve exact sources through the reviewed
provenance. Prior cases remain preserved; these update and extend their scope.

## 1. A long empty-target platform was largely helper construction

`a61cd2515cc23386df85`, stable specification and all-phase invariants.

|Call/event|Output tokens|Target match|Combined match|Verification|
|---|---:|---:|---:|---|
|1/23|556|0/6|0/80|Proof error|
|2/76|12,290|0/6|6/80|Proof error|
|3/89|18,443|0/6|28/80|Compile/unparsed|
|5/103|19,245|0/6|28/80|2 proof errors|
|6/110|20,197|0/6|29/80|1 proof error|
|7/123|24,860|5/6|71/80|Compile/unparsed|
|8/130|26,040|5/6|79/80|Verified|
|9/137|27,130|6/6|80/80|Verified|

Six related helpers supply74 reference lines. The old19,641-token pure target
platform is not one unproductive interval: helper text grows0 to29 retained lines.
The combined curve instead isolates an802-token pure platform (calls3-5), or526
tokens when the tier is also constant (calls3-4). Calls3/4 are candidates for
diagnosing the compile obstacle; call1 is a broad strategy candidate, not an
evidenced19,641-token waste point. No intervention has been tested.

## 2. A100% target curve can conceal a mostly unfinished proof dependency

`da745d47dba2a047f98d`, eventual stability of the scheduled resource.
Three retained helpers contribute41 lines beyond the11-line target.

At call2/event89, target overlap is11/11 but combined overlap is17/52 and the
candidate does not compile. Calls3-5 remain target-flat while combined matches
increase17,20,27 and reported errors fall5 to3. Calls8-9 increase27 to46 combined
matches, despite the target still being unchanged. Later calls13-19 progress46
to51, and call20/event262 verifies at52/52. Seven strictly pre-pass helper-gain
transitions are visible, plus one transition into the first pass.

The target-only43,839-token pure platform is split into475,6,609,7,503,2,387,773
token spans. Calls11-13 are particularly informative: combined overlap stays46/52
while errors fall3 to1, so even the new line metric is not a complete semantic
progress detector. Inspect the actual surviving obligation before labeling a
span stalled or prioritizing its first point.

## 3. Include retained helpers, not every explored lemma

`a3c9af1afebbd8d5fe93`, map marshalling.
Final scope includes u64 serialization length and two specialized fold helpers.
Their35 reference lines supplement the23 target lines. Calls15-16 keep target
1/23 while combined overlap rises1/58 to2/58; reported errors fall3 to2. This is
a genuine correction of the old target-flat view.

The separately explored `lemma_CKeyKV_is_marshalable` is outside the final static
closure; its11/13 to13/13 old diagnostic overlap must not inflate final-path
progress. It can still be useful exploratory/learning evidence. At calls20-21,
casts lower textual overlap without removing the broad proof strategy. Keep this
as a negative control for blindly choosing all overlap regressions.

## 4. Helper inclusion does not remove all repair plateaus

`cab5b8b8dbe5cad21502`, fold append/merge.
Calls1-4 are target-absent probes and remain unknown, even when the probe verifies.
Calls5-9 have target overlap1/1 and combined15/17, yet syntax/type errors remain:
the2,938-token plateau survives helper inclusion. Call10 verifies at15/17; only
call11 reaches17/17 after a later rewrite. This exposes another limitation:
final-text completeness and proof correctness are different quantities.
The restored full-target state at call5 is a diagnostic candidate; a probe's
standalone successful state is not automatically a preservation-safe fork.

## 5. A recurring obligation is not an identical diagnostic string

`3d762c82c4ba18b0c1b6`, executable sequence removal.
Target scaffold contributes6 lines, helpers18. Calls6-13 repeatedly attack the
same sequence-removal/set-membership relation: an assertion becomes a postcondition,
then several set-extensionality API variants fail. Call14 verifies after proper
helper construction and the nonduplication premise are used. A literal stderr
signature misses the continuity when location/API/error category changes.

This is a stronger contextual candidate family than high unchanged target overlap:
cluster attempts by the needed logical fact, not solely error text or count.
Such semantic grouping is case-reviewed here, not yet an automated selector.

## 6. Real API backtracking supplies two different intervention states

`f91ac92b861061915a41`, sequence equality under append: call3/event30 still has
the pointwise strategy; call4/event40 replaces it with unavailable `Seq.ext_equal`
and fails compilation. First verification is call9.
`3a77a3e4e72edf600e2a`, set/map union: call5/event39 is a membership proof;
call6/event47 replaces it with unavailable `lemma_map_union`; first pass is8.

Pre-drop hints could prevent invalid shortcuts. Post-drop hints can use the exact
missing-API diagnostic. Both are valid candidates, but neither is demonstrated
more useful. They are two states of one failure episode, not automatically two
independent checkpoint slots. Contrast with the cast-only false regression above.

## 7. Sparse sampling remains a limit even with helper scope

`d61c17b4662ca6d9cd58`: calls1-2/events20-101 still span95,414 output tokens on
a flat combined curve. The retained new helper has only one final line; seven
other changed proof helpers are outside the final static closure. Source reading
and exploratory helper work lie between these sparse verifier endpoints. Neither
target-only nor combined coverage can prove all95,414 tokens were wasted.
Use actual action/context episodes to localize the knowledge gap within it.

## 8. A short successful trace cannot supply three code-distinct failure states

`a7d8648acdb905dad951`, always-double: call1/event14 fails an empty target;
call2/event21 passes; total output1,780 tokens. No platform or regression exists.
Initial state, completed reads and first-error context provide distinct prefix
boundaries, often with identical code. Filling three must use prefix identity and
context, not fabricate three failures or include known passing code just before
the first successful verification. Such fallback points have no established value.
