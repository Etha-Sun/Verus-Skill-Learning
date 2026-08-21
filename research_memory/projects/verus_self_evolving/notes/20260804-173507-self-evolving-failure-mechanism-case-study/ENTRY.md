# Self-Evolving Failure Mechanism Case Study

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-04T17:35:07`
- status: `complete`

## Objective

Explain why the current Verus skill self-evolution loop does not show
monotonic cumulative improvement, with particular attention to two proposed
causes:

1. updates are not incremental;
2. skills are monolithic prompt files rather than indexed, retrievable memory.

The objective is a mechanism diagnosis and a falsifiable replacement design,
not a claim that LLM self-evolution is impossible.

## Context

- Pilot contract:
  `research_memory/projects/verus_self_evolving/experiments/20260726-001827-three-objective-metric-overfit-skill-evolution-pilot/ENTRY.md`
- Loop design: `skill-evolution-pilot/EXPERIMENT_PLAN.md`
- Visibility contract: `skill-evolution-pilot/INFORMATION_CONTRACT.md`
- Meta-agent implementation:
  `skill-evolution-pilot/src/skill_evolution_pilot/meta_agent.py`
- Solver batch implementation:
  `skill-evolution-pilot/src/skill_evolution_pilot/batch_runner.py`
- Token aggregation:
  `skill-evolution-pilot/src/skill_evolution_pilot/token_matrix.py`
- Full-proof scoring:
  `skill-evolution-pilot/src/skill_evolution_pilot/ig_scorer.py`
- Current aggregate results and caveats: `research_memory/CURRENT.md`

## Method / Actions

Compared the token, single-problem token-overfit, small-model, and full-proof
InfoGain branches. Inspected the meta-agent output schema, workspace contents,
skill materialization, solver visibility, and metric aggregation to determine
whether the implemented loop supports:

- persistent knowledge items;
- parent-child edit lineage;
- local credit assignment;
- state-conditioned retrieval;
- explicit merge, split, prune, or deprecation operations.

It does not. The meta-agent receives the previous round and emits three
complete replacement skills. `retained_principle` and `rejected_principle`
are prose summaries, not executable or versioned mutations. The solver
receives exactly one complete `SKILL.md`; there is no runtime retrieval or
no-skill routing decision. Evaluation assigns credit to the whole skill.

## Evidence

| Branch | Baseline | Evolved result | Observation |
|---|---:|---:|---|
| Four-task token loop | H0 ETtS 52,350 | R1 best 51,497; R4 best 59,032; R6 best 51,881 | Six rounds are non-monotonic; R6 remains worse than R1. |
| Single IronKV problem | Fresh H0 ETtS 87,312.7; range 12,908 | Screen best 61,232; three-run confirmation 82,391 | Confirmed delta is only -5.64% and smaller than H0 range; selection result regresses toward H0. |
| Small-model loop | H0 2/4, 312,656 tokens | Every complete skill condition remains 2/4 and uses at least 321,998 tokens | The skills do not change the reachable task subset and add cost. |
| Full-proof InfoGain | R1 post best 0.2198 bits/token | R2 best 0.2031; three-skill mean 0.2149 to 0.1805; R3 incomplete | The secondary proxy is not monotonic and post-proof summaries are hindsight, not causal pre-solve guidance. |

Additional diagnostic evidence:

- Across the 18 token skills from R1-R6, no complete skill improves primary
  uncached tokens over H0 on all four task roles. Per-task crossings are the
  rule, not an exception.
- The H0 four-task coefficient of variation is 0.518, while most
  task-condition cells have one trajectory. Whole-skill winner selection is
  therefore exposed to large sampling noise.
- Historical log fidelity is sufficient for many final diffs but not for
  universal incremental replay: only 7.8% of 9,383 logs have strict structured
  verifier trajectories and 34.7% have explicit verifier payloads.
- Full run evidence remains read-only below
  `${VERUS_SKILL_RUN_ROOT}/skill-evolution-pilot/`, including
  `token-r1-matrix-20260726/` through `token-r6-matrix-20260726/`,
  `qwen-small-model-r1-20260726/` through
  `qwen-small-model-r3-20260726/`, and the single-problem run directory.

## Result

### Main diagnosis

The current system is better described as **iterated monolithic prompt search**
than as self-evolving memory. Each round selects noisy whole-skill winners and
asks a new model call to rewrite several coupled policies at once. Later rounds
therefore do not inherit a measurable set of validated improvements.

The failure chain is:

```text
sparse/noisy whole-skill outcomes
  -> select best and worst complete prompts
  -> rewrite three complete prompts
  -> change many clauses simultaneously
  -> no clause-level causal credit or parent-child diff
  -> useful clauses are forgotten, harmful clauses hitchhike
  -> winner's-curse regression and non-monotonic rounds
```

### 1. The update is not incremental

- There is no stable memory item or clause identifier.
- A child skill has no `parent_id`, edit operation, or machine-readable diff.
- Only the immediately prior round is first-class. Older knowledge survives
  only if the meta-agent restates it, creating a multi-round telephone game.
- The fixed aggressive/conservative/structural output slots force three
  complete variants even when the evidence supports “keep the winner and
  narrow one rule.”
- Multiple rules change together, so aggregate ETtS cannot identify which
  mutation helped.
- The single-problem screen-to-confirmation regression is direct evidence that
  winner selection under this noise can look like evolution without stable
  learning.

### 2. The organization is not memory-like

- The storage unit is a whole procedural Markdown essay, not a small typed
  evidence-backed tactic.
- `applicability` and `negative_scope` are unindexed prose. The solver must
  read them after paying their prompt cost.
- Every task receives the same whole skill even though direct, closest,
  unstable, and hard tasks show different response directions.
- The runner has no query state, top-k retrieval, relevance threshold,
  contradiction handling, or explicit no-memory path.
- The system cannot merge duplicate tactics, split a broad tactic by failure
  mode, narrow its scope, or deprecate a harmful item.

This explains why a globally reasonable skill can increase tokens: irrelevant
instructions create extra hypotheses and verifier cycles. The problem is not
only prompt quality; it is that the architecture cannot deliver only the
locally relevant part.

### 3. Credit and objective are too coarse

- ETtS is attached to the complete skill, while the actual causal unit may be
  one sentence, one verifier-response rule, or one proof-state transition.
- Four heterogeneous tasks with one trajectory per cell cannot reliably
  distinguish small effects from model variance.
- Post-proof InfoGain rewards concise hindsight explanations, which need not
  improve the next action.
- Binary solve rate hides useful intermediate progress, while token cost alone
  can punish deliberate but necessary proof search.

### Replacement abstraction: indexed proof memory

Store small proof-memory cards rather than complete skills:

```text
memory_id
parent_id and version
trigger keys / proof-state signature
action
expected verifier-visible effect
applicable phase
negative scope
evidence run ids
success and failure counts
matched token delta
confidence
contradictions
last validated
status: active | shadow | deprecated
```

The retrieval query should include task family, verifier error class,
obligation form, proof phase, representation boundary, branch direction, and
available contracts. Retrieve zero to three cards, then compile only those
cards into a short task-local instruction. “Retrieve nothing” must be a valid
outcome.

Incremental update operations should be explicit:

```text
ADD | STRENGTHEN | NARROW_SCOPE | SPLIT | MERGE | DEPRECATE
```

Each experimental child should make one principal change while preserving
parent lineage. Promotion should use matched repetitions and item-level
ablation, not one whole-skill winner.

## Decision / Next Step

Do not spend the next budget on another round of three complete skill
rewrites. Run a small retrieval-vs-monolith case study:

1. Extract 6-12 short memory cards from existing best and worst traces, with
   evidence links and explicit negative scope.
2. Implement a deterministic state-keyed retriever first; do not train a
   router yet.
3. Compare matched arms: H0, best monolithic skill, retrieved cards, and an
   oracle-retrieval upper bound.
4. Allow one card or trigger mutation per round and preserve all other cards.
5. Measure ETtS, solve rate, retrieval precision, prompt overhead, card use,
   and per-card matched delta on development tasks plus held-out task families.
6. Promote only changes whose benefit exceeds baseline variability; otherwise
   retain the parent or deprecate the child.

The falsifiable claim for the next experiment is:

> State-conditioned retrieval of versioned, evidence-backed proof-memory
> cards reduces irrelevant prompt overhead and permits cumulative local credit
> assignment better than repeated full-skill rewriting.
