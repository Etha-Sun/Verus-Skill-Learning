# Information and Trace Contract

Status: `DRAFT / REQUIRED BEFORE EXECUTION`

## 1. Isolation boundary

Every solver and meta-agent call receives a newly created workspace. The host
program constructs it from an explicit allowlist and records a
`visibility_manifest.json` before model execution.

The solver workspace may contain only:

- `input.rs`: immutable original task;
- `candidate.rs`: writable copy initialized from `input.rs`;
- `TASK.md`: frozen solver instructions;
- `SKILL.md`: absent for H0, otherwise exactly one candidate skill;
- allowlisted wrappers or tool launchers that contain no answer.

The solver must not see:

- reference or verified proof;
- previous trajectories;
- other candidate skills;
- other tasks;
- meta-agent reflection;
- branch metrics;
- sealed/test labels;
- repository history or arbitrary files outside the workspace;
- API credentials.

## 2. Meta-agent boundary

Each objective has a separate meta workspace. Its visibility manifest may
allow:

- objective and metric contract;
- current meta-skill;
- three candidate skill files;
- compact per-task metric table;
- run-validity and safety table;
- selected branch-local best/worst trace evidence;
- the complete branch-local aggregate table.

It may not allow:

- another objective's files or scores;
- final-test results;
- evaluator-only reference proofs;
- provider credentials;
- raw data directories;
- hidden reasoning.

## 3. Evaluator-only boundary

The evaluator may access:

- frozen reference proof for teacher-forced scoring;
- original and final candidate;
- Verus and Lynette;
- sanitized normalized run events;
- provider usage fields.

Evaluator-only files are not copied into solver or meta workspaces. Their
paths are excluded from prompts and visibility manifests.

## 4. Required per-run records

Each solver run must produce:

| file | required content |
|---|---|
| `run_manifest.json` | run/task/condition IDs, transport, requested and returned model, generation settings, prompt/skill/tool/source hashes |
| `visibility_manifest.json` | every initially visible relative path, size, hash, and visibility role |
| `prompt.txt` | exact sanitized user-visible prompt |
| `agent_events.jsonl` | normalized ordered model, tool, edit, verifier, and lifecycle events |
| `provider_io.jsonl` | complete sanitized provider-native requests and responses when legally/technically available |
| `codex_events.raw.jsonl` | complete Codex `--json` stdout without summarization |
| `tool_events.jsonl` | command/tool input, output, exit status, timing, and evaluated code hash |
| `edits.jsonl` | exact patch or before/after hashes and snapshot pointers |
| `snapshots/` | full candidate state after every completed edit/tool boundary |
| `candidate.diff` | initial-to-final proof-only diff |
| `usage.json` | per-request and cumulative token fields; missing fields are null |
| `validation.json` | immutable-input check, final Verus, final Lynette, candidate hash |
| `workspace_inventory.json` | final relative path, size, and hash for every file |
| `result.json` | final status, success iteration, requests, tokens, wall time, and validity flags |

All model requests in a Qwen agentic trajectory must have a request index.
Actual request count and trajectory count are separate fields.

## 5. Normalized event schema

Every `agent_events.jsonl` row contains:

```json
{
  "schema_version": "1",
  "event_index": 1,
  "timestamp": "UTC ISO-8601",
  "run_id": "opaque id",
  "actor": "codex|qwen|host|verus|lynette",
  "type": "model_request|model_response|tool_call|tool_result|edit|verifier|lifecycle",
  "request_id": null,
  "tool_call_id": null,
  "payload_complete": true,
  "candidate_sha256": null,
  "data": {}
}
```

Rules:

- event indices are strictly increasing;
- tool calls/results share a `tool_call_id`;
- model requests/responses share a `request_id`;
- verifier events include the exact candidate hash;
- an edit includes an exact patch or immutable before/after snapshot hashes;
- primary pilot logs do not truncate or summarize provider, tool, edit, or
  verifier payloads;
- provider reasoning-token counts are usage metadata, not reconstructed
  reasoning text.

The normalized stream is an index over raw evidence, not a replacement for it.
Every field returned by Codex or OpenRouter is retained in the corresponding
sanitized raw log. If the interface returns `reasoning`, `reasoning_details`,
or a visible reasoning summary, it is retained in full. If it returns only a
reasoning-token count, only that count is available. If neither is returned,
the fields remain `null/unavailable`; this does not by itself prevent F3.
Hidden chain-of-thought that the interface does not return cannot be
reconstructed.

## 6. Token ledger

For each request, record provider-native:

- prompt/input tokens;
- cached input tokens;
- completion/output tokens;
- reasoning tokens if explicitly returned;
- total tokens;
- provider-reported cost if returned.

Also record host-derived:

- byte/character counts for prompts, skills, outputs, and tool results;
- local-tokenizer audit counts with tokenizer identity and version;
- cumulative counts at every agent iteration.

Never convert a missing usage field to zero. Store:

```text
value: null
availability: false
source: provider_missing
```

The token branch freezes one primary formula before comparing candidates. Its
primary ledger uses stable provider input/cached/output/total fields. Reasoning
tokens are supplementary when exposed, so their absence does not invalidate a
run.

## 7. Credential contract

The OpenRouter credential is:

- supplied only through `OPENROUTER_API_KEY`;
- read only at runtime;
- never accepted as a command-line argument;
- never included in a config, manifest, prompt, traceback, request record,
  process title, or git artifact;
- removed from all copied environment mappings.

Logs retain only:

```json
{
  "credential_env": "OPENROUTER_API_KEY",
  "credential_present": true
}
```

They do not retain length, prefix, suffix, hash, or value.

Before a live call, a fake canary credential must be passed through every
error/logging path. Repository and run-root scans must return no canary match.
HTTP authorization headers are removed before any request object is persisted.
Provider error bodies are parsed into a status/category and sanitized excerpt;
raw bodies are not printed blindly.

## 8. Fidelity levels

Each run receives one label:

- `F0_INVALID`: leak, model mismatch, corrupt manifest, or unbound verifier;
- `F1_OUTCOME_ONLY`: final code/outcome exist but the visible loop is not
  reconstructable;
- `F2_VISIBLE_TRACE`: visible model messages, tool calls/results, edits, and
  verifier checkpoints are reconstructable;
- `F3_AUDITED_TRACE`: F2 plus complete usage, visibility, hash binding,
  independent validation, and redaction audit.

Only F3 runs enter the primary pilot analysis. F1/F2 may be retained for
debugging but cannot be silently pooled.

Any truncated visible payload, summary-only code edit, missing tool result,
missing candidate snapshot at a completed tool boundary, or missing usage field
needed by the selected metric prevents F3 classification. Unavailable
reasoning text or reasoning-token subfields are explicitly exempt.

## 9. API/local transport contract

OpenRouter and local Qwen use the same normalized event and workspace schema,
but retain distinct:

- `transport`;
- model identity;
- serving version;
- generation parameters;
- tokenizer/usage source;
- latency and retry semantics.

A live run never changes transport after its first model request. If the API
fails after a partial trajectory, that trajectory is marked failed. A new
run ID is required for local fallback.

## 10. Safety and raw-data policy

- Raw and sealed datasets remain read-only.
- Complete traces and responses remain below `VERUS_SKILL_RUN_ROOT`.
- The repository may contain schemas, compact aggregate tables, reviewed
  conclusions, and external artifact pointers only.
- No complete reference proof, raw trace, token table, or provider response is
  committed.
