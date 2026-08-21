# Standout Skill-Memory Case Study Shortlist

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-05T13:56:28`
- status: `complete`

## Objective

Select concrete skill/memory files for qualitative case studies from the
completed token-cost, single-problem, and InfoGain experiments. Separate:

1. the strongest available repeated or cross-task evidence;
2. task-state specialists that motivate retrieval;
3. offline proxy exemplars that are not live-performance evidence;
4. a matched negative comparator.

## Context

- Failure-mechanism diagnosis:
  `research_memory/projects/verus_self_evolving/notes/20260804-173507-self-evolving-failure-mechanism-case-study/ENTRY.md`
- Token matrices:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r1-matrix-20260726/`
  through `token-r6-matrix-20260726/`
- Single-problem experiment:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/`
- InfoGain scores:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/information-gain-r1-scores-20260726/summary.json`

## Method / Actions

Ranked all 18 R1-R6 token skills by aggregate ETtS and then independently
ranked every verifier-safe task-skill cell against that task's H0. Checked the
selected skill files, exact hashes, run validation, F3 evidence, and normalized
tool/edit events. The single-problem candidate was evaluated using its
predeclared three-run confirmation, not its best screening trajectory.

Selection is descriptive because the four-task matrices contain one trajectory
per task-skill cell. A file may be selected as a useful mechanism case without
being promoted as a generally beneficial skill.

## Evidence

### Raw comparison table

Here `A = aggressive`, `C = conservative`, and `S = structural`.

| Experiment / round / slot | Memory | Evaluation scope | Result versus H0 | Safety/evidence | Selection role |
|---|---|---|---:|---|---|
| Four-task token / R1 / A | `bounded-exploration-gate` | Four-task aggregate | ETtS 51,497 vs 52,350, -1.63% | 4/4 solved, F3, Verus, Lynette | Best cross-task aggregate |
| Single-problem token / R3 / A | `local-proof-surface-cap` | IronKV three-run confirmation | ETtS 82,391 vs 87,312.7, -5.64% | 3/3 complete and verifier-safe | Best repeated same-task candidate; still inconclusive within H0 range |
| Four-task token / R4 / C | `zero-ceremony-direct` | Direct local task | 19,616 vs 25,555, -23.24% | One trajectory, verifier-safe and F3 | Direct-proof specialist |
| Four-task token / R3 / C | `local-contract-closure` | Small visible-contract task | 18,527 vs 32,784, -43.49% | One trajectory, verifier-safe and F3 | Largest task-specific token reduction |
| Four-task token / R6 / S | `typed-two-stage-oracle` | Opaque API/contract task | 58,473 vs 71,816, -18.58% | One trajectory, verifier-safe and F3 | Typed API-boundary specialist |
| Four-task token / R5 / A | `batched-compiler-oracle` | Hard IronKV task | 56,036 vs 79,245, -29.29% | Selected cell is verifier-safe and F3; whole skill is only 3/4 | High-gain, high-risk specialist |
| InfoGain / R1 / S | `dependency_bridge_map` | Four-task pre-proof InfoGain macro | +0.0705 bits/target token | Offline scorer only | Structural retrieval-content exemplar |
| InfoGain / R1 / C | `minimal_sufficient_rationale` | Four-task post-proof InfoGain macro | +0.2198 bits/target token | Offline hindsight summary only | Compression/summary exemplar |
| Single-problem token / R3 / C | `three-fact-witness-note` | Same IronKV round as selected candidate | 119,638 vs 87,312.7, +37.02% | One verifier-safe trajectory | Matched negative comparator |

### Exact files and hashes

- Cross-task:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r1-matrix-20260726/skills/bounded-exploration-gate.md`
  (`a4d26d07824f25a22150ffd87bb659c50e580c8abf4bf619162333b2e723b644`)
- Repeated same-task:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/final-confirmation/selected_skill.md`
  (`ace8d4093957b152f4117e28876867573ba4a6927533e2989d0c52b0020fb38b`)
- Direct specialist:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r4-matrix-20260726/skills/zero-ceremony-direct.md`
  (`030a28d41ad1ff716db53c96355aa4208e3c6f1545df32b7b19bc413c1239f22`)
- Visible-contract specialist:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r3-matrix-20260726/skills/local-contract-closure.md`
  (`1e99167a29fe8808f21dfecad99edf2c60781db6ab160f67ac1f8e594b4acad0`)
- Typed API-boundary specialist:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r6-matrix-20260726/runs/skills/typed-two-stage-oracle.md`
  (`bb7529bf7a2b328a05f2eee76b160c94e55d5ef967ae7f7e206d86857492a6b0`)
- Bounded compiler specialist:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/token-r5-matrix-20260726/runs/skills/batched-compiler-oracle.md`
  (`825ade1f48e6510bc9493292a4f19f2da06e6513476fefe948e5b69800388cc8`)
- Pre-proof structural proxy:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/information-gain-r1-trajectories-20260726/skills/dependency_bridge_map.md`
  (`3d2ecdcb0a2a62cfae82e0fc1f4003d72c3684ae7d6938f138bcde312f461400`)
- Post-proof compression proxy:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/information-gain-r1-trajectories-20260726/skills/minimal_sufficient_rationale.md`
  (`8057fe2a167dce238190708a1caf1ef2f529ed0a96eaa2872f3980f7f1ad18ce`)
- Negative comparator:
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/single-problem-token-evolve-delegation-map-20260730/round-3/skills/three-fact-witness-note.md`
  (`17566258ed6d6bf7d6c1c607fdfb2a3ed12bdf1539ca0d74e5d015c65c1e7bd1`)

## Result

### 1. Primary positive case: `local-proof-surface-cap`

This is the only shortlisted memory with a fresh three-run confirmation.
Compared with H0, aggregate tool calls fall from 41 to 30 (-26.8%), while ETtS
falls by 5.64%. The memory explicitly constructs a return-path ledger, requires
true-path coverage and false-path witnesses before the first verifier call,
caps helper creation, and stops at the first successful Verus/Lynette pair.
That makes it the best case for studying whether organizing the proof surface
before editing reduces exploration.

Caveats: the token delta is smaller than H0's own 12,908-token range, wall time
increases slightly, the raw generated file contains duplicated sections, and
the evaluation is exact-task overfit. It should be decomposed and normalized
before reuse, not promoted intact.

### 2. Cross-task case: `bounded-exploration-gate`

This is the lowest aggregate ETtS among all R1-R6 token skills and remains
4/4 verifier-safe. Its potentially reusable atoms are the evidence gate for
unknown symbols, the two-failure cutoff for one proof shape, the unchanged-
state no-rerun rule, and the final policy-check stop condition.

The aggregate benefit is only 1.63%, with two tasks helped and two harmed.
This is evidence for extracting general stop-control atoms, not for treating
the whole file as a universally useful memory.

### 3. Retrieval-specialist quartet

The four per-task winners align with four different proof states:

- `zero-ceremony-direct`: locally closed direct corollary; its selected
  trajectory performs one proof edit, one solver-run Verus call, and one
  solver-run Lynette call.
- `local-contract-closure`: a small hole closed from nearby contracts; it is
  the largest observed task-specific reduction, but helps only one of four
  tasks.
- `typed-two-stage-oracle`: one missing typed public bridge; useful on the
  opaque marshal obligation but adds about 20% on the direct and hard tasks.
- `batched-compiler-oracle`: one bounded namespace discovery step; best on the
  hard IronKV task, but its aggregate condition is worse than H0 and solves
  only 3/4.

These crossings are stronger evidence for a state-conditioned router than for
any one global skill. The key case-study question is whether the state
signature can retrieve the right specialist and abstain elsewhere.

### 4. Proxy-only exemplars

`dependency_bridge_map` is the only R1 skill with positive four-task pre-proof
macro InfoGain, but the value is driven by two marshal tasks; its pooled score
is negative and its hard-task score is negative. It is useful for extracting
representation-bridge and dependency-order cards, not as live-benefit proof.

`minimal_sufficient_rationale` has the highest post-proof InfoGain, but that
summary is generated after the solution exists. It is a case for memory
compression and terminal summarization, not pre-solve retrieval.

### 5. Negative comparator

`three-fact-witness-note` is useful because it appears in the same IronKV R3
as `local-proof-surface-cap`, passes all safety checks, yet costs 37.02% more
than H0 in its one screen trajectory. Both files mention local witnesses and
contain duplicated generated sections, but the positive candidate imposes a
complete return-path ledger and stronger proof-surface cap. This supports a
testable hypothesis that organization and coverage discipline matter more
than merely reminding the solver about witnesses. With one trajectory per
screen cell, this is a hypothesis, not a causal conclusion.

## Decision / Next Step

Use the first six files as case-study sources, not as a global prompt bundle.
Extract and version small cards from:

1. proof-surface enumeration and helper cap;
2. evidence-gated symbol use and repeated-diagnostic cutoff;
3. direct local closure;
4. visible-contract composition;
5. typed API-boundary discovery;
6. bounded compiler suggestion use.

Evaluate an explicit router with four state labels (`direct_local`,
`visible_contract`, `opaque_api_bridge`, `hard_branch_witness`) plus abstain.
Compare retrieved cards against H0 and the original monolithic skill with
matched repetitions. Keep the InfoGain files as secondary organization/
compression analyses and retain `three-fact-witness-note` as a negative
control.
