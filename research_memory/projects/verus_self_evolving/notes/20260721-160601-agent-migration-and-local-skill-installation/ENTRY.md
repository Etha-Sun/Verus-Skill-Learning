# Agent migration and local skill installation

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-21T16:06:01`
- status: `complete`

## Objective

Complete the agent-context migration into the GitHub-synchronized repository,
correct the independent audit findings, and install project-local ARIS skills
without coupling them to the deprecated workspace or public Git history.

## Context

- Migration audit:
  `research_memory/projects/verus_self_evolving/notes/20260721-140725-repository-architecture-boundary-review/ENTRY.md`
- Active control files: `PLAN.md` and `CHECKLIST.md`
- Repository rules: `AGENTS.md`
- Machine-local configuration: ignored `.env` and `.agent-context.local.md`

## Method / Actions

- Corrected the local Lynette executable path and removed the false unavailable
  statement from active memory.
- Replaced mixed M0/M1 control documents with a focused R041 train-only prompt
  distillation contract.
- Added ignore rules for local ARIS skill links and manifests.
- Cloned the ARIS upstream into an external stable tools directory, reset its
  origin to the public upstream, and installed its `skills-codex` package with
  `--no-doc`.
- Preserved unrelated concurrent source, test, and documentation changes.
- Made the versioned-layout unit test explicitly select its intended layout so
  a caller's legacy `.env` cannot change the test semantics.

## Evidence

- External ARIS checkout:
  `<external-tools-root>/Auto-claude-code-research-in-sleep`
- External ATLAS checkout: `<external-tools-root>/ATLAS`, pinned at
  `afbf010117cecb87ca23f55999b82e9054bcbdef`.
- Project-local skill directory: `.agents/skills/`
- Local installer manifest: `.aris/installed-skills-codex.txt`
- Installed links: 80
- Broken links: 0
- Links targeting the deprecated workspace: 0
- Lynette executable version: 0.0.0
- Full core unit suite: 54 tests passed with the real local `.env` loaded.
- Standalone ATLAS adapter suite: 5 tests passed against the external pinned
  checkout.
- Data-layout validation: `ok=true`; the external run root exists and is
  writable, with no missing directories or overlap issues.
- Installer reconcile dry-run: 80 reused, 0 create/update/remove/conflict.
- Cold-start static contract, memory index, ASCII-path, diff-check, and
  public-safety scans passed.

## Result

The active repository now has self-contained startup rules, coherent R041
execution controls, working local tool paths, and project-local ARIS skills
whose upstream no longer depends on `verusys-result`. System and user Codex
skills remain globally available and were not duplicated. Local absolute paths
and symlinks are ignored rather than committed.

## Decision / Next Step

R041 remains the next research action; R042 remains blocked until H1/H2 are
frozen and frontier authentication is available. Reconcile project skills
after updating the external ARIS checkout.

No raw or sealed trace content was modified. Generated outputs remain outside
the Git repository under `VERUS_SKILL_RUN_ROOT`.
