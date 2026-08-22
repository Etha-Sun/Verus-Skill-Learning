# Experiment Tracker: V-FACE

| Run ID | Milestone | Purpose | Split | Priority | Budget | Status | Decision |
|---|---|---|---|---|---|---|---|
| R001 | M0 | unused-pool metadata inventory | candidate pool | MUST | CPU | TODO | enough eligible tasks? |
| R002 | M0 | hash/declaration/lemma-family contamination graph | candidate pool | MUST | CPU | TODO | freeze Build/Evaluation manifests |
| R003 | M1 | static instantiation on 30 checkpoints | Build | MUST | CPU | TODO | ≥18/30? |
| R004 | M1 | blind semantic/locality/fidelity audit | Build | MUST | CPU + 2 annotators | TODO | ≥90%, 100%, ≤5%? |
| R005 | M1 | identity/mismatch controls | Build | MUST | CPU | TODO | no systematic target improvement? |
| R006 | M2 | 3+3 exposure replicate stability dry run | Build | MUST after M1 | ≤2 GPUh/API eq. | BLOCKED | label stable/conclusive? |
| R007 | M3 | freeze/hash all baseline decisions | Evaluation | MUST after M2 | CPU | BLOCKED | coverage≥40% predicted? |
| R008 | M3 | randomized exposure outcomes | Evaluation | MUST | ≤4 GPUh/API eq. | BLOCKED | score prospective decisions |
| R009 | M3 | equal-budget CAR/TRACE protocol runs | Build/Evaluation | MUST | ≤2 GPUh/API eq. | BLOCKED | strongest baseline established |
| R010 | M3 | clustered statistics + failure taxonomy | Evaluation | MUST | CPU | BLOCKED | C1 pass/audit-only/stop |
| R011 | M4 | new sealed end-task preregistration | new sealed | FUTURE | separate | NOT STARTED | only if C1 passes |

**Current next run**: R001.
**Hard stop**: do not start R006 unless R003–R005 pass; do not start R011 in this workflow.
