# Candidate build status: short-index review candidate generated; no evaluation

## Short index update

User authorized shortening the main index. New compact-v1 candidate SKILL is
7957bytes versus31507first candidate and11545flat control.37one-line entries,
72rules and all39non-SKILL files unchanged; original pre-index prefix unchanged.
All149related tests and37reference reader checks pass. One Pro/max call estimated
USD0.02385372; cumulativeUSD1.74243608, no actor evaluation. See
[SHORT_INDEX_REVIEW.md](SHORT_INDEX_REVIEW.md) for current artifacts and provenance.
The earlier long-index checkpoints below remain historical records.

## Latest result

All37reducers completed. Candidate rendered after explicit source-verbatim fallback
for two groups of unsafe model merges:37references,72rules,78source cards covered exactly once.
Original model proposals remain unchanged. See [CANDIDATE_REVIEW.md](CANDIDATE_REVIEW.md)
for the artifact map, checks, cost reconciliation and unresolved issues.
Main SKILL31507bytes versus control11545:2.729x, not a token or performance claim.
Cumulative estimated costUSD1.71858236, no unresolved calls/reservations, no actor
evaluation. All139related offline tests and37full-reference reader checks pass.
Next: user review of the candidate and directory length; no further paid calls
or evaluation started. The chronological build checkpoints below remain as history.

## Authorization and budget

User authorized implementation and candidate skill construction using only
DeepSeek V4 Pro/max; review before evaluation. Future evaluation is one repeat
per arm on validation20 (40 episodes total), not the initially proposed80.
Credential source confirmed by user; only variable names/path are exposed,
never values. No evaluation or sealed-test access is authorized in this stage.

Historical complete40 actor costs: repair USD4.535773, guidance USD5.716284,
Executive USD5.225239. These are historical estimates, not guarantees for this
candidate. Construction has its own USD5 ceiling; future actor ceiling USD10
is an estimate to confirm later, not permission to launch.

Official pricing checked at https://api-docs.deepseek.com/quick_start/pricing/:
Pro peak input cache-hit/miss/output per million = USD0.044/1.32/3.96;
off-peak half. Current bridge estimates only use UTC-hour windows, not the
official weekend/holiday exceptions; they may overestimate these calls. Peak
reservation remains conservative. Do not relabel the ledger as a provider invoice.

## Frozen run

Run-root relative path: `skillopt-verusage/card-organization-20261012-v1/`.
Prepared2026-10-12T03:44:14Z. `build_contract.json` hashes source bank, revision
recipe, original Executive, both v2 prompts, template, driver, validator/renderer,
and provider/budget/context code. Router complete78 packet contains no dev/test
tasks or results. It passes conservative context admission:206586 tokens bounded
by UTF8 request bytes plus65536 output cap. Peak request reservation USD0.456522.
Reducer cap32768; single sequential construction worker; no paid automatic retry.
Uncertain provider costs block further dispatch. Successful responses are saved;
the incomplete-response evidence gap in the shared client is documented below.

## Implementation and initial checks

- `scripts/build_card_organization.py`: prepare/router/reduce/render phases;
  paid phases require explicit env path and frozen-input hashes; reduction
  requires a router-hash-bound review receipt. No actor-evaluation entrypoint.
- `skillopt-verusage/src/skillopt_verusage/card_organization.py`: source-field
  anchors, card/case/family coverage, reciprocal source maps, rule/condition
  mapping, deterministic rendering, hash-checking whole-reference reader.
- `skillopt-verusage/tests/test_card_organization.py`:21offline tests cover
  source/case/claim validation, deterministic rendering, safe/hash-bound reading,
  offline preparation, frozen inputs and credential-model override prevention.
  Together with existing card-bank/context/guarded-storage regressions101pass.
- A control reconstructed from repaired78 and originalExecutive; SKILL bytes
  match published SHA10acd2d687754e70a470fc1d041a7e1308c82c4f34ac108de85d874ab50d07c1.
- Router request completed with provider terminal status `incomplete`; no usable
  complete proposal, no reduction calls, no candidate skill, no actor evaluation.

## First paid attempt: bounded failure, not a successful construction

Start2026-10-12T03:44:27Z, finish03:56:07Z (approximately699.5seconds).
Ledger confirms model `deepseek-v4-pro`; saved request uses reasoning effort `max`.
Prompt28889tokens (all cache miss), completion65536tokens, including33880reasoning.
Output reached exactly the configured65536cap. The provider returned incomplete;
the client correctly refused to admit it as a completed result.

Existing ledger estimateUSD0.29765604 (peak tariff); settled1request, uncertain0,
outstanding reservations0. Calendar-correct off-peak arithmetic isUSD0.14882802
for this Sunday UTC request, but no provider invoice was inspected: retain the
original conservative ledger amount and count it toward the USD5 ceiling.

Preserved: frozen request, context admission, started/error receipts, usage and
provider-model/terminal-status ledger. The shared client checks terminal status
before returning/writing `response.raw`, so the incomplete response body was
not retained. Do not claim the discarded partial JSON or reasoning text was
recovered. In any authorized retry, incomplete-body evidence capture should be
reviewed as an instrumentation repair, separately hash-recorded, not a prompt change.

Initially asked user whether to allow ONE new Router call with cap131072, same full78
input/prompt/Pro-max. Peak reserve approximatelyUSD0.72 for that request; retain
USD0.29765604prior expense under the SAME cumulativeUSD5construction ceiling.
User subsequently explicitly approved that one retry. See active attempt below;
no automatic third Router call is authorized. Alternative phased construction
would require separate design review, not silent input or reasoning reduction.

## Authorized attempt v2

Run-root relative path: `skillopt-verusage/card-organization-20261012-v2/`.
Prepared2026-10-12T03:58:48Z; Router retry launched immediately after preflight.
Full input packet SHA and Router prompt SHA equal attemptv1; model and reasoning
unchanged. Output cap131072, conservative context bound272123, peak reservation
USD0.71604588. Construction budget explicitly starts with priorUSD0.29765604,
not a freshUSD5 allowance. Parent budget/ledger/input files are hash-bound;
uncertain parent costs, pending requests or ledger disagreement reject preparation.

Instrumentation-only changes: guarded client now opts into public capture for
this builder; native bridge saves/redacts a returned body before terminal-status
validation. Incomplete responses still raise and are never admitted. Regression
verifies preservation of an incomplete body without leaking credentials; capture
receipt complete describes saved body, not successful provider completion.
New frozen contract records modified code. All132related tests pass, including
prior expense inheritance, parent-evidence immutability, bridge and capture checks.

The sole authorized retry returned terminal `completed`. Input28889tokens
(28800cache hit,89miss), output74333including35298reasoning. Original estimate
USD0.29574336; both Router calls cumulativeUSD0.59339940. No third Router call.
The public provider envelope (including returned reasoning/message blocks and
usage), raw response, parsed original proposal and request are saved in v2.
Original parsed proposal SHA92d28e68f376516df5a697cf9732f75bf5b175360429149ad5ce70a90b90baa7.

The provider completed, but its JSON violated two serialization constraints:
`card_features`/`assignments` were ID-keyed objects instead of arrays, and
anchor field names used lower case. An offline lossless normalizer checks
key/ID agreement, changes those containers and field capitalization only,
and revalidates exact source excerpts. It does not fix unsupported assertions.
All78cards,86cases and37families pass; no anchor mismatch. The original proposal
is unchanged. Normalized SHA5364c087b73beab1f639d8a8623978c434914793fc069ef539b0df04a612304e.

## Reduction continuation

Run-root relative path: `skillopt-verusage/card-organization-20261012-reduce-v1/`.
`scripts/adopt_card_router.py` prepares this separate reduction-stage run with
the same frozen inputs/prompts, priorUSD0.59339940 under the cumulativeUSD5cap,
and hash-bound original proposal/normalization receipt/code. No new Router call
was made. It does not overwrite either Router attempt or rewrite their contracts.
`router_review.json` permits draft reduction only and records unresolved issues.
`router_normalization.json` enumerates every deterministic format conversion.
All137related offline tests pass, including adoption without API calls, cumulative
cost inheritance, immutable parent evidence and rejection of unsupported anchors.

There are16singleton families; the other21have2–6primary cards. The37family
taxonomy is a model proposal, not proof of improved discoverability. In particular
the Router omitted a known card018Action/Validate wording tension, which the
independent review receipt retains. Its loop-family relation must not become an
unsupported mandatory three-step workflow. Do not silently correct source advice.
See [ROUTER_RESULT_REVIEW.md](ROUTER_RESULT_REVIEW.md).

The reducer completed all37calls sequentially, Pro/max, cap32768 per call,
no automatic paid retry, original reducer prompt unchanged. Reducer costUSD1.12518296.
Post-reduction audit found unsafe merges in the direct-lemma and trigger groups.
`scripts/finalize_card_candidate.py` preserves original proposals, binds review
decisions to their hashes, restores the affected source bodies verbatim in separate
reviewed proposals, preserves all case routes, and renders the review-only candidate.
No actor evaluation has started.

Structural correctness is not semantic validation. Any actual ambiguous grouping,
source contradiction, or oversized reference is surfaced for review rather than
silently rewriting knowledge or changing retrieval design. Model-produced JSON
and draft bundles are not approved for evaluation merely because rendering passes.

All generated outputs stay under `VERUS_SKILL_RUN_ROOT`. Original checkout,
source cards, historical results and raw/sealed data remain unchanged.
