# Blank/S2 Skill Four-Model Fixed-Test Plan

Time: 2026-08-20
Status: **SIX_OF_EIGHT_ARMS_COMPLETE / QWEN_GPU_BLOCKED**

## Objective

Compare four actors crossed with two skill inputs on one frozen held-out set:

| Actor | `blank` | `s2` |
|---|---:|---:|
| GPT-5.6 Sol | 20 | 20 |
| DeepSeek V4 Pro | 20 | 20 |
| GLM-5.3 | 20 | 20 |
| Qwen3.8-27B | 20 | 20 |

This is eight conditions and 160 task executions. GPT, DeepSeek, and GLM blank
and S2 arms are complete; both Qwen arms remain blocked on GPU availability.
Outcomes may not be used to edit or select either skill.

## Skill Conditions

| Label | Bytes | SHA-256 | Interpretation |
|---|---:|---|---|
| `blank` | 1 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` | Empty Markdown after stripping; no learned rule |
| `s2` | 4,179 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` | Accepted Epoch-3 Verus skill |

Microsoft SkillOpt has no universal released initial-skill text: its benchmark
seeds are task-specific. Upstream documentation and the base configuration
support an empty skill, so `blank` is the clean no-strategy control. The local
838-byte `skills/initial.md` is a custom Verus seed and is excluded.

## Locked Semantic Contract

| Item | Fixed value |
|---|---:|
| Actor harness | Autonomous noninteractive Codex CLI |
| Tasks per condition | 20 |
| Workers | 20 for remote APIs; 4 for local Qwen |
| Model context | 262,144 |
| Task timeout | 600 s |
| Retry for valid timeout | 0 |
| Retry for V0 harness invalid | At most 2 |
| CLI reasoning effort | max |
| Task prompt SHA-256 | `13a4598f7ff0fd6bf6955a961d48b77c7c59bfff68cd2f786aeac9fb6e81a0a6` |
| Judgment | Independent Verus pass and Lynette proof-only pass |
| Cost cap | None |

Every workspace contains the same immutable `input.rs`, editable
`candidate.rs`, `TASK.md`, verifier wrappers, and exactly one selected
`SKILL.md`. User config and rules are ignored, optional Codex capabilities are
disabled, unrelated credentials are removed from the actor environment, and no
reference proof, trajectory, retrieval card, or network resource is exposed.

## Model and Transport

| Condition | Exact model | Upstream path | Context | Workers |
|---|---|---|---:|---:|
| GPT | `gpt-5.6-sol` | Native Codex Responses | 262,144 | 20 |
| DeepSeek | `deepseek-v4-pro` | Native Responses passthrough | 262,144 | 20 |
| GLM | `glm-5.3` | Responses-to-Chat bridge | 262,144 | 20 |
| Qwen | `qwen3.8-27b` | Local vLLM Chat bridge | 262,144 | 4 |

The task-required edit and command capabilities are available to every actor.
Qwen's real bridge smoke completed five `apply_patch` file changes and seven
commands. Provider serialization is not byte-identical: GLM/Qwen map Codex
developer messages to system messages, Qwen moves system content to the front,
and each provider has required reasoning/sampling fields. Results must therefore
be described as a semantic-contract comparison, not a byte-identical request
comparison.

## Known Test-Set Limitation

The test manifest remains the original test-20 with SHA-256
`81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42`.
Two IronKV items (`f24cf9cc9db98c56f792` and `826687f9c56eb8e65d5d`)
contain a stale `verus_builtin_macros` alias. They are retained unchanged in all
eight conditions and count under the same verifier rule toward solved/20. No
replacement, special retry, or score adjustment is applied.

The GLM capability check passed. Its formal 20-worker arms required
bridge-internal 429 backoff to reach 20/20 provider-valid results. Qwen's
compatibility check passed, but its formal arms wait for four free target GPUs.

## Qwen Compatibility Evidence

The non-held-out blank-skill smoke ended as a valid `V1_TRUNCATED` timeout at
600.63 seconds. It was not solved and is not a score. It proved that the bridge
preserves custom `apply_patch` calls and their outputs, runs both verifiers,
retains input integrity, and records complete usage: 12/12 requests, 137,856
prompt tokens, 24,649 completion tokens, and USD 0 API cost.

## Planning Budget for Both Skills

| Actor | Approximate total for 40 tasks |
|---|---|
| GPT-5.6 Sol | 500–800 calls; 18–24M tokens; local quota |
| DeepSeek V4 Pro | 600–900 calls; 26–34M tokens; roughly USD 2.8–4.0 off-peak or USD 5.6–8.0 peak |
| GLM-5.3 | 500–1,000 calls; 20–36M input plus 1–3M output; roughly USD 12–30 |
| Qwen3.8-27B | Up to ten 10-minute waves at four workers; roughly 90–140 minutes wall or 6–9.4 L40S GPU-hours; USD 0 API |

These are planning estimates, not measured outcomes.

Measured six-arm results and complete-ledger costs are recorded in
`skillopt-verusage/refine-logs/FIXED_TEST20_RESULTS_20260820.md`.

## Canonical Entry Point

```bash
skillopt-verusage/scripts/run_s2_fixed_test20.sh \
  {gpt|deepseek|glm|qwen} {blank|s2}
```

The legacy script name is retained for compatibility. The evaluator checks the
skill label/hash, task-manifest hash, prompt hash, model identity, terminal
state, fidelity, input integrity, and verifier outputs. Invalid rows are retained
for accounting but excluded from solved counts.
