# M0 hands-off corpus integrity and unified harness execution

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-20T00:10:46`
- status: `go`
- dataset/split: eight frozen project directories under
  `claude_sonnet_gpt5`; original train/dev/sealed-test counts
  3,347/3,015/3,021; effective train count 3,341 after quarantine
- baseline: frozen hands-off Copilot prompt, H0 with no injected knowledge
- variant: H1 generic payload and H2 task-specific payload; M0 evaluates only
  mechanics, not method quality
- metrics: corpus coverage, sealed reads, exact/near overlap, usage coverage,
  prompt/source hashes, Verus result, Lynette target-mode result
- leakage controls: sealed MA/NR trace content never read; evaluation answers
  never accessed; exact name/hash and 7-token-shingle Jaccard audit at 0.90
- stop condition: satisfied for train-only R040-R041 after a live H0/H1/H2
  smoke recorded usage and verifier/checker status under the frozen harness

## Commands

```bash
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_m0 inventory ...
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_m0 audit ...
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_m0 quarantine ...
PYTHONPATH=src python3 -m unittest tests.test_handsoff_m0 tests.test_handsoff_harness -v
PYTHONPATH=src python3 -m verus_self_evolve.handsoff_harness ... --dry-run
Qwen3.6-27B vLLM + Copilot CLI H0/H1/H2 mechanical smoke
```

## Outputs

- run directory: `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/`
- logs: `RUNLOG.md`, `smoke_live_local_20260720/qwen36/*/copilot.log`, and
  integration fixture logs
- metrics: `m0_summary.json`, `historical_usage_coverage.json`,
  `leakage_report.json`
- manifest: `corpus_manifest.jsonl`, `effective_corpus_manifest.jsonl`,
  `split_manifest.json`, `run_manifest.json`, `harness_manifest.json`

## Results

| metric | result |
|---|---:|
| corpus trajectories | 9,383 |
| original / effective train trajectories | 3,347 / 3,341 |
| quarantined train trajectories | 6 |
| sealed trace content reads | 0 |
| final exact-name / exact-code / near overlaps | 0 / 0 / 0 |
| historical train logs with usage | 283 / 3,347 |
| regression tests | 15 passed |
| deterministic usage + Verus + Lynette integration | PASS |
| live H0/H1/H2 usage available | 3 / 3 |
| live H0/H1/H2 Verus checked / passed | 3 / 3 checked; 0 / 3 passed |
| live H0/H1/H2 Lynette checked / passed | 3 / 3 checked; 3 / 3 passed |
| H0/H1/H2 input tokens | 1.2M / 1.1M / 1.3M |
| H0/H1/H2 output tokens | 11.1k / 10.1k / 11.8k |
| H0/H1/H2 wall seconds | 516 / 478 / 560 |

## Interpretation

M0 is `GO` for train-only R040-R041. R036-R039 establish corpus/harness
integrity after fixing historical/current usage parsing, two rounds of leakage
quarantine, relative-path defects, and timeout footer flushing. The canonical
Qwen3.6 mechanical smoke produced complete usage and safety outcomes for all
three conditions. All three candidates failed Verus while passing Lynette and
all three agents exhausted the 32,768-token context, so no inference-efficiency
or knowledge-effect claim is made. This smoke validates measurement mechanics,
not the frontier-model baseline required by R042.

QwQ direct/adapter attempts produced no executable tool calls and are retained
as model/scaffold incompatibility evidence. Qwen3.6 cleanup required force
stopping four orphan workers after SIGTERM was ignored; all four GPUs finally
returned to 1 MiB memory and 0% utilization.

## Next Action

Run R040: deterministically select 20-50 de-duplicated successful AC/AL/IR
train traces with motif/error/model coverage. R042 frontier baseline remains
blocked until cloud authentication is available.
