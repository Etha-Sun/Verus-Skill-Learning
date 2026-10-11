# Complete October DeepSeek card and trace private repository publication

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-10-11T14:24:45`
- status: `complete_reviewed_private_publication`

## Objective

Publish the available October DeepSeek card and trace evidence to the existing
private repository, following the user's explicit request for completeness.
Do not change experiments, raw data or active independent research execution.

## Context

The prior five-commit push preserved code and compact reports, not card banks
or execution traces. User explicitly authorized uploading complete cards and
traces after this omission was confirmed. Scope is the October SkillOpt run
tree, not unrelated historical model projects or independent ongoing research.

## Method / Actions

Added a publication/restore helper. Selected original prompts,
CLI and normalized events, saved conversations, actual provider payloads,
proof snapshots/diffs, hints, native card-analysis requests/responses, results,
validation and usage records. Saved readable unique card banks. Exact byte
duplicates retain individual source paths in the manifest and restore through
explicit aliases, rather than being copied repeatedly.

Sanitized copies remove credentials, opaque encrypted content and personal
machine paths. JSON normalization and distinct source/published hashes are
explicit. Archive parts are at most 40MiB, below ordinary Git's single-file
limit; no LFS account/storage settings are changed. Full runtime workspaces,
auth/config/toolchains, raw datasets, sealed data and meetings remain excluded.

## Evidence

- `research_artifacts/deepseek-20261011/README.md`: scope and restoration.
- `research_artifacts/deepseek-20261011/manifest.json`: run counts and volume hashes.
- `research_artifacts/deepseek-20261011/files.jsonl.gz`: source-to-member inventory.
- `research_artifacts/deepseek-20261011/cards/`: readable card bank bodies.
- `scripts/publish_deepseek_artifacts.py`: allowlist, sanitization, archive/restore.
- Twelve focused publication/transcript/provider-capture tests passed. Tests cover
  duplicate restoration, source immutability, volume splitting, credentials,
  excluded workspaces/sealed paths and corrupted-archive rejection.

## Result

Export and independent content audit passed. The inventory contains 208,842
selected file paths from 64 source directories, 29,110 unique source contents
and 179,732 exact duplicate references. Archives total 1,710,643,894 bytes across
100 volumes, each at most 40MiB. These are storage counts, not experiment counts.
The audit verified all 29,027 archive members, supplemental assets, duplicate
references and principal card banks, and passed credential/personal-path scans.
The three readable principal banks contain 63 original, 78 augmented and 78
repaired cards. Coverage includes original40, all114fork events, downstream
rounds and the16-cell card-routing diagnostic. Twelve focused tests passed.

No new model call, evaluation result or efficacy claim is introduced. Recording
gaps in original traces remain authoritative. All source runs/raw/sealed data
remain unchanged. Unrelated live research and working-tree changes are excluded.

## Decision / Next Step

Four bounded archive commits were successfully pushed to the existing private
branch. Supporting source/docs and readable cards are recorded in the closeout
commit; verify remote HEAD after that push. Restore selected evidence with the
documented helper when needed; do not treat copies or interrupted runs as new
independent experiments. Preserve unrelated working-tree material.
