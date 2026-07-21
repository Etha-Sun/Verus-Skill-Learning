# Non-Blocking Verifier-Guided Self-Evolving Steering

## Metadata

- project: `verus_self_evolving`
- kind: `ideas`
- created_at: `2026-07-03T10:08:12`
- status: `active`

## Objective

Record the current shared research framing for a VeruSAGE/Verusage
self-evolving agent that preserves LLM free exploration while injecting
verifier-grounded, non-blocking rules/skills at selected decision points.

## Context

The user clarified a key design constraint:

> We should never block the LLM's thinking. We want hands-off-style free
> exploration, but insert verifiable rules/guidance at certain points so the
> model spends fewer tokens and explores more effectively.

This reframes the project away from a hard hands-on controller and toward
non-blocking steering.

Relevant prior memory/artifacts:

- Group meeting draft:
  `research_memory/projects/verus_self_evolving/notes/20260703-095155-group-meeting-draft-verusage-self-evolving-agent/ENTRY.md`
- VeruSAGE provenance audit:
  `research_memory/projects/verus_self_evolving/notes/20260703-093115-verusage-repair-scaffold-provenance-audit/ENTRY.md`
- Current scaffold:
  `verus-self-evolve-scaffold/`
- Offline eval:
  `verus-self-evolve-scaffold/docs/eval_summary.md`
- Earlier survey:
  `analysis_verusage_trace_ideas_20260624/auto_research_20260628/self_evolving_and_verus_specificity.md`

## Method / Actions

Searched and compared related directions:

- ReAct: interleaves reasoning and acting while preserving LLM-generated
  reasoning traces.
- Reflexion: does not update weights; stores verbal reflections from feedback
  to improve future decisions.
- Voyager: preserves open-ended exploration while growing a skill library and
  using environment feedback/self-verification.
- LATS: uses tree search, value estimates, self-reflection, and environment
  feedback to guide exploration rather than replace it with a fixed policy.
- TACO: self-evolves structured compression rules from terminal trajectories to
  improve token efficiency.
- AgentSpec: uses trigger/predicate/enforcement rules for runtime safety
  constraints and includes LLM-generated rules, but is mainly enforcement/safety
  oriented.
- VeruSAGE: hands-on scaffold improves weak models but can hurt strong models
  because small-step hard-coded policies can constrain large-step exploration.

## Evidence

Primary sources:

- ReAct: `https://arxiv.org/abs/2210.03629`
- Reflexion: `https://arxiv.org/abs/2303.11366`
- Voyager: `https://arxiv.org/abs/2305.16291`
- LATS: `https://arxiv.org/abs/2310.04406`
- AgentSpec: `https://arxiv.org/abs/2503.18666`
- VeruSAGE: `https://arxiv.org/abs/2512.18436`
- TACO: `https://arxiv.org/abs/2604.19572`

Local evidence:

- Parsed traces: 2,996
- Verified: 1,691
- Nonverified: 1,305
- Effective total tokens: 1,524,386,760

Current offline policy results:

| policy | covered failed | saved failed tokens | false-stop rate | peer diff |
|---|---:|---:|---:|---:|
| generic | 1,038 | 800,760,044 | 0.112951 | 0.748705 |
| project-aware | 539 | 548,995,746 | 0.039030 | 0.748252 |
| motif-aware | 227 | 309,382,084 | 0.005322 | 0.777778 |

Interpretation:

- Generic gates show token-saving potential but risk over-constraining.
- Motif-aware rules are safer, supporting Verus-specific steering.
- Current numbers are offline replay, not final live repair proof.

## Result

### Current Shared Framing

The project should be framed as:

> Non-blocking verifier-guided self-evolution for VeruSAGE-style proof agents.

The goal is not to stop LLM reasoning, not to replace hands-off exploration with
a fixed hands-on policy, and not to train a small RL model. The goal is to let
the LLM continue exploring freely while injecting verifier-grounded guidance at
decision points where traces show repeated waste or missed proof motifs.

### Core Distinction

Bad version:

```text
If repetition >= N, block the LLM or force one action.
```

Better version:

```text
If verifier/history signals indicate low marginal value,
surface a rule/skill/skeleton as a recommendation or sampling prior,
then let the LLM decide whether to follow, modify, or ignore it.
```

This preserves the strength of hands-off agents: large-step exploration,
creative proof restructuring, and model-native planning.

### Proposed Architecture

1. **LLM free exploration layer**
   - The LLM can still inspect code, run Verus, write large patches, and form its
     own plan.
   - No rule should block internal reasoning.

2. **Verifier-grounded observation layer**
   - Extract structured state:
     - Verus error type and location,
     - target error delta,
     - error count delta,
     - action history,
     - repeated `(error, action)` patterns,
     - project/motif features,
     - lemma/quantifier/opaque/reveal signals.

3. **Self-evolving rule proposal layer**
   - LLM reads hands-off and hands-on traces.
   - It proposes candidate rules, not only human-authored rules.
   - Rule schema can be AgentSpec-like:

```text
trigger: when does the rule become relevant?
evidence: what trace/verifier signal supports it?
recommendation: what should be suggested?
strength: hard / soft / sampling-prior
validation: how to replay or test it?
```

4. **Sampling-based steering layer**
   - Rules become priors over actions/skills, not only hard constraints.
   - Possible execution modes:
     - hard rule: only for illegal/cheating/safety violations;
     - soft recommendation: shown to LLM as guidance;
     - sampling prior: changes probability over actions/skeletons;
     - critique prompt: asks LLM to reconsider a repeated pattern;
     - retrieval hint: surfaces a relevant skeleton/skill.

5. **Skill/skeleton evolution layer**
   - LLM can add, rewrite, merge, split, or deprecate skills.
   - Promotion to stable memory requires verifier-grounded validation:
     - split-safe replay,
     - held-out trace agreement,
     - small live rerun,
     - solved-rate preservation,
     - false-stop control.

### Why This Is Not Just Low-Novelty Orchestrator Tuning

Low-novelty variants:

- hand-write a few repetition rules;
- tune retry thresholds;
- tune tree-search width;
- use exact-task cache;
- hard-code project-specific action order.

Potentially novel variant:

- rules are generated from trajectories by LLMs;
- rules are scored by verifier-grounded metrics, not natural-language
  plausibility;
- execution preserves exploration through soft rules and sampling priors;
- skill memory is editable/evolvable, not just retrieved;
- evaluation explicitly checks leakage and solved-rate preservation.

### Relation To Prior Work

- ReAct: establishes reasoning/action interleaving, but not self-evolving rules.
- Reflexion: uses feedback as memory, but feedback is general; ours uses Verus
  verifier structure.
- Voyager: learns reusable skills under open-ended exploration; ours learns
  proof-repair skills/skeletons with formal verifier checks.
- LATS: uses search/value/reflection to guide exploration; ours can use
  verifier-derived sampling priors instead of generic value estimates.
- TACO: closest for token efficiency via self-evolved rules; ours targets
  proof-repair decisions, not only observation compression.
- AgentSpec: closest for rule schema/runtime mechanism; ours shifts from
  human/safety enforcement to trajectory-induced verifier-validated steering.
- VeruSAGE: provides the real harness and traces; our method aims to improve its
  decision layer without inheriting the weakness of over-constraining strong
  models.
- verus-tla: should be treated as a concrete temporal-proof case study, not the
  main project. It can show that steering rules can exploit formal proof motifs
  such as `always`, `leads_to`, `weak_fairness`, and `tla_forall`, rather than
  only generic repetition patterns.

Lean4Agent clarification:

- Lean4Agent's verification is not only a score correlation. Its formal checks
  target concrete workflow quality layers: graph structure and loop-back,
  semantic pre/postcondition consistency, variable specification precision,
  context/information-flow consistency, and runtime trajectory violation
  localization.
- Its reported failure modes include unsatisfied preconditions, missing valid
  retry mechanisms, and context-insensitive execution steps that break
  information flow.
- The analogy for our work should be:

| Lean4Agent | VeruSAGE steering analogue |
|---|---|
| workflow graph predicates | repair action trajectory and reroute structure |
| pre/postcondition consistency | Verus error/action state delta |
| context/information-flow predicates | project/motif-aware context compaction |
| trajectory violation localization | repeated `(error, action)` loop localization |
| LeanEvolve workflow revision | rule/skill/skeleton evolution |

- Therefore our verifiable properties must improve specific repair-decision
  layers, not merely correlate with success. Target layers: continue vs reroute,
  skeleton retrieval, context compaction, target-error reduction, false-stop
  control, and exploration preservation.

### Verus-TLA Case Study Hook

Use AL/TLA-style VeruSAGE tasks to demonstrate motif-aware steering:

- Example task names include `AL__leads_to_always_tla_forall`,
  `AL__always_and_equality`, `AL__leads_to_apply`,
  `AL__always_tla_forall_apply`, `AL__init_invariant`,
  `AL__leads_to_rank_step_one`, and `AL__always_lift_action_unfold`.
- AL traces are not the largest token sink, but they are narratively clean for
  formal/temporal proof skeletons.
- Prior AL stats: 89 tasks per model; verified counts are claude 73, claude-s4
  65, gpt5 77, o4mini 46.
- AL threshold=8 repetition signal: 81 gated traces, 75 nonverified gated, 6
  verified false stops, estimated 12,674,971 saved tokens.
- Cross-model AL success-skeleton coverage: claude failed side 6, claude-s4 14,
  gpt5 2, o4mini 33.

Preferred research question:

> Can temporal-logic proof motifs from verus-tla guide LLM proof-repair agents on
> VeruSAGE TLA-style tasks?

Avoid framing it as:

> Can we use verus-tla to verify agents?

The latter is too broad and repeats the generic agent-verification framing. The
former ties formal structure to downstream proof-repair behavior.

### Evaluation Contract

Must avoid leakage and overfitting:

- no exact-task skeleton in eval;
- dev/test split for thresholds;
- model split to test cross-model transfer;
- project split to test generalization;
- report solved-rate preservation, not only token saving;
- measure exploration impact:
  - number/diversity of actions attempted,
  - large-step patch rate,
  - reroute acceptance,
  - verifier error delta,
  - false-stop rate.

### Candidate Claim For Group Meeting

> Rather than constraining LLM agents with fixed hands-on rules, we propose a
> non-blocking verifier-guided steering layer: rules and skills are induced from
> VeruSAGE trajectories, validated by Verus feedback, and used as soft
> recommendations or sampling priors so strong agents can keep exploring while
> avoiding repeated low-value repair loops.

## Decision / Next Step

Use this as the current shared framing. Update the group meeting draft to
emphasize:

- "do not block LLM thinking";
- soft guidance / sampling prior instead of hard gate;
- LLM-generated rules and editable skills;
- verifier-grounded validation as the source of trust and novelty.

Next experiment should implement split-safe non-blocking replay:

1. Mine candidate rules from train traces.
2. On held-out traces, compare:
   - no steering,
   - hard gate,
   - soft recommendation,
   - sampling prior / reroute prior.
3. Metrics:
   - token saved,
   - false-stop rate,
   - peer-success agreement,
   - action diversity preservation,
   - solved-rate preservation in any live rerun.
