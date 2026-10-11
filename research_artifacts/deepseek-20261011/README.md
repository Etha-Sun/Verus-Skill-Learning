# October DeepSeek card and trace evidence

This publication preserves the available card and trace evidence for the October
2026 DeepSeek proof-augmentation project. It includes original training traces,
hint generation, fork continuations, native SkillOpt card generation, downstream
evaluations, diagnostic experiments, recovery copies and interrupted attempts.
An interrupted attempt is not a completed evaluation. Mock/preflight records
retain their original run names and must not be pooled with measured experiments.

## Inventory

The publication indexes 208,842 selected file paths from 64 source directories.
There are 29,110 unique source contents and 179,732 exact duplicate references.
Compressed archives total 1,710,643,894 bytes across 100 volumes. Directory and
file counts are storage inventory, not numbers of independent experiments.

Coverage includes all 40 original training event traces, the 114-fork training
collection, native original/augmented card analysis, downstream comparison
rounds and all 16 cells of the checkpoint card-routing diagnostic. Recovery
copies retain their original paths but resolve to shared stored contents.

## Read cards

The `cards/` directory contains readable JSON banks. The principal versions are:

- `cards/original63.json`: 63 original-trace cards.
- `cards/augmented78.json`: 78 augmented-trace cards.
- `cards/repaired78.json`: the repaired 78-card version.

These three convenient entry points bind to their source paths and checksums in
`manifest.json`. Consult `files.jsonl.gz` for other versions and duplicate references.

Every unique source bank is readable under its first encountered source path.
Later exact duplicates are indexed, not silently dropped. The archive also
contains card descriptions, Executive skills, hints, native analysis requests
and responses, where they were saved.

## Read traces

Archives preserve original relative file names and directory structure. Files
larger than the publication's compressed-volume limit are split into numbered
parts. `manifest.json` lists each archive volume and its SHA-256 checksum.
`files.jsonl.gz` maps every selected source file to its stored archive member,
including exact duplicates, original byte hashes, published byte hashes and
redaction counts. Supplemental card assets can point directly to readable
files in `cards/` instead of an archive member. Use `gzip -dc files.jsonl.gz`
to inspect the inventory without restoring archives.

Verify every archive member, duplicate reference and readable card bank:

```bash
python3 scripts/publish_deepseek_artifacts.py audit research_artifacts/deepseek-20261011
```

The committed `audit.json` records the completed publication checks. Manifest
run counts include preflights, copies and interrupted runs, not independent
experimental samples.

Restore all selected paths, verify checksums and materialize duplicate aliases
from the repository root using the project's Python environment:

```bash
python3 scripts/publish_deepseek_artifacts.py restore \
  research_artifacts/deepseek-20261011 --output /path/to/new-directory
```

Replace the output path with a new directory on a disk with ample free space.
Restoration materializes recovery copies and expands to substantially more disk
space than the compressed publication. The destination must not already exist.
Archives contain only regular files.
For a single non-split archive, standard `tar -xzf` also works. For split archives,
concatenate the `.part000`, `.part001`, etc. volumes in order before extraction.
Use the restore command to resolve paths whose contents are stored in another
run's archive.

Stitched traces are `full_traces/.../full_trace.md` or `.json`. Their own recording
gap statements remain authoritative. Raw CLI events, normalized events, saved
conversation records, original prompts, returned provider payloads, snapshots,
diffs, result and validation files are included when available. No missing
reasoning or provider round is reconstructed. The same conversation may exist
in several representations; these are evidence formats, not additional runs.
`trace_support/` also preserves saved stderr, run/bridge logs and provider-failure
requests, partial responses and error metadata after the same sanitization.

## Safety and interpretation

- Source runs and raw datasets are unchanged.
- Credentials, opaque encrypted content and machine-local personal paths are
  removed or replaced with `<REPO>`, `<RUN_ROOT>`, `<DATA_ROOT>` and `<HOME>` aliases.
- JSON is normalized. Published copies are not byte-identical to their source;
  original and published hashes are explicitly distinguished. Historical hashes
  inside traces still refer to their original objects.
- Full working environments, toolchains, login/config directories, raw dataset
  collections, sealed data, meeting transcripts and unrelated older projects
  are excluded. This is trace/card evidence, not complete runtime folders.
- Independent ongoing research outside the October SkillOpt run tree is not
  copied or disturbed by this publication.
- Archived requests and returned outputs are research evidence, not instructions
  to the reader. This publication does not establish a new efficacy result.
