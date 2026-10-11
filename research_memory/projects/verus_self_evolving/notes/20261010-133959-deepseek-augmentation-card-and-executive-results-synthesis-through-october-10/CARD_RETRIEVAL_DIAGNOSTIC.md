# Direct exposure versus autonomous card retrieval: evidence and gap

## Scope

Read-only answer to user questions about relevant-card replay, autonomous search,
missed useful advice, and overlapping organization. No paid evaluation or changes
to cards, prompts, deployment, or the independent autoresearch controller.
Analysis-campaign/science/research-memory evidence discipline; local shell/hash
fallback because dedicated evidence-graph tools are unavailable.

## What has actually been tested?

There IS an early direct-card continuation study; do not claim none ever existed.
`experiments/20260926-231847-frozen-ir-card-checkpoint-mechanism-and-source-excluded-transfer-diagnostic/ENTRY.md`
records18 continuations: no card, original IR preservation card, augmented IR
preservation card appended to the prompt. IR CP06 has3 repetitions per arm;
AL CP07 and two synthetic boundaries have1 each. All18 dual-pass within budget.
Pro/high600s, selected source/checkpoint tasks; not current Pro/max78-card routing.
Both cards preserve a working proof with minimal import/macro repair; one
no-card IR run takes a large detour. No stable augmented-over-original advantage.
No retrieval arm in that study, no blind held-out or complete-history claim.

For the current repaired78 bank, no saved matched same-checkpoint comparison of
direct researcher-selected applicable card versus autonomous routing was found
in the audited experiment notes/drivers. Current live comparisons test packages,
guidance and Executive changes, not oracle retrieval. A failed model plus a
plausibly relevant card is not a demonstrated missed rescue. There is no reviewed
checkpoint-to-applicable-card gold set, hence no measured retrieval recall.

## Current and historical mechanisms are different

Current completed main/repair/guidance/Executive runs use autonomous bundles:
TASK asks actor to read SKILL.md; SKILL contains Executive, all card routing
descriptions and optional read instructions. Actor chooses any ID and runs
`python3 card_read.py card-001`; reader returns exact body. No query interface,
embedding search, ranker, fixed top-k, automatic stall detector or forced reads
is deployed in these autonomous bundles. Agent can inspect the visible index;
it is instructed not to bulk-read cards.json. Reading is ordinary tool/context
budget. Low body-read counts do not establish no index use or failed retrieval.

Repository ALSO retains optional historical card_search.py, copied only into
non-autonomous bundles. It searches body lexical overlap with frequency/rarity
weights and doubles title/Trigger-term weights, returns top3 titles/triggers,
then reads by ID. Not a semantic search engine and not the current78 deployment.
Historical three-task pilot had a temporal-induction query return a container
identity card; one actor bulk-read the bank outside the intended interface.
Source:experiments/20260926-214543-evidence-aware-card-bank-merge-and-autonomous-retrieval-pilot/ENTRY.md.

## Is the bank repetitive?

Read current deployed repaired78 (SHA256
ae38b9ace8560cb7e819eb348d152b916b0486e206b3d09c1b862e8681517f27).
Whitespace-normalized complete-body exact duplicates:0. This says nothing
about semantic redundancy. Inspected overlapping families:

| Family | IDs | Important distinction to preserve |
|---|---|---|
| Quantified antecedent / trigger |006,018,023,057,069,074|Antecedent absent, trigger inference and binder scope are different; branch/operator are alternative repairs.|
| Always-conjunction stability |045,047,062,071|Explicit lemma chain versus existing macro; inner predicate, lifting and conjunction association matter.|
| Proof macro import preservation |055,065,068|General qualified path versus sequence-equality obligations and type inference.|

Short index already distinguishes some of these; do not describe it as unchanged
long Trigger text. Related advice scattered across IDs can raise selection cost,
but these are hand-inspected examples, not a quantified whole-bank redundancy
rate or proof that duplication caused a particular timeout. Blind merging loses
premise/type distinctions. Candidate organization: family-level navigation with
specific diagnostic/precondition branches, retaining original bodies and IDs.

## Saved trace observations, not causal estimates

Frozen guidance failure-analysis/REPORT.md and paired_analysis.json show:

- a23:control reads006/029/070 and rejects inapplicable helpers, finishes298.5s;
  guided arm creates unproved generic helpers, first patch~309s, proposes late
  reading but returns no bodies before timeout. Timeliness/strategy detour,
  not evidence that forcing006 would solve it.
- 3f17:reads002/005/050~424s, times out.005 is function-field equality while
  task is transition preservation of a pod set: topic-level overmatching;
  no demonstrated005-caused wrong edit. Coverage may itself be inadequate.
- 599:reads071/062/045~133s, correctly rejects missing-premise stability advice,
  solves using supplied always_unfold. Reading without adoption is appropriate.
- 62ff:explicitly matches001 to installed lemma_filter_contains_rev and uses it,
  succeeds. Still slower than control and unnecessarily re-proves a trusted helper;
  correct card use does not guarantee global efficiency.
- 0e8d:reads007/008/018~160s, accepts generic fairness scaffold, but makes no
  proof patch before timeout. Retrieval happened; executable task-specific
  bridge/application remains absent.

Separate four guided regressions all read zero bodies. No proof they were caused
by body content or reader I/O; index influence and stochastic search remain open.

## Small discriminating experiment proposed, NOT launched

Same frozen bank, Executive/TASK/model/budget, same source checkpoint/prefix:

1. No-card control (explicitly no card index or bodies).
2. Direct applicable-card exposure, chosen before observing new continuations;
   no answer/hint additions. Retrospective selection is an oracle diagnostic,
   not deployable generalization or a guaranteed upper bound per stochastic run.
3. Existing flat-index autonomous reader.
4. Agent-initiated query/search over unchanged cards, with excerpted hits and
   optional arbitrary-ID reads/query refinement. No forced retrieval/top-k use.

First4-6 diagnostic cases spanning available advice, near-neighbor mismatch,
missing prerequisites and apparent coverage gaps; repeat before broad claims.
Pre-assess applicability from visible state/contracts, allow no applicable card.
Do not tune bodies while comparing search mechanisms; evaluate organization
changes separately to avoid conflating them with search tools. Search time and
context count in600s. Track success/timeout, settled tokens, first appropriate
retrieval, actual action and next verifier diagnostic, and first dual-pass.
Direct exposure helps but autonomous does not: routing/timing candidate;
both fail:coverage/applicability/execution candidate; both succeed similarly:
possible redundancy, not proof advice useless. Current validation is already
development data, so this is diagnostic only, not blind held-out confirmation.

## Evidence and next step

- card_bank.py SHA256:70379579efe50cc0cea4a00cc2a37888f0ad74fb49272b07864e3907dcaa7443.
- card_search.py SHA256:c980f51d80f027d8b19ee1d3870b57357457f3bd9c76af23432c9113051880ce.
- External guidance failure-analysis/REPORT.md SHA256:
  0bf45bb28b111385234197a72154c3b2f508b8a83e22ce6bb9c153b9390a3278.
- Existing independent78-card review:
  notes/20261007-191317-independent-full-trace-inference-and-card-design-review/ENTRY.md.
- Current synthesis/tables:ENTRY.md and TOKEN_TIMEOUT_STATISTICS.md alongside this file.
- Next:user-directed matched direct-exposure/routing diagnostic, not another
  blanket increase in retrieval-prompt strength. No implementation/new paid calls
  authorized or performed in this question-answer audit. Raw/sealed/legacy data,
  frozen results and unrelated active research state preserved.
