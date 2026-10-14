Solve the Verus proof task in candidate.rs from scratch.

Visibility and editing rules:
- Treat input.rs as immutable and edit only candidate.rs.
- Read TASK.md. Read SKILL.md only if it exists.
- Outside this workspace, you may inspect only the installed vstd source
  directory `${VERUS_SKILL_RUN_ROOT}/data-augment-20260911/no-reference-isolated-v2/verus-toolchain/vstd` read-only, including its source subdirectories.
  This exception does not permit editing library files or following symlinks
  outside that directory. Do not inspect any other outside files, repository history, prior runs,
  reference proofs, environment variables, credentials, or network resources.
- Make every code edit through the Codex file-edit/patch tool. Do not modify
  candidate.rs with shell redirection, sed, perl, Python, cp, mv, or a generated
  editing script.

Proof rules:
- Preserve executable behavior, signatures, requires, ensures, and decreases.
- Add or edit proof-only assertions, lemmas, invariants, triggers, and proof blocks.
- Never introduce assume, admit, external_body, new axioms, or verification bypasses.
- Pre-existing trusted declarations in input.rs are supplied background:
  preserve their attributes, signatures, contracts, and bodies. You may
  call them through their existing contracts when their premises hold.
  Repair the unverified target proof, not the supplied trusted background.
- Fix parse, type/mode, and scope errors before changing proof strategy.
  Make the smallest supported correction (ordinary assertions use
  assert(condition);), then re-run Verus before expanding the proof.
- Run `./tools/run_verus.sh` after edits and use its complete diagnostics.
- Run `./tools/run_lynette.sh` before finishing.
- Continue exploration until both checks pass or useful
  approaches are exhausted.

Leave the complete best candidate in candidate.rs. In the final response,
report verification status and strategies attempted. Do not omit failed steps.
