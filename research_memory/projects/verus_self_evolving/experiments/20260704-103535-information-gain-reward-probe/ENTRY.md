# information gain reward probe

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-07-04T10:35:35`
- status: `active`
- plan files:
  - `refine-logs/EXPERIMENT_PLAN.md`
  - `refine-logs/EXPERIMENT_PLAN_20260704_104500.md`
  - `refine-logs/EXPERIMENT_TRACKER.md`
  - `refine-logs/EXPERIMENT_TRACKER_20260704_104500.md`
- dataset/split: first version uses 20-50 verified hands-on VeruSAGE traces,
  train/dev only; final held-out traces reserved for later validation.
- stable prefix state: cut only after verifier feedback and before the next
  repair attempt, not at arbitrary token boundaries.
- prefix schedule: `early`, `middle`, `late` where available.
- baseline: trajectory prefix alone,
  `score_T(target | state_t)`.
- variant: trajectory prefix plus candidate artifact,
  `score_T(target | state_t, artifact)`.
- candidate artifacts:
  - no artifact baseline;
  - generic skill/rationale;
  - trace-derived rationale/counterexample-like explanation;
  - irrelevant control;
  - motif/TLA skill is nice-to-have, not first-pass must-run.
- metrics:
  - action information gain, first on VeruSAGE `primary_action`;
  - full-proof information gain, kept as a parallel metric;
  - patch-span information gain from deterministic proof-relevant diff;
  - main formula:
    `log P(target | state_t, artifact) - log P(target | state_t)`;
  - store both per-token probabilities and per-token logprobs for baseline and
    artifact-conditioned scoring;
  - positive/zero/negative IG rate by artifact type;
  - separation between trace-derived artifacts and irrelevant controls;
  - rank quality: whether useful artifacts rank above controls for the same
    trajectory prefix;
  - sensitivity across `IG_sum`, `IG_avg`, chunked full-proof score, and
    hunk-level patch score.
- leakage controls:
  - final proof text is used only as scoring target, never as candidate artifact
    input;
  - candidate generation sees only `state_t`, verifier errors, and allowed
    generic context;
  - do not evaluate promotion claims on the same exact traces used to mine
    candidate artifacts;
  - write all outputs under `verus-self-evolve-scaffold/runs/` or
    `research_memory/`, never raw data directories.
- scorer plan:
  - plan supports local and cloud scorers;
  - first implementation should try local QwQ-32B via HF/vLLM teacher-forced
    token logprobs;
  - DeepSeek/OpenAI/Gemini can expose output token logprobs, but cloud APIs
    should be treated as sensitivity/fallback unless they can score arbitrary
    target text cleanly.
- stop condition:
  - if trace-derived artifacts do not outperform irrelevant controls under
    action/full-proof/patch-span IG, do not build the full self-evolving loop
    yet;
  - if they separate cleanly, proceed to a selector/reranker prototype for
    `P(sampled_skill | skills, trajectory_t)`.

## Commands

```bash
# planned; exact command to be filled after inspecting current trace schema
python3 -m verus_self_evolve.experiments.information_gain_reward_probe \
  --input <verified_trace_manifest> \
  --output verus-self-evolve-scaffold/runs/information_gain_reward_probe_<date> \
  --limit 50
```

## Outputs

- run directory:
  `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704`
- plan/tracker/results:
  - `refine-logs/EXPERIMENT_PLAN.md`
  - `refine-logs/EXPERIMENT_TRACKER.md`
  - `refine-logs/EXPERIMENT_RESULTS.md`
  - `refine-logs/EXPERIMENT_CODE_REVIEW.md`
- implemented code:
  - `verus-self-evolve-scaffold/src/verus_self_evolve/ig_probe.py`
  - `verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py`
  - `verus-self-evolve-scaffold/src/verus_self_evolve/cli.py`
- run artifacts:
  - `traces.jsonl`
  - `prefix_manifest.jsonl`
  - `prefix_manifest.csv`
  - `targets.jsonl`
  - `patch_audit.jsonl`
  - `scoring_cases.jsonl`
  - `scoring_cases_no_code_explicit.jsonl`
  - `summary.json`
  - `report.md`
- logs: terminal commands recorded in `refine-logs/EXPERIMENT_RESULTS.md`
- metrics:
  - parsed verified traces: 3
  - usable prefix states: 7
  - targets: 28
  - scoring cases: 84
  - primary action coverage: 1.000
  - final proof coverage: 1.000
  - patch span non-empty rate: 1.000
  - patch fallback rate: 0.000
  - QwQ/vLLM action-primary cases scored: 21 raw + 21 explicit
- manifest:
  `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704/summary.json`

## Results

| metric | baseline | variant | delta |
|---|---:|---:|---:|
| R001 trace parsing | - | 3 verified traces / 7 prefixes | passed |
| R002 action target | - | coverage 1.000 | passed |
| R003 full-proof target | - | coverage 1.000 | passed |
| R004 patch-span target | - | non-empty 1.000 / fallback 0.000 | passed |
| scoring case builder | - | 84 cases | passed |
| R005 QwQ/vLLM scorer | - | token logprobs available | passed |
| R006 action IG raw prompt | artifact vs no artifact | all artifact means negative | measurement passed, prompt invalid |
| R006b action IG explicit prompt | artifact vs no artifact | trace mean 1.0817, generic mean 0.8894, irrelevant mean 0.6295 | measurement passed, method inconclusive |

## Interpretation

Initial interpretation:

- R001-R004 are implemented and pass a 3-trace CPU sanity run.
- The pipeline now produces action/full-proof/patch-span targets plus
  artifact-conditioned scoring cases.
- QwQ scoring works through vLLM prompt-logprobs using
  `<model-root>/QwQ-32B`. The HF route is not preferred because loading
  was too slow and base Python lacked `accelerate`.
- Raw action continuation is not a valid scoring query: all 21 action-primary
  cases had negative artifact IG. Explicit action-prediction prompting made most
  artifact IG values positive, with trace rationales highest on mean, but the
  irrelevant control also remained positive.
- Current method interpretation is therefore cautious: action IG is feasible as
  a measurement, but current templates do not yet provide clean evidence that
  trace-derived rationales are uniquely useful.

Planned interpretation rule:

- Supports the claim if trace-derived artifacts show consistently higher action,
  full-proof, or patch-span IG than irrelevant controls and produce a meaningful
  positive-IG rate.
- Inconclusive if only full-proof works, only one scorer works, or the effect is
  dominated by proof length/style.
- Refutes the immediate route if controls score similarly to real artifacts,
  suggesting the reward is too noisy for skill promotion.

## Next Action

1. Add stronger controls for action IG, e.g. shuffled trace rationales,
   wrong-error rationales, or same-length neutral Verus text.
2. Run patch-span IG next before full-proof IG; patch-span is more reviewer
   auditable and much cheaper than full final-code scoring.
3. Only scale beyond 3 traces after artifact/control separation improves under
   the explicit prompt.

## July 11 Correction

The corrected normalized-action run R017 failed the artifact-quality gate. Trace rationale beat shuffled rationale in `3/7` states and irrelevant control in `2/7`; generic skill mean PMI was negative. An independent audit also found one rejected action target and an in-sample four-action candidate set. The scorer is engineering-valid, but no skill-quality claim is supported. Future runs use accepted observed actions, a fixed 22-action ontology, exact intervention-token density, and durable paired analysis. See `experiments/20260711-145632-corrected-action-information-gain-pilot-and-audit/ENTRY.md`.
