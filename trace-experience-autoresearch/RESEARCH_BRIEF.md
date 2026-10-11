# Open Research Brief: Learning From Agent Traces

## Research aim

Investigate how experience from agent execution traces can improve performance
on other problems of the same kind. Start with VeruSAGE and prioritize verified
success rate and token cost. Long traces may contain useful experience; whether
trace analysis is the principal bottleneck is an open empirical question.

The researcher may challenge the motivation, identify alternative bottlenecks,
and recommend a revised direction with evidence. Do not assume a particular
trace representation, memory format, extraction algorithm, or agent architecture.
Do not treat an existing implementation or a positive pilot as the desired answer.

## Initial setting

- Use the existing fixed training split of 40 tasks and development validation
  split of 20 tasks. Training-only internal held-out probes can support early
  iteration; keep their complete task ancestry out of extraction inputs.
- The evaluated repair agent is DeepSeek V4 Pro. Freeze its model/settings,
  evaluator, toolchain and online budget within each comparison. Treat analyzer
  model and controller model as distinct roles; hold analyzer resources constant
  in a mechanism comparison or explicitly study them as a separate factor.
- Default inference allowance is 600 seconds per task. The user permits extending
  to 900 seconds when justified. Predeclare an extension and give comparator
  arms the same allowance; report 600-second and 900-second findings separately.
  These are task inference limits, not research-controller time limits.
- No additional untouched test pool has been established. Validation has prior
  development exposure; establish test provenance/exposure before final claims.
  Do not read test traces or solutions to generate or select methods.
- Verus-specific claims can remain on VeruSAGE. A claim of general improvement
  in code generation requires later evaluation on a separate code benchmark.

## Independent opening pass

Start in a fresh research context with this brief, data schema, training-only
inputs, and a minimal executable evaluation interface. Do not seed that
context with repository idea notes, historical method proposals, learned memory,
preferred interventions, or outcome-selected examples.

Record alternative explanations, candidate approaches, predicted observable
behavior, and falsifying evidence before viewing the project's existing methods.
Then consult relevant literature and introduce existing methods as comparators,
with their provenance. Do not withhold unfavorable evidence once experiments or
comparison choices depend on it. Record when prior project information is exposed.

This is a context policy, not an implemented sandbox. The current chat already
knows previous ideas. An agent launched inside this repository may inherit root
instructions and memory; use a separate quest workspace with a reviewed input
packet and limited harness access to implement the intended separation. Verify
the actual startup prompt, available files, memory retrieval and tool access.
Reusing an evaluator does not require inheriting its author's proposed method.
Training traces still reflect their collection policy; a fresh context reduces
idea anchoring but does not remove sampling or collection-policy bias.

## Objectives and accounting

Report the success-versus-cost frontier rather than inventing one scalar score
or allowing trivial token savings through fewer attempted tasks. Use verified,
budgeted dual-pass success, retaining all scheduled failures and timeouts.

Track total actor input/output/reasoning/cache token usage, actual monetary cost,
wall time and timeout rate. Report extraction/learning cost and research-controller
cost separately, plus total campaign cost. The user excludes research-controller
consumption from the method's inference resource limit and optimization target;
keep that consumption visible in a separate ledger. Show amortized learning cost for explicit
deployment volumes. Cache billing discounts do not by themselves prove reduced
token usage. Joint-success comparisons are useful diagnostics, not substitutes
for the all-attempt comparison. Do not imply that a small observed tie proves
noninferiority or that repeated runs are independent tasks.

Freeze task selection, baselines, budgets and primary comparisons before each
run; use paired tasks and record random settings and all attempts. Revisit those
choices between rounds through versioned contracts, not after seeing a round's
outcomes. No numerical success/cost exchange rate or total campaign monetary cap
was specified. Start with bounded stages and explicitly limited experiment batches;
do not interpret task-level inference allowance as authorization for unlimited runs.

## Required experiment interpretation

For every experiment, record:

1. Hypothesis, competing explanation, predicted behavioral change and a result
   that would count against the hypothesis.
2. Baseline, changed factor(s), immutable controls and resource allowances.
3. All task outcomes, success/cost tradeoffs, variability and accounting gaps.
4. Explanations for positive, negative and null results; distinguish unsupported
   mechanism, insufficient evidence, implementation failure and task mismatch.
5. A reasoned continue, revise, compare or stop decision. Positive outcomes need
   skeptical checks as much as negative outcomes need diagnosis.

## Case studies and mechanism evidence

Every comparison needs trace-grounded case analysis. Cover observed gain and
regression tasks, persistent failures, and resource savings or overruns among
common successes, when those categories exist. Include task counts and explain
case selection; never manufacture a representative case or hide counterexamples.

For each case, show the task requirement, relevant prior experience and provenance,
whether and when it was accessed, what action changed, and the actual code/tool/
verifier evidence that followed. Locate where tokens were saved or wasted.
If state or events were not recorded, mark the causal link unknown.

Distinguish levels of support: observed association; evidence consistent with a
mechanism; and a controlled intervention supporting that mechanism locally.
Reading a lesson followed by success does not prove the lesson caused success.
Use the smallest useful ablation, matched rerun or intervention when an important
claim needs it; charge that work to the campaign budget. Selected qualitative
examples explain and challenge aggregate findings, not establish transfer alone.

## Direction changes and execution boundaries

The user confirmed the working scope as the experience extraction-transfer-use
chain and instructed the project to start. If a different bottleneck dominates, document the
evidence, old and new questions, predictions, and consequences for comparisons.
A generic harness improvement can be a control or infrastructure fix; it does
not automatically establish improved experience learning. Unrelated VeruSAGE
optimization is outside the confirmed research scope.

Preserve raw/sealed inputs and source provenance. Keep generated outputs below
the selected external run root. Starting research is now authorized. The initial
stage is independent framing and local readiness diagnostics; before actor batches,
freeze their task membership, exact comparison and enforceable resource limits.
Service startup alone does not establish model connectivity or live evaluation.
