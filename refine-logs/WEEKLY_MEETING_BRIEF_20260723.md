# Weekly Research Update

| Component | Setup | Main Result | Takeaway |
|---|---|---|---|
| Qwen capability calibration | Qwen3.6-27B on 30 Verus repair tasks | **7/30 solved (23.3%)** | Qwen has basic repair ability but limited stability. |
| Trace distillation | Qwen summarized 30 successful training traces into a 632-token global prompt | H0: **5/9**; generic H1: **5/9**; distilled H2: **4/9** | Small-model batch summarization did not produce effective transferable knowledge. |
| Inference cost | Same three cases and matched experimental conditions | H2 used **4.449M tokens**, versus **3.503M** for H0 | H2 consumed approximately **27% more tokens** without improving success. |
| ATLAS diagnosis | Qwen3.6-27B vs. `gpt-5.6-sol/high` on 8 failure traces | Same coarse label on **7/8** traces; blinded quality score: **36 vs. 45** | Qwen recognized broad failure patterns, while the frontier model produced more specific and actionable diagnoses. |
| Codex exploration baseline | Fresh Codex exploration on three selected tasks without prior traces or rationales | **3/3 solved** | The tasks are solvable through strong, task-specific exploration. |
| Next step | Frontier-model trace analysis and skill extraction | Per-trace diagnosis → causal attribution → cross-trace consolidation | Keep Qwen H2 as a weak-distiller baseline and compare it with frontier-distilled and state-specific skills. |

## Per-Task Results

| Frozen case | Qwen H0 | Qwen H1 | Qwen H2 | Codex | Task |
|---|---:|---:|---:|---:|---|
| Stable pass | **3/3** | **3/3** | **2/3** | **1/1** | `seq_filter_contains_implies_seq_contains` |
| Stable closest failure | **0/3** | **0/3** | **0/3** | **1/1** | `marshal_v__impl2__lemma_serialize_injective` |
| Unstable | **2/3** | **2/3** | **2/3** | **1/1** | `marshal_v__impl5__lemma_same_views_serialize_the_same` |
| **Total** | **5/9** | **5/9** | **4/9** | **3/3** | Three selected tasks |

H0, H1, and H2 used Qwen3.6-27B with three independent runs per task and
condition. Codex used `gpt-5.6-sol/high` with one fresh run per task, so its
3/3 result is a qualitative exploration baseline rather than a
repetition-matched statistical comparison.
