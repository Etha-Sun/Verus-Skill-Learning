# Compact autonomous card index and offline applicability review implementation

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-07T18:02:17`
- type: auxiliary/dev implementation; no live outcome experiment
- dataset/split: existing original63/augmented78 banks; seven synthetic development
  states only, no validation/task sources or sealed-test input
- baseline: frozen completed-campaign title/Trigger index
- variant: deduplicate title==Trigger or absent heading; preserve complete Trigger
  by default; optional independently reviewed description map
- metrics: exact source/body/ID preservation; UTF-8 entrypoint bytes; unit tests
- leakage controls: analyst-only case answer keys; no model calls; no raw writes;
  no old deployment/outcome overwrite; source hashes verified after rehearsal
- stop condition: regression suite and fresh real-bank deployment rehearsal pass

## Commands

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt \
python -m pytest -q skillopt-verusage/tests/test_card_bank.py \
  skillopt-verusage/tests/test_card_review.py \
  skillopt-verusage/tests/test_native_card_update.py \
  skillopt-verusage/tests/test_augmentation_campaign.py \
  skillopt-verusage/tests/test_evaluate_resume.py

# Run artifacts/check_index.py with --source-root set to completed recovery,
# --old-artifacts set to the parent artifacts directory, --cases set to
# skillopt-verusage/review/card_routing_cases.json and a fresh --output child.
```

Final tests used the existing vrl Python3.11 environment (pytest8.3.5/openai2.8.0),
123 passed. The first system-Python wider test attempt had9 import failures from
missing `openai`, not logic regressions; no dependency install or code workaround.
Before implementation, the focused revised tests gave14 expected failures/10
passes (duplicate rendering and missing description API); after implementation,
all focused tests passed. `git diff --check` passed.

## Outputs

- final external directory: `VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-index-review-dev-20261007-180217-final/`
- metrics/source hashes/deploy manifests: `receipt.json`
- fresh bundles: `original_only/`, `augmented/`; each has SKILL.md, cards.json,
  arbitrary-ID card_read.py; no new ranking/search helper
- private analyst packet: `applicability-review/review.json`, seven cases,
  complete deployed index and manifest, full target-card bodies, blank evidence
  fields; not a retrieval measurement or an actor-visible fixture
- earlier default-renderer rehearsal retained at sibling without `-final`
- reusable check: [artifacts/check_index.py](artifacts/check_index.py)
- implementation/use: [review README](../../../../../skillopt-verusage/review/README.md)

## Results

| metric | baseline | variant | delta |
|---|---:|---:|---:|
| Original63 entrypoint UTF-8 bytes |26462|14336|-12126 (-45.8%)|
| Augmented78 entrypoint UTF-8 bytes |35342|18836|-16506 (-46.7%)|
| Complete ordered ID visibility |141|141|0|
| Exact full-body reads |141|141|0|

All141 actual reader subprocesses returned the exact source card content and ID;
both source bank bytes and old entrypoint bytes retain their hashes. New deployed
cards.json hashes equal the frozen bank hashes. The description-map tests prove
it changes only discovery text, not card bodies; all IDs must be covered, no
empty/multiline/unknown-ID entries accepted. No description generation occurred.

Case families:052 post-pass cleanup optional vs failed quantifier inapplicable;
069 missing antecedent applicable vs unrelated universal failure inapplicable;
021 fixed-width connector applicable vs map-view/no-connector inapplicable.
These verdicts are hypotheses derived from card prerequisites. The packet leaves
observed applicability/read/premise/action-or-decline/diff/Verus/preservation/
conclusion blank until independent trace review. Do not report7/7 accuracy.

## Interpretation

The engineering contract is supported: index duplication is removed without
information loss to bodies, ID availability or autonomous read selection.
Claude-inspired separation influenced the optional description interface and
near-miss/trace evidence worksheet, not a new retriever or native-learning change.
Byte savings are not measured provider token savings, cost reductions, or solved
rate gains. Actual bank summaries still use complete Triggers after deduplication;
short descriptions are only an explicit, reviewable future input. This does not
resolve overlapping rule families or establish semantic card utility. Main
campaign inference remains inconclusive; broader R042 is not declared complete.
Dedicated graph/execution APIs are unavailable; local hash evidence fallback.

## Next Action

Review routing descriptions and actual usage on development data before any
new live index comparison. Keep actor advice separate from analyst expectations;
old validation has been analyzed and is not fresh confirmatory evidence. No
additional paid or sealed-test run was started or required for this version.
