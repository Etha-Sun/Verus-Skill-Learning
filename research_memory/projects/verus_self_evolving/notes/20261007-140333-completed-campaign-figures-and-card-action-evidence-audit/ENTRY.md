# Completed campaign figures and card action evidence audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-10-07T14:03:33`
- status: `complete_offline_figures_and_bounded_card_trace_review`

## Objective

User-requested quick follow-up: visualize the completed validation results and
audit whether deployed cards express correct observable-state/action rules,
with actual training and downstream trace evidence rather than retrieval counts.

## Context

Parent: [completed campaign results](../../experiments/20261006-024326-authorized-hindsight-hint-forks-grouped-native-cards-and-downstream-campaign/RESULTS.md).
Existing run: `VERUS_SKILL_RUN_ROOT/skillopt-verusage/evaluation-resume-20261007-ri57is`.
Four frozen conditions,20 validation tasks/two repetitions/600s unchanged;
original63 and augmented78 cards. No new model experiments or sealed-test access.

## Method / Actions

Three user-authorized subagents: result figures, full-bank content/provenance
audit, and live retrieval/application evidence. CPU-only local parsing and
Matplotlib renders; no GPU or paid provider requests. Generated outputs use
the fresh `analysis/quick-followup-20261007/` subdirectory of the existing run.
Root checks outputs and writes compact memory; agents do not edit banks,
production, old results or raw datasets. Completion requires inspected figures,
bounded positive/negative trace cases and explicit causal limitations.
Card audit distinguishes all-card structural checks from sampled semantic
judgment; prose-only formatting is the intended contract, not an error itself.
Live cases include all three discordant paired episodes and predetermined
lexicographic success/read, failure/read and success/no-read supplements.

## Evidence

Parent `analysis/hindsight-summary/summary.json` and
`audits/discordant_pair_case_review.json`. Fresh external artifacts below
`analysis/quick-followup-20261007/`:

- `figures/primary_success.{png,svg}`, `paired_success_interval.{png,svg}`,
  `joint_success_resources.{png,svg}`, generating `plot_results.py`,
  `figure_receipt.json` and `README.md`. Root inspected all three PNGs;
  labels, zero baselines and task-cluster interval are readable and faithful.
- `card_quality_review.json` and replayable `card_quality_review.py`:
  all141 card structural/exact-proposal checks;22 purpose-selected content
  readings, plus bounded training/live checks;76 source hashes verified by root.
  `CARD_QUALITY.md` provides compact Chinese rules, boundaries, positive/negative
  examples and links to the actual training/live trace files.
- `trace_evidence_review.json` and `audit_trace_evidence.py`: all80 card-condition
  episodes' exposure/timing census; bounded manually checked adoption/decline
  cases, not a whole-corpus semantic effectiveness score.
  `trace_evidence_review.md` links actual raw line numbers; root reverified564
  source bindings. Final receipt SHA610dd8e1c8f8055f689534d9c832e1be83f858cfb63f0582a71e8485053bd2e2.
- `index_redundancy_review.json`: independent root count of all141 repeated
  title/Trigger lines in the actual frozen deployment artifacts.

## Result

Primary comparison remains +2.5pp with95% task-cluster bootstrap interval
[-5,+10]pp;30 joint-success pairs use more resources with augmentation.
The three result figures visualize these limits without inventing significance.

Content audit finds real conditional repair rules, not a proven learned
decision policy. All141 cards have Trigger/Action/Why/Validate/Avoid fields.
Augmented71/78 contain fork references,7 cite only originals; references do
not themselves establish novel information or branch contrast.71 augmented
cards are supported by just one source task (correlated suffixes are not new
tasks). Manual families overlap: antecedent handling and import safety, among
others; zero exact-content duplicates does not eliminate semantic repetition.
Original rules already contain many of the observed tactics.

Concrete evidence:

- `599792dd13f472f45fa4/r1`: raw item7 reads006/058/069;8 explicitly adopts069
  antecedent branching;10 Verus pass;11 reads052;12 accepts automatic trigger
  warning cleanup;15 Lynette pass;18 confirms both. Root independently checks
  raw messages. Correct phase-specific adoption, not causal success evidence.
- `aa78e84a931f703c7e9c/r1,r2`: reads021/046/053 and discovers installed
  round-trip contracts/triggers for closed serialization. Root checks r1
  items57/59/67/68/72/73/77: actual proof passes, safety catches executable
  temporary modification, restoring executable shape yields both passes.
  Supports a relevant rule family, not attribution to021 alone.
- `a23/r1`: partial057 use with appropriate029/047 declines.057 cites only
  original evidence and substantially overlaps original047, so this is not
  an augmentation-exclusive new trick.
- `013`: training checkpoint chosen-witness equality failure clears after
  using universal safe-result facts; no explicit downstream body reads.
- `08d/r1`: closed map-view failure leads to consulting021 without its
  serialization premise; no final verified proof. Surface diagnostic matching
  is not successful semantic transfer.
- `31ee/r1`: consulted001/078 stronger library machinery explicitly declined;
  a narrow new-key assertion suffices. Same task/r2 passes without body reads.
- `9ee/r2`:052 read only after both checks already pass, so its body cannot
  explain earlier proof construction; initial index exposure remains possible.

Deployment problem independently reproduced: all63 original and78 augmented
index rows display the exact same Trigger twice as title and Trigger.
Redundant UTF-8 bytes12126/26462 and16506/35342 respectively; bytes are not
provider-token or causal-cost estimates. Some empty-body triggers are too broad;
native SkillOpt's short pattern list omits several applicability distinctions
that cards021/052 handle better. These are omission risks, not proof of live harm.

Scope: structural/provenance census is exhaustive; semantic quality inspection
is purpose-selected, not a random quality-rate estimate. No causal benefit,
necessity, representative transfer rate or optimal checkpoint claim follows.

## Decision / Next Step

Follow-up retrieval mechanism question: root rechecked actual frozen augmented
SKILL.md/card_read.py and current `card_bank.py` (autonomous instructions,
`_index_entry`, `build_bundle`) plus actor prompt builder. Current deployment
supplies the entire title/Trigger index and optional arbitrary-ID body reads;
explicit instructions require applicability/avoidance prechecks, verification
after action and a short adoption/decline explanation. No automatic stagnation
detector, mandatory read point, ranker, fixed top-k, or search helper is deployed
in this autonomous variant. The separate default lexical-search variant exists
in code but was not used by this campaign. Missing-heading fallback to Trigger
followed by unconditional title-plus-Trigger rendering explains the duplicate
index. A future soft prompt reminder at repeated failure/strategy switching is
a proposal only, not an implemented or validated retrieval policy.

Report and stop this bounded read-only follow-up. Recommended later priorities:
remove duplicate index rendering; consolidate overlapping rules while preserving
boundaries; distinguish semantic premises from surface errors; retain an offline
card-to-source/adoption/decline evidence sidecar. Preserve plain-prose and agent
autonomous retrieval. No implementation, bank edits or new evaluation here.
Any changed prompts, card banks, retrieval policy or additional paid validation
requires a separate user request. Raw datasets/frozen banks/old outcomes unchanged;
sealedtest20 unread. Science graph APIs unavailable; local hash-bound fallback.
