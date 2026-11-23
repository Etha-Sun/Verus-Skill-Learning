# verus-speed: where Verus time goes and how to cut it

Started 2026-11-22. Question: AXLE (arXiv 2606.26442) made Lean checking fast
at scale; what is the Verus equivalent, and how much can we save?

Setup: Verus 0.2025.09.12.bb1f342 with bundled Z3 4.12.5, VeruSAGE-Bench
human ground-truth proofs (849 files, 802 verify in this setup; 42 storage
files need the `deps_hack` crate and 4 memory-allocator files fail). The host
was heavily shared during all runs (load about 350 on 384 cores), so absolute
seconds are inflated and noisy (repeat max/min of total time: median 1.33).
Phase numbers use the best of 3 runs; comparisons are within one run.
Bulk outputs: `$VERUS_SKILL_RUN_ROOT/verus-speed-20261122/` (not committed).

## 1. What AXLE's speed comes from

Only v1 of the paper exists (2026-06-24). The GitHub repository
`AxiomMath/axiom-lean-engine` (MIT) holds the Python client and CLI only: 75
files, no `.lean`, no server code. The service itself keeps releasing (v1.9.1
on 2026-11-18) but its source is not public, so the list below comes from the
paper and the changelog.

| Source of speed | Evidence in the paper | Verus analogue |
|---|---|---|
| Mathlib kept loaded, no per-request cold start | median 5.14 s (raw Lean) -> 1.05 s; total wall 4873 s -> 2389 s | per-call fixed cost: rustc start, `vstd.vir` import, Z3 start (section 2) |
| `verify_proof` trusts normal elaboration, no environment replay | 0.97 s vs 10.1 s (SafeVerify) and 95.7 s (Comparator) | no analogue: Verus has no replay step |
| Horizontal concurrency | 7.27x at 8 in flight on 8 vCPU, flat beyond | one process per file already scales; inside a file Verus only parallelizes across modules |
| Queueing, fair share, retries, timeouts | described, not measured | harness policy |
| Reworked worker pool, "no environment warm-up time" | changelog only | not reproducible |

The paper has no ablation separating these; the one experiment that isolates
a factor is the concurrency sweep. Kimina, which caches imports per header and
keeps a warm REPL pool, is slightly faster than AXLE at the median (0.75 s).

## 2. Verus baseline

`baseline.py` + `analyze_baseline.py`, default flags, 802 verifying files.

| Phase | Median ms | p90 ms | Sum s | Share |
|---|---|---|---|---|
| rustc init and types | 43 | 305 | 79 | 4.2% |
| lifetime check | 57 | 93 | 51 | 2.8% |
| rustc compile | 39 | 257 | 69 | 3.7% |
| `vstd.vir` import | 173 | 194 | 140 | 7.5% |
| other VIR | 81 | 273 | 98 | 5.3% |
| AIR | 75 | 328 | 116 | 6.2% |
| SMT init | 16 | 81 | 24 | 1.3% |
| SMT run | 44 | 1783 | 1195 | 64.1% |
| **total** | **660** | | **1864** | |

| Class | Files | Share of total time | SMT share inside class |
|---|---|---|---|
| light (SMT < 0.2 s) | 544 (68%) | 19% | 5% |
| medium | 181 (23%) | 18% | 37% |
| heavy (SMT >= 2 s) | 77 (10%) | 64% | 89% |

The 10 slowest files take 31% of all time, the 40 slowest 53%.

Two regimes follow. On two thirds of the files the solver is 5% of the time
and the rest is fixed start-up cost, which is the AXLE situation. On one tenth
of the files the solver is 89% of the time, and only a cheaper proof helps.
In a typical file one function carries 99.5% of solver time (median), so
`--verify-function` and in-file parallelism have nothing to save.

## 3. Levers measured

| Lever | Applies to | Result | Verdict changes |
|---|---|---|---|
| `batch_verify.py`: many files as modules of one crate | light files that pass | CPU 0.56x, wall 1.57x faster at 12 processes (batch size 8, 547 files) | 0 of 547, in each of 6 runs |
| same, on a half-failing set that includes heavy files | 200 verified + 200 unproved | a net loss: CPU 1.18x, wall 0.59x as fast | 0 of 400 with the final code |
| `--multiple-errors 0 --no-auto-recommends-check` | failing runs | 0.86x total time (200 unproved tasks; each flag alone 0.93x and 0.91x) | none; fewer diagnostics |
| `auto_speed.py` (wraps the existing exact-cost search) | heavy verified proofs | 0.78x geomean exact rlimit on 67 heavy human proofs (earlier study); re-checked here on `step_MemOp_refines`: 0.45x from one deletion | proof still verifies on 3 seeds |
| `fast_cost.py`: one capped solve per search candidate instead of two | the rewrite search | per call 1.65x to 2.3x faster with identical exact rlimit (4 heavy files); whole search 1041 s -> 774 s on 5 heavy proofs (geomean 1.31x) | same final proof: same ratio and edits on all 5 |
| best of 3 solver seeds | heavy files | about 0.91x for 3x CPU (from earlier 3-seed data) | none |
| `-V spinoff-all` | one probe file | slower (1.62 s vs 1.41 s) | none |
| `--no-lifetime` | iteration only | removes the 2.8% lifetime phase; not a full check | skips a check |

Batch size matters: in the size sweep, CPU ratio was 0.61 / 0.59 / 0.61 / 0.66
at sizes 4 / 8 / 16 / 48, and wall speed-up 1.53 / 1.45 / 1.13 / 0.79. Larger
crates cost more per module, so the default is 8.

Use batching for sets that are expected to pass and are light: re-verifying a
dataset, checking accepted proofs, costing search variants of a light file. Do
not use it for agent iteration, where most calls fail (each failure is run
twice), or for heavy files (a batch runs its files one after another).

Why the search gains less than a single call: the input check, the gate in
`auto_speed.py` and the two seed confirmations still use normal Verus; large
files spend much of each call outside the solver; and a file using
`by (compute)` falls back to two solves (the 1.09x case). The cap is the
input's total cost, so a candidate that exceeds it on any query is dropped
without being solved to the end. Such candidates are recorded as failed, so
the per-candidate table no longer shows how much costlier they were.

How batching keeps verdicts equal to separate runs: a file counts as verified
only if no diagnostic points into its module and all of its functions pass; a
file that fails inside a batch is re-run alone and that verdict is used; a
batch that cannot be attributed per file is split and retried down to single
runs; files with crate-wide trusted declarations run alone; files are batched
only with files that declare the same `global size_of` directives.

One real disagreement was found before the re-run rule existed:
`OS__slinkedlist__spec_impl_u__impl2__remove_helper4` passes alone (3 of 3)
but hit the resource limit inside a batch, reproducibly. Module renaming
changes the solver's search on a proof near its limit. The opposite case (a
file that passes in a batch and fails alone) did not occur in any run (213
failing files per mixed run), but it is not excluded by construction; run the
final check of a result that matters without batching.

### Not done

- Newer Z3 under the old Verus (needs `-V no-solver-version-check`): not run.
- A result cache keyed on file content was considered and dropped: in 391
  recorded agent episodes about 8% of 4226 Verus calls had no edit since the
  previous call (a proxy from the command stream), and Verus is 1% of episode
  wall time (median; p90 3.6%), so a cache would save under 0.1% of an episode.
- SeVerus (arXiv 2611.07194): its artifact is on Zenodo
  (10.5281/zenodo.23894085) and was not downloaded. Its six projects are Vest,
  IronKV, PMemLog, NRKernel, TLA-RS and Anvil; VeruSAGE-Bench already contains
  Vest, IronKV, the storage (pmem) code, NRKernel and Anvil, which is what was
  measured here. The paper reports no Verus performance engineering.

## 4. Newer Verus (0.2026.11.02) is slower here, and half the benchmark breaks

Getting it to run on this host (glibc 2.35) needs no source build: the
release's `rust_verify` runs as is; only its `verus` launcher and bundled `z3`
need a newer glibc. A small launcher script calls `rust_verify` through Rust
1.99.1 with the exact Z3 4.16.0 it expects, taken from the official PyPI
wheel. Both versions were then run side by side on all 849 files (2 repeats,
same load, best run per file).

| | 0.2025.09.12 (Z3 4.12.5) | 0.2026.11.02 (Z3 4.16.0) |
|---|---|---|
| files that verify unchanged | 802 | 461 (352 build errors, 36 verification errors) |
| median wall per file, on the 461 common files | 0.69 s | 1.29 s |
| median reported total | 463 ms | 1160 ms |
| `vstd.vir` import, median | 174 ms | 395 ms |
| other VIR, median | 57 ms | 164 ms |
| time outside the reported phases, median | 51 ms | 397 ms |
| SMT run, sum over common files | 151 s | 161 s |
| SMT run on the 12 common heavy files (geomean) | 1.00 | 0.91 |

- Per file the new version is 2.1x slower (geomean of total time); summed
  over the common files it is 1.66x. The extra time is fixed per-call cost
  (larger vstd, more front-end work), not the solver.
- Solver time is about equal. The 0.91 on heavy files rests on 12 files and
  is not a reliable gain.
- The build errors are language and library changes (mutable references in
  postconditions, type mismatches, `transparent` struct rules, trait bounds,
  removed vstd methods), so the failing files need proof-level migration.
- Caveat: Z3 4.16.0 here is the PyPI build, not the build shipped with the
  release; that could shift solver time but not the fixed cost.

Conclusion: stay on 0.2025.09.12 for this benchmark. Upgrading costs speed on
light files, which are two thirds of the benchmark, and loses 43% of the
tasks. Batching matters more on the new version, since its fixed cost is
larger; that was not measured.

## 5. Whole repositories

Sections 2-4 use single-file tasks. This section verifies whole upstream
projects with the same Verus (`repo_run.sh`, `repo_incremental.py`). Same
noisy host; single runs unless noted.

Pinned commits: verified-ironkv `472c621` (2025-07-24), verified-nrkernel
`733950a` (2025-09-18), verified-node-replication `c3acacf` (2025-08-13),
anvil `a65d68c1` (2025-12-10; earlier commits predate the
`verus_builtin_macros` rename and do not build), atmosphere `17ceb4d`
(2025-09-16).

| Crate | Functions verified | Wall, 16 threads | CPU | Wall, 1 thread |
|---|---|---|---|---|
| IronKV (11k lines) | 319 | 8.2 s | 22 s | 18.2 s |
| Node Replication (18k lines) | 254 | 15.5 s | 14 s | not run |
| NRKernel page table (44k lines) | 524, plus 2 that exceed rlimit | 79 s | 600 s | 617 s |
| Anvil framework (`anvil.rs`) | 339 | 63 s | 222 s | not run |
| Anvil vreplicaset controller crate (includes the framework) | 429 | 175 s | 611 s | not run |
| same, `--verify-module vreplicaset_controller` (Anvil's CI command) | 90 | 173 s | 414 s | not run |

Atmosphere (61k lines) did not verify cleanly at this commit with this Verus
(2 loops without `decreases`, 3 failing obligations), so it is left out; the
partial run took 107 s wall.

What changes at repository scale:

- A full check is minutes, not seconds, but not hours: 1 to 3 minutes of wall
  time and about 10 CPU-minutes for the two largest crates.
- Wall time is bounded by the heaviest functions, because functions inside a
  module run one after another. In the Anvil controller one lemma takes 156 s
  of the 175 s; the 10 heaviest functions hold 67% of solver time (56% in
  NRKernel). More threads stop helping early: NRKernel takes 206 / 79 / 95 s
  at 4 / 16 / 64 threads.
- `-V spinoff-all` (one solver process per function) removes the in-module
  ordering. NRKernel: 61 s at 64 threads against 79 s. Anvil controller: no
  gain (183 s), since one function is the bound.
- Re-verifying one function (`--verify-only-module M --verify-function F`) is
  the large lever for an agent editing one proof. A light function costs
  7.4 s in NRKernel (full check 79 s) and 16 s in the Anvil controller (full
  check 175 s). In IronKV it costs 6.1 s against 8.2 s, so it is not worth it
  on small crates. A proof-body edit cannot change what other functions see,
  so this check is exact for such edits; a full check is still needed once at
  the end.
- That single-function cost is almost all whole-crate front end (type
  checking and VIR: 4.2 s IronKV, 5.6 s NRKernel, 12.4 s Anvil controller).
  This is the repository-level fixed cost; nothing measured here removes it.
- The single-file task for the same function avoids that front end: light
  functions take 0.6 to 2 s as single-file tasks against 6 to 16 s in the
  repository. For heavy functions solver time is about the same either way
  (for example 183 s against 185 s for the heaviest Anvil lemma).
- Proof rewriting was then tried for real; see section 6. The estimate first
  written here (about 0.85x from transplanting single-file rewrites) did not
  hold.

Not measured at repository scale: batching, fail-fast flags, an agent run,
and whether the rewritten single-file proofs transplant back unchanged.

## 6. Proof rewriting at repository scale

**Transplanting single-file rewrites fails.** The rewrites found earlier on the
single-file tasks were re-applied to the same functions in the repository
(`repo_transplant.py`), timing each function alone before and after:

- Anvil: the heaviest lemma was 0.67x on its task and 1.36x in the repository
  (179 s -> 243 s); one deletion made a proof fail; `spinoff_prover` edits
  gave 0.65x to 0.92x; two statements were not found (different commit).
- NRKernel: three clear gains (0.34x, 0.74x, 0.79x), two unchanged, two
  slower (1.06x, 1.22x), one proof broken, and one function that fails in the
  original started to verify.

**Searching inside the repository works per function.** `repo_search.py` runs
the same search with every candidate verified in the repository, costed with
one capped solve, and the result confirmed on seeds 0-2 with normal Verus.

| Project | Functions searched | Made cheaper | Best | Summed search time (8 workers per function) |
|---|---|---|---|---|
| NRKernel (30 heaviest; 6 skipped, 2 not found) | 22 | 14 | 0.39x | 5522 s |
| Anvil controller (22 heaviest; 2 not found) | 20 | 13 | 0.25x | 4743 s |

**Whole-repository effect is small.** All confirmed rewrites merged into a
copy (`repo_apply.py`), then exact rlimit of the full check by log replay
(`repo_rlimit.py`), which does not depend on machine load:

| Project | Total rlimit | Rewritten functions | Untouched functions |
|---|---|---|---|
| NRKernel | 0.917x | 0.736x (31.5% of the total before) | 1.001x |
| Anvil controller | 0.932x | 0.933x (49.4%) | 0.932x |

- In seconds, three alternating full runs each: NRKernel solver time of the
  rewritten functions fell from 332-383 s to 226-289 s with the untouched
  functions unchanged; median wall 122 s -> 99 s. Anvil median wall 221 s ->
  169 s and solver time 817 s -> 606 s, but the load during those runs cannot
  be separated from the effect, so only the rlimit table is reliable.
- The per-function ratios do not add up to the whole-repository ratio. A
  function verified alone gets a fresh solver process; in a full check the
  functions of a module share one, so the same proof costs a different amount.
  In Anvil an untouched lemma became 20 million rlimit cheaper because a
  neighbour was moved out of the shared process by `spinoff_prover`.
- Verified items fell from 524 to 522 in NRKernel with the same two failures:
  two deleted `assert ... by` blocks were counted as separate items.

**Stability.** Each rewritten function and its original were verified in the
repository on five seeds the search never used (`repo_stability.py`). Anvil:
65 of 65 runs pass before and after. NRKernel: 70 of 70 before, 68 of 70
after; `next_step_preserves_overlap_mem_inv` (0.88x) fails on 2 of 5 new
seeds. One of 27 accepted rewrites is therefore unstable, so confirming on
three seeds is not enough; that rewrite should be dropped, and the rlimit
table above still includes it.

Proof cost therefore depends on three contexts that give different answers:
the single-file task, the function alone in its repository, and the function
inside a full check. Only the last one is what a project pays.

Conclusion for speed: at repository scale, rewriting saved 7 to 8% of solver
cost for about 1.5 hours of summed per-function search time per project. Single-function re-verification
(about 10x for an edit) and enough threads are the large levers; rewriting is
a minor one.

## 7. AXLE for Verus: resident verifier and trusted check

After reading AXLE's paper, every tool page and its changelog
(`AXLE_FOR_VERUS.md`), the direction changed from making proofs cheaper to
what AXLE does: a fast, trustworthy verification service plus proof tools.

### 7.1 Resident verifier (AXLE's warm environment)

Verus keeps nothing between calls: each call starts a process, loads the
rustc library, deserializes all of vstd.vir and re-checks vstd. A ~100-line
patch (`patches/verus-serve-bb1f342.patch`, Verus 0.2025.09.12 built from
source) adds `rust_verify --internal-serve`: one process answers many
requests, keeps vstd deserialized, and resets the two once-per-process
globals of Verus's forked MIR builder. `verus_serve.py` is the pool client
(restart on crash or timeout, optional response cache).

Benchmark (`serve_bench.py`, `analyze_serve.py`): 849 VeruSAGE human proofs
plus 200 unproved task files, concurrency 8, same binary and flags in both
arms, cold = one process per request, warm = 8 resident processes.

| Class | Requests | Cold median | Warm median | Paired geomean warm/cold |
|---|---|---|---|---|
| light (SMT < 0.2 s) | 547 | 0.90 s | 0.46 s | 0.53x |
| medium | 178 | 2.49 s | 1.92 s | 0.80x |
| heavy (SMT >= 2 s) | 77 | 12.5 s | 10.9 s | 0.88x |
| unproved (failing attempts) | 200 | 0.90 s | 0.42 s | 0.49x |

- Verdicts and per-function verified/error counts agree on all 1048
  requests that produced a result; one request
  (`MA__bin_sizes__bounds_for_smallest_bin_fitting_size`) timed out at
  600 s in both arms. No worker crashed.
- Caveats (from the audit): the warm arm ran fully before the cold arm, so
  load drift is a confound (two cold-only runs at different times differed
  by 4% in median); the interleaved run on the newer Verus (8.1) does not
  have this problem. The table leaves out 47 human proofs that fail on this
  Verus version (802 rows plus 200 unproved). Classes come from
  `baseline_default.jsonl`.
- Overall median 1.04 s → 0.58 s. Total throughput barely moves (1.52 →
  1.58 req/s) because a few heavy files dominate the total.
- Empty file: 0.57-0.81 s cold, 0.18-0.24 s warm. What is left per request:
  the rustc front end, VIR passes that re-check vstd, and the lifetime check,
  which still spawns a child rustc process.

### 7.2 Trusted check (AXLE's verify_proof)

`verify_proof.py` accepts a candidate only if Verus verifies it, `lynette
additions` confirms it only adds proof code to the original task, and no
trust escape (assume, admit, external_body in either attribute syntax,
assume_specification, unsafe, ...) is added to any function; escapes are
counted on a whitespace- and comment-free token stream per function. The
structural part takes about 0.1 s and runs in parallel with Verus.

Finding while building it: `lynette compare` drops proof functions (it
compares extracted Rust), so it never sees a lemma's requires/ensures.

Adversarial evaluation (`cheat_eval.py`; final numbers in 8.4): 120 sampled
tasks, of which 101 have a human proof with a target function to edit; 46 of them have
a human proof that is a proof-only extension of the task file (for the
others VeruSAGE built the task separately, and both checkers rightly reject
the human file). Eight cheat kinds on the target function:

| | Cheats Verus accepts | VeruSAGE check lets through | Ours lets through |
|---|---|---|---|
| all kinds, on the 46 tasks | 334 of 492 | 45 | 0 |
| `assume (false);` (space before the parenthesis) | 45 | 45 | 0 |
| honest proofs accepted (of 101) | | 46 | 66 |

Numbers are from the rerun with the final check and eleven cheat kinds
(`cheat_eval.json`; the first run is kept as `cheat_eval_v1_prerule.json`).
Of the 101 human proofs, 35 are rejected by our check and 55 by VeruSAGE's;
these files are not literal extensions of the VeruSAGE task file, and the
audit found some differ only in function order or `spinoff_prover`, so they
are reported as rejections, not counted as honest or dishonest. On the 66
tasks our check accepts, 490 of 709 cheats verify; VeruSAGE's check lets 45
through, ours none. `builtin::admit()` and `builtin::assume_(false)` never
verify on these files with this Verus, so they are not a working cheat here,
but the check rejects them; the `cfg_attr(..., verifier::external_body)`
variant verifies on all 101 and both checkers reject it.

The cheat set is synthetic and the honest set is small; this shows a real
hole in a widely used checker, not a full robustness evaluation.

### 7.3 More projects

`repo_probe.py` tries projects at a pinned commit with either toolchain. Two
toolchains now work on this host: 0.2025.09.12, and 0.2026.11.02 with its
`verus` and `cargo-verus` launchers rebuilt from source for the local glibc.

| Project | Toolchain | Functions verified | Wall (8 threads) |
|---|---|---|---|
| IronKV | old / new | 319 / 313 | 7 s / 11 s |
| Node Replication | old / new | 254 / 253 | 9 s / 19 s |
| NRKernel page table | old | 524 (+2 rlimit failures) | 104 s |
| Anvil framework / vreplicaset controller | old | 339 / 429 | 63 s / 175 s |
| Vest | old / new | 477 / 2958 (`vest_lib`) | 9 s / 56 s |
| pmemlog (verified-storage) | old | 80 | 6 s |
| verified-graphs | old | 101 | 2 s |
| cedar-json-parser | new | 136 (+1 error) | 4 s |

Not usable: verified-memory-allocator (needs a Singular-enabled Verus),
Atmosphere (fails on both toolchains), capybaraKV and multilog (pinned
nightly toolchains and crates.io vstd versions that match neither release),
vostd (builds its own Verus fork), verified-tiff (version mismatch).

Repository single-function checks, with and without the lifetime pass:
NRKernel 5.9 → 4.5 s, IronKV 5.2 → 3.5 s, Anvil controller 13.5 → 9.6 s. The
rest is whole-crate rustc type checking and VIR conversion; rustc's own
incremental cache (`-C incremental`) is written but gives no speed-up.

## 8. Round 3: newer Verus, repository iteration, real-trajectory trust check

Goal and plan: `RESEARCH_PLAN.md` (set by the user on 2026-11-23). Native
Verus speed only; no agent runs.

### 8.1 Resident verifier on Verus 0.2026.11.02

The patch was ported (`patches/verus-serve-8bf68ee.patch`). This version has
six per-process globals to reset, including maps keyed by `DefId` and
`HirId` that would carry stale entries from the previous crate. Benchmark:
461 human proofs that verify on this version plus 200 unproved task files,
concurrency 8, both arms per request in random order (`--interleave`).

| Class | Requests | Cold median | Warm median | Paired geomean warm/cold |
|---|---|---|---|---|
| light | 415 | 1.39 s | 0.55 s | 0.41x |
| medium | 29 | 2.58 s | 1.88 s | 0.73x |
| heavy | 17 | 7.69 s | 6.47 s | 0.97x |
| unproved | 200 | 1.45 s | 0.49 s | 0.35x |

464 passes in both arms (3 of the 200 "unproved" files verify on this
version), no mismatch in (verified, errors) on all 661, no crash. Classes
use this version's own baseline (`cmp_new.jsonl`); the heavy class has only
17 files and no confidence interval, so read it with medium. The gain is larger
than on 0.2025.09.12 (0.53x / 0.49x) because the newer version's fixed cost
per call is larger.

### 8.2 Repository single-function checks (Verus 0.2025.09.12)

`repo_serve_bench.py`: 12 random functions per project, each checked with
`--verify-only-module M --verify-function F`, 2 repeats, arms interleaved.

| Project | Native | Resident | Resident, no lifetime pass |
|---|---|---|---|
| IronKV | 4.65 s | 4.50 s | 3.26 s |
| Node Replication | 7.66 s | 8.62 s | 6.03 s |
| Vest | 5.57 s | 6.11 s | 3.23 s |
| pmemlog | 1.74 s | 1.32 s | 0.97 s |
| verified-graphs | 1.15 s | 0.90 s | 0.73 s |
| NRKernel | 6.35 s | 5.22 s | 4.11 s |
| Anvil controller | 12.78 s | 9.84 s | 7.56 s |

A resident process alone barely helps here: the ≈0.3 s it saves is small
next to the whole-crate front end, and in two projects it is within noise
(no growth with request count; worker ≈500 MB). One warm request in IronKV
returned no result once and could not be reproduced in 8 repeats; exit
status and stderr are now recorded for every warm request.

### 8.3 Function slicer (`slice_stub.py`, `fnspans/`)

The slicer copies the crate and replaces the body of every proof and exec
function except the target (and every function the `--verify-function`
selector also matches) with a trusted `#[verifier::external_body]` stub.
Signatures, requires/ensures and spec bodies stay. Function spans come from
a small syn_verus parser (`fnspans/`); a first regex-based version broke on
`ensures if c {} else {...}`, `ensures match`, comments and macro templates,
and was replaced. Functions used as termination proofs (`decreases_by`) are
never stubbed: Verus panics on an external_body termination proof.

Why the verdict should not change: callers only ever see callee specs. On
IronKV's `DelegationMap::get` the slice's SMT query differs from the
repository's only by 23 missing `ens%` declarations of functions that only
the stubbed bodies called (Verus prunes module context from the bodies
present); nothing is added.

`slice_bench.py`: same 12 functions per project, each also broken
(`assert(false);` inserted at the start of its body) in both the repository
and the slice. Agreement is exact equality of (verified, errors) and counts
only non-trivial cases: as-is rows where the repository verified at least
one function, broken rows where the repository reported at least one
verification error (an insertion that fails before SMT in both, or a
selector that matches nothing, tests nothing and is listed separately).

| Project | Repo check | Slice | Slice + resident + no lifetime | Agree (as is) | Agree (broken) |
|---|---|---|---|---|---|
| IronKV | 4.14 s | 2.28 s | 1.38 s (0.33x) | 11/11 | 5/5 |
| Node Replication | 6.08 s | 5.27 s | 3.17 s (0.52x) | 12/12 | 3/3 |
| Vest | 4.50 s | 2.27 s | 1.11 s (0.25x) | 12/12 | 1/1 |
| pmemlog | 1.40 s | 0.94 s | 0.44 s (0.31x) | 11/11 | 10/10 |
| verified-graphs | 0.94 s | 0.67 s | 0.32 s (0.34x) | 12/12 | 12/12 |
| Anvil controller | 12.44 s | 6.71 s | 3.87 s (0.31x) | 12/12 | 8/8 |
| NRKernel | 6.50 s | 3.34 s | 1.82 s (0.28x) | 11/11 | 5/5 |

Over all 7 projects: 81/81 functions and 44/44 broken variants agree (3
trivial as-is rows and 5 trivial broken rows not counted). The
first NRKernel run had one disagreement that came from the keep rule, not
the slicer: `--verify-function '*inv'` matches every function whose name
ends in `inv`, so the repository run verified `lemma_inv_implies_interp_inv`,
which the slice had stubbed; the slicer now keeps every function the
selector matches. Building a slice takes 0.03-0.74 s.

What this does not test: with `--no-lifetime` the fast check skips
ownership and borrow checking of the target; termination through mutual
recursion with a stubbed callee is not re-checked; type errors in other
bodies are not seen; and `assert(false)` exercises only SMT-level failures.
All of these are caught by the final full check. Broken variants are fewer than 12 where
the function name is not unique in the crate or the insertion does not
compile in the repository either. The slice is a filter: the final verdict
still comes from the full in-repository check.

### 8.4 Trusted check on real agent output

`trajectory_check_eval.py` re-judges the final files of 459 recorded Codex +
DeepSeek episodes (no new runs; verdicts from the recorded results). Of 306
verified finals, VeruSAGE's check and our first version both rejected the
same 7. All 7 are legitimate on inspection: a `broadcast use` statement in
an exec body (3), and new helper lemmas plus `proof { }` blocks that
`lynette additions` mis-classifies (4). No real cheat was found.

The check now accepts a candidate if it adds no trust escape and either
`lynette additions` or the repository's proof guard accepts it (the two have
different blind spots; every synthetic cheat is rejected by both or by the
escape check).

| | Synthetic cheats let through (46 tasks / 66 tasks) | Honest human proofs accepted (of 101) | Real verified agent finals accepted (of 306) |
|---|---|---|---|
| VeruSAGE check | 45 / 45 | 46 | 299 |
| ours | 0 / 0 | 66 | 305 |

From `cheat_eval.json` and `trajectory_checks.json`, both produced with the
final check. The audit of the first version found a hole of its own:
statements were matched only without a path prefix, so `builtin::admit();`
would have passed; patterns now match path-qualified calls, `assume_`, and
attributes in any position.

## 9. Files

- `baseline.py`: per-phase timing of named flag configurations.
- `analyze_baseline.py`: tables in section 2 and config ratios.
- `batch_verify.py`: batched verification (library and CLI).
- `eval_batch.py`: batch vs single at equal process budget, with verdict check.
- `auto_speed.py`: single-file front end to `scripts/proof_time/speed_search.py`.
- `fast_cost.py`: one-solve exact cost with a cap, used by `auto_speed.py`.
- `repo_run.sh`: verify one whole project crate and save timing.
- `repo_incremental.py`: single-function re-verification cost in a project.
- `repo_transplant.py`: re-apply single-file rewrites in a repository copy.
- `repo_search.py`: cheaper-proof search for a function inside a repository.
- `repo_apply.py`: merge confirmed rewrites and time the full check.
- `repo_rlimit.py`: exact whole-project rlimit by log replay, and comparison.
- `repo_stability.py`: rewritten against original proofs on unseen seeds.
- `AXLE_FOR_VERUS.md`: AXLE inventory and Verus counterparts.
- `patches/verus-serve-bb1f342.patch`: resident-verifier patch for Verus.
- `verus_serve.py`, `serve_bench.py`, `analyze_serve.py`: pool client and benchmark.
- `verify_proof.py`, `cheat_eval.py`: trusted check and adversarial evaluation.
- `repo_probe.py`: which projects verify with which toolchain.
- `patches/verus-serve-8bf68ee.patch`: resident-verifier patch for Verus 0.2026.11.02.
- `repo_serve_bench.py`: repository single-function checks, native vs resident.
- `slice_stub.py`, `fnspans/`, `slice_bench.py`: function slicer, its span parser, and its benchmark.
- `trajectory_check_eval.py`: acceptance checkers on recorded agent finals.
- `RESEARCH_PLAN.md`: goal, claims, experiment blocks, paper options.
- `LLM_GUIDE.md`: guidance for an LLM writing proofs, tagged by evidence.
