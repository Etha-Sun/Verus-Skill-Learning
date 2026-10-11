# Diagnostic-first Executive six-task repeated development pilot

## Objective and status

User authorizes the proposed fresh 24-episode comparison. All24episodes complete
after fresh independent Astra approval. Results and settled integrity audit in
RESULTS.md. Initial9/12 versus diagnostic11/12 budgeted dual-pass; actor time25%
lower, estimated cost22.6%lower. Favorable development direction, not stable or
general efficacy. No new run started for result inspection.
See PLAN.md for frozen protocol and CHECKLIST.md for progress.

Question: does the new Executive avoid observed diagnostic/scope detours more
consistently than initial Executive under the same corrected task prompt?
Primary metric is within-budget Verus AND Lynette pass, not read frequency.

## Artifact pointer and reproducibility

External root: VERUS_SKILL_RUN_ROOT/skillopt-verusage/executive-pilot-20261009-NYYmFA/.
validation_contract.json SHA256:
474db01d0957203524e93ed53d17d0e10e8d9da2462ca279ce8a328a71dd6bb3.
24 unique keys; balanced arm ordering reversed on second repetition. Six fixed
seen validation problems, 12 episodes/arm, no historical result reuse. Old bundle
exactly reproduces frozen repaired78 control; new bundle differs only in Executive.
Both use same corrected TASK, card bodies/index/reader and read-only vstd permission.
Code: scripts/validate_executive_revision.py; shared driver changes only optional
repeat key suffix, preserving historical keys. Initial seed and frozen runs intact.

Prepare invocation: environment VERUS_SKILL_RUN_ROOT configured to external root,
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt;
vrl Python scripts/validate_executive_revision.py --prepare --config
RUN_ROOT/skillopt-verusage/train38-hindsight-native-20261007-aQfE7o/config.json
--baseline RUN_ROOT/skillopt-verusage/retrieval-mechanism-audit-20261009-i8ZabJ/guidance-validation/control
--old-seed skillopt-verusage/skills/initial.md
--new-seed skillopt-verusage/skills/diagnostic-first-v1.md
--descriptions skillopt-verusage/review/augmented78_revision.json --output EXTERNAL_ROOT.
Run invocation replaces prepare/seed/baseline/descriptions options with
--review EXTERNAL_ROOT/review.json, retaining config/output.

## Verification and evidence boundary

22 targeted pytest tests pass: repeated schedule, package equality, common prompt,
matrix completeness/duplicate detection, late-pass separation, old review/default
driver, retrieval guidance, diagnostic-first policy and task prompt tests.
Another40 probe/card-bank/isolation tests pass, total62 across disjoint invocations.
An initial optional test command named a nonexistent path and collected zero tests;
corrected discovery command passes40. Astra independently passes9 overlapping tests.
git diff --check passes. 1.9TB disk available before preparation.
No new card learning, forced reads, reference proof, ordinary retry, or sealed-test
access. Two repetitions are stochastic runs, not two new independent problems;
no inferential/general solved-rate claim. No fixed random seed is exposed by this
provider runner. Results must be interpreted as development evidence.

Environment bash_exec/artifact APIs unavailable; exec_command/hash/memory fallback
used, no evidence-graph registration claimed. All bulk outputs external; raw,
sealed, legacy and historical baselines unchanged. No new commit requested.

## Result and next action

Fresh Astra receipt APPROVE_WITH_NONBLOCKING_NOTES in review.json, copied to
external root. No blocking issues. Notes require final late-ledger-error/unknown
cost audit and actual outside-read audit; prompt-level vstd restriction is not
equivalent to a physically vstd-only toolchain mount. No generalization claim.

Durable background PID1295902 launched2026-10-09T23:04:40.345491+00:00.
External launcher.json contains exact argv/environment overrides/review SHA;
run.log contains live starts/completions. Startup confirmed PID alive, two actors
dev_{old,revised}--aded79905be896942897--repeat-0 with nonempty provider ledger
and raw Codex/agent events; stderr empty. This is actual inference, not preparation.
Full queue, request draining, full trace exports and executive_summary.json
aggregation are automatic. Post-run case interpretation is still pending.

evaluation_summary: complete24/24,9/12 versus11/12 budgeted dual-pass;
claim_update: favorable development direction, general/stable benefit inconclusive;
baseline_relation: fresh initial-versus-diagnostic Executive, common corrected TASK;
failure_mode: residual stochastic quantifier timeout in both arms;
next_action: inspect residual/pair behavior and actual access/edit compliance,
then propose full validation20; no automatic additional run. Settled874 requests
have0provider errors/unmetered/unknown costs; inputs unchanged and bridge drained.
