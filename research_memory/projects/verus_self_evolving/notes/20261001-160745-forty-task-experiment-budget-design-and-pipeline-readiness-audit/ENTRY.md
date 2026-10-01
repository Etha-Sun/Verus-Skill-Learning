# Forty task experiment budget design and pipeline readiness audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-10-01T16:07:45`
- status: `audited_plan_runtime_not_ready`

## Objective

Design the next forty-source-task experiment, account for learning costs, and
distinguish reusable pipelines from missing code and missing server configuration.
This is an audit and proposal, not an executed experiment or an approved spend cap.

## Context

- Meeting interpretation: `meetings/20261001-144332-forty-task-augmentation-experiment-priorities-and-learning-budget-meeting/ENTRY.md` within this project.
- Active detailed proposal: `docs/augmentation-main-experiment-20261001.md`.
- Previous ablation matrix: `docs/augmentation-experiment-plan.md`.
- Historical cost and eligibility evidence: `experiments/20260817-140332-skillopt-deepseek-v4-pro-fixed-80-epoch-1/ENTRY.md` within this project.
- Source audit at branch `feat/skillopt-fork-packets-20260918`, code head `ecc018e`.
  Existing working-tree meeting/document changes were preserved.

## Actions

Read startup research memory, the meeting interpretation, training configurations,
actor/teacher bridges, the shared cost guard, packet exporter, card optimizer,
baseline reoptimization and validation runners. Checked named runtime variables,
expected project configuration files and executable availability without exposing
credentials. Consulted official DeepSeek model, pricing and capability documents.

Ran the focused existing suite with isolated uv dependencies: skill proxy,
Codex DeepSeek bridge, formal epoch contract, hint augmentation, fork packets,
fork card optimizer, card bank, skill validation, Codex selection gate, bridge
cost ledger, Codex reoptimization, Pro reanalysis and pilot Codex runner.
Result: **83 passed, 10 subtests passed**, 7.44 seconds. These are offline tests
with temporary fixtures and mocks, not an authenticated provider or verifier smoke.
Dependency setup required downloading PyYAML; no model inference was requested.

## Evidence

### Reusable components

- `skillopt-verusage/src/skillopt_verusage/train.py` and
  `skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e1_600s.yaml` implement
  the historical train40 baseline with Pro actor and Sol extractor.
- `skillopt-verusage/src/skillopt_verusage/codex_reoptimize.py` can reuse a
  qualified original source run for baseline extraction.
- `skillopt-verusage/scripts/run_hint_augmentation.py` provides the established
  three-task hint and no-hint continuation route, with isolation and dual validation.
- `skillopt-verusage/src/skillopt_verusage/skill_validation.py` supports frozen
  artifacts, audit/hash gates, paired randomized repetitions and from-scratch use.

### Blocking code gaps for the proposed large experiment

1. Exporter uses `tasks/{project}`; reflection uses `fork_{project}`. Multiple
   distinct source tasks in one project collide. Export arms are also fixed to
   historical v1/v2/no_hint. Need stable source IDs and variable arms.
2. `fork_card_optimize.py` rejects more than eight evidence-bank source tasks,
   after reflection has already run. Merely removing the check does not preserve
   provenance through larger semantic merges. Proposed O/H bank path retains
   per-source proposals with exact deduplication and provenance union.
3. Teacher preparation requires a final original that passes both checks.
   Historical 600-second train40 solved 23/40, so eligible hint sources would be
   at most 23 for that source run. Failure originals must remain in all arms.
4. Teacher issues direct Responses requests outside SharedBudgetGuard;
   extractor lacks cumulative learning-spend admission. Existing actor guards
   do not implement the meeting's complete learning budget.
5. Native Responses forwarding reserves against 131,072 output tokens when
   the payload lacks a cap, but does not forward that assumed cap. Model limits
   can be higher. Enforce the request cap and a valid input bound before claiming
   a strict spend bound. Separate reservation waits from task timeout clocks.
6. Price-band selection only checks UTC hours and ignores weekends/holidays;
   Flash prices/alias assumptions are stale. Pro rate numbers agree with the
   current official table. Record pricing snapshots and any conservative estimates.
7. Progress-aware checkpoint selection, forty-task budget scheduling and an
   all-DeepSeek fork extractor adapter remain unimplemented. Current extractor
   relies on Codex shell access to evidence paths; changing its model name is
   insufficient. The historical formal contract must remain unchanged.
8. Validation's paired report is fixed to `original_only`; add the H/S comparison.
   Its main schedule shuffles across repetitions; configure or adapt complete
   repetition blocks before promising a paired first-80-attempt interim report.

### Service and machine status

Official documentation currently lists `deepseek-v4-pro`, Pro-0813, 1M context,
maximum 384K output and Responses support. Pro off-peak input hit/miss/output
rates per million are USD 0.022/0.66/1.98; peak rates double. Published peak
windows apply on weekdays excluding Chinese public holidays. Sources:
[pricing](https://api-docs.deepseek.com/quick_start/pricing/) and
[authenticated model capabilities](https://api-docs.deepseek.com/api/list-models/).

The inspected project environment has no DeepSeek key/config or configured run/data
environment variables; the historical server mount is absent. Recovered local
trajectory files were subsequently found, as detailed below. Verus/Lynette are
not on PATH; Codex, uv, Python
and bwrap are available. No authenticated account, balance, model response, tool
round-trip or complete Verus/Lynette run was verified. Another server may have
these; its readiness is unknown. A pending user clarification asks for the target
SSH alias or configuration file path, not a secret pasted into chat.

### Cost anchor

Historical 80-task S0/train40/S1 known actor cost was USD 8.035293 off-peak,
with one additional unknown-usage 502. Subtracting S0 and S1 gives train40 known
cost USD 4.468367. Sol optimizer quota is not a known zero-cost resource.
New-run estimates and explicit assumptions are in the active proposal; do not
turn historical small-pilot prices into guaranteed future bills.

## Result

Recommend fresh or strictly compatible reused original40, at most one hint branch
per eligible source, and four conditions: initial skill, native SkillOpt,
original-only cards and augmented cards. Evaluate from scratch on val20 twice
(80 attempts for the first complete repetition, 160 for two). Reserve test20.
Use the same extractor for all learned conditions; an all-DeepSeek adapter enables
complete dollar accounting, while retaining Sol requires a separate token/quota
ledger and a narrower comparison claim.

Proposed planning envelope is USD 40–80 API cash, subject to complete-input
preflight and explicit caps; worst cases can exceed this envelope and must stop.
A tentative all-DeepSeek learning ceiling is USD 25 per method including the
shared original cost charged in full to each method, with at most USD 5 for
extraction/finalization. Hold back 20% of that extraction allowance for closure.
These are proposals, not meeting decisions or spend authorization. Equal ceilings
are not equal realized learning cost; report both. Strict equal-cost superiority
requires later baseline opportunities to spend remaining budget and multiple
budget points. No augmentation efficacy has been established by this audit.

## Trajectory accessibility follow-up

The user asked whether the concrete trajectories underlying the eligibility
claim are accessible. Read-only inspection found three recovered original
trajectories under local `incoming/skillopt-original-three-traces-20260922/`.
Their manifests identify Pro/max/600s, their source hashes match the frozen
train manifest, and their recorded final Verus and Lynette results both pass.

| Project | Source ID | Canonical events | Raw Codex events | Snapshot files |
|---|---|---:|---:|---:|
| IR | `3a77a3e4e72edf600e2a` | 104 | 61 | 26 |
| AC | `bcf0292578550cb38451` | 148 | 90 | 41 |
| AL | `f91ac92b861061915a41` | 94 | 53 | 25 |

Parsed their event streams and conversations, read manifests/results, and
inspected representative verifier events. For example, IR's event 24 records
the failed set_map_union postcondition; the final stored result passes both
checks. This was file inspection, not a new verifier run or an exhaustive
semantic review of every action. Corresponding recovered branch files and
three-task packets also exist. No copied trace was written into the repository.

The full forty-source run has not been located locally. A similarly named
incoming/train40 directory contains a predictions directory but no result.json
files. Thus 23/40 remains a historical report statistic; the eligible upper
bound is an inference from that statistic and the current prepare assertion,
not a fresh per-task audit of all forty trajectories. Exact failed-case and
checkpoint eligibility checks require the complete source run. The original
assertion is an implementation restriction, not an inherent limit on all hint
methods. Machine-local paths are saved in ignored `.agent-context.local.md`.

## Next step and data safety

Confirm target runtime; fix identity, bank and budget gaps; freeze extractor and
new contract; then perform authenticated probes and training-only smoke before
the forty-task batch. Exact runtime and budget remain pending. All generated
experiment outputs must live under the configured external run root.

Only reviewed documentation and research memory were written. No paid inference,
GPU use, experiment launch, raw/sealed-data mutation, commit or push occurred.
Meeting transcript files remain untracked and were not copied into this note.
