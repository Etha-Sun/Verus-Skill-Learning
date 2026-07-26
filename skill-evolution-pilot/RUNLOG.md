# Infrastructure Run Log

## 2026-07-26: model-free fidelity tests

- Run tier: `auxiliary/dev`
- Model calls: none
- Result: 12 unit tests pass.
- Covered:
  - complete long tool/reasoning payload retention;
  - raw and normalized event pairing;
  - exact code snapshots and diffs;
  - missing/malformed payload rejection;
  - `todo_list` lifecycle events;
  - OpenRouter model mismatch and missing credential;
  - credential redaction with zero fake-secret matches.

## 2026-07-26: Codex fidelity smoke 01

- External artifact:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/codex-fidelity-smoke-20260726-01/`
- Task role: prior `stable_pass` diagnostic; not the fourth task.
- Model: `gpt-5.6-sol`, reasoning effort `high`.
- Reasoning capture: default catalog behavior (`summary=none`); later found
  insufficient for the final fidelity contract.
- Outcome: solver passed independent Verus and Lynette.
- Fidelity outcome: `F3=false`.
- Cause: Codex 0.144.5 emitted four complete `todo_list` lifecycle events
  (`item.started`, `item.updated`, and `item.completed`) that the initial
  adapter preserved but conservatively marked incomplete.
- Preserved evidence:
  - 38 raw Codex events;
  - 13 completed tool/edit boundaries;
  - 15 complete candidate snapshots;
  - zero JSON, pairing, or verifier-binding errors;
  - usage: 353,103 input, 319,488 cached input, 4,621 output, and 2,159
    reasoning-output tokens.
- Decision: retain the failed fidelity smoke, add a lossless `todo_list`
  mapping, and rerun the same task/configuration once.

## 2026-07-26: Codex fidelity smoke 02

- External artifact:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/codex-fidelity-smoke-20260726-02/`
- Task role: same prior `stable_pass` diagnostic; not the fourth task.
- Model: `gpt-5.6-sol`, reasoning effort `high`.
- Reasoning capture: default catalog behavior (`summary=none`); this run proves
  tool/edit fidelity but is not the canonical reasoning-capture configuration.
- Outcome: solver passed independent Verus and Lynette.
- Fidelity outcome: `F3=true`.
- Audit:
  - 25/25 raw events exactly indexed;
  - five completed command boundaries and one completed edit boundary;
  - eight complete candidate snapshots; every completed boundary covered;
  - every snapshot/diff file exists and matches its recorded hash;
  - zero incomplete payloads, JSON errors, unpaired calls, unbound verifier
    events, output truncation markers, and shell-edit suspects;
  - immutable input unchanged;
  - usage: 232,495 input, 203,264 cached input, 1,671 output, and 369
    reasoning-output tokens;
  - no visible reasoning text was returned.

## 2026-07-26: Codex fidelity smoke 03 with reasoning capture

- External artifact:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/codex-fidelity-smoke-20260726-03-reasoning/`
- Configuration added:
  - `model_reasoning_summary="detailed"`;
  - `model_supports_reasoning_summaries=true`;
  - `hide_agent_reasoning=false`;
  - `show_raw_agent_reasoning=true`.
- Motivation: the local model catalog says `gpt-5.6-sol` supports reasoning
  summaries but defaults to `default_reasoning_summary="none"`. Therefore the
  absence of reasoning text in smokes 01-02 was a harness configuration
  omission, not evidence of interface unavailability.
- Outcome: solver and F3 both passed.
- Reasoning evidence:
  - four visible `reasoning` events;
  - 186 total characters of returned reasoning text, preserved exactly in raw
    and normalized logs;
  - 392 `reasoning_output_tokens` reported in usage.
- Other fidelity evidence:
  - 25/25 raw events exactly indexed;
  - five completed tool/edit boundaries covered by seven snapshots;
  - zero missing/incomplete payloads, truncation markers, shell-edit suspects,
    pairing errors, or verifier-binding errors;
  - final Verus/Lynette passed and input remained unchanged.

The returned 186 characters are reasoning summaries, not the full sequence of
392 hidden reasoning tokens. The runner now requests the maximum available
Codex reasoning visibility and preserves every returned reasoning field, but
does not claim access to raw hidden chain-of-thought.

## 2026-07-26: canonical H0 batch and token G6 smoke

- Three-task canonical H0: 3/3 F3 and 3/3 solved.
- Primary uncached tokens:
  - stable pass: 25,555;
  - stable closest failure: 71,816;
  - unstable: 32,784.
- A second canonical stable-pass H0 yielded 29,765 uncached tokens. Across the
  two repeats, mean was 27,660 and coefficient of variation was 10.8%.
- The one-task token meta-agent produced exactly three schema-valid candidate
  skills. Its visibility replay found no command outside the allowlisted
  workspace.
- Same-task G6 comparison, all F3 and solved:
  - H0: 25,555;
  - conservative: 15,611 (-38.9%);
  - aggressive: 20,320 (-20.5%);
  - structural: 28,880 (+13.0%).
- This is an engineering/counterfactual-sensitivity smoke, not evidence of
  general token-efficiency improvement.
- The proposed fourth task's standard source was solved by current Codex in
  410.97 seconds (79,245 primary uncached tokens). Its same-task no-lemma
  variant also solved in 496.61 seconds (81,130 primary uncached tokens). The
  standard source is frozen as `hard_solved`; neither run may be described as
  a current Codex failure.
- The first full-four meta-agent attempt was rejected after writing scratch
  files to `/tmp`. A second isolated attempt stalled before tool use and was
  terminated. The recorded retry completed in 327.04 seconds with a
  schema-valid output, zero outside-workspace commands, and zero secret
  matches.
- Frozen round-one skills:
  - aggressive: `bounded-exploration-gate`;
  - conservative: `delta-certificate`;
  - structural: `obligation-graph`.
- The 12-run token matrix was launched with Codex concurrency 6 and a
  600-second per-run cap.

## Current decision

Smoke 03 defines the canonical capture configuration, and the token G6 smoke
passes. The next research-facing step is the frozen four-task matrix; the
single-task deltas above are not a method claim. OpenRouter remains
blocked until `OPENROUTER_API_KEY` is supplied to the process environment; the
credential is not read from chat or persisted in the repository.
