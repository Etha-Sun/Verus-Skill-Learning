# Qwen3.6 Three-Target Experiment Tracker

| Run ID | Milestone | Purpose | Target | Split | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| R027 | M0 | acquire/model audit | model | Qwen3.6-27B | MUST | DONE | 52 GiB; vLLM 0.19.1; hashes in M0_AUDIT.md |
| R028 | M0 | build exact-matched cases | all three | 3 traces / 6 states | MUST | DONE | 126 cases; proof hashes pass; max sequence 78,392 |
| R029 | M0 | unit/integrity tests | scorer | synthetic + cases | MUST | DONE | 24/24; tqdm, atomic resume, 512-token chunks; exact run needs no sliding |
| R030 | M0 | independent code review | implementation | read-only | MUST | DONE | blocker resolved with exact 131,072 context; vLLM integration remains R031 gate |
| R031 | M1 | one-state sanity | all three | 1 state / all controls | MUST | TODO | mechanical gate only |
| R032 | M2 | full action run | action | 6 states / all controls | MUST | TODO | cannot stop proof runs |
| R033 | M2 | full patch run | patch | 6 states / all controls | MUST | TODO | token/hunk tables |
| R034 | M2 | full proof run | final `.rs` | 6 states / all controls | MUST | TODO | tqdm + resume required |
| R035 | M3 | analysis and audit | all three | completed outputs | MUST | TODO | cross-target figures and claims |
