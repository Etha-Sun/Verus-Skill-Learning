# Core code and reproduction

This is a reviewed compact publication of the two-task, three-arm experiment (24 continuations), not an archive of all local pilots. The report, figures, selected proof sources, start contracts and final validation summaries are included. Raw conversations, snapshots beyond selected starting/final code, API ledgers, credential files, model catalogs and tool binaries are not committed. Source hashes in `results.json` preserve endpoint provenance; this summary cannot replace raw process logs for independent event-by-event auditing.

## Code map

- [Continuation harness](../../skill-evolution-pilot/src/skill_evolution_pilot/codex_runner.py): checkpoint initialization, optional read-only reference, new session prompt, hash contract and existing isolation/validation.
- [SkillOpt runner adapter](../../skillopt-verusage/src/skillopt_verusage/codex_flash_runner.py): forwards continuation parameters to the harness.
- [Frozen extractor](../../scripts/audit_trajectory_progress.py): original Yuechun DeepSeek checkpoint semantics; hash enforced by preparation and scoring scripts.
- [Patch F1](../../src/verus_self_evolve/trajectory_progress.py): fixed original baseline B; score against original F or continuation final F′.
- [Greedy proof pruning](../../src/verus_self_evolve/proof_progress.py): existing `greedy_prune_proof_lines`; this package preserves actual verified pruned inputs instead of claiming to reproduce the historical pruning search from scratch.
- [Preparation](scripts/prepare_task.py): stage the published starts and references outside the repository; optionally compare all starts against the frozen extractor applied to the original external run.
- `scripts/run_{full_reference,pruned_reference,no_reference}_{IR,AL}.py`: six historical launchers with machine paths replaced by environment variables. Model, timeout, checkpoint loop, reference visibility, isolation flags and validation calls retain the historical settings. Original launcher hashes are in [launcher_provenance.json](launcher_provenance.json). These path-portable copies were checked locally without new provider calls.
- [Scoring](scripts/plot_three_groups.py), [token-aligned plotting](scripts/plot_token_groups.py): operate on external artifacts with the historical directory layout. Both current PNG/SVG/PDF figures are included.

## Runtime and preparation

The actual experiment used DeepSeek V4 Pro, native Responses bridge, high reasoning, blank skill, 600 seconds per start, context window 1048576. Historical Verus release: `0.2025.09.12.bb1f342`. Supply compatible Codex CLI, Verus/vstd/Rust and Lynette executables, and the native model catalog. Their host installations are not bundled; provider nondeterminism and runtime drift prevent a promise of identical regenerated traces.

From repository root, stage one of the six task/arm combinations into an external output directory:

```bash
python3 docs/deepseekv4pro-augmentation-20260911/scripts/prepare_task.py \
  --project IR --arm full_reference --out "$AUGMENT_TASK_DIR"
```

Add `--source-run "$ORIGINAL_PREDICTION_DIR"` to check the original extraction yields exactly the published events and hashes. Without that option preparation uses the reviewed frozen starts in this package; it does not invent new checkpoint selection.

Set `AUGMENT_TASK_DIR`, `RUST_ROOT` (cargo/ and rustup/), `VERUS_BIN`, `LYNETTE_BIN`, `CODEX_BIN`, `MODEL_CATALOG`, and `DEEPSEEK_ENV_FILE` externally. The credential file supplies `DEEPSEEK_API_KEY` and optionally `DEEPSEEK_BASE_URL`. Its contents are never part of this publication. For historically isolated arms also set `ISOLATION_SCRATCH_ROOT` and `VERUS_TOOLCHAIN_ROOT` consistently with the main harness isolation contract. `VERUS_BIN` must be a working executable or wrapper with its Rust environment configured.

```bash
python3 docs/deepseekv4pro-augmentation-20260911/scripts/run_full_reference_IR.py
```

The launcher performs live API calls and writes only into the external run directory. Run task launchers sequentially: historical bridge ports are shared. The legacy pruned-F/AL no-F isolation mismatch is retained for fidelity and explicitly reported; it is not a recommendation for future causal comparisons. The actual extra per-arm instructions are preserved in `protocols/`.

## Recompute figures from local artifacts

Set `AUGMENT_RUN_ROOT` to the external experiment root containing the historical groups: `alternative-path-tasks-v1`, `full-reference-two-task-v1`, `no-reference-isolated-v2` (IR only), and `no-reference-control-v1` (AL only). Each group has task-id directories with `continuation_NN` outputs; token plotting additionally requires their local `bridge_calls.jsonl`. Python needs matplotlib (and the repository modules used by the frozen extractor).

```bash
python3 docs/deepseekv4pro-augmentation-20260911/scripts/plot_three_groups.py
python3 docs/deepseekv4pro-augmentation-20260911/scripts/plot_token_groups.py
```

Outputs go to `$AUGMENT_RUN_ROOT/research-summary`. They include local score/token tables and ledger-derived plot data, not committed here. Readers without raw artifacts can inspect the committed figures and endpoint proof/hash comparisons but cannot independently reconstruct token timing from this compact publication.

[Main findings](README.md) · [Audit boundaries](AUDIT.md)

## Publication checks

- Existing `test_codex_runner.py`: 10 tests passed.
- Both preparation cases matched all 8 published starts against the original external runs using the frozen extractor.
- All 24 final-source SHA256 values and stored dual-validator success summaries matched their local artifacts. This is an artifact audit, not a new live proof-validation run.
- Portable scoring/plot scripts reproduced both published PNGs byte-for-byte from local artifacts.
- Python syntax, all local Markdown links, personal-path exclusion and credential-value exclusion checked.
- No new API rollout or optimizer training was performed for publication.
