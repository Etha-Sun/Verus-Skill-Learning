# Extensible checkpoint selector and native SkillOpt two task card batches

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-03T12:38:47`
- dataset/split: unchanged fixed train40;39 reviewed progress reports plus one failed original
- baseline: preserved helper-inclusive reports and unchanged native SkillOpt skill-update path
- variant: extensible deterministic three-checkpoint selection; native Reflect card-output sink; two source tasks per batch
- metrics: selector coverage/reasons, batch task/trace coverage, card schema/provenance, local regression tests
- leakage controls: no sealed reads; original traces read-only; failed task has no successful reference; no paid launch
- stop condition: verified offline40-task selection and native two-task/eight-trace card integration with mocked transport

## Commands

```bash
# Offline command and regression list are in RESULTS.md and the interface guide.
python3 research_memory/scripts/mem.py index
```

## Outputs

- approved external run-root pointers: `skillopt-verusage/checkpoint-rule-v1-20261003-dev03/`
  and `skillopt-verusage/native-card-original40-mock-20261003-dev01/`
- manifests: preparation manifest/source bindings, preservation audits, implementation
  verification code/tool hashes; native update and explicit mock_run.json
- metrics:40 sources/120 points,142 tests/13 subtests,20 full original native mock batches
- summary and interpretation: RESULTS.md

## Results

Dev implementation and offline verification complete under the explicit2-originals
plus6-continuations assumption. No contrary async answer arrived. Exactly3 points
each, native two-question Reflect and cards-only sink wired. No paid requests,
real new augment traces or real model-derived cards. See RESULTS.md and checklist.

## Interpretation

Local integration success does not establish better checkpoint value or learned-card
utility.84 of120 selected points are marked context fallbacks. Some regression
seeds are excluded by preservation/parser admission. Full eight-real-trace context
admission remains dependent on actual generated suffixes.

## Next Action

Review the interpretation/contracts, then authorize a fresh real fork/card smoke
before full120 continuations/20 augmented batches. Paid gates remain closed.
