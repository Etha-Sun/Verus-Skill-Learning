# Fixed Claude-Stratified AC/AL/IR Split

Date: 2026-08-14

## Contract

- Frozen sizes: 40 train / 20 selection (`val`) / 20 held-out test.
- Projects: AC and AL from Anvil, plus IR from IronKV.
- Historical outcome label: the final status in the Claude VeruSAGE
  `results.csv` files.
- `normal`: `VERIFIED`; `failed`: `FAILED` or `TIMEOUT`.
- Every split contains exactly 25% historical Claude failures.
- Selection and test use identical project/outcome quotas; train uses exactly
  twice those quotas.
- Previously used SkillOpt-100 and R040 tasks are excluded.
- No verified reference proof is included.

## Frozen Composition

| Split | AC | AL | IR | Claude failed | Claude normal | Total |
|---|---:|---:|---:|---:|---:|---:|
| Train | 12 | 14 | 14 | 10 | 30 | 40 |
| Selection | 6 | 7 | 7 | 5 | 15 | 20 |
| Test | 6 | 7 | 7 | 5 | 15 | 20 |

Within every `(project, Claude outcome)` stratum, tasks were ranked by the
mean percentile of source LoC, historical Claude runtime, and historical
Claude tokens. Adjacent difficulty quartets were assigned 2:1:1 to
train/selection/test. The resulting mean difficulty proxies are 0.503, 0.481,
and 0.520, respectively.

## Provenance And Integrity

- Candidate source: the local public VeruSAGE-Bench AC/AL/IR task checkout.
- Historical labels: `all_batch_results-cyy-claude/results-batch_*/results.csv`.
- All 143 post-exclusion candidates matched their historical Claude
  `fix-v0-input.rs` after removing only the harness-injected
  `#[verifier::loop_isolation(false)]` line and normalizing trailing whitespace.
- All 143 candidates failed the current Verus source precheck as expected;
  there were no precheck timeouts and no already-verified sources.
- The frozen 80 tasks have 80 unique task IDs and 80 unique source hashes,
  with zero cross-split exact overlap.
- Exclusions: 84 tasks used by the previous SkillOpt split and 28 tasks used by
  R040.
- MA/NR sealed directories were not read. Raw sources and historical results
  remained read-only.

Frozen split SHA-256:
`a71e2a3838c2222312cc2487fc35b6a24cbc924e0a917d5e9120499f0ba2b49c`.

## Artifacts

- Split root:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/fixed-claude-stratified-80-seed20260814/`
- Human-readable task list: `split_tasks.csv`
- Loader manifests: `train/items.json`, `val/items.json`, and `test/items.json`
- Audit summary: `split_manifest.json`
- Materialized reference-free inputs: `sources/`
- Reproduction code:
  `skillopt-verusage/src/skillopt_verusage/fixed_split.py`

## Validation And Scope

The frozen split loads successfully through `VeruSAGEDataLoader`; four focused
unit tests, Python compilation, mypy, source-hash checks, and uniqueness checks
pass. Historical Claude failure is a difficulty stratum, not ground truth that
another model will fail. The split is task-disjoint but not project-held-out:
AC tasks share substantial Anvil controller context, and all three splits use
the same AC/AL/IR families.
