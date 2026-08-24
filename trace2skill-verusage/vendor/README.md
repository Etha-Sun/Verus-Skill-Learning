# Verus Trace2Skill runtime snapshot

`trace2skill_verus/` is the self-contained producer runtime migrated from the
reviewed `feature/trace2skill-verusage-20260813` state at commit
`92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e`.

The snapshot contains the prompt-driven Trace2Skill `skill_evolver/` MAP/REDUCE
implementation adapted for the Verus task, including only the thin model client
needed to execute its generation prompts. The frozen Verus construction prompts
are overlaid in place. The deprecated ReAct task-solving harness is excluded;
produced skills are consumed and evaluated through the shared Codex CLI
harness. The custom semantic REDUCE/router and the experiment bundle's semantic-v4, M_core, candidate-gate,
actor, and legacy evaluation-bridge paths are not part of this runtime.

Evaluation remains outside this directory and delegates to the shared
evaluator under `skillopt-verusage/`.

See `SNAPSHOT.json` for the source and deterministic tree hashes. Trace2Skill
originates from Qwen-Applications and is described upstream as Apache-2.0.
