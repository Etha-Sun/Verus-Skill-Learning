# Frozen checkpoint contract

This publication covers only IR `3a77a3e4e72edf600e2a` (6 starts) and AL `6fc5661ffaeee1c57342` (2 starts), from the unchanged fixed train-40. See [tasks.json](tasks.json) for source paths, original event indices and checkpoint SHA256 values.

Extraction uses [`scripts/audit_trajectory_progress.py::_load_run`](../../scripts/audit_trajectory_progress.py) at SHA256 `642f76ab5774df0685f1268cccf49802cee9ef1f9649c012ea38dae45331ab0e`.

1. Read only `actor == verus` and `type == verifier` events.
2. Match `candidate_sha256` against saved candidate snapshots.
3. Globally deduplicate candidate hashes, preserving first event order.
4. Append terminal source if its hash was unseen.
5. For continuation, exclude the original terminal F hash. Keep every other extracted state, including already-verified states. Do not manually select individual checkpoints or substitute edit boundaries.

The three arms have byte-identical starts. Continuation launches a new session with original task `input.rs` and checkpoint `candidate.rs`, plus read-only full/pruned reference only in the reference-visible arms. **Original conversation prefixes are not passed.** The result is a continuation suffix, not a replay of the original full conversation.

Token figures preserve this extractor. The two panels share exactly the same checkpoint events and cumulative completion-token coordinates. Token accounting uses local bridge request ledgers, including reasoning once; input tokens are excluded. Raw ledgers and traces remain external. Duplicate verifier calls are omitted from both plotted panels; the plot is not a complete tool-call timeline.

[Preparation / frozen-extractor verification](scripts/prepare_task.py) · [Experiment report](README.md)
