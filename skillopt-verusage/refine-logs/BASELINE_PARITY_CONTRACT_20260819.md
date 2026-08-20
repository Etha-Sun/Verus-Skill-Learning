# Fixed Test Baseline Parity Contract

Date: 2026-08-19

## Terminology

`Codex autonomous execution` means that Codex CLI receives one task and works
until it finishes or reaches the fixed timeout without human turns. The earlier
label `hands-off` was descriptive only. It did not select the legacy VeruSAGE
`RepairRunner` pipeline. The fixed test evaluator calls the common Codex runner
for every model; the word `hands-off` has been removed from its task prompt to
avoid this ambiguity.

## Upstream SkillOpt Initial Skill

The local Microsoft SkillOpt checkout is at commit
`9639719632daecacd1baaa47fe781f3c0253600a`. Its first release commit is
`244e346b8387931adff2a9698739cb814ce8f289`.

There is no single universal upstream initial-skill text. Each benchmark ships
its own seed. ALFWorld, DocVQA, LiveMath, OfficeQA, and SpreadsheetBench use
task-specific strategy documents. SearchQA uses only this placeholder:

```markdown
# Question Answering Skill

(No learned rules yet. Rules will be added through the reflection process.)
```

Both the first-release and current SkillOpt documentation explicitly support
starting from an empty Markdown file. This is the cleanest no-strategy control;
copying one of the benchmark seeds would introduce task-specific prior
knowledge.

Our earlier `skillopt-verusage/skills/initial.md` is an 838-byte custom Verus
seed. It is not a blank control and must not be described as the original
SkillOpt skill.

## Skill Conditions

| Label | File | Bytes | SHA-256 | Meaning |
|---|---|---:|---|---|
| `blank` | `skillopt-verusage/skills/blank.md` | 1 | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` | One newline; empty after stripping; no strategy or requirement |
| `s2` | accepted Epoch-3 `best_skill.md` | 4,179 | `1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e` | Evolved Verus skill |

The evaluator requires the expected hash and records the label, hash, byte
count, and common task-prompt hash. A mislabeled or modified skill fails before
any model call.

## Comparison Grid

The full controlled comparison is 4 models x 2 skill inputs = 8 conditions,
with 20 held-out tasks per condition:

| Model | `blank` | `s2` |
|---|---:|---:|
| GPT-5.6 Sol | 20 | 20 |
| DeepSeek V4 Pro | 20 | 20 |
| GLM-5.3 | 20 | 20 |
| Qwen3.8-27B | 20 | 20 |

No condition has started. Per the experiment decision on 2026-08-20, the
original test-20 is retained unchanged. A real GLM-5.3 Codex edit/verify smoke
passed Verus, Lynette, bridge-ledger, and F3 checks. The current public Z.AI
documentation lists `glm-5.1`, not the frozen `glm-5.3` ID, but the smoke
confirmed exact `glm-5.3` availability for this account; the model must not be
silently substituted in only one condition.

## Locked Common Controls

All eight conditions use:

- the same frozen test-20 manifest and order;
- the same `TASK.md` text, with prompt SHA-256
  `13a4598f7ff0fd6bf6955a961d48b77c7c59bfff68cd2f786aeac9fb6e81a0a6`;
- the same Codex CLI autonomous runner and workspace layout;
- the same visible task source and exactly one selected `SKILL.md`;
- reasoning effort `max`, 262,144 context, and 600 seconds;
- 20 actor-task workers for each remote provider group and four for local Qwen;
  blank and S2 run sequentially within each group, so a provider never exceeds
  its declared worker cap;
- no retry for a valid timeout and at most two retries for invalid harness
  execution;
- no reference proof, prior trajectory, retrieval cards, or cost cap;
- the same hard metric: independent Verus pass and Lynette proof-only pass;
- the same task-required edit/command capabilities. A real Qwen smoke completed
  five `apply_patch` changes and seven command calls without shell editing.

The task prompt contains only the benchmark contract: file visibility, allowed
editing surface, proof-safety constraints, verifier commands, and completion
criterion. These are not learned skill guidance and cannot be removed without
changing the task or allowing invalid proofs.

## Unavoidable Model Transport Differences

Model selection entails provider-specific serialization:

- GPT uses Codex's native Responses path and local quota.
- DeepSeek uses native Responses passthrough.
- GLM and Qwen use the Responses-to-Chat compatibility bridge.
- Qwen's official chat template requires system/developer content at the
  beginning, so its bridge moves only those messages to the front while
  preserving user, assistant, tool-call, and tool-result order.

The bridge model ID, protocol, terminal state, messages, and usage are logged.
These differences provide no extra task knowledge, but they prevent a claim of
byte-identical provider requests. Raw Codex tool schemas also differ: native
arms receive Codex's complete built-in schema, while Chat arms receive the
task-required `apply_patch`, `exec_command`, and `write_stdin` subset. The
defensible claim is that the semantic task prompt, skill input, task-required
tools, outer budgets, retries, and evaluator are controlled; model
implementation and required transport are the treatment.

## Known Dataset Limitation

The frozen `test/items.json` hash is correctly enforced as
`81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42`, but
two referenced IronKV sources still contain the stale
`verus_builtin_macros` alias:

- `f24cf9cc9db98c56f792`;
- `826687f9c56eb8e65d5d`.

Preserving the alias fails before Verus proof checking; repairing the crate
line changes a non-proof surface and is rejected by Lynette. Raw data remains
unchanged. These cases stay in every condition, follow the same verifier rules,
and count toward the main solved/20 denominator. They are recorded in each run
contract as known harness-incompatible cases and are not excluded or replaced.

## Canonical Command

```bash
skillopt-verusage/scripts/run_s2_fixed_test20.sh \
  {gpt|deepseek|glm|qwen} {blank|s2}
```

The script name is retained for compatibility; the second argument now makes
the skill condition explicit.
