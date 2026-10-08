# Train40 rerun checklist

- [x] User authorized DeepSeek V4 Pro and 1,800 seconds per task.
- [x] Train40 has 40 unique tasks and all source hashes match.
- [x] Initial 838-byte skill hash is fixed.
- [x] Formal repaired Verus identity passes.
- [x] Namespace isolation host preflight passes.
- [x] Native request output-cap forwarding regression tests pass.
- [x] DeepSeek credential supplied locally, without exposing the secret.
- [x] Authenticated provider model listing contains DeepSeek V4 Pro.
- [x] Full isolated toolchain probe on a historical crate-alias input passes.
- [x] Fresh external run/configuration and explicit request cap frozen.
- [x] First included task passes actual provider/fidelity gate; remaining 39 admitted.
- [x] Full run launched in detached tmux with durable outputs and accounting.
- [x] Higher concurrency authorized; graceful drain and eight-worker continuation queued.
- [x] Eight-worker continuation health verified after current actors drain.
- [x] Exactly 40 task results and settled provider ledgers collected.
- [x] Inputs/skill still match hashes after execution.
- [x] Validity, solves, failures, time, tokens, and recorded cost audited.
- [ ] Final provider billing reconciled: one open reservation remains after timeout.
- [x] Preparation recorded in repository-canonical research memory.

Outcome status: complete and audited; 39/40 solved, one valid timeout. No task
retried during the concurrency transition. Recorded settled cost is about
USD 5.68, but final billing is unresolved due to one open reservation. No actors
or coordinators remain active. Next: review the single regressed AL trajectory;
no additional paid execution is authorized by this closeout.
