# Hands-off trace distillation long-horizon experiment roadmap

## Run Contract

- project: verus_self_evolving
- created_at: 2026-07-19T10:37:27
- status: complete
- objective: freeze a claim-driven, gated roadmap for distilling reusable
  knowledge from frontier-agent hands-off Verus trajectories and measuring
  live inference cost reduction
- dataset/split: provisional train AC/AL/IR, dev OS/VE/ST/NO (10 existing
  tasks), sealed test MA/NR (27 existing tasks); M0 must audit and freeze
  mappings before any outcome is viewed
- baseline: original hands-off prompt under the same Copilot agent scaffold,
  frontier model, tools, permissions, task snapshot, and run budget
- variants: length-matched generic control; <=800-token trace-distilled prompt;
  compressed/retrieved skills only after the simple prompt passes its dev gate
- primary metrics: security-valid solved rate and total uncached tokens per
  solved task, including all failed-task cost
- secondary metrics: input/cache/output tokens, wall time, tool/verifier calls,
  illegal-edit rate, GPU/model cost, one-time distillation cost, break-even task
  count, and offline IG only as a diagnostic
- leakage controls: project holdout, task/source/spec hashes, target-function
  and lemma overlap, near-duplicate grouping, sealed test outputs, and one test
  pass after prompt freeze
- stop condition: do not launch confirmatory frontier/GPU runs unless corpus
  provenance, leakage, usage accounting, prompt injection, and safety-check
  smokes pass; stop/redesign if the dev trace prompt loses more than one solve,
  saves <15% tokens/solved, or does not beat the generic control

## Commands

Planning-only turn; no model or GPU runs were launched.

    python3 research_memory/scripts/mem.py index

## Outputs

- canonical plan: refine-logs/EXPERIMENT_PLAN.md
- versioned plan: refine-logs/EXPERIMENT_PLAN_20260719_103128.md
- canonical tracker: refine-logs/EXPERIMENT_TRACKER.md
- versioned tracker: refine-logs/EXPERIMENT_TRACKER_20260719_103128.md
- archived prior IG tracker:
  refine-logs/EXPERIMENT_TRACKER_20260714_163854.md
- planned run root: runs/handsoff_distill_20260719/
- meeting constraint source:
  research_memory/projects/verus_self_evolving/meetings/20260718-112059-hands-off-trajectory-distillation-and-inference-cost-objective/ENTRY.md

## Results

No experimental result was produced in this planning turn.

The roadmap freezes two maximum core claims:

1. same-model/same-scaffold trace knowledge preserves held-out solved rate while
   reducing uncached tokens per solved task;
2. the same frozen knowledge improves a local 27B model and narrows its gap to
   the frontier no-knowledge baseline.

Five experiment blocks and runs R036-R061 cover corpus/harness integrity,
same-model live evaluation, mechanism/simplicity controls, cross-model transfer,
and failure/amortized-cost analysis.

## Interpretation

The project is ready to begin data and harness sanity work, not yet ready for a
method claim or expensive confirmatory run. The main live metric replaces IG as
the decision endpoint; IG remains conditional artifact-ranking evidence.

The plan deliberately treats the existing 27-task sealed test as potentially
underpowered. R045 must estimate sensitivity from the reproduced baseline. If
the predefined non-inferiority target cannot be supported, the test set must be
expanded or the conclusion labeled a pilot.

## Next Action

Execute R036-R039 only:

1. build the read-only corpus inventory;
2. freeze and audit the project split;
3. implement/test the unified Copilot prompt/usage/safety wrapper;
4. run one non-sealed H0/H1/H2 mechanical smoke.

All frontier/GPU method runs stay blocked until these integrity gates pass.
