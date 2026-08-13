# IronKV Claude-to-DeepSeek Trace2Skill-Style 77/77 Experiment

This experiment is cross-model skill distillation, not self-evolution:

- teacher trajectories: Claude Sonnet 4.5 successful IronKV runs;
- skill construction: Trace2Skill-style trajectory-local patches and hierarchical consolidation;
- student and held-out evaluator: DeepSeek API;
- skill representation: raw Trace2Skill `(M, R)` output, with no additional de-specialization pass.

## Frozen split

The dataset contains 154 complete triplets. The frozen split contains 77 evolution/train tasks and 77 held-out tasks. Run:

```bash
python verus_agent/experiments/ironkv_claude_to_deepseek_77_77/build_split.py
```

The builder refuses to overwrite a populated split directory unless `--force` is supplied.

## Leakage controls

Tasks are joined into an indivisible component when any of the following holds:

1. the target function name is identical;
2. the names are explicit wrapper variants such as `_auto`, `_temp`, the observed `send_packet-poly`/`send_packet_seq` pair, or members of the `retransmit_un_acked_packets*` helper family;
3. identifier-normalized source-code 7-token-shingle Jaccard similarity is at least 0.80;
4. identifier-normalized proof-delta 5-token-shingle Jaccard similarity is at least 0.80.

Only whole components are assigned. The optimizer then finds an exact 77/77 split while balancing module counts and trajectory volume. The final audit requires no shared target/canonical-target name and both cross-split maximum similarities to remain below their grouping thresholds.

`heldout_tasks.jsonl` deliberately contains only original `.rs` paths and hashes. Held-out `.log` and `_verified.rs` files must not be mounted into or passed to the solver workspace. They are labels for later evaluation only.

## Files

- `split/split_manifest.json`: protocol, thresholds, counts, and module balance;
- `split/train_trajectories.jsonl`: train source, trajectory, and verified-proof metadata;
- `split/heldout_tasks.jsonl`: held-out original tasks only;
- `split/train_ids.txt`: frozen train task IDs;
- `split/heldout_ids.txt`: frozen held-out task IDs;
- `split/leakage_audit.json`: component assignments, grouping evidence, and audit results.

The split reduces identifiable sibling leakage but cannot prove semantic independence: every task still belongs to the same IronKV codebase and shares domain definitions.
