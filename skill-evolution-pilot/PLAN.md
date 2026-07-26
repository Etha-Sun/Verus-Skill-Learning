# Implementation and Smoke Plan

Run ID: `skill-evolution-infra-v1`

Tier: `auxiliary/dev`

Selected idea: build one auditable host layer that converts Codex and Qwen
execution into the same event schema before spending budget on skill
comparison. The first measured run is a fidelity smoke, not a skill-evolution
result.

## Research contract

- Research question: can we reconstruct the visible agent loop and bind every
  final result to the exact task, skill, model, workspace, code, verifier, and
  token ledger?
- Null hypothesis: the available model interfaces omit enough payload or usage
  information that the proposed comparisons are not auditable.
- Alternative hypothesis: both interfaces can produce F3 audited traces under
  a host-controlled workspace and normalized event contract.
- Baseline: current `verus_self_evolve.codex_baseline` behavior and its existing
  tests; baseline code and previous run artifacts remain read-only.
- Primary smoke metrics: JSON parse errors, unpaired request/tool events,
  unbound verifier events, secret matches, immutable-input violations.
- Success: all counts are zero and independent Verus/Lynette validation agrees
  with the recorded result.
- Abandonment: any credential leak, reference-proof leak, silent model
  substitution, or verifier result that cannot be bound to code.

## Minimal code-change map

| path | planned role | reason |
|---|---|---|
| `src/skill_evolution_pilot/events.py` | normalized event schema and audit | common Codex/Qwen comparison surface |
| `src/skill_evolution_pilot/redaction.py` | recursive credential/header sanitization | live API safety |
| `src/skill_evolution_pilot/workspace.py` | allowlisted visibility/inventory manifests | information isolation |
| `src/skill_evolution_pilot/codex_adapter.py` | Codex JSONL conversion | preserve visible Codex trace faithfully |
| `src/skill_evolution_pilot/openrouter_adapter.py` | env-only Qwen request adapter | safe primary small-model transport |
| `src/skill_evolution_pilot/cli.py` | model-free smoke and bounded preflight commands | reproducible entry point |
| `tests/` | fake-provider and malformed-event coverage | avoid spending credit while debugging |

All code remains under `skill-evolution-pilot/` because it is experiment-local
and has not yet earned promotion into the repository-wide `src/` package.

## Execution sequence

1. Implement schema, redaction, workspace manifest, adapters, and unit tests.
2. Run model-free tests with a fake key and fake provider responses.
3. Run a local model-free CLI smoke into a temporary directory.
4. Run a one-task Codex smoke only if steps 2-3 pass.
5. Run one OpenRouter preflight only when `OPENROUTER_API_KEY` exists in the
   process environment and redaction scans pass.
6. Stop after the first interpretable live result and update the tracker before
   spending further credit.

## Runtime and outputs

- Model-free tests: seconds, zero model calls.
- Codex smoke: at most one task/run initially, fixed timeout.
- OpenRouter preflight: one minimal request.
- Qwen solver inference: `temperature=0.2`, `top_p=1.0`.
- API meta-skill generation, if used: separate exploratory
  `temperature=0.7`; never inherit the solver temperature.
- Connectivity preflight: `temperature=0.0`.
- Codex temperature: not configurable through the supported CLI contract;
  control variance with matched repeated H0 runs.
- Durable live outputs:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/<run_id>/`
- Repository output: source, tests, schemas, compact reviewed conclusions only.

## Fallbacks

- If OpenRouter reports no credit or remains unavailable after bounded retry,
  create a new local-Qwen run ID using the same normalized schema.
- Never switch transport inside a partial trajectory.
- If Codex lacks a payload, mark it incomplete; do not invent or infer it.
- If a smoke reveals an implementation problem, change one layer and repeat
  only the smallest discriminative test.

## Revision log

| date | change | reason |
|---|---|---|
| 2026-07-26 | implementation phase opened | planning-only artifacts were insufficient |
