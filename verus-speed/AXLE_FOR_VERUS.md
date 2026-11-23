# AXLE for Verus: what AXLE does, what Verus has, what we built

Sources: AXLE docs (every tool page, `axle.axiommath.ai/v1/docs/`), its
changelog v1.0.0-v1.9.1, the paper (arXiv 2606.26442, read in full), the
public client code, and live API calls; Verus source at our release
(bb1f342) and at main (1ce6a59), verus-analyzer, lynette, VeruSAGE, SeVerus.
Collected 2026-11-22. AXLE's server code is not public.

## 1. Where AXLE's speed comes from

| AXLE mechanism | Evidence | Verus today | What we did |
|---|---|---|---|
| Warm, pre-built environment: the import header is replaced by a cached `import Mathlib` environment | raw Lean 5.14 s → 1.05 s median; a non-default import costs 14 s | No reuse at all: every call starts a process, loads the rustc library, deserializes all of vstd.vir (≈170 ms) and re-checks vstd in merged-crate passes | Resident `rust_verify --internal-serve` with an import cache (patch, section 3) |
| Response cache for identical requests | `cached_response: true` seen live | none | `verus_serve.Pool(cache=True)` |
| No environment replay in `verify_proof` (trusts elaboration) | 0.97 s vs SafeVerify 10.1 s, Comparator 95.7 s | Verus has no replay step; trust checks are cheap text/AST checks | `verify_proof.py` runs the 0.1 s structural check in parallel with verification |
| Elaborate only selected declarations (`names`/`indices`, `permitted_sorries`, `elaborate_proofs=false`) | changelog v1.5-v1.9 | `--verify-function`/`--verify-only-module` filter SMT only; the whole crate still goes through rustc and VIR | measured: single-function check in a repo is 3.5-13.5 s, almost all front end |
| Concurrency, queueing, fair share, autoscaling | linear to vCPU count | one process per file already scales; inside a file only modules run in parallel | pool of resident workers |
| Executor pool rework, warm-up removed (v1.1.0) | −50% latency | n/a | — |

## 2. AXLE's tools and their Verus counterparts

| AXLE tool | What it does | Verus counterpart | Status here |
|---|---|---|---|
| `check` | compile; escapes only warned | `verus FILE` | resident pool |
| `verify_proof` | candidate must match `formal_statement` (types, defs), no sorry, axiom whitelist, no unsafe / `open private`; no environment replay | lynette `additions` (proof-only change), `--no-cheating` (rejects stubs, so unusable on VeruSAGE tasks), SeVerus `make anticheat` | `verify_proof.py`: token-level escape check per function + `lynette additions`; adversarial evaluation in `cheat_eval.py` |
| `simplify_theorems` | remove unused tactics / `have`s, fixed point, roll back any breaking pass | assert minimizers (KVerus `kverus-strip` skill, Tunable Automation's minimizer) | `speed_search.py` / `repo_search.py` (cost-guided); a validity-only mode is a subset |
| `repair_proofs` | insert sorries, drop extraneous tactics, try `grind`, replace unsafe tactics, fix options | houdini (deletes failing annotations) | not built |
| `have2lemma`, `sorry2lemma`, `have2sorry` | lift `have`/sorry/error positions into standalone lemmas (decompose-solve-merge) | none found | candidate next tool: `assert ... by` → lemma |
| `extract_decls` | per declaration: self-contained source with in-file dependencies, hashes, metrics | VeruSAGE's task extraction (offline), lynette `func extract` | candidate: function slicer for fast repo iteration |
| `extract_proof_states`, `disprove`, `normalize`, `merge`, `rename`, `theorem2sorry`, `theorem2lemma` | data and agent utilities | verusfmt, lynette | not built |

## 3. The resident verifier patch

Against Verus 0.2025.09.12 (bb1f342), about 100 lines, in
`patches/verus-serve-bb1f342.patch`:

- `main.rs`: the old `main` becomes `verus_main(argv) -> i32` (no
  `process::exit`); `--internal-serve` reads one JSON request per line,
  `{"cwd", "args"}`, runs `verus_main` under `catch_unwind`, and ends each
  answer with a sentinel line carrying the exit code. The rustc logger is
  installed once per process.
- `import_export.rs`: with `VERUS_IMPORT_CACHE`, deserialized imported crates
  (vstd) are kept, keyed by path, size and mtime.
- `rustc_mir_build_additional_files/verus.rs`: two set-once globals of
  Verus's forked MIR builder are reset at the start of each request
  (without this the second request in a process panics).

Still per request: the rustc front end of the request's crate, the
merged-crate VIR passes over vstd, and the lifetime/trait-conflict check,
which spawns a child rustc process.
