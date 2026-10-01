# Matched augmentation ablations: representation, grouping, selection and scale

## Budget revision (2026-09-29; supersedes counts and staging below)

The user requests fewer expensive 160-trace conditions. The active table is
`docs/augmentation-experiment-plan.md`; the earlier matrix below is retained as
design history, not the current execution schedule. Core augmentation now uses
K=1 new trajectory per source: N=10 gives 20 total, N=40 gives 80 total.
Small ordinary-resampling, targeted-hint, random-point-hint and obfs conditions
require 40 new training trajectories altogether. Teacher/obfs generation,
extraction and from-scratch evaluation costs are additional.

Original grouping/format controls reuse existing data. Augmented grouping/format
controls reuse the same generated traces. Expand only promising routes from
10 to 40 source tasks, adding 30 new trajectories per route if the protocol is
unchanged. A single selected-method 160-total condition (120 new relative to
40 originals) is optional and deferred. No 160-trace condition is required in
the first stage. Small-task ablations support small-task conclusions; broader
claims need corresponding replications. No experiment launched by this revision;
raw/sealed data remain untouched.

## Status

Proposed experiment design only; no runs authorized or launched by this design
review. The user proposes comparing card-like versus single-file skills,
problem-grouped versus random analysis, stagnation/regression versus random
checkpoint selection, sample/compute efficiency, low/high data utility, and
positive/negative versus random SkillOpt reflection grouping. These are
hypotheses; neither large improvement nor equivalence is assumed.

An asynchronous clarification asks whether 160 augmented trajectories come
from 40 source problems or 10. Pending an answer, the worked design assumes
40 source problems x 4 NEW trajectories, with the original trajectory retained:
200 total trajectories. Low-data uses 10 x 4 new plus 10 original = 50 total.
If 160 denotes total rather than new trajectories, use three new per source
instead; if 10 sources generate 160 variants, keep that as a separate fixed-N
multiplicity experiment. Do not treat variant count as independent task count.

## Definitions

- N: number of distinct source training problems; suggested nested N=10,40.
- K: new rollouts per source problem; example K=4 for every matched augmentation
  and ordinary-resampling condition. Total extraction traces N(1+K).
- Representation: structured cards with Trigger/Action/Why/Validate/Avoid-when,
  versus free-form skill prose. Both can be serialized to one Markdown file.
  File count and retrieval access are separate factors.
- Grouping: ordinary seeded random groups, success/failure-separated groups
  (native SkillOpt), or source-problem groups containing all related branches.
- Sampling random train cases and randomly grouping evidence are distinct axes.
- All deployment evaluations start from scratch on the same separate tasks;
  never provide task checkpoints, reference proofs, future hints or certificates.

## Main efficacy matrix

Run each of the following at N=10 and N=40, with K=4 in augmented conditions.

| ID | Evidence | Total traces at N=10 / N=40 | Analysis grouping | Representation |
|---|---|---|---|---|
| O | Original only | 10 / 40 | Random | Cards |
| U | Original + ordinary fresh resampling of the same problems | 50 / 200 | Problem-grouped | Cards |
| H | Original + hint continuations at stagnation/regression states | 50 / 200 | Problem-grouped | Cards |
| B | Original + obfs-derived fresh-solving trajectories | 50 / 200 | Problem-grouped | Cards |

O versus H/B estimates the complete added-data recipe relative to original
card extraction; several components change. U versus H/B controls source and
trajectory count, grouping and representation to identify the augmentation
recipe's value relative to more ordinary experience. A separate same-checkpoint
no-hint control is required to isolate hint content from checkpoint restarting;
it is not interchangeable with fresh-from-start resampling.

## Focused ablations

Start on the same N=40 source set; reuse frozen evidence for grouping/format
ablations. These are additional extraction/evaluation conditions, not new
augmentation rollouts except random-point generation.

| ID | Evidence | Grouping | Representation | Matched contrast |
|---|---|---|---|---|
| H-point | Hint continuations at random eligible points | Problem-grouped | Cards | H: checkpoint policy |
| H-group | Exact H evidence | Random | Cards | H: grouping |
| H-format | Exact H evidence | Problem-grouped | Prose in one document | H: representation |
| S-PN | Original-only traces | Positive/negative | Prose in one document | Native SkillOpt baseline |
| S-R | Exact S-PN evidence | Random | Prose in one document | S-PN: P/N versus random |

S-R versus O at N=40 also measures representation on original evidence with
random grouping fixed. To claim representation or grouping effects on obfs too,
repeat the relevant ablation there; H alone establishes only conditional effects.
To claim grouping specifically helps augmentation, add a U-random arm and inspect
the grouping-by-data interaction. To claim synergy between checkpoint selection
and grouping, add random-point + random-group rather than inferring interaction
from only one-factor-at-a-time contrasts. Extend S-PN/S-R to N=10 if that claim
is intended to cover low-data settings too. Native Trace2Skill at matched N
and the initial skill are useful whole-pipeline references, not replacements
for these factor-controlled comparisons.

## Claim-to-evidence mapping

1. Cards beat free-form skills: H vs H-format (and O vs S-R on original data).
   Fix delivery mode, actor, extraction effort and instruction budget. A card
   library retrieved selectively versus a long always-visible document tests
   representation plus routing plus context budget, not structure alone.
2. Problem grouping helps augmented evidence: H vs H-group; inspect branch
   attribution, useful decision distinctions and boundaries alongside deployment
   success/cost. Better outcomes alone do not explain the mechanism.
3. Targeted selection helps: H vs H-point, with same source trajectories, hint
   generator, K and continuation cap. Use the same feasible checkpoint universe;
   stratify/report start progress and remaining work. Targeted selection may
   legitimately choose different states but should not silently get more budget.
4. Augmentation is more efficient: U vs H/B at equal N and trace count establishes
   count-matched utility only. Compute efficiency needs an explicit matched
   generation/learning spend or token budget including teachers, failed proposals,
   verification and extraction. Report online full-task cost separately.
5. Low/high-data benefit: compare H/B to their O and U at each N, rather than only
   comparing augmented-10 with original-40. Repeat several stratified 10-task
   subsets and extraction/actor randomness, use nested source sets and fixed test
   tasks. Conclusions cover this 10-to-40 regime, not arbitrary large data.
6. P/N and random are similar: S-PN vs S-R with identical original traces. Predefine
   a practically meaningful equivalence tolerance and report paired uncertainty.
   Nonsignificance alone is not evidence of equivalence. Keep original success/
   failure labels fixed; group counts can differ because separate pools have
   separate partial batches, affecting analyst/proposal budgets.

## Essential controls and execution order

Match actor/model/toolchain/time limit, initial skill, fast/slow settings,
extractor, proposal budget, final edit budget, representation length and actual
runtime exposure except the intended factor. If a larger card bank is allowed,
record that as a separate capacity change instead of silently dropping native
SkillOpt's edit cap in only one arm. Grouping must not receive more total
analyst proposals or unlimited per-source weight; normalize extraction resources
and account for repeated shared prefixes. Reusing prefixes does not mean actors
observed the whole historical conversation.

Keep all variants/branches of one source task in one data split. Stagnation/
regression selection is train-only. Freeze artifacts before evaluation. Use
validation for choices and a final frozen test for reporting. Report success,
paired gains/regressions, total input/output usage, wall time, failure/timeout
cost, offline construction cost and online deployment cost. Independent units
are source/evaluation tasks, not hundreds of correlated variants or API calls.

The certified Boolean obfs implementation currently has mostly AC coverage;
use a matched eligible subset or choose a separately declared ExVerus-style
verifier-accepted generation route. Do not silently compare an AC-only obfs
cohort with a full-project hint cohort or describe uncertified variants as proven
equivalent. Insufficient valid variants must be logged, not hidden by replacing
hard tasks with easy sources.

Recommended staging: first fixed original-trace grouping/format checks; then
N=10 H versus O/U plus random-point control; then matched N=40 and the full
format/group ablations. Obfs joins after reliable task export and new-trajectory
creation. A complete factorial is optional; individual claims should stay scoped
to the contrasts actually run. No thresholds or budget approval are implied.

## Safety and provenance

Design uses the just-audited pinned SkillOpt and existing experiment records;
no new literature, API call, GPU allocation, data generation, code change or
raw/sealed-data mutation. The no-local-GPU constraint remains active. Only
reviewed compact planning text and index/current pointers are written here.
