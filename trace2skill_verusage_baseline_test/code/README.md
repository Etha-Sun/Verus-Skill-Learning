# Delivered runtime components

`react_agent/` is the local ReAct runtime used by `verus_agent/`.
`verus_agent/` contains the VeruSAGE-adapted hands-off harness, IronKV training/evaluation runners, and the semantic-v4 consolidation implementation.
`skill_evolver/` is the Trace2Skill hierarchical MAP/REDUCE evolver used for the native-compression condition.
`analysis/` contains the two parsers directly imported by the training runner.

The delivery intentionally contains no local dataset, verified answer, full run, API payload, or credential. To execute the portable split/qualification scripts, set `IRONKV_DATASET_DIR`, `VERUSAGE_TASK_ROOT`, `VERUS_BIN`, and `LYNETTE_BIN` to local paths. Model credentials and external run roots are likewise local configuration, not repository artifacts.
