# Case first card mechanism validation and transfer boundaries

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-09-26T23:07:25`
- status: `complete_read_only_case_audit`

## User correction and objective

The user emphasizes that a small bank permits case analysis: why a card was
extracted, whether it solves the source trace problem, and whether it generalizes.
Do not let the bank-size explanation replace individual-card mechanism testing.
Broad retrieval evaluation does not isolate those questions.

## Directly checked evidence

IR original events show verification success followed by preservation failure.
IR CP06 hinted diffs remove an import and qualify a macro without rewriting the
proof; no-hint diffs remove the import, replace the proof, then fix helper call
syntax. Final validations pass. AL CP07 v2 independently shows preservation
failure followed by unused-import removal and dual success. This supports a
shared repair mechanism, but both sources contributed to the current merged card.
It is cross-case corroboration, not held-out transfer. Do not attribute a
pre-cleanup preservation failure to AL original, where none was observed.

AC original shows success with informational trigger notes, unsupported annotation
insertion, attribute failure, then removal restoring success. All CP06 branches
repair the annotations. This lesson already exists in the original trajectory;
these branches alone provide weak evidence of unique augmentation knowledge.

Historical hints and generated abstract cards differ. A successful hinted repair
supports the described action, not a claim that the final card causes that action.

## Next recommended experiment

Prioritize directly supplied-card checkpoint diagnostics before scaling the bank:
no card, original-derived card, augmented-derived card; equal actor-visible state,
history, diagnostics, model/tools/budget; independent repeated attempts. Examine
first action, exact repair, dual validation, detours and cost. Source-checkpoint
reconstruction is not generalization. For transfer, freeze a card before using
independently sourced cases excluded from extraction, with positive and negative
applicability examples. Small code variants test surface robustness only.
The current merged IR+AL card cannot claim AL as unseen. No new run was launched.

## Artifacts and safety

External case audit: `skillopt-retrieval-pilot-20260926/audit/CASE_STUDIES.md`.
Sources remain in `skillopt-validation-20260923/extraction/augmented/tasks/`.
Only existing events/diffs/validations and compact memory were read or written.
No API/model calls, GPU use, verifier reruns, test reads or raw/sealed modifications.
