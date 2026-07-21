# Hands-off trajectory distillation and inference-cost objective

## Metadata

- project: `verus_self_evolving`
- kind: `meetings`
- created_at: `2026-07-18T11:20:59`
- status: `complete`

## Objective

Capture the July 17, 2026 group-chat decision about how to use the
`claude_sonnet_gpt5` hands-off traces. The immediate goal is to distill useful
knowledge from frontier-model/agent trajectories and test whether that
knowledge preserves hands-off-level proof success at lower inference cost.

## Context

Participants in the user-provided chat: Kexin Pei, Xinyue Huang, and Yuechun
Sun. The source transcript was pasted into the July 18 conversation; this entry
is its durable digest.

Trace corpus and example:

- primary hands-off corpus: `claude_sonnet_gpt5/`
- example Opus 4.5 IronKV trace:
  `claude_sonnet_gpt5/verified-ironkv/results-opus45/delegation_map_v__impl1_erase.log`
- the corpus currently contains 9,823 `.log` files; the example log is 5,716
  bytes and records a successful iterative proof-repair trajectory plus usage
  statistics.

Related prior memory:

- July 4 information-gain meeting:
  `research_memory/projects/verus_self_evolving/meetings/20260704-103108-kexin-new-project-3-information-gain-skills/ENTRY.md`
- July 14 three-target IG pilot:
  `research_memory/projects/verus_self_evolving/experiments/20260714-164002-qwen3-6-three-target-information-gain-pilot/ENTRY.md`

## Method / Actions

Extracted the project's goal, scope, cost definition, and immediate experiment
sequence from the chat. Inspected the cited example trace to confirm that it
contains a concise sequence of diagnoses, attempted repairs, verifier/checker
feedback, the final successful repair summary, duration, and model-token usage.

Proposed experiment ladder, ordered from the cheapest falsifiable baseline to
more complex methods:

1. **Corpus inventory and leakage-safe subset**
   - Select 20-50 successful hands-off traces from train projects only.
   - Parse task/project/model, success, duration, input/output/cache tokens,
     verifier-error sequence, repeated attempts, and final proof strategy.
   - Keep exact tasks and close variants out of the evaluation split.

2. **Manual-or-teacher distilled prompt baseline**
   - Distill recurring useful knowledge into one short, initially unstructured
     prompt. Do not build a skill framework yet.
   - Compare `no knowledge` against `distilled prompt` on real held-out Verus
     repair cases using the same model and agent scaffold.

3. **Knowledge ablation and compression**
   - Split the prompt into atomic skills such as verifier-first diagnosis,
     invariant strengthening, sequence-bound obligations, executable-code
     preservation, and checker-aware repair.
   - Test full prompt, leave-one-skill-out, compressed prompt, and a
     length-matched generic control to identify which knowledge saves tokens.

4. **State-conditioned retrieval**
   - Retrieve only skills matching the current verifier error or proof motif.
   - Compare against injecting the entire skill set. Sweep retrieved top-k and
     prompt-token budget to find the solved-rate/cost frontier.

5. **Cross-model transfer**
   - Evaluate the same frozen knowledge on a frontier model and a local
     27B/70B-class model.
   - Test two claims separately: the frontier model uses fewer tokens, and the
     smaller model plus knowledge approaches the larger no-knowledge baseline.

6. **Distillation-cost comparison**
   - Generate the same bounded skill set with a frontier model and a local
     model, then freeze it before evaluation.
   - Account for one-time trace-parsing/distillation tokens separately from
     recurring inference tokens; report break-even task count.

7. **Optional optimization only after signal exists**
   - Use IG, information density, or search/self-evolution to rank or refine
     candidate skills only if the simple prompt/retrieval baselines improve the
     live cost-quality frontier.
   - Harness/scaffold evolution is a later branch, not the first experiment.

## Evidence

Key statements distilled from the chat:

- The immediate research goal is trace analysis and learning from traces;
  whether self-evolution is useful remains open.
- Start with hands-off traces because they come from frontier models plus agents
  and already set a high success-rate bar.
- A useful first artifact can be a collection of unstructured prompts; novelty
  of the methodology is not the current priority.
- The artifact must be evaluated by augmenting an agent on real Verus repair
  cases during inference.
- Operationally, "beat hands-off" first means comparable proof results with
  substantially fewer tokens and/or a substantially smaller model. Higher
  solved rate is a stretch goal, not the initial gate.
- Knowledge-generation cost also matters because parsing long trajectories,
  sampling rationales, and rationalizing them into skills can be expensive.

The inspected example trace supports candidate knowledge around:

- diagnosing verifier errors before patching;
- strengthening loop invariants and subrange bounds incrementally;
- respecting integer/natural-number coercions;
- preserving executable code so the safety checker accepts the repair;
- validating with both Verus and the project checker.

## Result

The short-term framing changes from "design a self-evolving method" to:

> Distill reusable knowledge from successful hands-off frontier trajectories,
> inject it into held-out proof-repair runs, and measure whether it shifts the
> success-versus-cost frontier.

Primary live outcomes:

1. verifier solved rate / task success;
2. total uncached inference tokens per task and per solved task;
3. wall-clock time and number of repair iterations/tool calls;
4. model size and serving cost.

Secondary offline diagnostics:

- artifact IG/specific IG and information density;
- retrieval precision or skill-use frequency;
- distillation cost and amortized break-even task count.

Interpretation rule: token savings do not count if solved rate materially
drops. IG does not count as final evidence unless it predicts a live improvement.

## Decision / Next Step

Run experiment 1 and experiment 2 first. Freeze a small train-only trace subset,
create a short distilled prompt, and execute a paired held-out live comparison
with the same scaffold/model/decoding settings. Predeclare a solved-rate
non-inferiority margin and report bootstrap confidence intervals clustered by
task/project.

Do not begin RL, a large self-evolution loop, or broad harness mutation before
the simple distilled-prompt baseline shows useful signal. Preserve the current
IG work as an offline artifact-ranking tool, not as the main system claim.
