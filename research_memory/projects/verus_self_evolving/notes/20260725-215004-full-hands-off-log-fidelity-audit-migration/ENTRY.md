# Full hands-off log fidelity audit migration

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-25T21:50:04`
- status: `complete`

## Objective

Migrate the full-corpus hands-off log-fidelity audit into this repository,
preserve its validated parsers and conclusions, and correct the earlier
30-trace R040 sample interpretation.

## Context

The earlier phase-segmentation note inspected only the leakage-safe R040
selection of 30 traces. That sample was appropriate for a pilot parser and
phase-design discussion, but it was not evidence for corpus-wide completeness.

The authoritative audit instead uses the M0 inventory of 9,383 primary
hands-off logs:

- corpus: `${VERUS_SKILL_DATA_ROOT}/claude_sonnet_gpt5/`
- manifest:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m0/corpus_manifest.jsonl`
- prior pilot:
  `research_memory/projects/verus_self_evolving/notes/20260724-165940-hands-off-verifier-anchored-phase-segmentation/ENTRY.md`

## Method / Actions

- Read the full Chinese report, metadata, three global summary files, three
  per-log indexes, four audit scripts, and five representative log families.
- Verified the frozen outputs with the six-log regression suite and global
  cross-checks.
- Migrated the parsers and validator without changing their logic.
- Migrated the reviewed compact report, but did not copy raw logs, per-log
  indexes, token tables, or the full derived-results directory into git.
- Reframed downstream selection around separate fidelity fields rather than a
  single `complete` flag.

## Evidence

- Report: `docs/hands_off_log_fidelity_audit.zh.md`
- Code and usage contract: `scripts/hands_off_log_fidelity/`
- Frozen external derived results:
  `${VERUS_SKILL_DATA_ROOT}/research_memory/projects/verus_self_evolving/notes/20260724-181030-hands-off-log-fidelity-audit/results/`
- Regression result:
  `PASS: 6 sample logs and global cross-checks`
- Independent edit and line-composition parsers agree on all 1,833,283
  displayed changed logical lines with zero per-log mismatches.

## Result

The full audit covers 9,383 logs, not 30:

- Tool-call markers occur in 8,447 logs (90.0%), while only 859 (9.2%) have
  all started shell commands paired with uncompressed completed JSONL events.
- Of 75,904 successful Edit events, 60,581 (79.81%) retain an exact line-level
  diff. Within the 60,740 events that display a diff box, 60,581 (99.74%)
  match the declared added/deleted line counts. Therefore the prior broad
  statement that code edits are usually incomplete was wrong.
- The important edit losses are format-specific: 15,164 successful Edit
  events are summary-only; all 5,977 UI Create events omit their bodies; and
  all 4,000 o4 `file_change` events omit patches.
- Paired original/final code exists for 9,031 logs (96.3%), so exact final net
  diffs are usually recoverable even though no format guarantees an end-to-end
  replayable incremental history.
- Strict structured verifier trajectories occur in 735 logs (7.8%); explicit
  verifier result/error payloads occur in 3,259 (34.7%).
- No log contains an explicit thinking/reasoning-token field. Usage exists in
  9,268 logs (98.8%), but visible narration and output-token totals must not be
  interpreted as hidden thinking tokens.

Format interpretation:

- rendered UI: tool markers and diff-box edits are often informative, but
  tool/verifier results are frequently collapsed;
- plain/mixed: fidelity varies materially by model/result directory and must
  be classified per log;
- o4 JSONL: shell command/result and verifier events are most structured, but
  file changes have path/kind only and no patch.

## Decision / Next Step

For trajectory and skill-learning analyses:

1. Use per-log fidelity fields instead of assuming one uniform hands-off
   format.
2. Use exact incremental diff-box edits for local edit-action analysis.
3. Use paired original/final artifacts for exact final net diff; use both
   views when available, but never present net diff as incremental history.
4. Treat summary-only Edit, Create, and o4 `file_change` as incomplete edit
   payloads.
5. Treat visible narration as visible narration, not hidden reasoning.
6. Use verifier-anchored phases only when verifier payload and code-state
   evidence meet the analysis-specific contract; otherwise emit a weaker
   provenance label.
7. Keep the 30-trace R040 phase study as a pilot, not a population audit.
