# Checkpoint case studies: eight contrasts across seven traces

## Review protocol

Cases cover the longest observed platform, productive flat intervals, a textual
false-positive drop, structural/API backtracking, repeated failed obligations,
off-target probes and a short zero-platform trace. This is purposive coverage of
failure modes, not a random sample or an estimate of their prevalence. Every
case uses the same questions: what state and diagnostic existed, what the next
source edits did, what changed in target/helper verification, and what a hint
at each boundary could address. No hint was run, so benefits remain hypotheses.

Evidence addresses below identify original task IDs, report call ordinals and
original event indices. Resolve them through the reviewed report's provenance
and parent trace paths in `ENTRY.md`; no raw trace is copied into research memory.

## 1. A flat target curve can hide productive helper work

Target: `IR / lemma_is_marshalable_CKeyHashMap`, `a3c9af1afebbd8d5fe93`.
Calls15-18, original events121,128,135,142, cost4,000 output tokens.

|Call|Target overlap|Verified functions|Reported errors|
|---|---:|---:|---:|
|15|1/23|2|3|
|16|1/23|2|2|
|17|1/23|3|1|
|18|1/23|4|1|

The target-body hash is identical at all four states. Snapshot/diagnostic review
shows serialization helper proof work outside that body; by call17 only the
target's marshaling assertion remains reported as failing. Additional helper
verification succeeds at call18 while the target still fails. Thus the flat
curve is not evidence of four thousand tokens of ineffective work.

Candidate implication: retain platform starts as hypotheses, but annotate newly
verified helpers and active failing obligations. A long platform containing
dependency progress should not automatically outrank repeated unproductive
attempts merely because it is longer. This does not prove a hint cannot help it.

## 2. A text-overlap regression need not delete a proof strategy

Same target, calls20-21, events156-163. Overlap falls20/23 to18/23;
verified-function/error counts remain4/1 and verification tier stays proof-error.

The actual diff adds a vector-length bound assertion and changes three fold
expressions to include explicit integer casts. It does not remove the broad
proof structure. Exact reference-line matching penalizes those rewritten lines.
This is a concrete counterexample to equating every overlap drop with proof
deletion. Unchanged diagnostics do not establish semantic improvement either.

Candidate implication: inspect the changed obligation/strategy, not just negative
overlap. Pre-drop and post-drop hints here are not automatically valuable. Treat
this as a negative control when considering an "all regressions" candidate pool.

## 3. Pre-regression prevention and post-regression diagnosis differ

Target: `AL / seq_equal_preserved_by_add`, `f91ac92b861061915a41`.
Call3/event30 to call4/event40, with subsequent calls5-9.

At call3 a22-line explicit pointwise proof still has a proof error and9/14
overlap. The next rewrite replaces it with a nine-line approach invoking a
nonexistent sequence extensional-equality method. Call4 has5/14 overlap and
compiler diagnostics identifying two missing-method uses. Call5 remains in
compiler failure. Call6 removes those calls but still fails the postcondition;
call7 restores pointwise work, and call9 first verifies the target.

- Before the drop, a hint could help preserve/use the existing pointwise strategy
  and avoid an invalid shortcut. This is a preventive hypothesis.
- After the drop, the concrete missing-method diagnostic is available; a hint
  could address the installed API and return to a valid proof route. This is a
  diagnostic hypothesis.

Both points are defensible research candidates, but they address different
information states. The observed recovery does not tell us which intervention
would save more tokens. They also belong to one episode, not two independent
stagnation discoveries; a three-point diversity policy should acknowledge that.

## 4. A second actual API dead-end corroborates the distinction

Target: `IR / set_map_union`, `3a77a3e4e72edf600e2a`.
Call5/event39 to call6/event47; first target pass is call8.

The rewrite replaces a14-line membership proof with a single presumed library
lemma call. That function is absent from the installed library. Overlap falls
7/13 to zero and the verifier switches from proof errors to a missing-function
compile diagnostic. Unlike the casts in case2, this is an observed operational
dead-end, though no hint-effect experiment was conducted.

Candidate implication: classify missing installed APIs separately from logic
obligations and strategy changes. A post-error checkpoint has precise evidence;
a pre-error checkpoint is a hypothesis about avoiding the upcoming rewrite.

## 5. The longest platform also exposes sparse verification sampling

Target: `AC / lemma_always_there_is_no_request_msg_to_external_from_controller`,
`d61c17b4662ca6d9cd58`. Calls1-2, events20-101.

Recorded output tokens rise393 to95,807: a95,414-token flat span. The target
body stays empty at both endpoints and both have proof-error tier. However,
verified functions increase0 to1, and original events contain source/library
searches, reads and helper edits. There is no dense target-verification sampling
inside this long interval. Counting started/completed/derived records as separate
actions would overstate the number of actual commands, so no such count is used.

Candidate implication: the platform beginning is an interesting strategic-hint
candidate, but endpoint overlap cannot establish that the whole interval was
stagnant. Inspect long search/read intervals and newly verified dependencies as
separate signals. They may suggest an earlier knowledge gap, but usefulness is
not established. The interval length is not a recoverable-savings estimate.

## 6. Repeated obligation/API variants are stronger contextual evidence

Target: `IR / remove`, `3d762c82c4ba18b0c1b6`.
Calls6-14, events49,59,66,73,101,109 for the inspected key states.

Target overlap remains5/6 through repeated changes. Call6 fails an assertion
relating sequence removal and its set representation. Removing it at call7
moves the failure to the equivalent postcondition. Calls8-9 try variants of a
set-extensionality interface; call9 instead fails argument-count checking.
Call13's set-equality macro still cannot prove the desired relation. At call14,
proved sequence-removal helper lemmas use the relevant nonduplication premise
and the complete candidate verifies three functions.

The executable scaffold explains why5/6 overlap is not "83% of the proof done".
Changing assertion location also explains why a literal diagnostic fingerprint
is not a robust semantic stagnation detector. Count a normalized obligation and
attempt family, not merely an identical stderr string or identical error count.

Candidate implication: the beginning of repeated attempts at the same missing
sequence-to-set fact is a plausible alternative checkpoint. Distinguish actual
helper construction progress from repeated interface substitution. Normalized
obligation tracking is a proposed next implementation, not implemented here.

## 7. Full target overlap and successful probes can both mislead

Target: `IR / lemma_fold_left_append_merge`, `cab5b8b8dbe5cad21502`.
Calls1-4/events27,34,41,48 contain a standalone probe instead of the target.
Call4 verifies that probe, not the original task. Those four coverage values
are explicitly unknown and excluded from overlap-platform/regression counts.

At call5/event56 the original target returns with a one-line helper invocation:
target overlap is already1.0. Calls5-9 remain uncompilable because syntax/type
errors occur in the new helper code. Their state-aware platform is2,938 tokens.
Call10/event91 first verifies the complete three-function candidate without
changing the target body.

Candidate implication: measure dependency readiness as well as target overlap.
A useful recovery point might follow a learned probe result when the complete
target is restored; an isolated target-absent snapshot is not automatically a
safe fork seed. These boundaries require baseline/preservation checks in replay.

## 8. A genuinely short trace needs a non-platform fallback

Target: `AL / always_double`, `a7d8648acdb905dad951`.
Call1/event14 has an empty target and a proof error. Call2/event21 verifies
the target at full overlap; call3/event33 is host validation. Total output1,780
tokens. It has no failed-to-failed flat pair and no regression flag.

There are not three distinct failed-verifier snapshots to select here. The raw
trace still has presolution task, read/diagnostic and edit-context boundaries.
Thus honoring three checkpoints requires defining the eligible conversation
boundaries and replay semantics, not inventing platforms or using post-success
states. Identical code with different accumulated context is not necessarily
the same checkpoint, but that must be specified rather than silently assumed.

## Evidence-bounded proposal, not a selected policy

1. Keep longest coverage-platform starts as a candidate family consistent with
   the user's graph intuition; annotate progress in verified helper dependencies.
2. Add repeated failed-obligation/unsuccessful-attempt episode starts and
   prolonged search/API uncertainty as candidate families. These are supported
   qualitative directions, not validated automatic detectors.
3. Classify actual strategy deletion/API dead-ends separately from casts,
   formatting and diagnostic-parser changes before treating a regression as
   promising. Preserve both pre-drop and post-drop addresses for comparison.
4. Fill to three using eligible presolution context boundaries when these signals
   are insufficient. Review episode duplication and context replay first. Do not
   silently reduce the count, split a flat line arbitrarily, or reuse solved states.
5. Later matched hint/no-hint continuations must test usefulness; this audit
   cannot choose a causally optimal ranking or prove token savings.

The initial analysis is complete with one explicitly incomplete pruning case.
No selector, fallback thresholds, hint branches or native card generation were
implemented or paid for in this investigation.
