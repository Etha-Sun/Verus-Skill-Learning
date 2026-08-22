# SkillOpt multi-file and Claude skill support audit

## Scope

Audit the current public Microsoft SkillOpt repository to determine whether it
still evolves one file, whether it can optimize Anthropic-style skill bundles
with `references/`, `scripts/`, and `assets/`, and whether any merged or open
pull request has closed that gap.

## Sources

| source | link | why it matters |
|---|---|---|
| SkillOpt `main`, audited at `bdfdc30a8e17309c06cdbe8449f01bdecc120203` | https://github.com/microsoft/SkillOpt/commit/bdfdc30a8e17309c06cdbe8449f01bdecc120203 | Current implementation and documentation on 2026-08-21 America/Chicago |
| SkillOpt README and skill-document guide | https://github.com/microsoft/SkillOpt/blob/main/README.md | Defines the paper/research artifact as one `best_skill.md` and the trainable state as one skill document |
| Issue 54 | https://github.com/microsoft/SkillOpt/issues/54 | Maintainer acknowledges that code, scripts, references, and assets are not supported by the released single-file example and promises a richer future package |
| Issue 145 | https://github.com/microsoft/SkillOpt/issues/145 | Direct prompt-optimization criticism; maintainer explicitly says the released system optimizes one `SKILL.md` and promises whole-folder optimization |
| PR 212 | https://github.com/microsoft/SkillOpt/pull/212 | Merged end-to-end multi-skill fan-out, one independently gated `SKILL.md` per hinted skill |
| PR 241 | https://github.com/microsoft/SkillOpt/pull/241 | Merged containment hardening confirms fan-out adoption targets exact `<name>/SKILL.md` files inside recorded skill roots |
| PR 134 | https://github.com/microsoft/SkillOpt/pull/134 | Merged Superpowers adapter loads a candidate through a real Claude plugin checkout but overlays only one candidate `SKILL.md` |
| Anthropic skill-creator | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Defines the reference bundle shape: required frontmatter-bearing `SKILL.md` plus optional `scripts/`, `references/`, and `assets/` |

## Method Patterns

The research engine remains unambiguously single-document. Its state and gate
operate on Python strings, the initial state is one Markdown path, and the
deployed output is one `best_skill.md`.

SkillOpt-Sleep now has two separate improvements that should not be conflated
with multi-file bundle evolution:

1. It can create or preserve a loadable agent `SKILL.md` with YAML `name` and
   `description` frontmatter. In that narrow packaging sense, it can operate on
   a Claude/Codex/Cursor/Devin-style skill entry file.
2. PR 212 added opt-in multi-skill fan-out. A night groups evidence by skill
   hint, resolves several existing skill directories, reads each exact
   `SKILL.md`, consolidates and gates each document separately, then stages and
   adopts selected `SKILL.md` replacements.

The current resolver ends at `<root>/<name>/SKILL.md`; the cycle reads only that
file's bytes; `SkillProposal` contains one text string and one live file path;
staging requires the destination basename to be exactly `SKILL.md`; adoption
replaces only those files. Repository-wide searches found no bundle manifest,
reference/resource-file candidate model, per-file edit operation, reference-link
validation, script execution gate, or atomic directory publication path.

PR 134 is the closest runtime-realism improvement: it clones a pinned
Superpowers plugin, overlays a single candidate file at
`skills/<name>/SKILL.md`, and invokes Claude with `--plugin-dir`. Companion
files from the baseline checkout can participate in execution, but SkillOpt
does not read, propose, or mutate them as trainable state.

The full open-PR inventory at audit time contained eight PRs (114, 118, 152,
153, 238, 242, 244, 246). None implements whole-folder or reference evolution.
An all-PR title/body search for multi-file, entire skill folder, auxiliary
files, `references/`, code/assets, and skill package returned no implementing
PR. Issues 54 and 145 were closed after maintainer promises, not after a linked
implementation.

## Takeaways For This Project

1. The fair current description is: core SkillOpt is still a single-document
   optimizer; SkillOpt-Sleep can fan out across multiple single-file skills and
   can preserve a valid `SKILL.md` envelope.
2. Do not say upstream now optimizes Anthropic-style skill bundles. The promised
   `SKILL.md + references + scripts/assets` release has not landed.
3. If the Verus workstream needs reference cards or executable helpers, model
   the deployable artifact explicitly as a versioned bundle manifest with
   per-file hashes and operations. Gate and publish the entire bundle, including
   dangling-link checks, path containment, script safety/tests, and rollback;
   do not encode the feature as several unrelated `SKILL.md` fan-out targets.
4. PR 212 is still useful prior art for independent routing, per-target baselines,
   held-out gates, review-driven adoption, hashes, locks, and rollback.

## Gaps / Risks

- The repository is unusually active; this negative result is pinned to
  `bdfdc30` and the eight open PRs visible on 2026-08-21.
- This was a code/interface audit, not a live execution of the new fan-out path.
- “Claude-type” is ambiguous. If it means only a frontmatter-bearing file at
  `.claude/skills/<name>/SKILL.md`, SkillOpt-Sleep supports it. If it means the
  full progressively disclosed directory artifact, it does not.
- No raw or sealed Verus dataset was read, modified, moved, or copied.

## Decision / Next Action

Treat upstream multi-file support as unavailable until a PR introduces a
directory-level artifact contract and the corresponding end-to-end tests. If
the local project pursues this direction, first specify a minimal bundle model
and leakage-safe whole-bundle gate; re-check upstream immediately before
implementation in case the promised release lands.
