# Evidence aware card bank merge and autonomous retrieval pilot

## Metadata

- project: `verus_self_evolving`
- kind: `experiments`
- created_at: `2026-09-26T21:45:43`
- status: `complete_diagnostic_no_utility_gain_established`

## Objective and authorization

The user authorized starting the evidence-complete merge, fidelity fix, and
small matched retrieval pilot, and asked whether an API was needed. Stored
DeepSeek credentials passed an authenticated model-list check; V4 Pro is
available. Codex's existing login supports the Sol optimizer. No key was exposed.

## Method

Reused frozen original-only/augmented three-task analyses from external
`skillopt-validation-20260923/extraction/`. No original/hint/no-hint trajectory
or analyst call was rerun. Each arm completed one Sol/high merge. The opt-in
`evidence_bank` profile forwards full sidecars through native normalization,
binds source-card identities, requires Why, and accounts for every proposal.
There is no global four-card truncation; both arms have the same per-card limit.
Original retained six proposals as six cards; augmented retained six as five,
merging only preservation suggestions. The wrapper now saves exact stdin and
visible events externally. Previous prompts, cards and optimizer outputs remain
unchanged in their original directories.

Astra approved both unedited banks for a pilot after symmetric review without
validation access. Known caveats: helper fallback generalization, imprecise Why
and evidence-history wording, ambiguity in prechecks, and prerequisites spread
across cards. These remain testable native outputs, not manually corrected cards.
Old/new comparison jointly changes evidence forwarding, Why, length and bank
capacity; it does not isolate one factor.

The two old incomplete-payload records per rollout were ignored-configuration
warnings for `model_supports_reasoning_summaries`. Removed this unsupported
setting for new actors. Kept old records unchanged, with a separate diagnostic
audit; no validity gate was relaxed or old result reclassified. One old timeout
also has an unmatched command, retained in the diagnostic audit.

Added dependency-free lexical search/read, identical in both frozen bundles.
Search returns up to three titles/triggers; read returns one card. Both main
skills are identical. Private sidecars are excluded from deployed bundles.
Visible outputs measure exposure; application correctness requires manual audit,
and direct file reads may bypass the helper. Twenty-two focused tests and
formal Verus/actor-isolation preflight passed before launch.

## Frozen pilot contract

- Two conditions: original-only bank and augmented bank.
- Same predeclared lexicographically first validation item per IR/AC/AL.
- One attempt per condition/item, six total; no provider seed control.
- DeepSeek V4 Pro/high, 600 seconds, three workers, USD 5 local actor estimate guard.
- Same main skill, search/read tool and exposure limits; bank counts may differ.
- Success requires dual validation, valid fidelity and within-budget completion.
- Preserve all failures, timeouts, actor usage and retrieval events.
- No automatic expansion, actor retry, GPU use or final-test access.

## Artifacts

External root: `skillopt-retrieval-pilot-20260926/` beneath run storage.

- `audit/CARD_BANK_AUDIT.md`, `audit/card_bank_audit.json`;
- `audit/fidelity_root_cause.json` (diagnosis, not reclassification);
- `merge_launch.json`, per-arm merge logs;
- `bundle_manifests.json`, `skills/`, `matched_audit.json`;
- `experiment_contract.json`, `runtime_config.json`, `implementation_hashes.json`;
- `launch.json`, `status.json`, `validation.log`, `results.json`, `summary.json`;
- `rollouts/` full traces/validators and `retrieval_audit.json`;
- `budget.json`, `bridge_calls.jsonl` for actor usage.

New merge outputs are under each existing evidence packet's separate
`optimizer-evidence-bank-20260926/` directory. Production code and prompt:
`skillopt-verusage/src/skillopt_verusage/{fork_card_optimize,card_search,card_bank,skill_validation}.py`
and `skillopt-verusage/prompts/fork_cards/merge_evidence_bank.md`.

## Result at launch

Both merges and preflight complete. First three actors emitted normal events
without the old config warnings. No completed utility result claimed yet.
This three-item pilot cannot establish generalization or token efficiency.

## Next action and safety

Finish all six attempts unless infrastructure validity requires a stop. Audit
retrieval/application and actual verifier results, then report paired outcomes
without tuning cards on validation cases. Do not automatically launch later
paper-scale no-hint/teacher-only controls. Historical/raw/sealed inputs and old
run outputs remain unchanged; new outputs stay in external run storage.

## Completed pilot result

All six planned attempts finished. Each condition solved the same AL item and
had two timeouts (IR and AC): one of three solved per condition. The two successes
are V2_TRACE; all four timeouts are V1_TRUNCATED. No V0 outcome occurred, all
incomplete-payload counts are zero, input/skill files stayed unchanged, and the
frozen implementation hashes still match. Historical records were not changed.
On the sole jointly solved item, augmentation used more recorded output tokens.
This diagnostic does not establish a general gain or disadvantage. Do not treat
smaller recorded timeout usage as efficiency, especially with unsettled calls.

Actual retrieval behavior matters: original IR searched twice but read no full
cards; original AC/AL used no search/read. Augmented AC searched and read two
cards, AL searched and read one, while IR directly read the entire five-card
JSON bank and helper source. That last behavior bypasses the instructed retrieval
interface: file-level access does not enforce per-call exposure limits. Retain
it as a protocol deviation instead of silently excluding the attempt. Search
snippets themselves are exposure. An AL temporal-induction query returned a
container-identity card, illustrating weak matching/coverage. In AC, reading
cards did not avoid a subsequent quantified-antecedent mistake before verifier
feedback corrected it. No explicit card-ID rationale establishes actual use.

Actor accounting has settled requests plus two remaining reservations when the
bridge exits. The reservations were not cleared or treated as charges; final
billing/usage is incomplete. Exact recorded costs, tokens and exposure events
remain external in `audit/pilot_outcome_audit.json` and `ANALYSIS.md`, alongside
all attempts. Optimizer and historical teacher costs remain separate.

Next recommended diagnostic: distinguish bank coverage, retrieval and correct
application from card utility, possibly with controlled relevant-card exposure
and broader training-task coverage. Do not tune cards on these validation answers.
No additional calls or full validation expansion were launched after this pilot.
All raw/sealed inputs, historical trajectories and prior outputs remain unchanged.
