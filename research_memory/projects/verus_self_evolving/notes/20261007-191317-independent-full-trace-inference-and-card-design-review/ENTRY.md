# Independent full trace inference and card design review

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-10-07T19:13:17`
- status: `complete_independent_read_only_review`

## Objective

User requested one independent reviewer to audit inference-time and card
design, primarily using the full trace. Review only; not a repair request.

## Context

Primary episode: approved one-case compact-index live demonstration, an
already-analyzed validation task, not a fresh confirmation or sealed test.
Its saved CLI export contains initial host prompt, all completed execution
items, outputs, snapshot diffs and validation. It explicitly lacks provider
request/response bodies, thinking text and exact request-to-item mapping.

Related entries:

- `experiments/20261007-183017-one-real-deepseek-pro-compact-index-trace-demonstration/ENTRY.md`
- `notes/20261007-185938-full-stitched-cli-trace-export-with-explicit-thinking-and-request-payload-gaps/ENTRY.md`

## Method / Actions

Spawned one reviewer without conversation-history inheritance. Reviewer read
all 2132 Markdown lines, raw/normalized/exported events, all78 card bodies,
deployment prompt/index/code, source snapshots and targeted training evidence.
Required observed/risk/missing-evidence distinctions and minimal fixes with
acceptance criteria. Preserved autonomous optional arbitrary-ID retrieval.

Main agent independently checked card-072 declarations and cp2 failed/success
diffs, library-access policy, shared parser behavior, learning prompt/version
limits and provenance support counts. Recomputed all62 source hashes with zero
mismatches; eight primary before-review hashes also match after-review files.

Used review and research-memory skills. Dedicated review/artifact/memory APIs
unavailable: local shell reports and hash receipts used instead. This is a
local design audit, not publication readiness or a Science Evidence Graph.

## Evidence

External report root:
`VERUS_SKILL_RUN_ROOT/skillopt-verusage/inference-card-review-20261007-lGqbOO/`

- `REVIEW.md`: independent Chinese report, seven ranked findings.
- `findings.json`: evidence anchors, observed/risk/missing fields, fixes/checks.
- `SOURCE_SHA256.json`: 62 immutable sources.
- `ROOT_CHECK.md`: main-agent reconciliation and scope restrictions.

Episode facts: 38 raw events, 18 completed items, 19 candidate snapshots;
14 provider requests; index read, zero body reads; independent Verus and
preservation pass. All unchanged. Index is18836 bytes including17130 index
bytes,78 rows/2632 whitespace words. These are NOT provider token counts.

## Result

F1 High: card-072 incorrectly/misleadingly describes the required inner
temporal predicate as state-level; success kept lifting and removed extra
always. Current demo did not use072, so no observed downstream harm claim.

F2 Medium: installed-library prechecks conflict with the initial workspace-only
read rule. Latent policy ambiguity, not observed unauthorized access.

F3 High (evidence): saved execution is auditable, but provider decision evidence
is incomplete. No-read is legitimate and index influence remains unknown;
this sample establishes neither card causation nor efficiency improvement.
71 cards have one distinct source task,7 have two; no whole-bank accuracy rate.

F4/F5 Medium: complete long Trigger index burdens context; related mechanism
families lack clear routing boundaries. Similar triggers are not proof of
equivalent actions. No measured token/cost harm or justified blanket merge.

F6 Medium: prose-only restrictions obscure precise syntax changes; some
version limitations remain private sidecar-only. Risk, not observed causation.

F7 Medium: shared parser crosses inline labels in14 actual cards; synthetic
empty Action returns subsequent nonempty fields. Autonomous index compensates
and direct card reader does not use it: no current index body-leak claim.

## Decision / Next Step

Recommend user-directed offline corrections:072 layer wording, consistent
read-only installed-library policy, field parser and empty-field validation,
family distinctions then reviewed short routing descriptions, visible syntax
and version limitations. Future mechanism logging/live comparison requires
separate scope; not automatically authorized by review recommendations.

Audit made no code/card/result/log changes, no paid calls or evaluation starts,
and no sealed-test access. Raw datasets and historical runs stayed read-only.
Only new review artifacts and canonical compact research memory were written.
