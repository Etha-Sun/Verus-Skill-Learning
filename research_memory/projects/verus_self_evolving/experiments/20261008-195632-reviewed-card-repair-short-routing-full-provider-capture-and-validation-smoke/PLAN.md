# Card repair and validation development check

## Contract

Implement the six current TODOs without changing proof safety or agent choice:
accurate card semantics, explicit installed-library visibility, reliable fields,
short distinguishable complete-ID routing, visible version limits, and opt-in
provider conversation capture. User approves validation checks after an Astra
reviewer approves a reasonable approach. This is local engineering review, not
a publication or efficacy gate; ask immediately if a material design is unclear.

Tier: auxiliary/dev. Existing analyzed validation20 may be used, sealed test20
must not be accessed. Existing banks, runs and outcomes remain immutable.
No retraining, forced retrieval/top-k/read-count, broad campaign restart or push.

## Minimum change map

- Shared card parser: recognize inline/multiline field boundaries, reject empty,
  missing and duplicate fields; preserve original body text for reads.
- Prompt/runner: optional exact installed-library read root supplied only when
  present within the existing read-only isolation mount. Default remains closed;
  all history, answers, network and secrets restrictions stay in place.
- Versioned external bank: correct072 and inspect071; clarify affected prose
  syntax/version limits, preserving IDs/order/provenance and unchanged cards.
  Add reviewed short descriptions for all78 IDs, with clear family distinctions.
  Do not merge strategies merely because their triggers look similar.
- Bridge/export: opt-in external success request/response capture without headers
  or secrets; bind ledger IDs to captures. Retain actual public reasoning only;
  no reconstructed hidden thought or invented API-to-CLI mapping.
- Regression and offline bank/body/index checks before live execution.

## Reasonable acceptance gate

One Astra reviewer assesses applicability, preservation, leakage, permission
scope, description/body consistency and capture security. No novelty review,
significance requirement or complete causal efficacy proof. Fix practical blocking
issues; record nonblocking limitations without endless refinement. Get a durable
approval before any paid validation calls.

## Validation

Four fixed already-analyzed validation questions covering quantified implication,
temporal stability, serialization and a set/sequence obligation. Select identities
from existing validation manifest and freeze before runs, without target solution
inspection to improve cards. Run old frozen augmented78 and new reviewed78 on
each task, once: eight episodes total, Pro/max/600s, two concurrent episodes.
No ordinary failure/timeout retry; provider/recording failures stop for diagnosis.
Costs recorded, no artificial fee ceiling. Actor never sees training provenance,
review answers or future proof. Old-v-new is the total revised package, not an
index-only causal ablation. Version/prompt/capture deltas explicitly recorded.

Record episode completion, Verus/preservation, actual reads/adoption/declines,
per-request and accumulated prompt/cache/output/time/estimated cost, exact saved
provider payloads and honest capture gaps. Export full saved traces and case
review. Zero reads is allowed; pass rates from four tasks cannot establish gain.

## Evidence and next action

External root: VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-repair-validation-20261008-3gtA3H/.
Minimum: tests and reviewer-approved internally consistent new bundle.
Solid for this task: eight accounted development episodes and full trace review.
Maximum: not requested; no additional campaign/sealed tests/statistical claims.
Next: Astra reviews this plan while local implementation proceeds; present any
material ambiguity to user. Then final bundle/code review, bounded validation,
source-hash/safety checks, CURRENT/index and concise result handoff.
