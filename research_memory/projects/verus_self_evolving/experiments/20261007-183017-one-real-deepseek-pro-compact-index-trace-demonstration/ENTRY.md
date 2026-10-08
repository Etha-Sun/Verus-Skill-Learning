# One real DeepSeek Pro compact index trace demonstration

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-07T18:30:17`
- type: auxiliary/dev, user-authorized exactly one real trace demonstration
- dataset/split: purpose-selected previously analyzed validation task
  `599792dd13f472f45fa4` / `AL__always_distributed_by_and`; not an independent test
- baseline: existing augmented78 card bodies and initial skill unchanged
- variant: deduplicated full index, all IDs, optional arbitrary-ID reads
- metrics: actual event sequence, body reads/application evidence, final dual
  validation, actor walltime, settled provider usage; no statistical comparison
- leakage controls: existing filesystem/network-isolated actor; no reference
  solution, old trace or review answer key supplied; no sealed-test access
- stop condition: one saved episode and bridge drain, whether success or failure;
  no ordinary failure retry or forced read

## Commands

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt \
python artifacts/run_demo.py --config "$RECOVERY_CONFIG" --bundle "$COMPACT_AUGMENTED_BUNDLE" \
  --manifest fixed-claude-stratified-80-seed20260814/val/items.json \
  --item-id 599792dd13f472f45fa4 --output "$FRESH_APPROVED_DEMO_ROOT"
```

Execution used existing vrl Python3.11 and an explicit approved
VERUS_SKILL_RUN_ROOT override. First preflight stopped before any output/API
because .env has a legacy root; credentials/config were not edited. Corrected
environment admitted one real episode, exec session95706, exit0.
Exact command/driver/tool/input hashes, PID/start/model/budget/artifact captured
in external contract.json. Native graph/bash_exec APIs unavailable; local evidence
fallback only, not a graph-recorded main experiment.

## Outputs

- external: `VERUS_SKILL_RUN_ROOT/skillopt-verusage/compact-index-live-demo-20261007-183017/`
- user-readable actual flow: `TRACE.md`
- raw events/conversation/candidate: `episode/codex_events.raw.jsonl`,
  `episode/conversation.json`, `episode/workspace/candidate.rs`
- actor result/independent validation: `episode/result.json`, `episode/validation.json`
- input/artifact/runtime binding: `contract.json`, `episode/run_manifest.json`
- settled provider/read/hash evidence: `summary.json`, `provider_calls.jsonl`,
  `episode/retrieval_audit.json`
- raw event SHA256: `5d88ae1725cf3a5d021329a426ee7d599899696dbcce8834c142ebd28b9743b2`
- [plan](PLAN.md), [driver](artifacts/run_demo.py), [checklist](CHECKLIST.md)

## Results

| metric | actual single episode |
|---|---|
| actor / total including independent validation seconds |70.58 /71.55|
| final Verus |1 verified,0 errors|
| final preservation |pass,exit0|
| fidelity/provider/terminal |V2_TRACE,valid,completed1/failed0/errors0|
| body reads / direct-bank accesses |0 /0|
| provider requests |14,all metered,all Pro|
| prompt tokens |257002 (247424 cache hit,9578 miss),across all turns|
| completion tokens |5278 (including3786 reasoning)|
| estimated settled usage USD |0.022215248,unknown0|

Actual sequence: read task/input/full index -> empty-body postcondition failure
item7 -> add quantified proof item8 -> antecedent/helper precondition failure
item9 -> `==>` to dedicated `implies` operator item10 -> first Verus success
item11 -> preservation success item12 -> explicit trigger cleanup item13 ->
both checks again item14/15 -> final diff/report item16/17. Snapshot diffs031,
038 and049 independently preserve those edits. Final host also dual passes.
No model/private reasoning reproduced in the concise trace report.

## Interpretation

This supports executable clean deployment and the saved actual proof-repair
sequence, not efficacy. Agent exposed to complete index but never read a card
body, so there is no read/adoption chain. The repair agrees with a card family
and the explicit verifier diagnostic; neither establishes card causality.
Optional reads allow solving without a body read; do not force one or rerun to
make this demonstration look better. Post-pass trigger cleanup is not the change
that first made verification succeed. Prompt257002 is summed usage over14
requests, not one initial prompt size or evidence of old/new token reduction.
All source task/manifest/config/deployed-bank hashes unchanged; raw/sealed data
untouched. Frozen completed160 results remain unchanged and inconclusive.

## Next Action

Show the actual concise trace and full files. If user later requests quantitative
index comparison, design same-card-bank old/new runs with independent leakage
controls; no need to relearn cards or rerun augmentation. Do not autonomously
expand this one-example authorization into another full evaluation.
