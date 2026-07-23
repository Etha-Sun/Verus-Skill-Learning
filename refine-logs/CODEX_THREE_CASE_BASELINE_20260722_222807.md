# Codex Three-Case Fresh-Exploration Baseline

**Date:** 2026-07-22

**Model:** `gpt-5.6-sol`, reasoning effort `high`

**Scope:** one fresh, independent Codex run on each of the three H0-frozen
R041A qualitative cases.

## Protocol

- The runner invoked the local Codex CLI programmatically in an ephemeral,
  workspace-write session.
- Each run received only the canonical unverified source and one identical
  proof-task prompt. Old trajectories, verified answers, H1/H2 rationales, and
  case labels were not visible.
- `input.rs` was immutable; Codex edited only `candidate.rs`.
- Every final candidate was independently checked with Verus and Lynette.
- Raw JSONL events, stderr, final message, prompt, manifest, candidate diff,
  independent verifier logs, validation, workspace inventory, and result JSON
  were preserved per run.

## Results

| Frozen case | Task | Codex | Wall time | JSONL events | Unique commands | Output tokens |
|---|---|---:|---:|---:|---:|---:|
| stable pass | `seq_filter_contains_implies_seq_contains` | PASS | 27.2 s | 14 | 3 | 688 |
| stable closest failure | `marshal_v__impl2__lemma_serialize_injective` | PASS | 279.6 s | 84 | 21 | 9,382 |
| unstable | `marshal_v__impl5__lemma_same_views_serialize_the_same` | PASS | 37.9 s | 17 | 4 | 1,048 |

All three inputs remained unchanged; all three independent Verus runs reported
`1 verified, 0 errors`; all three Lynette comparisons passed. Codex returned
normally without timeout in all three runs. Total Codex wall time was 344.7
seconds. The final cumulative usage records sum to 1,357,125 input tokens
(1,244,672 cached), 11,118 output tokens, and 3,793 reasoning-output tokens.

The closest-failure task was the informative case. Codex used 21 unique shell
commands and iterated through failed length-prefix, reveal, and extensionality
arguments before proving the fixed eight-byte prefix, equal payload lengths,
and bytewise vector equality. The other two tasks were short: an existing
subset lemma plus instantiation, and componentwise tuple-serialization lemmas.

## Interpretation

On these deliberately selected cases, fresh Codex exploration solved 3/3. The
corresponding Qwen H0 repetitions had passed 3/3, 0/3, and 2/3 respectively,
so the main qualitative difference is that Codex solved the stable localized
failure that Qwen repeatedly approached but did not finish.

This is not a solve-rate estimate or a pure model-size comparison: task
selection was diagnostic, Codex has one repetition per task, transports and
agent scaffolds differ, and token accounting is not directly comparable. It
does show that the three tasks are solvable under ordinary fresh exploration
without exposing prior trajectories or distilled rationales, and it provides
full logs for later failure-path comparison.

## Audit note

The first two run-local `event_summary.json` files were produced before a
started/completed event-deduplication fix and therefore store doubled command
counts (6 and 42). Raw JSONL is correct and unchanged. The post-hoc
`batch_audit.json`, generated after the fix, is authoritative for the unique
counts 3, 21, and 4 and records hashes for every raw event log, result, and
candidate diff.

Canonical artifacts:

- `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/codex_baseline_contract.json`
- `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/codex_baseline_jobs.jsonl`
- `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/batch_audit.json`
- `${VERUS_SKILL_RUN_ROOT}/codex_three_case_baseline_20260722_attempt1/runs/`
