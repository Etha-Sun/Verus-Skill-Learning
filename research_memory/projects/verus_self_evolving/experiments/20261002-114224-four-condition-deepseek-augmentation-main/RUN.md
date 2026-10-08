# Launch handoff

## Superseding stop and alignment status

External progress stopped at2026-10-02T19:06:30 UTC with
`Card missing or exceeds byte cap`; no active campaign/actor remains. Snapshot:
36 hint continuations,3 rejected hints, O4/H3 accepted source proposals,
evaluation0, new settled provider estimate USD5.076593324 across812 requests,
zero unknown requests/open reservations. After the user's objection, the full
transcript-to-code audit found fundamental method discrepancies. See
[MEETING_ALIGNMENT_AUDIT.md](MEETING_ALIGNMENT_AUDIT.md). Do not restart; the
older live-status and continuation instructions below are historical only.

## Configuration audit at card-extraction stage

The user asked how cards and stagnation checkpoints are actually extracted.
This was a read-only code/manifest/status audit, not authorization to change the
selector or launch another run. Evidence: external `selection.json`,
`progress.json`, `artifacts/native/learning.json`, `proposals/`, and
`budgets/global.json`, interpreted against `campaign_evidence.py` and
`augmentation_campaign.py`. Science evidence interfaces are unavailable; existing
files plus this compact parsed-evidence record are the fallback.

- All models Pro; original/hint actors max/1800s; validation max/600s; teacher,
  card extractor and native optimizer high. Teacher output cap8192 tokens and
  extractor/native cap16384, including reasoning. Actor request default131072.
- Selector has39 successful-source checkpoints:17 plateau-rule and22 middle
  fallbacks. Eligible points are saved Verus-verifier states excluding the final
  code hash. Consecutive identical verifier count tuples form a plateau only if
  at least two points and positive intervening output-token cost. Choose the
  greatest-token plateau, break ties earliest, and resume from its first point.
  Otherwise select lower-middle eligible verifier point. There is no hard token,
  time or three-attempt threshold, no patch-F1, and no semantic diagnostic
  matching. Equal counts can hide changed obligations. This is an offline
  hindsight selector, not demonstrated online stagnation detection.
- Teacher sees complete original evidence, future events and final proof;
  actor receives task, saved checkpoint, initial skill/protocol and hint text,
  not privileged source corpus. Automatic hint screening does not prove meaning.
- O/H independently extract at most two cards per unique source, using all40
  originals including the failure. H adds its hint/screen record and continuation
  where present. Original and branch are one source group, not independently
  weighted tasks. Exact-text dedup only; provenance union stays host-only.
  Same700-byte/five-field/schema/audit rules for O/H. No semantic merge or native
  top-four cap on card banks. Retrieval is optional lexical top-three search,
  followed by individual read; bulk filesystem bypass is audited, not impossible.
- Parsed progress snapshot:36 continuations completed,3 hints rejected; native
  plain candidate covers40 originals and has4 selected edits. O/H each have3
  accepted source proposals (6 cards before final dedup); validation0/160.
  Global settled estimate USD4.822966104, unknown requests0; two open guarded
  requests at inspection. These are live partial counts, not final results.

The configuration explanation follows the science claim discipline: separate
parsed implementation facts, prompt instructions and unverified semantic claims.
Canonical memory remains in this repository, not the legacy read-only tree.

External campaign ID: `augmentation-main-20261002-Ws4keW`.
Tmux session: `augmentation-main-20261002`.
Current coordinator: `resume_with_card_schema.py` in the external campaign.
Current log: `resume_schema.log`. Original logs and infrastructure failures are
preserved; no historical source output or sealed dataset was changed.

## Verified before launch

- All40 source hashes, accepted Pro/max run results and common initial skill.
- Every stored snapshot diff independently regenerated from complete snapshots;
  initial whole-source diffs are represented losslessly by their full baseline.
- Full original evidence fits the conservative byte admission; no event truncation.
- Frozen deterministic selector identifies39 eligible successful sources.
- Six native success/failure-separated minibatch contexts fit without path-only
  evidence: largest rendered input is761,444 UTF-8 JSON bytes.
- Fifty-five focused tests pass, including local routed HTTP integration, budget
  admission, exact-response reuse, no unresolved replay, all40-source dedup
  provenance, deterministic checkpoints, card deployment and validation contracts.

## Runtime gates and recovery

The teacher smoke returned a completed `deepseek-v4-pro` response with recorded
usage. Its cost estimate was USD0.0274164. The first actor failed before any
upstream request because the forbidden source-run ancestor contained the allowed
Rust toolchain mount. The second actor failed at the local bridge route because
the runner appends task routing and `/v1` to the bridge root. Neither failed actor
reached the provider. Both complete failure directories remain under external
`infrastructure_failures/`. Fixes scope forbidden checks to the source corpus and
manifest, and pass the server root to the existing runner. A routed HTTP test
now covers the latter contract. Recovery asserts the single teacher ledger and
absence of unknown or outstanding costs before starting. Exact teacher request
cache was reused; no paid teacher replay. Real continuation requests and tool
events were observed with Pro/max; that continuation subsequently solved with
V2_TRACE and Verus/Lynette dual pass inside the actor budget.

The first O extraction returned735/724-byte cards; a reviewed train-only prompt
repair returned669/910-byte cards. Both outputs, ledger costs and audit stops are
preserved. Do not deploy these rejected proposals. Prompt-only constraints did
not enforce the limit. A second reviewed interface repair uses native Responses
JSON Schema, with content maxLength700 and ASCII-only pattern, the same schema
for O/H before main learning. All source identities, evidence, card fields and
hard700-byte limit remain unchanged; copied inline proof expressions are also
rejected. Native support is documented by the official
[Responses API](https://api-docs.deepseek.com/api/create-response/).
Completed teacher and actor are explicitly reused without paid replay. New
reviewed extractor calls and all failed smoke costs count against O and the
global cash cap. No held-out input has been read for this repair.
The constrained O smoke passed its complete schema/content/evidence audit at
17:21:38 UTC; the matched H smoke is currently running. Formal continuation waves
start automatically only after H passes. Full learning and validation still
remain pending at this handoff.

Full final code can also be represented by its matching last snapshot in the
already verified complete diff chain, avoiding duplicate large source files;
all40 final hashes match these lossless references. Full O wire-payload byte
admission was checked, not just inner packet lengths: maximum1,011,189 bytes
including output allowance before the small schema addition, below1,048,576.

The campaign continues automatically only after the included teacher/continuation/
O/H extraction smoke passes. It then generates at most one hint continuation per
eligible source with two workers, learns native S and source-covered O/H, freezes
four deployable artifacts, and schedules two whole paired80-attempt repetitions
at eight actor workers. All downstream clocks are600 seconds. No test20 read.
Context, audit, model/usage, infrastructure or budget failure stops the phase;
do not declare160 attempts complete from launch alone.

Inspect `progress.json`, `provider_calls.jsonl`, `budgets/global.json`,
`cost_summary.json` (when written), `frozen_artifacts.json` (when written), and
the current tmux process before any restart. Do not delete reservations. The old
source corpus still has an unresolved reservation charged conservatively to
logical method costs; it is not charged again to this new physical cap.

## Pricing and claims

Official DeepSeek docs checked on2026-10-02 still list `deepseek-v4-pro` as
V4-Pro-0813, with Pro API service retained and unchanged billing in the changelog.
Reference rates match [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)
and [Change Log](https://api-docs.deepseek.com/updates/).
Guards reserve peak, uncached upper bounds; current per-call cost tables are
price-band estimates, not actual account invoices. Their UTC-hour classifier
does not implement holiday/weekend discounts, so estimates can be conservatively
high. Direct text-only teacher/extractor requests use UTF-8 serialized-byte
token bounds plus8192 framing tokens for reservations; actor calls retain the
existing full-context upper bound. Unknown costs stop new guarded requests.

No downstream gain, equal realized-cost comparison, semantic hint correctness,
or causal card-use claim is supported at launch. Canonical research memory stays
in this repository; skills' legacy storage paths were not used for writes.
