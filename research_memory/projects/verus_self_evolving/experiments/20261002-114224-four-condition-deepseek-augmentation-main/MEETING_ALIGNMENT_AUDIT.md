# Meeting-to-implementation alignment audit

## Status and authority

Reviewed on 2026-10-02 after the user rejected the campaign's method alignment.
The supplied transcript was read in full, lines 1--269. Its SHA-256 is
`85108c7dd8dcef27b837480fc29d4370090d0b297aabeb069616250cf35c986b`, identical
to the source already reviewed in
`../../meetings/20261001-144332-forty-task-augmentation-experiment-priorities-and-learning-budget-meeting/ENTRY.md`.
This is not a missing-source problem: the implementation did not enforce
requirements that were already recorded. No original audio was listened to.
No raw transcript is reproduced or added to version control.

Evidence priority: explicit later user decisions for model/time/spend settings;
the actual meeting transcript for the method; reviewed historical evidence for
reusable components; agent-authored proposals only as proposals. Approval to
launch a proposed run does not establish that its implementation faithfully
realizes the meeting. Do not silently promote examples to frozen parameters.

The external campaign `augmentation-main-20261002-Ws4keW` is stopped, not paused
with actors still running. Runtime stop was a card byte-cap exception at
2026-10-02T19:06:30 UTC. Subsequent read-only process checks found no campaign,
bridge or inference actor. Method alignment is now an additional hold reason.
Do not restart, repair paid outputs automatically, or call this the accepted
meeting-aligned main experiment. Preserve it as diagnostic/reference-only data.

## Requirement inventory and implementation discrepancies

| Meeting source | Requirement or design direction | Actual campaign | Assessment |
|---|---|---|---|
| 19:04--21:14, lines 55--59 | Use the final verified proof as hindsight reference; delete redundant proof lines only after fresh verifier acceptance; compare the target function's proof at each verifier snapshot against that pruned reference. | `campaign_evidence.select_checkpoint` does no pruning or target-proof comparison. It reads verifier/error count tuples. | Fundamental metric substitution, not an equivalent implementation of progress. |
| 21:41--22:52, lines 61--65 | Select interesting points from proof progress, including stagnation starts and drops, with compilation/verification feedback as additional evidence. | Picks the start of the largest output-token interval with equal verifier counts, otherwise the lower-middle eligible verifier point. Of 39 selections, 17 are count plateaus and 22 are middle fallbacks. No proof-progress regression selection. | Counts can stay equal while obligations change. The meeting's example of an additional middle point does not authorize using a generic median fallback instead of progress analysis. |
| 17:50 and 22:52, lines 53, 65 | Multiple checkpoints/branches per original; example original + 3 branches = 4 traces. | At most one hint branch per eligible source. | A simplification that removes the discussed alternative-path comparison; exact K was illustrative, but changing this construction needed explicit alignment. |
| 22:52--25:10 and 34:30, lines 65--77, 129 | New trace is original prefix + hinted suffix; organize related attempts, with the example two source problems x four traces = eight-trace minibatch. Analyze hint, fork position, changed actions and actual convergence; keep harmful branches too. | H extraction receives one full original and one separately recorded continuation. Each source is extracted independently; `source_weight=1` is metadata, not an eight-trace grouped reflection algorithm. No explicit aligned prefix/original-suffix/new-suffix comparison contract. | Full evidence availability and source IDs do not establish the intended grouping or comparative analysis. Failure retention and branch-reference disambiguation are compatible safeguards. |
| 43:02--44:23 and 48:45, lines 175--181, 199 | Reasonably matched learning budget; stop admitting analysis at the budget frontier, then finalize completed proposals. | Equal USD25 ceilings, USD5 extraction and USD4/1 reflection/finalization split; budget denial propagates to a stop, and all40 coverage is required before freezing. | Ceilings are not matched realized expenditure. The completed-prefix finalization behavior is missing. Exact dollar amounts and cost boundary were agent proposals, not meeting decisions. |
| 49:26, line 201 | Plain skill needs merge; retain different card directions rather than forcing them into a small merged skill. | No semantic merge or top-four bank truncation, but each source can emit at most two cards, each <=700 bytes. The latter constraint stopped the run. | Exact dedup with provenance is potentially compatible; these hard per-source/card-length limits were not specified by the meeting and materially constrain extraction. |
| 16:14, line 51 | Why/what-style cards plus a small summary/index visible to the agent; agent chooses what to retrieve for its current difficulty. | Agent may search/read voluntarily, but initial skill has generic search instructions, not a visible bank index. Search supplies at most three lexically ranked titles/triggers. | Agent autonomy aligns; the visible-index design was not implemented. Lexical top-three is an implementation choice, not a meeting requirement. |
| 46:15, 48:45, 49:55--51:00 and 54:01 | First establish the basic40-source augmented method versus SkillOpt; broad ablations later; compare learned knowledge and improved/worsened live traces qualitatively. | Four proposed deployment conditions, two repetitions, no completed bank or evaluation. Generic extraction does not require the targeted fork/hint/path comparison. | Additional controls are not inherently wrong, but cannot substitute for the core construction. No effectiveness or mechanism claim is established. |

The native adapter uses upstream success/failure reflection with minibatches of
at most8 traces, four proposals, and merge/rank/apply. It produced a40-source
candidate with four selected edits. That is not a completed acceptance-gated
SkillOpt result: its common held-out gate is pending. Do not infer three epochs
or an exact final edit count from the meeting's oral examples.

## Correct methodological interpretation

The causal hypothesis is not simply that an extractor sees more text. Related
attempts provide evidence about which actions work at which proof states and
which alternatives fail or waste search. The extraction contract must explicitly
examine fork location, hint content, aligned subsequent changes, verifier results,
and observed convergence cost. Observed contrasts do not alone prove causal
benefit, and hinted branches may be slower, unsuccessful, or misleading.

The intended chain is: verified final proof -> verifier-gated pruning -> exact
target-proof progress at verifier calls with cumulative output-token coordinates
-> interesting checkpoints -> multiple non-solution hints and isolated suffixes
-> reconstructible prefix-plus-suffix alternatives -> related-trace analysis
-> budget-frontier closure -> plain merge or retained card directions/index
-> common from-scratch live evaluation and qualitative trace/skill audit.

Existing relevant components were found, not executed in this audit:

- `scripts/analyze_proof_progress.py` and
  `src/verus_self_evolve/proof_progress.py` already implement verifier-gated
  greedy proof pruning, target-proof line coverage, token alignment, plateau
  reporting and regression-transition reporting.
- `skillopt-verusage/scripts/export_skillopt_fork_packets.py` already exports
  exact original prefixes/suffixes and checks their concatenation reconstructs
  the original. Its historical identity/arm limits need review before reuse.
- Historical whole-file patch-F1 audit is a different metric; it must not be
  silently substituted for the target-proof/pruned-reference design described
  here. The prior pruning pilot used fixed test20 post hoc; do not use that
  task's measurements to tune the new train-only selector.

Line coverage is a text-based hindsight proxy, not semantic proof progress.
Coverage drops can reflect useful deletion or a different valid proof; verifier
feedback is necessary. Greedy line/block pruning is not global minimality.
Verified references are teacher/offline-only, never exposed to continuation or
held-out actors. Keep verifier-preservation and isolation safeguards.

## Explicit decisions, examples and open implementation details

Later user decisions remain valid: all roles DeepSeek V4 Pro; complete-path
original/hint actors max/1800s; downstream evaluation600s; campaign cash ceiling
USD80. Fixed train40/val20/test20 and sealed test boundary remain unchanged.
All-role reasoning effort was not explicitly settled by naming the model;
current teacher/extractor/native use high, actors max.

Examples, not newly frozen decisions: K=3 branches, two four-trace source groups
per eight-trace batch, USD10 learning budget, and baseline final K=3 edits.
Nevertheless the multi-branch, related-attempt, progress-based construction is
clear and must not be replaced unilaterally with independent one-branch cards.

Details still requiring a repair contract before new spend: exact checkpoint
ranking/thresholds and fallback for no eligible point; exact K and handling of
the unsolved original/no verified reference; monetary learning boundary and
sampling/teacher/failed-attempt/closure accounting; card length/count/index
exposure limits. Use existing reviewed implementations where suitable; do not
ask the user to re-decide the already explicit method, model or evaluation clock.

## Artifact trust and current result

- Source run `train40-pro-initial-1800s-20261001-KjQXKA`: reusable original40
  evidence,39 independently dual-verified originals plus one safe timeout.
  Its result measures that run only, not augmentation efficacy.
- New campaign:36 completed hint continuations,3 rejected hints, O proposals
  from4 sources and H proposals from3; downstream evaluation0. These are
  diagnostic outputs. Checkpoint identities must be checked against a corrected
  progress selector before considering any branch reuse; do not assume all36
  qualify as the meeting's selected branches.
- New campaign global ledger:812 settled requests, estimated USD5.076593324,
  zero uncertain requests and zero open reservations at inspection. This is
  provider-usage accounting, not an account invoice. Prior original-run costs
  and its unresolved historical reservation are separate and unchanged.
- Native candidate and accepted card proposals: preserve for reference, not
  accepted final learned artifacts. Neither card bank nor deployment was frozen.
- Guarded transport, complete snapshots/events, source hashing, safe actor
  isolation, preservation checks and ledgers are reusable infrastructure subject
  to review. Their tests do not validate meeting alignment.

## Next action and safety

Deliver this discrepancy audit first. Do not resume the old coordinator merely
to relax its byte limit. Align the repair contract with the meeting, resolve
only genuinely open settings, and verify the entire corrected train-only chain
before requesting/using new paid execution authority.

This turn performed read-only source/code/process/ledger inspection and compact
research-memory updates only. No paid inference, pruning verifier run, code fix,
restart, deletion, raw/sealed-data modification, transcript copy, commit or push.
Specialized intake artifact/memory interfaces are unavailable in this session;
local evidence plus canonical repository research memory are the explicit
fallback. This audit supersedes conflicting execution instructions in the
campaign ENTRY/PLAN/RUN and earlier CURRENT snapshots; preserve those as launch
history rather than treating them as an approved meeting interpretation.
