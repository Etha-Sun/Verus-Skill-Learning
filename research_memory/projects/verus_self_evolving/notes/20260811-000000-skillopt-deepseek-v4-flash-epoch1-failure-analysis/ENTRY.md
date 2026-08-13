# SkillOpt DeepSeek V4 Flash Epoch-1 Failure Analysis

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-11T00:00:00-05:00`
- status: `complete`

## Objective

Diagnose whether the valid negative SkillOpt epoch is primarily explained by
weak target-model capability, weak optimizer-model capability, or the local
optimization contract. This is a post-hoc mechanism audit, not a new model
comparison or a general SkillOpt effectiveness claim.

## Evidence Base

The audit used only the completed v5 run below
`${VERUS_SKILL_RUN_ROOT}`:

`skillopt-verusage/deepseek-v4-flash-e1-corrected-v5-20260810/`

The run used `deepseek-v4-flash` for both the VeruSAGE target and the SkillOpt
optimizer. It completed all 80 planned task ledgers with no invalid tasks,
silent truncations, or task requeues. The generated candidate was evaluated on
the same 20 selection tasks as the initial skill and was rejected.

## Aggregate Results

| Metric on the 20-task selection set | Initial skill | Candidate skill | Change |
|---|---:|---:|---:|
| Strict solves | 6 | 4 | -2 |
| Provider requests | 837 | 1,461 | +624 (+74.6%) |
| Prompt tokens | 6,238,467 | 15,126,540 | +8,888,073 (+142.5%) |
| Completion tokens | 2,770,316 | 4,296,881 | +1,526,565 (+55.1%) |
| Estimated target cost | USD 0.970353 | USD 1.707599 | +USD 0.737245 (+76.0%) |
| Sum of per-task wall time | 20,754.7 s | 30,245.7 s | +9,491.0 s (+45.7%) |

Paired outcome transitions were:

| Initial -> candidate | Tasks |
|---|---:|
| fail -> fail | 14 |
| fail -> pass | 0 |
| pass -> fail | 2 |
| pass -> pass | 4 |

The exact two-sided McNemar p-value is 0.5 because there are only two
discordant pairs. The 95% Wilson intervals are wide: approximately
14.5%-51.9% for the 6/20 initial result and 8.1%-41.6% for the 4/20 candidate
result. The sample therefore does not establish a population-level regression.
It does establish that this candidate failed its live gate, produced no new
solves, and consumed substantially more resources on this frozen selection
set.

## Key Findings

### 1. One regression is directly linked to false learned guidance

Task `923e5db8e4029514048d` is
`lemma_seq_fold_left_append_len_int`.

- Initial skill: solved in 3 requests, 62.4 seconds, USD 0.002651.
- Candidate skill: failed after 128 requests, 6,055.9 seconds,
  USD 0.311291.

The candidate skill recommends the concrete identity:

```text
s.fold_left(init, f)
  == s.drop_last().fold_left(f(init, s.last()), f)
```

This is false for a general left fold. For a two-element sequence `[a, b]`,
the left side is `f(f(init, a), b)`, while the recommended right side is
`f(f(init, b), a)`. The target copied this pattern into a helper lemma almost
verbatim, and the final independent Verus check failed at that assertion.

The false identity was not present in the successful training proof from
which the optimizer generalized. That proof used the correct last-element
form `f(s.drop_last().fold_left(init, f), s.last())`. The optimizer therefore
introduced a semantic error while compressing a success trajectory.

**Interpretation:** this failure is active prompt poisoning, not merely a hard
task that the target happened not to solve.

**Implication:** concrete formulas and code patterns must not be promoted into
a global skill without replay or an independent semantic check.

### 2. The candidate contradicts the benchmark's safety contract

Task `f78c3bf5d4b367325ef0` regressed from a 68-request verified repair to a
185-request failed repair. Its input intentionally contains existing trusted
`external_body` helper lemmas. The successful initial-skill repair calls those
helpers and passes both Verus and Lynette.

The learned skill nevertheless says that calls to lemmas with
`unimplemented!()` or `external_body` bodies are verification bypasses and
must be removed. It also warns that proof blocks inside executable bodies may
be rejected, although the baseline repair uses such proof blocks and passes
Lynette. The candidate target trajectory then calls the pre-existing helpers
despite the skill's prohibition and still fails Verus.

The skill also contains internal policy conflicts, including discouraging
`choose` in one section and recommending a `choose` witness in another.

**Interpretation:** the optimizer did not distinguish "do not introduce a new
bypass" from "do not use trusted declarations already provided by the task."
It also did not reconcile its merged edits against the actual VeruSAGE/Lynette
contract.

**Implication:** optimizer capability matters, but a host-side contract linter
is also required; relying on the optimizer model alone is unsafe.

### 3. The update was too large and expensive for a multi-call harness

The skill grew from 838 bytes / 112 words to 10,322 bytes / 1,491 words. The
optimizer merged two append operations: an 8,073-character failure block and
a 1,409-character success block. Its merge reasoning explicitly prioritized
the failure block and appended it unchanged.

On two selection tasks with exactly three requests under both conditions, the
candidate used exactly 6,270 more prompt tokens, consistent with about 2,090
extra skill tokens per request. Across the full gate, the larger skill was
repeated through 1,461 requests and amplified both direct prompt overhead and
longer search trajectories.

The effect was not uniformly negative. On the four tasks solved by both
skills, requests fell from 151 to 79 in aggregate, mainly because one IronKV
task improved from 121 to 49 requests. However, the candidate produced no new
solves, regressed two solved tasks, and increased requests on 11 of the 14
tasks that remained unsolved.

**Interpretation:** the candidate likely contains some locally useful tactics,
but a monolithic global append makes irrelevant or harmful rules hitchhike
with them.

**Implication:** retain clause-level candidates and task-state routing rather
than promoting the whole 10 KB document.

### 4. Weak target capability is plausible but not isolated

The target baseline solved 6/20 selection tasks and 8/40 training tasks. Long
repair loops and a 20%-30% solve rate are consistent with a substantial
DeepSeek-V4-Flash capability ceiling on these tasks. The historical GPT-5.5
100-task result was much higher, but it used a different sampled task set and
harness, so it is not a matched model comparison.

There is no A/A repeat of the initial skill on these 20 tasks. Consequently,
the two paired regressions cannot be cleanly separated into target sampling
variance and skill causality. The copied false fold identity provides direct
causal evidence for at least one harmful-skill mechanism, but not for the full
10-point solve-rate difference.

**Interpretation:** DeepSeek Flash is probably weak as a target, but the
current evidence is stronger that it was unreliable in the harder optimizer
role.

**Implication:** replace the optimizer first while holding the cheap target
fixed. This is also the lower-cost intervention: the full epoch used only 7
optimizer calls / 181,930 optimizer tokens versus 4,184 target requests.

### 5. The one-step epoch cannot learn from this rejection

With train size 40, batch size 40, and accumulation 1, the run has exactly one
fast-update step per epoch. The step buffer is populated only after that
candidate is gated and is reset at the start of the next epoch. Therefore the
rejected edit buffer cannot influence another fast update under this
configuration. Meta skill was disabled, and the epoch-1 slow update was only
the upstream placeholder.

**Interpretation:** running epoch 2 unchanged would not be a robust response
to the diagnosed failure; the most specific rejection evidence is not carried
into its next fast update.

**Implication:** repair the optimizer and representation contract before
spending on another 40/20 epoch.

## Decision And Minimal Next Experiment

Do not continue the identical Flash/Flash configuration into epoch 2.

The lowest-cost causal sequence is:

1. Re-optimize the already stored 40 trajectories with a stronger optimizer,
   while keeping DeepSeek-V4-Flash as the target. This step needs no new target
   rollouts.
2. Require an atomic, compact candidate: at most one or two short clauses, no
   unverified concrete proof formula, and no blanket rule that conflicts with
   the frozen harness safety contract.
3. Add host-side checks for skill length, internal contradictions, forbidden
   changes versus permitted use of pre-existing trusted context, and replay of
   any concrete Verus formula against its originating task state.
4. Run one A/A repeat of the initial skill on the same 20 selection tasks to
   estimate target variance, then run one 20-task gate for the compact
   candidate. Do not accept a one-task apparent improvement without a matched
   repeat.
5. If a stronger optimizer still produces a compact, valid skill that cannot
   improve the Flash target, then test a stronger target on the same frozen
   tasks. That would more directly diagnose the target capability ceiling.

No held-out test should be opened during this diagnosis.

## Data Safety

All inspected inputs and generated artifacts remained in their existing
locations. No raw or sealed dataset was modified, moved, renamed, copied, or
committed. No new model call or experiment was launched.
