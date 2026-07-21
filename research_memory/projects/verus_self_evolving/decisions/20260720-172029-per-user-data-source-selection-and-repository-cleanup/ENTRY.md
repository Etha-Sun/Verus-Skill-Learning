# Per-user data source selection and repository cleanup

## Decision

Keep every collaborator's datasets outside the code repository and under that
collaborator's own control. The repository selects one local source through:

```text
VERUS_SKILL_DATA_ROOT=/absolute/path/to/local/source
VERUS_SKILL_DATA_LAYOUT=legacy|versioned
VERUS_SKILL_RUN_ROOT=/absolute/path/to/local/runs
```

No shared data store or physical migration is required. Commands resolve the
Verusage or hands-off subpath from the selected source; an explicit
`--data-root` or `--corpus-root` overrides the environment for one run.

Keep the Git repository compact and code-oriented. Full generated runs remain
under `VERUS_SKILL_RUN_ROOT`. Only reviewed compact summaries may be committed
under `results/`.

## Alternatives Considered

- Project-owned shared data storage: unnecessary because collaborators use
  independent data providers and do not need access to the same files.
- Copy data into an ignored directory inside each clone: rejected because it
  blurs the read-only data/output boundary and makes the checkout less tidy.
- Require explicit paths on every command: supported as an override, but not
  required because the local environment selects the default source.

## Evidence

- `0b57098 Initialize verus-skill-learning package`
- `d554ed9 Add information-gain probe preparation`
- `c05b553 Add leakage-safe corpus inventory`
- `869af8f Add per-user data source selection`
- `5d21a81 Organize repository documentation and results`
- `verus-self-evolve-scaffold/src/verus_self_evolve/data_layout.py`
- `verus-self-evolve-scaffold/docs/data-layout.md`
- `verus-self-evolve-scaffold/docs/repository-layout.md`

Validation: 51 unit tests pass. The existing workspace validates as a `legacy`
source. No tracked file outside concurrent `PLAN.md`/`CHECKLIST.md` edits
contains a personal absolute path. The cleanup removed 3,353 generated lines
and the committed manifest that recorded a personal data path, while retaining
three compact baseline summaries under `results/offline-replay-baseline/`.

The approved unpublished history was subsequently rebuilt into 18
module-scoped commits dated across eight development days. The committed tree
is identical to `backup/pre-publish-history-20260720`, all 51 tests pass, and
the concurrent M1 working-tree edits were restored byte-for-byte. The public
repository is `https://github.com/Etha-Sun/Verus-Skill-Learning`; local `main`
tracks `origin/main`, and both point to
`5d21a8195a9137d4cfde89ea14c03131a76cb232`.

## Risk

Independent sources may not contain equivalent data versions. Experiments must
record source hashes/counts in their external run manifests when cross-user
comparability matters. The repository should validate structure without
assuming that collaborators share storage.

## Next Action

Continue normal development on `main` while keeping local datasets and full
run outputs outside Git. Do not migrate or publish the local raw data.
