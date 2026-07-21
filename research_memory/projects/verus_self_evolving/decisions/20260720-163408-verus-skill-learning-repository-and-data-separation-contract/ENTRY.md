# verus skill learning repository and data separation contract

> Superseded in part on 2026-07-20 by the per-user data source decision. The
> code/data Git boundary remains valid, but shared storage and physical data
> migration are no longer planned.

## Decision

Create the new code repository under the name `verus-skill-learning` and keep
full Verus trajectory corpora and large run outputs outside Git. The repository
will contain reproducible code, tests, configs, documentation, small fixtures,
data schemas, versioned manifests, and compact result summaries.

Use two collaborator-configured roots instead of machine-specific paths:

```text
VERUS_SKILL_DATA_ROOT=/absolute/path/to/verus-skill-learning-data
VERUS_SKILL_RUN_ROOT=/absolute/path/to/verus-skill-learning-runs
```

The shared data root follows this versioned layout:

```text
verus-skill-learning-data/
  verusage-batch-v1/
    all_batch_results-cyy-claude/
    all_batch_results-cyy-claude-s4/
    all_batch_results-cyy-gpt5/
    all_batch_results-cyy-o4mini/
  handsoff-v1/
    verified-anvil/
    verified-atmo/
    verified-ironkv/
    verified-memory-allocator/
    verified-node-replication/
    verified-nrkernel/
    verified-storage/
    verified-vest/
  eval/
```

Commands continue to take explicit paths. For example,
`--data-root "$VERUS_SKILL_DATA_ROOT/verusage-batch-v1"`,
`--corpus-root "$VERUS_SKILL_DATA_ROOT/handsoff-v1"`, and
`--out-dir "$VERUS_SKILL_RUN_ROOT/<run-id>"`. No committed config may contain a
personal absolute path. Raw corpora remain read-only, and outputs must remain
outside all corpus roots.

## Alternatives Considered

- Keep code and all data in `YangChenyuan/verusys-result`. Rejected for new
  work because that repository already tracks about 309,688 files and has a
  1.22 GiB Git pack; it is useful as a private legacy archive, not as the active
  development repository.
- Put data in `verus-skill-learning/data/` and ignore it. Rejected as the main
  contract because it encourages accidental writes and makes clone-local paths
  ambiguous. A local symlink may be used by an individual, but it is not the
  canonical interface.
- Use Git LFS for every trace and run artifact. Rejected because LFS does not
  solve the very large small-file count, sealed-test access control, or frequent
  derived-output churn.

## Evidence

- Core repository content excluding `.git` and `runs/` is about 728 KiB; the
  `src/`, `tests/`, `docs/`, `configs/`, and `scripts/` files total about 1 MiB.
- The current CLI already accepts explicit `--data-root`, `--corpus-root`,
  `--out`, and `--out-dir` arguments.
- `handsoff_m0.py` rejects outputs placed inside a raw corpus.
- Existing frozen split manifest:
  `verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/split_manifest.json`.
- Existing code repository: `verus-self-evolve-scaffold/`.

## Risk

The main failure modes are collaborators using different unrecorded corpus
versions, accidentally reading sealed-test content, or committing raw data and
large token-level outputs. Mitigation requires a committed data contract,
dataset-version manifests with hashes, a layout validation command, and strict
`.gitignore` rules before the new repository is published.

## Implementation (2026-07-20)

Implemented in the existing nested code repository with six local commits:

- `71bfb61 Add information-gain scoring pipeline`
- `f32effb Add leakage-safe hands-off pipeline`
- `dbcdcff Record hands-off execution plan`
- `3effb78 Define external data layout contract`
- `4b03f9d Configure verus-skill-learning package`
- `9cac335 Document repository and data migration`

Main artifacts:

- `verus-self-evolve-scaffold/docs/data-layout.md`
- `verus-self-evolve-scaffold/docs/repository-plan.md`
- `verus-self-evolve-scaffold/configs/data_registry.example.json`
- `verus-self-evolve-scaffold/src/verus_self_evolve/data_layout.py`
- `verus-self-evolve-scaffold/.env.example`

Validation: 49 unit tests pass; Python compilation, JSON parsing, shell syntax,
and Git whitespace checks pass. The checker accepts the existing workspace with
the `legacy` profile when the run root is outside the legacy data root. No raw
data was moved or modified. The pre-split three-commit history is retained on
`backup/pre-split-20260720`, and its tree is identical to the six-commit
history. Concurrent M1 edits to `PLAN.md` and `CHECKLIST.md` were restored after
the history split and remain uncommitted.

## Migration Audit (2026-07-20)

The four read-only `all_batch_results-cyy-*` corpora plus
`claude_sonnet_gpt5` occupy about 4.4 GiB across 253,715 files. The current
filesystem has about 153 GiB available and ample free inodes, so storage
capacity does not prevent migration. Candidate personal staging directories do
not yet exist. Existing ownership is `ycsun:nogroup`, which does not establish
the intended collaborator access or the isolation required for sealed MA/NR
evaluation data.

Migration should therefore proceed after the project-owned target and ACLs are
chosen. Use a non-destructive copy, generate and compare manifests/hashes,
validate the versioned layout, switch `VERUS_SKILL_DATA_ROOT`, and freeze the
legacy source. Do not delete the original data as part of this migration.

## Next Action

Follow the superseding per-user data source decision. After a secret/license
audit, create the private GitHub repository `verus-skill-learning`, add it as
the code repository's remote, and push the reviewed commits. Do not migrate or
publish local raw data.
