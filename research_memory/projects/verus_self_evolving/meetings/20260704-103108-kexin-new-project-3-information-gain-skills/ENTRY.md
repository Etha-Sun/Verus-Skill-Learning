# Kexin New Project 3: Information-Gain Skills From VeruSAGE Trajectories

## Metadata

- project: `verus_self_evolving`
- kind: `meetings`
- created_at: `2026-07-04T10:31:08`
- status: `complete`

## Objective

Digest the July 4, 2026 meeting transcript and update the research direction.
The meeting moves the project from only non-blocking steering rules toward
learning/evolving interpretable debug rationales or skills from VeruSAGE
trajectories, evaluated by information gain on the likelihood of the ground-truth
proof.

## Context

Transcript:

- `analysis_verusage_trace_ideas_20260624/20260704222437-kexin-new-project-3-transcript-1.txt`

User-provided Google Meet formulas:

```text
P(gt_proof | trajectory_1, counterexample) - P(gt_proof | trajectory_1)

(1,2,3,....10)
trajectory (1), trajectory (1,2,3)

P(gt_proof | trajectory_1, skills) - P(gt_proof | skills)
P(gt_proof | trajectory_1, skills) - P(gt_proof | trajectory_1)

P(sampled_skill | skills)
P(gt_proof | trajectory_1, sampled_skill ) - P(gt_proof | trajectory_1)
```

The meeting starts around midnight; the formula messages align with the
discussion around transcript times 00:19-00:43.

Reference added after the meeting:

- InfoGain-RAG: `https://arxiv.org/html/2509.12765v1`
- Local literature note:
  `research_memory/projects/verus_self_evolving/literature/20260704-103229-infogain-rag-reference-for-proof-rationale-reward/ENTRY.md`

## Method / Actions

Read the full 308-line transcript, with special attention to:

- 00:05-00:12: recap of AgentSpec, Lean4Agent, VeruSAGE hands-on/off.
- 00:12-00:16: local repetition/reroute experiments.
- 00:18-00:30: Kexin proposes trajectory-based rationale/counterexample
  generation with information-gain reward.
- 00:30-00:43: discussion of skill evolution, sampling a skill, and reducing
  engineering complexity.
- 00:44-00:46: TLA/verus-tla role as external knowledge/lemma substrate.
- 00:46-00:47: high-level constraints: low cost, avoid brittle RL, exploit
  private trajectory data.

## Evidence

Key transcript anchors:

- 00:05: downstream metrics are performance and token cost, ideally with
  verifiable properties.
- 00:06: AgentSpec rules are still largely human/developer described; LLM rule
  generation exists but is weaker.
- 00:07: Lean4Agent improves workflow quality, e.g. fewer repeated failed
  operations / lower token cost / better structure.
- 00:09-00:11: VeruSAGE hands-on pipeline is error-type routing to specialized
  agents and repair actions such as `USELEMMA`.
- 00:12-00:15: repetition gate and reroute prior experiments were explained.
- 00:18-00:19: Kexin emphasized "四两拨千斤" rather than expensive brute-force
  self-evolution; trajectories are the core asset.
- 00:19-00:25: proposed training a rationale/counterexample agent from
  intermediate trajectory states, using likelihood increase of the ground-truth
  proof as a reward.
- 00:25-00:27: the information-gain formula can be used either as RL reward or
  as search reward for self-evolving examples/skills; learning can happen in the
  skill set rather than model weights.
- 00:32-00:35: hands-on trajectories are stateful and easy to slice at nodes;
  hands-off trajectories can also be sliced using heuristics around error
  messages.
- 00:36-00:39: key indirection: evolving skills is not directly evaluated unless
  the skill is plugged into an agent or used to generate a counterexample/rationale
  scored by the information-gain reward.
- 00:41-00:43: possible variant: skip explicit counterexample and directly score
  skills; if the agent must choose among skills, need a `P(sampled_skill | skills)`
  or skill-sampling mechanism.
- 00:44-00:46: verus-tla/TLA is like external proof knowledge/lemmas; some
  VeruSAGE tasks already involve these modules, especially AL/AC from Anvil.
- 00:46-00:47: constraints: manage cost, avoid painful RL if possible, exploit
  non-public trajectories, learn something nontrivial from them.

## Result

### 1. Main Conceptual Shift

Previous framing:

> Mine trajectories into non-blocking steering rules / action priors.

New meeting framing:

> Use trajectories as supervision for generating useful debug rationales,
> counterexamples, or skills; score their usefulness by how much they increase
> the likelihood of the ground-truth proof.

The target artifact is no longer only a rule like "reroute after N repeated
actions." It can also be:

- a counterexample-like explanation of why the current proof attempt fails;
- a debug rationale;
- a proof-repair skill;
- a skill selector / sampling policy;
- a temporal/TLA proof motif skill.

### 2. Information-Gain Reward

The basic reward is:

```text
IG(counterexample; trajectory_t)
  = log P_T(gt_proof | trajectory_t, counterexample)
    - log P_T(gt_proof | trajectory_t)
```

where:

- `trajectory_t` is a prefix of the repair trajectory, e.g. step 1 or steps 1-3
  from a 10-step hands-on trajectory.
- `counterexample` can be generalized to debug message / rationale / hint.
- `P_T` is a teacher/scoring model that exposes token log probabilities.
- `gt_proof` is the final successful proof, scored by teacher forcing rather
  than generated from scratch.

This answers the "how do we evaluate a rationale/skill cheaply?" problem:
we do not need the scoring model to solve the task; we ask whether the proposed
rationale makes the known proof more likely.

InfoGain-RAG gives the closest literature analogue. It measures whether a
retrieved document increases the model's confidence in the ground-truth answer.
Our translation is:

```text
query               -> trajectory_t
retrieved document  -> rationale / counterexample / skill
ground-truth answer -> gt_proof
DIG                 -> proof information gain
```

The main adaptation risk is proof length: raw sequence probability will be
biased against long proofs, so the probe should use normalized or chunked
logprob scores rather than a naive product of token probabilities.

### 3. Skill-Based Variants

Kexin then generalized from counterexamples to skills:

```text
IG(skill; trajectory_t)
  = log P_T(gt_proof | trajectory_t, skill)
    - log P_T(gt_proof | trajectory_t)
```

To distinguish whether the skill itself is useful beyond the trajectory:

```text
log P_T(gt_proof | trajectory_t, skills)
- log P_T(gt_proof | skills)
```

To model skill selection:

```text
sampled_skill ~ P(sampled_skill | skills, trajectory_t)

reward(sampled_skill)
  = log P_T(gt_proof | trajectory_t, sampled_skill)
    - log P_T(gt_proof | trajectory_t)
```

This introduces a new design choice:

- either evolve one skill set and score it directly;
- or learn/sample which skill to apply at each trajectory state.

The second option aligns with the earlier non-blocking steering idea, but adds
a more explicit probabilistic skill-selection objective.

### 4. Why Hands-On Trajectories Are Useful

Hands-on VeruSAGE traces are stateful:

```text
trajectory prefix: (1), (1,2,3), ..., (1,2,...,t)
current error/action/history: known
final proof: known if eventually verified
```

This makes them easy to slice into training/evaluation examples:

```text
input: trajectory prefix at step t
candidate output: rationale / counterexample / skill
score: likelihood gain on the final proof
```

Hands-off traces can also be sliced, but require heuristics to identify failure
points, error-message boundaries, and tool-feedback boundaries.

### 5. Relationship To Self-Evolution

The meeting reframes self-evolution as "training" over a mutable knowledge
object:

- standard training updates model weights;
- self-evolution updates skills / rules / examples / rationales.

The information-gain score can serve as:

- RL reward for a small rationale/counterexample generator;
- search reward for sampling better rationales/counterexamples;
- selection reward for promoting skills into memory;
- critique signal for why a skill or rationale was useful/useless.

Kexin's preference is to avoid expensive brute-force self-evolution and avoid
painful RL if possible. The more academia-friendly route is to exploit the
private trajectory dataset as a high-value supervision source and derive
interpretable skills/rationales from it.

### 6. Key Open Gap

The main unresolved gap:

```text
evolved skill set
  -> how exactly is it used?
  -> how exactly is it evaluated cheaply?
```

Two possible routes:

1. **Counterexample/rationale route**
   - skill set helps generate a debug rationale/counterexample;
   - reward is information gain on `gt_proof`;
   - later the best rationales are summarized into skills.

2. **Direct skill route**
   - evolved skills are inserted directly into the scoring prompt;
   - reward is likelihood gain on `gt_proof`;
   - if multiple skills exist, need a skill sampler/selector.

Kexin seemed to prefer keeping it interpretable: skills should mean something
like "debugging skill" or "counterexample-generation skill," not arbitrary
opaque text.

### 7. Role Of TLA / verus-tla

TLA/verus-tla was discussed as external proof knowledge:

- sometimes the agent needs to construct helper modules/lemmas first, then cite
  them in the end-to-end proof;
- AL and AC tasks likely include Anvil/TLA-style proof modules;
- another student with TLA/VeruSAGE experience may join the discussion.

Current interpretation:

- TLA remains a case study / domain-specific skill family.
- It can provide meaningful skill content, e.g. temporal proof rationale,
  `always/leads_to/weak_fairness/tla_forall` skeletons, rather than generic
  repetition rules.

### 8. Practical Constraints

- Cost must be controlled; avoid "big-token brute force" self-evolution.
- Pure RL/model-weight training may be painful and not reliable under academic
  compute constraints.
- Need to exploit the private/non-public VeruSAGE trajectory dataset as the main
  advantage.
- A small local/open-weight model can be used if token logprobs are accessible;
  if a larger scoring model is needed, keep calls limited and use it as a reward
  model, not as the main proof solver.

## Decision / Next Step

Recommended next plan:

1. **Formalize the data unit**
   - Define `trajectory_t`, `gt_proof`, `candidate_rationale`, `candidate_skill`.
   - Decide how to extract final proof from verified traces.
   - Decide how to slice hands-on traces into prefixes.

2. **Build a tiny offline prototype**
   - Sample 20-50 verified traces.
   - For each, choose 1-3 prefix states.
   - Generate 2-4 rationales/counterexamples per prefix:
     - baseline generic rationale,
     - trace-derived rationale,
     - random/irrelevant control,
     - optional TLA/motif-specific rationale.
   - Score by teacher-forced log-likelihood gain on final proof.

3. **Check whether the reward has signal**
   - Does a good rationale increase `log P(gt_proof)` over baseline?
   - Are irrelevant rationales near zero or negative?
   - Do successful-trace-derived rationales score higher than generic ones?

4. **Only then decide route**
   - If IG reward is noisy/flat: fall back to non-blocking steering/reroute
     experiments.
   - If IG reward has signal: build self-evolving skill/rationale loop.
   - If skill selection is promising: introduce `P(sampled_skill | skills,
     trajectory_t)` as a sampling policy.

5. **Keep evaluation leakage-safe**
   - Generate/evolve skills on train traces.
   - Score/select on dev traces.
   - Report final effect on held-out traces or a small live rerun.

Immediate implementation target:

> `information_gain_reward_probe`: an offline script that slices verified
> VeruSAGE trajectories and measures whether candidate rationales/skills improve
> teacher-forced log-likelihood of the final proof.

InfoGain-RAG makes this target more concrete: first collect proof-IG labels for
candidate artifacts, then optionally train or tune a lightweight selector that
classifies positive-IG skills and ranks them above neutral/negative controls.
