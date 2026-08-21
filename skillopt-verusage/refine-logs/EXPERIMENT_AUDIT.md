# Blank/S2 Four-Model Baseline Audit

Date: 2026-08-19
Formal test status: **NOT STARTED**

## Verdict

- **Strict byte-identical cross-provider comparison:** NO-GO. GPT and DeepSeek
  use native Responses paths, while GLM and Qwen require a Responses-to-Chat
  compatibility layer with provider-specific message and sampling treatment.
- **Semantic-contract comparison:** conditional GO after a real GLM edit/verify
  smoke. Qwen's corresponding smoke now passes. By explicit experiment
  decision, the original test-20—including two known harness-incompatible
  items—is retained unchanged and scored uniformly. The comparison must
  be reported as controlling the dataset, task contract, skill bytes, Codex
  runner, outer budgets, retry policy, and verifier—not provider serialization.

The independent reviewer was a same-family Type-A reviewer
(`gpt-5.6-sol`, high reasoning), not a cross-family Type-B reviewer. Its initial
verdict was FAIL / NO-GO and led directly to the remediations below.

## What `hands-off` meant

The old label meant only **autonomous noninteractive Codex CLI execution**: one
task is sent to `codex exec`, and the actor runs until completion or timeout
without human turns. It did not activate the legacy VeruSAGE `RepairRunner`.
The ambiguous term has been removed from the common task prompt.

## Upstream SkillOpt Baseline Finding

Microsoft SkillOpt does not ship one universal initial skill. Released
benchmarks point to task-specific initial documents. SearchQA has the nearest
neutral placeholder, but it is still a titled, non-empty QA document. Both the
first-release and current documentation explicitly support an empty Markdown
skill, and the base configuration defaults to an empty value.

Therefore the canonical no-strategy control is:

- file: `skillopt-verusage/skills/blank.md`;
- content: one LF byte, empty after stripping;
- SHA-256:
  `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`.

The local `skills/initial.md` is a custom 838-byte Verus seed and is neither
blank nor a universal Microsoft SkillOpt default.

## Independent Findings and Remediation

| Finding | Initial status | Current status |
|---|---|---|
| Actor confused with legacy VeruSAGE `RepairRunner` | PASS with naming warning | Label changed to `autonomous noninteractive Codex CLI actor` |
| Blank and S2 skill bytes/hash | PASS | Both variants are hash-locked |
| Prompt, workers, context, timeout | PASS | Four workers, 262,144 context, 600 s for all arms |
| GLM/Qwen lost Codex custom `apply_patch` | FAIL | Custom-tool translation implemented and unit-tested |
| Qwen real edit capability | BLOCKED | PASS: five real file changes, seven command calls, no shell edits |
| Direct/bridge V0 handling and solved counting differed | FAIL | Invalid rows retained consistently and excluded from solved count |
| GPT actor inherited credentials from `.env` | FAIL | Actor environment is now allowlisted; unrelated credentials are removed |
| Frozen test-items hash was recorded but not enforced | FAIL | Exact expected SHA is checked before task loading |
| Plan/tracker described the old four-arm S2-only run | FAIL | Replaced with the eight-condition blank/S2 contract |
| Two test-20 items fail before proof checking under the current host contract | FAIL | Accepted as a disclosed fixed-set limitation; retained unchanged and counted in solved/20 |
| Provider message roles, transport, and sampling differ | FAIL for byte parity | Unavoidable and explicitly disclosed |
| Direct and Chat arms expose exactly the same raw tool schema | FAIL | Still not byte-identical; task-required edit/command tools are available |
| GLM real edit/verify smoke | BLOCKED | Requires `ZAI_API_KEY`; formal GLM run remains blocked |

## Qwen Edit Smoke Evidence

The smoke used one non-held-out training item, the canonical blank skill, the
same Codex task prompt, max reasoning, 262,144 context, and the formal 600-second
task limit. It is compatibility evidence only and is excluded from test scores.

- result: valid `V1_TRUNCATED`, unsolved at 600.63 s;
- five completed `file_change` events through `apply_patch`;
- seven completed command events;
- eight later requests carried `custom_tool_call` and
  `custom_tool_call_output` history;
- 12/12 model requests completed with exact `qwen3.8-27b` identity;
- 137,856 prompt and 24,649 completion tokens; USD 0 API cost;
- input unchanged, fidelity F3 true, shell-edit suspect count zero;
- independent Verus and Lynette validation both executed.

Artifact:
`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/qwen38-blank-apply-patch-smoke3-20260819/`

## Remaining Claim Boundary

The eight planned conditions are four models crossed with `blank` and `s2`, 20
fixed held-out tasks each. No condition has started. The frozen manifest contains
two IronKV sources with the stale `verus_builtin_macros` alias:
`f24cf9cc9db98c56f792` and `826687f9c56eb8e65d5d`. Preserving the alias fails
before proof checking, while changing it violates the proof-only Lynette
contract. By explicit experiment decision, both remain unchanged in all eight
conditions and count toward solved/20; there is no replacement or score
adjustment. A later report may make a
paired, fixed-set descriptive comparison, but it must not claim byte-identical
requests, stability across repeated samples, or broad model-family
generalization.
