# SkillOpt and Skill Entropy comparative literature review

## Scope

Compare Microsoft SkillOpt (arXiv:2605.23904v2) with Skill Entropy / Skill-Entropy
RL (arXiv:2608.05139v1), determine whether they optimize the same object, audit
their main evidence and limitations, and identify the narrow implications for
the Verus SkillOpt workstream.

## Sources

| source | link | why it matters |
|---|---|---|
| SkillOpt paper, v2, 2026-05-25 | https://arxiv.org/html/2605.23904 | Primary method, experiments, costs, and limitations |
| Skill Entropy paper, v1, 2026-08-05 | https://arxiv.org/html/2608.05139 | Primary definition, benchmark, RL reward, experiments, and appendices |
| SkillOpt code/docs | https://github.com/microsoft/SkillOpt | Released implementation and paper-style configuration |
| Skill Entropy code | https://github.com/Gen-Verse/Skill-Entropy-RL | Released benchmark/training implementation linked by the paper |
| Local SkillOpt feasibility proposal | `research_memory/projects/verus_self_evolving/ideas/20260806-022611-skillopt-on-verusage-feasibility-proposal/ENTRY.md` | Existing project adaptation contract |
| Local accepted/rejected audit | `research_memory/projects/verus_self_evolving/notes/20260818-161558-skillopt-accepted-versus-rejected-skill-case-study/ENTRY.md` | Evidence of monolithic-skill negative transfer |
| Local failure audit | `research_memory/projects/verus_self_evolving/notes/20260819-190726-skillopt-non-timeout-failure-audit/ENTRY.md` | Evidence that harness-invalid traces can contaminate skill learning |

## Method Patterns

The papers use the word *skill* for different objects.

| dimension | SkillOpt | Skill Entropy / Skill-Entropy RL |
|---|---|---|
| trainable object | one external natural-language skill document | model weights plus an emitted per-step skill-label plan |
| target model | frozen | post-trained with SFT and GRPO |
| feedback | scored agent rollouts and a held-out selection gate | step answers plus a scalar skill-entropy-rank reward |
| deployed state | compact `best_skill.md` | a new model checkpoint |
| main problem | how to improve reusable agent procedures | how to measure and train cross-skill switching |

SkillOpt separates the frozen target and optimizer. It analyzes success and
failure rollout minibatches, merges proposals, ranks bounded add/delete/replace
edits under a textual learning-rate budget, accepts only strict selection-score
improvements, remembers rejected edits, and performs an epoch-level slow/meta
update. Its default paper protocol uses four epochs, 40 training rollouts per
step, reflection minibatches of 8, edit budget 4 with cosine decay, and a
20-sample slow update.

Skill Entropy defines a directed transition score

`SkE(a,b) = (0.5 * (Acc(a) + Acc(b)) + 0.1) / (Acc(a,b) + 0.1)`.

It is an empirical performance ratio under a fixed reference model, not
Shannon entropy. Task entropy is the mean transition score along a skill
sequence. Skill-Entropy RL first teaches structured `<skill><answer>` outputs,
then combines mean step accuracy with a reward that matches the empirical-CDF
rank of the predicted sequence's *average entropy* to the gold sequence's
average-entropy rank. Predicted labels are mapped to the nearest canonical
skill with an embedding model.

## Evidence Assessment

SkillOpt reports best-or-tied performance in all 52 evaluated
(model, benchmark, harness) cells. For GPT-5.5, its average improvement over
no skill is +23.5 points in direct chat, +24.8 in Codex, and +19.1 in Claude
Code. The final skills contain 379--1,995 tokens and only 1--4 accepted edits,
but the six GPT-5.5 runs consume 20.8M--213.8M aggregate training tokens. The
paper uses disjoint test sets and useful component ablations, but does not
report repeated-seed uncertainty for the headline cells. Repeated adaptive
queries to a finite selection split can still overfit the gate. A strict
scalar score also cannot by itself protect security, cost, or subpopulation
performance. The authors explicitly acknowledge reliance on reliable
verifiers, offline rollout cost, and the limitation of one monolithic skill
in heterogeneous domains.

Skill Entropy evaluates 12 models on a 300-task synthetic test pool with four
samples and reports a broadly decreasing low/medium/high-entropy curve. The
clean causal comparison for its RL signal is not base-to-final: relative to
answer-only GRPO on the same data, the method adds +9.6 points for Qwen3-4B and
+7.9 for Qwen3-1.7B; the much larger 34.4-to-68.4 and 14.6-to-40.1 changes
also include SFT and RL. Off-the-shelf OpenR1-Math improves by +1.9 points over
GRPO on the six-benchmark average, while the five external-benchmark average
improves only +0.7 to +0.8 points.

The main Skill Entropy caveats are structural. The score is reference-model,
prompt, data-generation, and smoothing dependent; the implementation further
approximates fine-grained skill-to-skill transitions by skill-to-domain
switches. The benchmark's skill labels, scenarios, and filtering depend on
LLMs plus manual cluster review. Most importantly, the reward matches only one
scalar sequence-level entropy rank: different labels, orders, or transitions
can receive the same reward if their mean difficulty matches. It therefore
does not directly supervise the gold skill sequence despite the paper's
informal phrasing. The RL evaluation appendix also says the evaluated model
itself judges open-ended steps, whereas the benchmark evaluation and reported
human-agreement study use Claude-opus-4.7; this protocol difference needs an
independent-judge sensitivity check.

## Takeaways For This Project

1. The two papers are complementary, not direct competitors. SkillOpt is an
   external artifact optimizer; Skill Entropy is a switching diagnostic and
   weight-training signal.
2. The useful import is transition awareness, not the published entropy
   formula. The local accepted/rejected audit already shows that a narrow rule
   can solve one Verus item while causing three retained successes to time out.
   This is consistent with a routing/switching problem and strengthens the
   case for a short global core plus triggered cards with abstention.
3. If transition difficulty is tested in Verus, define it from fixed-harness,
   verifier-valid, task-held-out executions over explicit proof-state motifs
   (for example contract triage, quantifier instantiation, extensional bridge,
   invariant preservation), with directed paired outcomes and confidence
   intervals. Do not call an unvalidated ratio "entropy" or derive it from
   harness-invalid traces.
4. Keep the primary gate lexicographic: independent Verus+Lynette success and
   invalidity veto first, then regressions, tokens/cost, and wall time. A
   transition score can stratify diagnostics or route cards, but must not
   replace the live verifier endpoint.
5. Do not revise the locked S2 skill or inspect held-out test items from this
   literature result. The first useful experiment is a development-only
   comparison of global S2 versus S2 plus abstaining transition cards, after
   the nine harness-invalid IR tasks are repaired or excluded by a strict
   preflight.

## Gaps / Risks

- Both papers are arXiv preprints; no independent reproduction was evaluated.
- SkillOpt headline uncertainty and adaptive-selection overfit remain unclear.
- Skill Entropy needs label/transition ablations that distinguish scalar
  difficulty matching from correct per-step skill identification.
- The local Verus SkillOpt run has selection reuse, one rollout per checkpoint,
  timeout-coupled gains, no held-out test, and contaminated training evidence.
  It cannot validate either paper's broader claim.

## Decision / Next Action

Treat arXiv:2608.05139 as support for a transition-aware evaluation and
routing hypothesis, not as a replacement optimizer or an immediately valid
reward. Preserve the current S2 and test lock. Before new paid or held-out
execution, fix task/harness validity and predeclare a development-only
transition-card ablation with repeated paired seeds.

No raw or sealed dataset was read, modified, moved, or copied in this review.
Only public paper/code pages and reviewed compact repository memory were read.
