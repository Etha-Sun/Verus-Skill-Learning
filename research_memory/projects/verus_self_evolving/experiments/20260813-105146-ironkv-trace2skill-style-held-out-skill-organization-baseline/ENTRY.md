# IronKV Trace2Skill-style held-out skill organization baseline

## Run Contract

- project: `verus_self_evolving`
- dataset/split: 77 IronKV Claude Sonnet trajectories for skill construction; a leakage-controlled, deterministically selected held-out set of 15 tasks. Held-out trajectories and verified solutions were never exposed to the DeepSeek proof agent.
- baseline: `deepseek-v4-pro` hands-off Verus repair without learned skill context.
- variants: native Trace2Skill MAP/REDUCE `(M,R)` skill and a DeepSeek-induced semantic-v4 `(M,R)` skill.
- metrics: verifier- and Lynette-validated task success, effective ReAct action turns, M/R reference consultations, and contract/source preservation.
- leakage controls: held-out component overlap count zero; original source immutable; candidate proof must pass Verus and Lynette; function contracts are compared post hoc for new successes.
- stop condition: 40 effective action turns for Stage A; a selected six-task 60-turn fresh resample for Stage B. After an effective edit-to-Verus cycle, the shared host stops after 13 consecutive tool turns without material proof progress.

## Commands

The public bundle contains the exercised harness, evolver, prompts, schemas, and tests under `trace2skill_verusage_baseline_test/code/`. Re-running requires a locally configured Verus/Lynette installation, model endpoint, and external data/run roots; none are bundled.

## Public Outputs

- detailed report: `trace2skill_verusage_baseline_test/README.md`
- final native and semantic-v4 skills: `trace2skill_verusage_baseline_test/skills/`
- compact split/training/evaluation audits: `trace2skill_verusage_baseline_test/results/`
- harness/evolver code and offline tests: `trace2skill_verusage_baseline_test/code/` and `trace2skill_verusage_baseline_test/tests/`

Raw trajectories, verified solutions, complete agent runs, API payloads, token/usage records, and credentials are deliberately excluded.

## Results

| condition | held-out Stage A (15 tasks, 40 turns) |
|---|---:|
| No skill | 8/15 |
| Native MAP/REDUCE skill | 7/15 |
| Semantic-v4 skill | 8/15 |

Semantic-v4 changed the solved-task set: it solved task 3 that no-skill missed, but missed no-skill-only task 6. On the seven shared successes, it used fewer effective action turns on five (155 combined turns for no-skill versus 123 for semantic-v4). A selected Stage-B fresh 60-turn resample was 1/6 no-skill and 3/6 semantic-v4; it is not aggregated into the Stage-A 15-task score.

## Interpretation

This is a leakage-controlled baseline study of skill organization, not a demonstrated general solved-rate or cost improvement. Native textual MAP/REDUCE over-compressed heterogeneous IronKV mechanisms into one catch-all reference. The semantic `(M,R)` form retained 14 bounded references and yielded a promising but small selected-resample signal. In observed semantic successes, the root procedure was sufficient without opening R; the large reference map embedded in M should be ablated from the core procedure in future work.

## Next Action

Run a preregistered held-out comparison of no-skill, M-only core procedure, M+index, and M+index+R, then assess whether selective skill self-evolution improves the frozen evaluation protocol.
