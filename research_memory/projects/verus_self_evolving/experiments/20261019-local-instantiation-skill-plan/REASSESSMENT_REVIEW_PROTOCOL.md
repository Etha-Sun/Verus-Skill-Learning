# R0/R1 offline review protocol

Researcher-only. Never install this file, the plan, calibration records, or historical
solutions in an actor workspace. Apply the same evidence rules to both arms.

## Frozen comparison

R0_current copies the v3 new_skeleton bundle byte for byte. R1_reassess inserts
REASSESSMENT_RULE.md immediately before the same Card index. Body text, index text
and order, reader, Executive, initial TASK, model, toolchain and actor harness stay
fixed. Structured means new_skeleton, not new_pseudocode. No feedback reminder.

Stage1 is Rely, Unpack, De Morgan and Filter, each three fresh samples per arm:
24 cells. Arms alternate first position across adjacent task/repeat pairs. The
unchanged two-worker executor pulls this queue as workers finish; start times need
not coincide. Repeat numbers are blocking labels, not reproducible paired seeds.
All runs start from hashed unverified inputs. No failure checkpoint continuation.

Historical results are background only, not R0 observations. This comparison tests
the added reassessment/use rule against current instructions; it cannot establish
superiority over the historical DIAGNOSTIC_RETRIEVAL_GUIDANCE. That historical
prompt raised reading from 1/20 to 5/20 while passes fell from 16/20 to 13/20;
the four lost tasks had no body exposure. Neither benefit nor body harm follows
from reading counts alone. These are known development tasks, not unseen tests.

## Opportunity review

Review all episodes, including those with zero card reads. Determine opportunities
from visible proof state before inspecting whether a later read occurred. A new
line number or fewer errors alone is insufficient evidence of a changed/discharged
obligation. Record uncertainty rather than guessing a semantic diagnosis.

Create one researcher-only JSONL row per candidate opportunity, with these fields:

| Field | Required evidence |
|---|---|
| episode_key, arm, task_id, repeat | Frozen schedule cell |
| diagnostic_event_id, timestamp, elapsed_seconds | Original diagnostic event; include stdout/stderr pointer |
| candidate_sha256, edited_before_event | Recorded candidate identity and preceding edit event |
| current_obligation, local_premises, proof_scope | Assertion/call contract and source span; do not rely solely on actor claims |
| trigger | rejected_card_open_obligation / changed_obligation / persistent_after_justified_repair / not_an_opportunity / uncertain |
| trigger_evidence, prior_action_event_id | Why the trigger applies; retain explicit small-repair exceptions |
| read_cards_before_event | IDs with exact returned body evidence and provider request linkage |
| reassessed, decision_event_id, decision_quote | yes / no / uncertain; use-existing / consult-candidate / no-match / direct-small-repair |
| applicability_evidence, rejected_ids | Binding to actual conditions and lemma contracts, not topical similarity |
| new_body_return_events, provider_request_ids | Exact tool body and subsequent provider content match; direct/bulk separately |
| edit_event_id, before_sha256, after_sha256, diff_pointer | Concrete local code action; already-read guidance can be used |
| intended_local_fact, next_validation_event_id | What this action should establish and the subsequent check |
| local_progress, progress_evidence | discharged / unresolved / moved-or-hidden / uncertain; inspect the same assertion and scope |
| same_hash_dual_600, first_dual_seconds, normal_exit | Separate whole-task endpoint from local progress and exit status |
| reviewer, evidence_limits | Review provenance, missing/truncated evidence, unverified interpretation |

Opportunity counts are arm-specific because runs reach different proof states.
Do not pretend opportunities are paired across arms. Do not count no rereading as
non-use: existing guidance and known small fixes are valid exits. After dual pass,
warning cleanup is not failure-driven retrieval. Direct cards.json exposure is
not ten independent selection decisions. Infrastructure interruptions are not
proof failures; preserve attempts and costs, with no automatic paid retry.

## Outcomes and cost

Primary: observed Verus and Lynette completion within 600 seconds on the same
candidate hash. Record normal exit separately, including dual-pass-then-timeout.
Retain historical exit-based outcome for comparison, without replacing the new
primary. Unsupported/masked commands or changed-during-command hashes need manual
review; lack of confirmed evidence is not proof no valid state existed.

Report all planned cells as complete/ordinary failure/timeout/infrastructure/unstarted,
all terminal evidence, and coverage. Do not select only reading episodes for the
main result. Report first dual time, input/cache/output tokens, reasoning as a
subset of output, request and verification counts, known fees, pending reserves
and uncertain fees. Timeout cost is censored; fewer tokens do not imply efficiency.
API in-flight time includes reasoning/generation and cannot be subtracted as pure
network/server waiting. Confirm the intervention main and exact consulted bodies
appear in captured upstream requests. Saved raw requests allow this offline audit;
the tool-return parser does not itself prove upstream exposure or correct use.

## Decision and launch boundary

More reading with worse passes or cost is a reason to pause expansion and inspect
failed routes. Execution of the rule plus verified progress and acceptable overall
outcomes is a reason to consider the unchanged remaining-four-task extension, not
automatic authority to run it. Changed rules require a new version and new control.

Only offline preparation is authorized now. Before any paid launch, record an
explicit user instruction, exact contract hash, 24-cell scope, new USD20 ceiling,
data transfer destination, current pricing evidence and server-background permission.
Do not generate an approved authorization file from the preparation request.
The example format below is deliberately non-authorizing:

```json
{
  "approved": false,
  "contract_sha256": "REPLACE_AFTER_REVIEW",
  "episodes": 24,
  "new_batch_cap_usd": 20,
  "destination": "https://api.deepseek.com",
  "automatic_paid_retry": false,
  "background_launch": false,
  "pricing_verified": false,
  "pricing_evidence": "",
  "user_instruction": ""
}
```

The proposed fresh ledger applies only to this newly authorized batch. It neither
clears historical uncertainty nor treats the old USD30/USD80 limits as fresh
authorization. If the user instead chooses a shared cumulative budget, revise and
freeze that accounting contract before launch. The unchanged bridge's one-million
input-token reserve is floored by the new driver guard at the configured 1,048,576
context window; no actor prompt, wrapper or transport behavior is changed.

Run check and unit tests again immediately before launch; verify actual model
availability and pricing then. A changed interface, binary, catalog, price assumption
or library requires a recorded new condition, not silent substitution. Use a
server-managed process with Restart=no, two workers, retained logs and request
drain. Do not launch from an interactive session that depends on the laptop.
