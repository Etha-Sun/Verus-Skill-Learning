# R040C/R041 Code And Integrity Review

## Verdict

**GO** for continuing the R040C H0 repetitions and treating
`${VERUS_SKILL_RUN_ROOT}/r041_frozen_prompts_20260722_attempt3/` as the
canonical R041 prompt freeze. R041A remains blocked on R040D case stability.

## Reviewed Scope

- `src/verus_self_evolve/handsoff_rationale.py`
- `tests/test_handsoff_rationale.py`
- `refine-logs/EXPERIMENT_PLAN_20260722_125407.md`
- `refine-logs/EXPERIMENT_TRACKER_20260722_125407.md`
- R040C attempt2 candidate manifest and repetition jobs
- R041 distillation attempt1 and frozen-prompt attempt3

## Initial NO-GO And Resolution

The first independent review found four blockers:

1. distillation paths were constrained only to the corpus root;
2. prompt provenance was recorded but not transitively enforced;
3. AI-agent edit time was incorrectly labeled as human time;
4. freeze/provenance/safety gates lacked negative tests.

All four are closed:

- the distillation pack now enforces the Anvil/IronKV allowlist and
  group-specific physical containment, with a sealed-directory negative test;
- prompt freeze enforces
  `selection -> pack -> raw H1/H2 -> review -> frozen H1/H2` hashes;
- cost metadata records AI-agent edit time as 5 minutes and human time as 0;
- tests cover sealed rejection, freeze-cases success/cardinality enforcement,
  transitive provenance rejection, and permissive-bypass rejection.

The follow-up independent review returned **GO** with no blocking findings.
The full repository has 76 passing tests.

## Frozen Prompt Checks

- H1: 633 Qwen tokenizer tokens.
- H2: 632 Qwen tokenizer tokens.
- Length delta: 0.158%.
- H2 budget: below 800 tokens.
- H2 is one global prompt derived from the independent 30 R040 traces; it is
  not task-specific.
- Frozen task-identifier leaks: none.
- Permissive proof-bypass advice: none.
- H2 generation usage: 28,206 input and 634 output tokens.

## Non-Blocking Follow-Ups

- Validate the H1/H2 input-length delta again using provider-reported tokens
  on the first R041A live runs.
- Add raw-log hashes to future distillation packs.
- Add the 30-task manifest hash to future R040C summaries.
- Optionally pass raw H1/H2 paths directly to the freeze command rather than
  relying on their generation-summary and review hashes.

These items do not block the current R040C or R041 artifacts.
