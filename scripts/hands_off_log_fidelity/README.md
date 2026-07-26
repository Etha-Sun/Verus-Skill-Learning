# Hands-Off Log Fidelity Audit

These scripts audit the structural fidelity of the historical Verus hands-off
agent logs. They distinguish visible markers from retained payloads and keep
tool, edit, verifier, usage, and reasoning-token evidence separate.

The authoritative full-corpus result covers 9,383 primary logs matching
`claude_sonnet_gpt5/verified-*/*/*.log`. The compact report is:

- `docs/hands_off_log_fidelity_audit.zh.md`

## Run

Set the repository-local data and run roots described by
`.agent-context.local.md`, then run from the repository root:

```bash
AUDIT_OUT="${VERUS_SKILL_RUN_ROOT}/hands_off_log_fidelity_audit/results"
CORPUS_ROOT="${VERUS_SKILL_DATA_ROOT}/claude_sonnet_gpt5"
MANIFEST="${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/corpus_manifest.jsonl"

python3 scripts/hands_off_log_fidelity/audit_logs.py \
  --corpus-root "${CORPUS_ROOT}" \
  --manifest "${MANIFEST}" \
  --out-dir "${AUDIT_OUT}"

python3 scripts/hands_off_log_fidelity/audit_code_edits.py \
  --corpus-root "${CORPUS_ROOT}" \
  --features "${AUDIT_OUT}/per_log_features.jsonl" \
  --out-dir "${AUDIT_OUT}"

python3 scripts/hands_off_log_fidelity/audit_line_composition.py \
  --corpus-root "${CORPUS_ROOT}" \
  --features "${AUDIT_OUT}/per_log_features.jsonl" \
  --out-dir "${AUDIT_OUT}"

python3 scripts/hands_off_log_fidelity/validate_audit_outputs.py \
  --results-dir "${AUDIT_OUT}"
```

The corpus and manifest are read-only inputs. Generated JSONL, JSON, and CSV
files must stay below `VERUS_SKILL_RUN_ROOT`; do not commit the per-log indexes.

## Completeness Contract

Do not collapse fidelity into one `complete` flag. At minimum, retain and
filter on:

- `model_family` and `log_format`;
- tool-call and tool-result presence versus complete payload;
- exact diff-box Edit versus summary-only Edit, Create, failed Edit, or o4
  `file_change` metadata;
- explicit verifier result versus a visible call or narrative claim;
- paired original/final artifacts;
- incremental-history replayability;
- usage availability and reasoning-token availability.

For skill-learning data:

- Use exact diff-box edits for local edit-action analysis.
- Use paired original/final files for the final net transformation.
- Use both when available, but never substitute final net diff for the missing
  incremental trajectory.
- Treat visible narration as narration, not hidden reasoning.
- Exclude authentication failures, self-overwritten logs, and records whose
  required payload is absent.
- Redact secrets before any raw command output enters prompts, training data,
  or public artifacts.

## Frozen Full-Corpus Findings

- Tool-call markers occur in 8,447/9,383 logs (90.0%), but only 859 (9.2%)
  have all started shell commands paired with uncompressed completed JSONL
  events.
- Of 75,904 successful Edit events, 60,581 (79.81%) retain an exact line-level
  diff. Among the 60,740 Edit events that show a diff box, 60,581 (99.74%)
  match the declared added/deleted line counts.
- All 5,977 UI Create events omit their body, and all 4,000 o4 `file_change`
  events omit patch text.
- Original/final files are paired for 9,031 logs (96.3%), allowing exact final
  net diff recovery but not intermediate-state replay.
- Strict structured verifier trajectories occur in 735 logs (7.8%); explicit
  verifier payloads occur in 3,259 (34.7%).
- No log contains an explicit thinking/reasoning-token field. Usage is present
  in 9,268 logs (98.8%), but visible narration and output usage are not hidden
  reasoning tokens.
