# Runtime and reproducibility

This is a reviewed publication of the 0916 initial-skill experiment, not a complete raw-run archive. Reports and plots are inspectable without API access. Re-running requires authorized access to the original step_0001 prediction directories, their original raw/structured events and snapshots, plus compatible local tooling. The three original trajectories are not bundled; complete hindsight input cannot be reconstructed from only the published final proofs and selected diffs.

## Frozen inputs

- Train40 SHA256: `0e42aad8c5e8a6789d06e7b15cfdca903479b16dc76f863544f219e6bbe40536`.
- Yuechun extractor `scripts/audit_trajectory_progress.py` SHA256: `642f76ab5774df0685f1268cccf49802cee9ef1f9649c012ea38dae45331ab0e`.
- Initial skill SHA256: `96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`.
- Each project's `checkpoints.json` records original events and code hashes; `selection_manifest.json` supplies the historical selection expected by the runner.
- Exact versioned prompts are in `prompts/v1` and `prompts/v2`; the runner's default repository prompt is v1. Always set `prompt_dir` explicitly for v2.

## Configuration templates

Copy a `{ir,ac,al}/{v1,v2}/config.example.json` to an **external** run directory and replace every `<SET_...>` value with an absolute path. No environment-variable interpolation is performed by the runner.

| Field | Required local value |
|---|---|
| output_root | Fresh external output directory, never inside this repository |
| original_run | Original task prediction directory under step_0001; name must equal task_id |
| original_selection_manifest | This package's project/selection_manifest.json |
| prompt_dir / actor_skill_file / actor_protocol | This package's prompts/version, initial.md, actor_protocol.txt |
| credential_file | External file defining DEEPSEEK_API_KEY and optionally DEEPSEEK_BASE_URL; never commit it |
| codex_bin / verus_bin / lynette_bin | Compatible installed executables; Verus wrapper must configure Rust |
| verus_root / rust_root / scratch_root | Toolchain and isolation roots consistent with the harness |
| model_catalog | Original compatible native Responses model catalog |
| old_reference_dir | Existing historical reference directory to deny actor access to |
| v1_root | Matching external v1 output root, for comparison plotting |

Historical runtime: DeepSeek v4 Pro, native Responses bridge, high reasoning, actor 600s, hint max_output_tokens 8192, hint request timeout 540s. Historical Verus release used the 0.2025.09.12.bb1f342 toolchain. Tool availability and provider changes may prevent exact reruns; samples are nondeterministic. The scripts require repository packages plus jsonschema and matplotlib.

From repository root, preparation is local-only; `run` and `hint` make live provider calls:

```bash
python3 skillopt-verusage/scripts/run_hint_augmentation.py --config "$CONFIG_FILE" prepare
python3 skillopt-verusage/scripts/run_hint_augmentation.py --config "$CONFIG_FILE" run --checkpoints 1
```

For the entire project, first prepare both external v1/v2 roots and store their filled configs and selection.json. Then the portable queue script runs each selected checkpoint and exports evidence/plots:

```bash
python3 docs/hint-augmentation-20260916/scripts/run_project.py "$PROJECT_RUN_ROOT"
```

The script is not itself a daemon; use the server's normal detached-job mechanism for long runs. Use independent ports and directories for concurrent projects. A blocked checkpoint is preserved while independent points continue. Do not copy a historical manual screen override onto a freshly generated hint. Review each new block separately; historical CP2 evidence is not authorization to approve a different output.

## Plotting and audit

With the original external layout, provider ledgers and full run outputs:

```bash
python3 docs/hint-augmentation-20260916/scripts/summarize_task.py "$VERSION_RUN_ROOT"
python3 docs/hint-augmentation-20260916/scripts/compare_versions.py "$V2_RUN_ROOT"
```

These are path-portable copies of the actual scripts, not replacements for the checkpoint extractor. They preserve an existing semantic_audit.json report by writing refreshed auto evidence separately. The published comparison.json files retain the plot coordinates; raw ledgers remain external. Output tokens include reasoning once; attribution includes original prefix cost, but the actor did not replay that prefix. The hint generation cost is separate. Patch F1 is reference similarity, not a universal measure of correctness.

The published PROCESS.md files contain all captured source changes plus abbreviated checker feedback, not full tool histories. Final result.json retains complete final host diagnostics with paths redacted. The original unredacted sources remain external. Code/source hashes are preserved; publication_provenance.json distinguishes exact copies from path-portable adaptations.

## Checks for this publication

Run offline prompt-boundary tests with:

```bash
python3 -m unittest discover -s skillopt-verusage/tests -p test_hint_augmentation.py -v
```

Publication review also checks all relative links, 38 unique result identities, checkpoint/final/skill hashes, equality of frozen prompts across tasks per version, portable script syntax and absence of credentials or personal host paths. No live API calls are needed for those checks. None of these checks establishes downstream SkillOpt benefit.
