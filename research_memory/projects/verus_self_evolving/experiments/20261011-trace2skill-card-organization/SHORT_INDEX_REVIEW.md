# Short index revision: complete, no evaluation

## Why the first index was too heavy

The first renderer expanded every family's long title, include_when,
exclude_when and distinguish_from into the main file. Those details were also
present in each reference. It reused an offline taxonomy/audit representation
as a solver-facing directory and had no enforced directory-size ceiling.
That was an implementation/design mistake, not a necessary cost of clustering.
Thirty-seven verbose entries can outweigh seventy-eight short card descriptions.

Yuechun's reconstructed control has one short routing line per card. The user
explicitly authorized adopting the same short-entry principle for references.
This revision retains the existing taxonomy, rules and reading behavior; only
the main directory changes. Full boundaries remain in the unchanged references.

## Result

| Artifact | UTF-8 bytes |
|---|---:|
| Original grouped main SKILL | 31507 |
| Original grouped directory alone | 29388 |
| Yuechun flat-control main SKILL | 11545 |
| Revised main SKILL | 7957 |
| Revised directory alone | 5838 |

The main file is74.75%smaller than the first candidate and31.08%smaller than the
flat-control main file. These are byte comparisons, not measured model-token,
episode-input, cost-saving or performance percentages. Actual episode usage
also depends on histories and optional reference reads; no episodes have run.

Each of the37references now has one ID/link/short-entry line. All72rules,78source
cards,39non-SKILL bundle files, full reader behavior, reference manifests and
unresolved source-review items are unchanged. The2119-byte pre-index prefix
(Executive plus optional-reading instructions and directory heading) is exact.

Example cues distinguish active trigger-inference errors, missing antecedents
or shadowed binders, a universal fact not used at a concrete term, and cleanup
after verification. They are navigation cues, not complete applicability tests;
the actor still must read a rule's actual Trigger/Avoid when before using it.

## Artifacts

Run-root relative directory:
`skillopt-verusage/card-organization-20261012-compact-v1/`

- `candidate/SKILL.md`: current short-index review candidate; previous long
  candidate remains unchanged in `card-organization-20261012-reduce-v1/`.
- `candidate/references/`: byte-identical copies of the same37references.
- `candidate_manifest.json`: updated hashes, parent manifest, index revision,
  unchanged-file list, prior review issues and explicit evaluation prohibition.
- `index_proposal.json`: unchanged DeepSeek output,37descriptions, at most148
  characters each; its direct rendering would have been9784bytes.
- `index_reviewed.json`, `index_review.json`: reviewed entry cues and explicit
  before/after edits, hashes and rationale.
- `index_contract.json`, `index_input.json`, `index_system.md`, `calls/`,
  `provider_capture/`, `provider_calls.jsonl`, `budget.json`: frozen request and
  response, usage, inputs, cumulative-budget and evidence records.

## Review of the compacting output

One DeepSeek V4 Pro/max call generated the short descriptions from the existing
family routing information only. It did not see evaluation problems or outcomes.
The output also appended actions to many entry cues, including an unsupported
trigger-selection suggestion for universal equivalence. These were not deployed.

The reviewed version keeps the complete leading entry clause, removes action
tails after semicolons, and removes an unwarranted assertion of immediate proof
closure. The verified-cleanup entry retains its diagnostic clause, rather than
mistaking that clause for an action. Raw model output is retained; the explicit
offline edit log makes clear that final cues are reviewed derivatives, not the
unaltered response. This is not character-limit truncation: the raw descriptions
already passed the150-character and whole-file-size checks. No second paid call.

Implementation:

- `scripts/compact_card_index.py`: prepare/generate/draft-render; requires exact
  ID coverage, printable ASCII cues of at most150characters, valid local links,
  and a main file no larger than the contemporaneous flat control; rejects
  overflow rather than truncating. No repeated paid request in the same run.
- `scripts/review_compact_index.py`: renders the reviewed entry-only candidate
  while retaining model output, old bundle and review provenance.
- `prompts/compact_index_system.md`: isolated offline directory editing, not
  another Router, Reducer, Executive change or online retrieval model.

The old renderer and frozen build inputs remain unchanged for reproducibility;
new grouped candidates must pass the short-index stage before evaluation review.
The updated template/PLAN documents this requirement rather than silently
pretending the old long-index build was already the intended final design.

## Validation and expense

149related offline tests pass. All37links resolve; all37whole-reference reader
results match their files. All40bundle file hashes match the new manifest; all39
non-SKILL files match the parent exactly. Rule counts, source coverage, reduction
receipts and unresolved-review lists match the parent. The entire pre-index
prefix is unchanged, not merely the Executive subsection.

This call used7352input and3573output tokens, including2209reasoning tokens.
Local estimated chargeUSD0.02385372; cumulative construction estimateUSD1.74243608
including both Router attempts and37reducers, below the existingUSD5ceiling.
One settled compacting call, no uncertainty or outstanding reservations. These
are ledger estimates, not a provider invoice; existing pricing caveats still apply.

No actor evaluation or sealed-data access; no source-card/reference edits.
Shorter input text is established, but retrieval quality and performance benefit
remain unmeasured. Current candidate remains review-only pending evaluation approval.
