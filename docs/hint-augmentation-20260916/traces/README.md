# Complete recorded augmented continuations

This archive contains all 38 initial-skill DeepSeek v4 Pro continuations for IR/AC/AL, with freshly generated v1/v2 hints (36 final dual-verifier passes and two unsuccessful continuations). These are checkpoint suffixes: the actor received the task, checkpoint code, initial skill and hint, **not a replay of the original trajectory prefix**. Original teacher trajectories and provider-side unrecorded reasoning are not included.

Each checkpoint directory contains:

- `agent_events.jsonl`: complete recorded structured event stream.
- `codex_events.raw.jsonl`: complete recorded native model/CLI event stream, including recorded assistant and tool events.
- `conversation.json`: recorded command/conversation representation; use the event streams for full recorded event coverage.
- `prompt.txt`, `target_user_prompt.txt`, `hint.txt`: actor context and hint.
- `snapshots/`: every recorded intermediate source and diff, preserving event-relative references.
- `workspace/{input.rs,candidate.rs,SKILL.md,TASK.md}`: input, endpoint and task/skill context.
- Result, validation, fidelity and runtime manifests: original recorded metadata, with the path substitutions below.

Personal host path prefixes are replaced by `/REDACTED/...` placeholders in logs and metadata. No events or messages are dropped or shortened. All Rust sources remain byte-identical. `manifest.json` records original and published SHA256 values for every file. Thus “raw” denotes the original event format, not byte-identical unredacted logs. Runtime path placeholders are historical metadata, not working filesystem links.

Credentials, hidden CLI state, runtime caches/tool installations, provider transport ledgers and full original teacher input are excluded. This is sufficient to inspect recorded actor actions and code snapshots; it is not a self-contained harness installation or an already-adapted SkillOpt minibatch. Preserve failed steps and validation labels when preparing training examples; final success does not certify every intermediate claim.

## Browse by checkpoint

| Task | Hint version | Continuations |
|---|---|---|
| IR | v1 | [CP01](ir/v1/CP01/), [CP02](ir/v1/CP02/), [CP03](ir/v1/CP03/), [CP04](ir/v1/CP04/), [CP05](ir/v1/CP05/), [CP06](ir/v1/CP06/) |
| IR | v2 | [CP01](ir/v2/CP01/), [CP02](ir/v2/CP02/), [CP03](ir/v2/CP03/), [CP04](ir/v2/CP04/), [CP05](ir/v2/CP05/), [CP06](ir/v2/CP06/) |
| AC | v1 | [CP01](ac/v1/CP01/), [CP02](ac/v1/CP02/), [CP03](ac/v1/CP03/), [CP04](ac/v1/CP04/), [CP05](ac/v1/CP05/), [CP06](ac/v1/CP06/) |
| AC | v2 | [CP01](ac/v2/CP01/), [CP02](ac/v2/CP02/), [CP03](ac/v2/CP03/), [CP04](ac/v2/CP04/), [CP05](ac/v2/CP05/), [CP06](ac/v2/CP06/) |
| AL | v1 | [CP01](al/v1/CP01/), [CP02](al/v1/CP02/), [CP03](al/v1/CP03/), [CP04](al/v1/CP04/), [CP05](al/v1/CP05/), [CP06](al/v1/CP06/), [CP07](al/v1/CP07/) |
| AL | v2 | [CP01](al/v2/CP01/), [CP02](al/v2/CP02/), [CP03](al/v2/CP03/), [CP04](al/v2/CP04/), [CP05](al/v2/CP05/), [CP06](al/v2/CP06/), [CP07](al/v2/CP07/) |

Validation: `python3 docs/hint-augmentation-20260916/traces/validate.py` from the repository root. No API calls.
