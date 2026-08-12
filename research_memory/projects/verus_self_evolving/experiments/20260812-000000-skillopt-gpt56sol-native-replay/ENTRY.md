# SkillOpt GPT-5.6 Sol Native Optimizer Replay

Date: 2026-08-12

## Objective

Test whether replacing the failed DeepSeek-Flash optimizer with local Codex
GPT-5.6 Sol can produce a better SkillOpt update from the already-completed
40-task robust-v5 rollout, then evaluate that update on the same frozen
20-task DeepSeek-V4-Flash selection gate.

## Contract

- Reuse only the stored 40 training trajectories from robust v5; do not rerun
  training tasks.
- Preserve native SkillOpt reflection, merge, ranking, patch application, and
  strict hard-score gate semantics.
- Use local Codex quota for the optimizer with no artificial completion-token
  cap and no network access.
- Keep the candidate below 4,000 bytes and reject task identifiers, concrete
  task formulas, verification-bypass instructions, blanket bans on frozen
  trusted context, or unapplied edits.
- Evaluate only the frozen 20-task selection split with DeepSeek-V4-Flash.
  Do not open the 40-task held-out test.
- Require approval before conservative DeepSeek exposure exceeds USD 20.

## Actions

1. Added a resume-safe stored-rollout optimizer entry point and a prompt-free
   per-call Codex token ledger.
2. Ran native reflection on 32 failures and 8 successes: four failure
   minibatches and one success minibatch.
3. Ran native failure merge, final merge, and ranking. The initial four-edit
   candidate was 4,109 bytes, so native ranking was rerun at L=3 rather than
   manually editing model output.
4. Automatically and manually audited the resulting 3,490-byte candidate.
5. Ran the same 20 selection tasks through the robust Flash harness with a
   configured 60-task worker pool and the shared conservative budget guard.

## Durable Evidence

- Run root:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-gpt56sol-reopt-v5-20260811/`
- Optimizer result: `optimizer_result.json`
- Candidate: `candidate_skill.md`
- Prompt-free optimizer ledger: `optimizer_calls.jsonl`
- Automatic/manual audit: `optimizer_result.json`, `manual_audit.json`
- Gate result: `gate_result.json`
- Paired outcomes: `paired_selection_results.json`
- DeepSeek budget and cost: `deepseek_gate_budget.json`, `cost_ledger.json`
- Archived zero-cost environment preflight failure:
  `preflight-failure-base-python-20260811/`

## Result

Optimizer:

- model/backend: GPT-5.6 Sol through local Codex quota;
- calls: 8 = 5 analyst + 2 merge + 1 ranking;
- tokens: 246,313 prompt + 11,184 completion;
- metered API dollar cost: USD 0;
- candidate: 3 edits, 3,490 bytes, SHA
  `ee73bdc4c1e226d9c71ee636a4164cb379896212e8650a0a8f229f3cfb48097a`;
- automatic and manual contract audits: pass.

Selection gate:

- S0 baseline: 6/20;
- GPT-5.6-Sol-generated candidate: 4/20;
- action: reject;
- paired transitions: 14 fail-to-fail, 0 fail-to-pass, 2 pass-to-fail,
  4 pass-to-pass;
- requests: 1,627;
- prompt tokens: 12,924,510 = 9,559,168 cache hit + 3,365,342 cache miss;
- completion tokens: 5,446,664;
- Flash cost: USD 2.0229794704;
- response integrity: 1,613 accepted responses, 13 explicit length rejects,
  1 explicit empty-content reject, 0 silent truncations, 0 invalid tasks, and
  0 uncertain spend.

The prior confirmed estimated DeepSeek spend was USD 9.078453, so adding this
gate gives approximately USD 11.101432 confirmed estimated spend. Including
the earlier worst-case interrupted-call exposure, the conservative total is
USD 19.1068324704, below the USD 20 approval threshold.

## Interpretation and Decision

The stronger optimizer fixed the obvious semantic and size failures of the
Flash-generated 10,322-byte skill, but optimizer capability alone was not
sufficient: the compact audit-clean global skill still failed the live gate,
introduced no new solves, lost two baseline solves, and more than doubled gate
cost relative to robust v5's S0 selection run.

This is a valid negative selection result, not held-out-test evidence. Because
there was no fresh S0 A/A repeat, stochastic target variance remains a causal
confounder; the two paired regressions cannot be attributed entirely to the
new skill. Do not run epoch 2 or the held-out test. The next reviewed experiment
should add S0 A/A variability measurement and test typed, replay-supported,
proof-state-conditioned retrieval cards with abstention rather than another
global skill expansion.

## Data Safety

Raw split data and all source files remained read-only. Generated prompts,
traces, task workspaces, token ledgers, and complete run outputs stayed below
`VERUS_SKILL_RUN_ROOT`. The held-out test split and sealed MA/NR data were not
evaluated or exposed to either model.
