# Delivered runtime components

`react_agent/` is the local ReAct runtime used by `verus_agent/`.
`verus_agent/` contains the VeruSAGE-adapted hands-off harness, IronKV training/evaluation runners, and the semantic-v4 consolidation implementation.
`skill_evolver/` is the Trace2Skill hierarchical MAP/REDUCE evolver used for the native-compression condition.
`analysis/` contains the two parsers directly imported by the training runner.

The delivery intentionally contains no local dataset, verified answer, full run, API payload, or credential. To execute the portable split/qualification scripts, set `IRONKV_DATASET_DIR`, `VERUSAGE_TASK_ROOT`, `VERUS_BIN`, and `LYNETTE_BIN` to local paths. Model credentials and external run roots are likewise local configuration, not repository artifacts.

## Codex CLI + DeepSeek harness

`verus_agent/codex_harness/upstream_skillopt/` contains the audited native
Responses bridge used to connect Codex CLI to DeepSeek V4 Pro. The bridge
records provider-returned usage per task in `bridge_calls.jsonl`; it does not
record the API key. The runner supports the delivered semantic-v4 skill,
native-compressed skill, and no-skill condition.

The bridge is ported from `feature/skillopt-verusage-20260812` at
`d33b1ecbe4042c5ae282e15715366fbaa41b2186`; only its Python import path is
adapted to this delivery package.

Put local credentials in an ignored `.env.deepseek` file (or export the same
variables):

```dotenv
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Run from this `code/` directory with a frozen 15-task public-source selection:

```bash
PYTHONPATH=. python -m \
  verus_agent.experiments.ironkv_claude_to_deepseek_77_77.run_strict_heldout15_semantic_v4_codex \
  --condition semantic-v4 \
  --selection-root /path/to/frozen-selection \
  --env-file ../.env.deepseek \
  --timeout-seconds 900
```

`--selection-root` must contain `hard15_tasks.jsonl` and
`hard15_selection.json`; task sources are checked against their frozen SHA-256
hashes before execution. Override local tools with `--codex-bin`,
`--verus-bin`, and `--lynette-bin`. Compact progress for two output roots is
available through `python -m verus_agent.codex_harness.watch_pair_status`.
