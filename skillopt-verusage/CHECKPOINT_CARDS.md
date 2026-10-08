# Three checkpoints and native SkillOpt cards

This is a locally tested implementation with a user-authorized38-source campaign,
not a completed downstream experiment or a claim that selected points improve
utility. `require_design_review()` admits only the explicit reviewed38-source
contract; other paid entry points remain closed. The real two-question smoke and
the final frozen artifacts each require a hash-bound qualitative quality receipt
before expansion or held-out validation, respectively.

## Selection interface

`checkpoint_selection.select_checkpoints(report, trace, snapshots, policy=...)`
returns the same `three-checkpoints-v1` contract for every policy. Hints, actors
and card batches consume this contract, not a particular scoring algorithm.
New strategies can register an ordered provider tuple in `POLICIES`, or pass
`providers=[...]` directly with their own versioned policy name. Each provider
returns `event_index`, `kind`, `reason`, `output_token_span`, `fallback`, and an
optional integer `priority` (lower first). Shared admission, duplicate-context
screening and the exactly-three requirement cannot be bypassed by a provider.

`rule_based_v1` uses these ordered pools:

1. Start of consecutive failed-verifier platforms, ranked by output-token span.
   Every target/helper component has unchanged matched lines and denominator;
   verifier tier is unchanged; known error counts do not improve or worsen.
   Unknown counts are labeled unknown, not treated as zero.
2. First explicit compiler error after a compiling proof failure, ranked by
   output tokens until compilation recovers (or the trace ends). This version
   chooses the post-error boundary; a pre-error variant can be a new provider.
3. Fallback failed-verifier boundaries, substantive completed reads, initial
   context, then administrative reads; chronological within each fallback tier.

Only completed canonical boundaries count. Passing code, post-success contexts,
target-absent probes and duplicate code-plus-visible-prefix contexts are excluded.
A continuous compiler-error episode gets at most one point. Lynette failures
and timeouts reject a seed; the selector continues through the pools to fill
three. No final reference is invented for the failed original. The
`coverage_top3_v1` control uses target-only platforms with the same admission/fill.
Even fallback points are not evidence of stalls. Selection is retrospective and
is not represented as an online stoppage detector or a necessity/causality proof.

Offline preparation (no model calls):

```bash
export PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt
python3 -m skillopt_verusage.checkpoint_prepare \
  --manifest fixed-claude-stratified-80-seed20260814/train/items.json \
  --source-root "$ORIGINAL_TRAIN_RUN" --reviewed-root "$REVIEWED_PROGRESS_RUN" \
  --output-root "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/checkpoints-fresh" \
  --lynette-bin "$LYNETTE_BIN" --policy rule_based_v1
```

Output must be a fresh approved external child. Reviewed report and source-event
hashes bind all 39 successful curves. One failed original is retained using
diagnostic/context candidates. Outputs include selections, 120 fork jobs and
per-source preservation audits. `Campaign.prepare_selection()` uses the same
command implementation; config adds `reviewed_progress_root` and optional
`checkpoint_policy`, `actor_workers`, `card_workers`.

## Forks and cards

Each question gets three independently named hint/continuation directories.
Continuation starts from exact checkpoint code plus its complete visible actor
prefix and a screened hint. This is context rehydration, not restoration of a
live Codex session or hidden model state. The actor never sees the future suffix
or teacher's final reference. Prefix and hint hashes bind the continuation.

`native_card_update.task_group()` preserves one original and three full suffixes,
with reconstruction recipes for shared prefixes and distinct evidence namespaces.
It rejects missing continuations, swapped hints/seeds/prefixes, invalid providers
and wrong model/source/skill contracts. Valid failed/time-out branches stay in.

`update_cards()` calls the pinned native SkillOpt `run_minibatch_reflect(M=2)`.
Each native input item is one source-question group, not one branch. Synthetic
failure routing keeps mixed outcomes in the same group; real outcomes remain
unchanged in evidence. One model call receives two groups/eight logical traces.
Original-only control uses the identical path with two original traces per call.
Pairs are deterministic: sort by losslessly encoded original-evidence size and
pair largest with smallest. Both card conditions use the same original-derived
pairs; augmentation outcomes/trace lengths never change pairing. This avoids a
large-large input pair without dropping traces, not a claim about learning quality.

The analyst emits `trace_analyses` for every supplied trace and `cards`, never
skill edits. A host-generated empty-edit envelope satisfies native parsing.
Generic skill patch normalization/aggregation/ranking/application is replaced by
the audited card-bank sink. Thus this is a native Reflect-based update adapter,
not an unmodified complete generic SkillOpt trainer. The separate native-skill
baseline retains its original algorithms.

Cards have Trigger/Action/Why/Validate/Avoid-when prose, evidence refs, distinct
source questions and limitations. Exact duplicate content is merged with all
provenance retained; no model-based ranking or forced number of cards. Zero
cards is a valid no-update. Deployable bank contains only id/content and reuses
the existing indexed card bundle; private provenance stays in external outputs.

`build_bundle(..., autonomous_retrieval=True)` deploys the complete title/Trigger
index and a read-by-ID helper only. The actor decides which cards to read, when,
and how many; no lexical ranking, fixed top-k, or mandatory retrieval trigger is
deployed. All cards remain available, and private provenance/source metadata is
not copied. The default bundle mode retains its optional lexical-search helper
for existing callers. Retrieval audits count visible reads, not correct use or
causal benefit; those require qualitative trace review and downstream evaluation.

All full two-question requests are admitted before any model request. Lossless
shared-string compression is allowed; silent truncation or splitting an oversized
pair is not. Actual augmented batch sizes can only be checked once real suffixes
exist. Configured text-only admission uses a fixed-hash official tokenizer, with
padding/truncation disabled and conservative framing/output allowance; unsupported
payloads or tokenizer mismatches fail closed. Without configured tokenization,
the conservative byte guard remains. API usage is authoritative; this simplified
token count is never applied to actor/tool/history payloads. Main actors remain
DeepSeek V4 Pro/max/1800s and evaluation remains 600s;
teacher/card transport also uses Pro. Costs are ledger-recorded without artificial
per-method cash caps. Unknown cost/provider failures still stop phase transitions.

## Local verification

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt \
  python3 -m pytest -q skillopt-verusage/tests/test_checkpoint_selection.py \
  skillopt-verusage/tests/test_native_card_update.py \
  skillopt-verusage/tests/test_augmentation_campaign.py
```

Tests call real native Reflect with a fake transport, including six isolated
forks feeding one eight-trace batch. They do not generate paid hints/cards or
measure learned-card usefulness. Raw originals and sealed splits stay read-only.
