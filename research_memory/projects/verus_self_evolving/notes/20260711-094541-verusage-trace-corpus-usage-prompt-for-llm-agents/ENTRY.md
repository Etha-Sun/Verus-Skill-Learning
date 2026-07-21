# VeruSAGE trace corpus usage prompt for LLM agents

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-11T09:45:41`
- status: `draft`

## Objective

Provide a reusable Chinese prompt that teaches another coding/research LLM how
to safely and correctly consume the local VeruSAGE trajectory corpus.

## Context

- Raw roots: `all_batch_results-cyy-{claude,claude-s4,gpt5,o4mini}/`.
- Canonical lightweight parser:
  `verus-self-evolve-scaffold/src/verus_self_evolve/data.py`.
- Detailed verified-prefix parser:
  `verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py`.
- The raw roots remain read-only.

## Method / Actions

Audited the directory structure, `results.csv` schema, representative repair
logs, reasoning files, LLM prompt files, code-version naming, and the existing
parser implementation. The prompt specifies a staged access protocol, stable
versus heuristic associations, parser commands, and leakage-safe task splits.

## Evidence

- Existing parser recovers 2,996 traces: 749 for each of four model roots.
- Status counts: 1,691 VERIFIED, 810 FAILED, 495 TIMEOUT.
- Parsed attempts: 34,801.
- Reusable artifact: `VERUSAGE_TRACE_DATASET_PROMPT.zh.md`.

## Result

Completed a self-contained Chinese prompt for an LLM agent. It explains that a
trace is a task-model run directory rather than one JSON object, and prevents
the two most serious interpretation errors: treating an accepted intermediate
version as final verification, and splitting the same task across models into
both train and test.

## Decision / Next Step

Use this prompt as the default trace-corpus onboarding context. If a future
agent needs exact per-call reconstruction, extend the detailed parser while
preserving the same read-only and task-grouped split contract.
