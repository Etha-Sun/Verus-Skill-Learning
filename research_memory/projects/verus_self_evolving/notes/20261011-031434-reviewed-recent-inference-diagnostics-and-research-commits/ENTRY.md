# Reviewed recent inference diagnostics and research commits

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-10-11T03:14:34`
- status: `complete_local_publication`

## Objective

Save recent reviewed implementation and compact research results in at most five
local commits. Do not push, launch experiments, change active research execution,
or include unrelated historical files, transcripts, credentials or runtime data.

## Context

User requested an unhurried local commit after checking what remained uncommitted.
The working tree also contains older August/September research and private local
files. Those are deliberately excluded. Canonical memory stays in this repository;
the external raw-data and run roots remain untouched.

## Method / Actions

Reviewed tracked diffs, recent source files, test coverage and compact documents.
Scanned publication candidates for credentials, personal absolute paths, binary
or large files and unintended runtime symlinks. Used explicit file lists, never
`git add .`. Independent integration is source-only; its ignored runtime link is
not committed. No running controller, daemon, actor or guardian was changed.

Publication groups:

1. `c9bb14b`: supplied-trust and diagnostic-first proof repair, local probes/tests.
2. `f35f011`: paired Executive validation, transport-only recovery and audit/tests.
3. `17c0c4d`: optional card query, four-arm checkpoint diagnostic and token audits.
4. `f7a4600`: independent trace research adapters, brief and lifecycle guardian/tests.
5. Documentation commit containing reviewed recent results, reports, this receipt
   and canonical memory. The Git log is authoritative for its final commit hash.

## Evidence

Focused checks, with `PYTHONPATH` selecting the existing source packages:

```text
python -m pytest -q tests/test_guidance_failure_probes.py
  tests/test_diagnostic_first_skill.py tests/test_card_revision_validation_driver.py
  tests/test_executive_revision_validation.py tests/test_full_executive_validation.py
  tests/test_single_executive_validation.py tests/test_card_routing_diagnostic.py
  tests/test_success_timeout_statistics.py skill-evolution-pilot/tests/test_codex_runner.py
  trace-experience-autoresearch/test_watch_controller.py
55 passed in 1.70s
```

Expanded regression: `tests`, `skill-evolution-pilot/tests`,
`skillopt-verusage/tests`, and the guardian test. Initial sandbox run:
1048 passed, 11 failed, one dependency warning, 135.08s. Failure classification:

- Nine failures require a loopback HTTP socket forbidden by the sandbox. The
  corresponding ten-test mock-only rerun outside it passed in4.64s. No paid API
  calls were made by these tests.
- Two old Trace2Skill tests hash every vendor-tree file. Five ignored Python
  cache files make that local hash differ. All106 tracked vendor files and the
  producer are byte-identical to the prior HEAD. Both tests pass in0.05s on a
  clean tracked-only archive with bytecode disabled. No vendor code, fixed hash,
  existing cache file or historical result was changed to obtain a pass.

Do not describe this as one clean full-suite run. Git whitespace and staged
content safety checks are separate from scientific efficacy evidence.

## Result

Recent implementations and evidence are preserved without new model calls or
changes to scientific outcomes. The comprehensive report still states that
stable augmentation utility is unproven and the search tool was unexercised.
Conversation clarification: excluding four development examples, the repair
comparison is11/16 to12/16, all-attempt input tokens down6.4%, output down14.2%,
estimated cost down9.6%, with revised body reads in1/16 episodes. This is not
the15 jointly-successful-pair statistic and is not a proven retrieval effect.

## Decision / Next Step

Rebuild memory indexes, stage only entries present in the publication, and verify
the final commit contents. Working indexes may retain links to deliberately
uncommitted historical entries; the committed index must not acquire those links.
Original/sealed/raw data, complete external runs, meeting transcripts and local
machine context are not committed. No remote push requested or performed.
