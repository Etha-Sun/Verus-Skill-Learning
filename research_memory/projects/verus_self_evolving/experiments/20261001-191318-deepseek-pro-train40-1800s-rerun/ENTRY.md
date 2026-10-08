# DeepSeek V4 Pro train40 initial rerun at 1800 seconds

## Final outcome audit

Completed at `2026-10-02T01:16:28Z`: all 40 task outcomes, 39 independently verified
Verus plus Lynette successes (97.5%), all within budget. The sole unsolved task
is `8722b35e3186b217ea38`, `AL__eliminate_always`, a 1,800-second timeout whose
candidate passed preservation. Recorded provider usage is valid for all 40;
fidelity is 39 V2 complete traces and one V1 truncated trace. Project outcomes:
AC 12/12, AL 13/14, IR 14/14. Exact task coverage, source and copied-input hashes,
initial-skill hash, model/effort/timeouts, safety, validation agreement and trace
file presence passed the final audit.

The eight-worker continuation completed after reusing eight finished initial-stage
tasks. No source was retried. Total wall duration, including transition, was
51 minutes 38 seconds. The coordinator, bridge and run tmux sessions have exited;
there are no active source tasks.

Settled ledger and summed task usage agree: 1,286 completed metered requests,
no recorded errors, estimated cost USD 5.675279016. Billing caveat: one open guard
reservation of USD 1.83904512 remains after timeout and bridge termination.
Provider work for that request may be billed without recorded usage. Do not
present USD 5.68 as the final invoice or silently clear the reservation.
Whole-run USD 30 protection was not reached.

Historical pairing: 22 retained successes, 17 newly solved and one regression
(the failed AL task was previously solved), net +16. Time cap, repaired toolchain
and explicit request output cap differ; this does not isolate a budget effect
or establish learned-skill improvement. The corpus supplies 39 successful
original traces, not 40 successful hints. Next: inspect the AL regression and
reconcile billing if needed before any new paid run. No further inference,
augmentation, optimization or held-out evaluation was launched by this audit.

Durable reviewed outputs: external run `summary.md` and `audit_summary.json`,
alongside original task and provider evidence. Repository memory is the fallback
because the skill's artifact recording API is unavailable; no artifact-service
submission is claimed.

## Objective and authority

### Next-stage readiness decision (2026-10-02)

Verdict: source evidence is ready for the planned training augmentation and
learning stage, but full paid main-experiment launch is not yet ready/authorized.
Action: `request_user_decision`, then a scoped engineering implementation pass.
Read-only scan confirms all 39 solved sources have saved candidate snapshots
whose hashes differ from their final proof; no proposed checkpoint-selection
rule has yet been applied. All40 originals, including the sole failure, remain
the common learning source. At most one new hint branch per eligible source is
the proposed first round, not three branches or 160 augmented trajectories.

The active plan is `docs/augmentation-main-experiment-20261001.md`: initial,
native SkillOpt, original-only cards and original-plus-hint cards; later
from-scratch val20 twice with test20 deferred. Verified code gaps remain:
packet export is keyed by project rather than source ID, reflection identities
are `fork_<project>`, evidence-bank rejects more than eight sources, hint actor
hardcodes high/600, and teacher/extractor lack unified cash admission. The native
bridge default request-cap gap was fixed during the rerun, not these other gaps.

Pending user choices: S/O/H extractor backend (all DeepSeek for complete API
cash accounting versus existing Sol with separate quota/token ledger), actor
settings for continuation/evaluation (proposed carry-forward max/1800 versus
the older proposed high/600), and a new explicit total cash cap covering hints,
learning and the four-condition validation stage. The previous USD 30 guard
authorized only original train40; no rollover authorization is inferred.
Recommendation: shared fresh source40, one hint maximum per eligible source,
same extractor across learned conditions, frozen common actor settings and
budget, minimal offline repairs and bounded engineering smoke before scaling.
Reject immediate unchanged-pipeline launch because of proven scale/accounting
gaps; defer full ablations and obfuscation because the active plan prioritizes
the first common-source comparison. No code changes or paid inference were
performed for this readiness decision. Reopen launch only after user choices
and the engineering gates have passed.

The user authorized one fresh full train40 rerun using DeepSeek V4 Pro with
1,800 seconds per task. This supersedes the earlier proposed 1,200-second cap.
Scope is initial-skill source rollouts only, not optimization, augmentation,
validation, or test evaluation. Paid execution started after local credentials
were supplied; see the running checkpoint below.

## Frozen contract

- Workspace base: `feat/skillopt-fork-packets-20260918`, commit `a517845`.
- Model: `deepseek-v4-pro`; reasoning effort: `max`, matching the historical run.
- Fixed input: `fixed-claude-stratified-80-seed20260814/train/items.json`.
- Input manifest SHA-256: `0e42aad8c5e8a6789d06e7b15cfdca903479b16dc76f863544f219e6bbe40536`.
- Exactly 40 unique sources; every source hash matched its manifest.
- Groups: 26 verified-anvil, 14 verified-ironkv.
- Initial skill: `skillopt-verusage/skills/initial.md`, 838 bytes.
- Skill SHA-256: `96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`.
- Timeout: 1,800 seconds for each source task, not a whole-run budget.
- Formal Verus: `release/0.2025.09.12.bb1f342`, commit
  `bb1f342683fd26de011825725a55325b65e7d359`, release profile, Rust 1.88.0.
- Native Responses; preserve isolation, per-task provider ledger, and independent
  Verus plus Lynette preservation validation.
- Freeze an explicit per-request output cap at launch. This is distinct from
  the per-task time budget and must be disclosed in the run manifest.
- Use a fresh external directory below the approved `VERUS_SKILL_RUN_ROOT`;
  override the local `.env` value, which currently points inside this repository.
- Never replace historical results or feed reference proofs to the actor.

## Local evidence and preparation

The train-only manifest and all source hashes were checked without accessing
val/test sources. The formal Verus identity gate passed. Linux user/mount/network
namespace isolation preflight passed with libseccomp and probe return code zero.

The native bridge previously reserved a default output bound but did not send
the configured cap to the provider. A surgical local change now forwards the
configured cap when the incoming field is absent/null, preserves explicit caller
caps, and reserves against the actual forwarded bound. Regression tests cover
absent/null/explicit caps and caller payload immutability. All 24 bridge tests
passed using mocked responses; no paid requests were made by those tests.

Verification command:

```bash
PYTHONPATH=skill-evolution-pilot/src:skillopt-verusage/src python -m unittest discover -s skillopt-verusage/tests -p test_codex_deepseek_bridge.py
```

## Historical running checkpoint and transition

The initial credential blocker was resolved by the user configuring the local
project `.env`; its mode is 600. Authenticated provider listing confirmed
`deepseek-v4-pro`. No secret value was printed, copied into Git, or supplied to
the isolated actors. Full isolated Rust/Verus/Lynette probing on historical
crate-alias task `a3c9af1afebbd8d5fe93` succeeded: the original missing proof
caused an expected postcondition diagnostic, not a missing-crate setup error.

The detached run started at `2026-10-02T00:24:50Z` (October 1 local time).
External run ID: `train40-pro-initial-1800s-20261001-KjQXKA`, under
`VERUS_SKILL_RUN_ROOT/skillopt-verusage/`. Exact host paths, commands, source
hashes, environment identities, and scripts are stored there, not in Git.
Native per-request output cap is 131,072 tokens. The USD 30 safety guard is
shared across the entire 40-task run, not USD 30 per task, and not an estimate
of expected spend. Per-task time remains 1,800 seconds.

The first included source task `3a77a3e4e72edf600e2a` passed independent Verus
and Lynette, provider validity and V2 trace fidelity, finishing within budget in
about 106 seconds. Its 21 provider requests were all completed and metered;
estimated usage cost was about USD 0.039. This is only an engineering gate, not
evidence of train40 or method performance. The initial four-worker run admitted
the remaining tasks, with four total completed solves at the last checkpoint.

The user subsequently authorized higher concurrency. Machine availability was
128 CPUs and about 446 GiB available memory. A scoped SIGINT to the coordinating
parent stopped new task admission while its ThreadPoolExecutor drains active
tasks; individual actors and their timeout timers continue unchanged. A detached
continuation waits for this coordinator to exit, then reuses all completed valid
results and the same bridge ledger/budget state while continuing the remaining
sources with eight workers. It will not relaunch any incomplete or invalid task.
The initial launcher is preserved separately. The transition may appear as a
planned KeyboardInterrupt/partial stage in the first manifest; that is not a
proof failure or a task retry. Updated launcher is syntax-checked.

Monitoring surfaces: initial `bash.log`, continuation `resume.log`,
`run_manifest.json`, `progress.json`, `budget_state.json`, `bridge_calls.jsonl`,
and `rollout/predictions/<id>/result.json`. Tmux sessions:
`train40-pro-1800-20261001` and `train40-pro-1800-eight`.
Next: confirm the graceful transition and eight-worker health, then audit all
40 task outcomes and final accounting. Do not launch any optimizer or held-out
evaluation as part of this run.

Historical 23/40 at 600 seconds is a comparator, not a result for this contract.
Final reporting must include actual completed/valid/solved counts, timeouts,
provider failures, tokens/time/cost completeness, and comparison caveats: both
the toolchain and wall-time cap differ from the historical run.

## Safety and durable artifacts

This entry, `PLAN.md`, and `CHECKLIST.md` are compact control records only.
Fresh inference outputs and staged tools stay in the external run directory.
Raw/sealed data and historical run outputs remain unchanged. No API credentials, raw traces,
personal absolute paths, or complete run directories were copied into Git.
