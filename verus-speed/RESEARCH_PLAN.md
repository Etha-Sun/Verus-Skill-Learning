# Research plan: fast, trustworthy Verus verification for LLM proving

Goal (user, 2026-11-23): study this to the end, with a mature evaluation
system, novelty, measured speed-ups and a possible paper. Structure follows
the ARIS `experiment-plan` skill. Results so far: `README.md`; AXLE
inventory: `AXLE_FOR_VERUS.md`; idea rounds:
`../idea-stage/IDEA_REPORT_20261122_verus_speed.md`.

Constraints: no LLM-agent end-to-end runs for now (native Verus speed only);
no external PRs of the Verus patch; benchmark on Verus 0.2025.09.12, port
the resident patch to 0.2026.11.02.

## Claim map

| Claim | Kind | Status |
|---|---|---|
| C1. In LLM proving loops most verifier time is fixed per-call cost and whole-crate front end, not SMT. A resident verifier removes the fixed cost without changing verdicts; a body-stub slice is a fast filter whose verdict matched the full in-repository check in every tested case, with the final verdict still from a full check. | primary | single files: 0.53x / 0.49x (old Verus, 1048 compared, 0 mismatches) and 0.41x / 0.35x (newer, 661, 0); repository single-function: slice fast path 0.25-0.52x on 7 projects, 81/81 and 44/44 non-trivial agreement |
| C2. Acceptance checks used by Verus proof benchmarks have holes and false rejections; a cheap structural check removes the ones we know of at negligible cost. | supporting | VeruSAGE's check: 45 synthetic cheats through, 55/101 honest and 7/306 real finals rejected; ours: 0, 35/101, 1/306 (README 8.4); the audit found a hole in our own first version (path-qualified `builtin::admit()`), now closed; the cheat set is synthetic and finite, so "closes all holes" is not claimed |
| M. Proof cost depends on context (extracted task, function alone in its repository, full check), so costs measured on extracted tasks mislead. | supporting measurement | shown on NRKernel and Anvil; needs a noise floor and more projects |

## Storyline

AXLE made Lean usable at RL scale by keeping Mathlib warm. Verus has the same
problem in a sharper form: no state survives between calls, and in
repositories each call re-checks the whole crate. We characterize where the
time goes across 8+ real projects and two Verus versions, build a resident
and scoped verifier that keeps verdicts identical, and add a trusted check
that closes holes in existing benchmark checkers.

## Experiment blocks

### B1. Workload characterization (mostly done)
- Per-phase breakdown for single files (802 proofs), failing attempts (200),
  repository single-function checks and full checks, on the project
  portfolio and both Verus versions.
- Output: the "where time goes" table and figure.
- Remaining: same breakdown on the newer Verus; repository single-function
  breakdown on all 8 projects.

### B2. Resident verifier
- Arms: native (cold, one process per request) vs resident pool; same
  binary, same flags, paired by request.
- Workloads: single files, failing attempts, repository single-function.
- Sweep: concurrency 1 / 4 / 8 / 16 (AXLE table 5 analogue); long runs for
  memory growth; both Verus versions.
- Metrics: latency median/p90, throughput, CPU seconds, verdict and
  per-function count agreement.

### B3. Scoped repository checks
- Arms: native single-function check; resident; resident without the
  lifetime pass (iteration mode); function slicer (to build) with the final
  in-repository check.
- Metrics: latency per edit, agreement of the fast verdict with the full
  in-repository verdict.

### B4. Trusted check
- Cheat suite: current 8 synthetic kinds, plus SeVerus categories, plus real
  cheating attempts mined from recorded agent trajectories already on disk
  (no new agent runs).
- Honest set: larger, by pairing tasks with proofs that are proof-only
  extensions.
- Baselines: VeruSAGE check, Verus `--no-cheating` where applicable,
  SeVerus `make anticheat` if its artifact runs.
- Metrics: missed cheats, false rejects, overhead.

### B5. Context dependence (measurement)
- Same edits measured in three contexts on 4 projects, with a multi-seed
  noise floor; diff the SMT queries to locate the cause.

## Baselines

1. Native Verus, one process per request (the default everyone uses).
2. Batching files into one crate (our earlier lever) and `--verify-function`
   scoping (Verus's own).
3. Existing acceptance checkers (VeruSAGE; SeVerus if runnable).

## Run order

1. B2 on the newer Verus (patch ported and built), repository
   single-function arms on all 8 projects (running).
2. B3: build the slicer, measure.
3. B2 concurrency sweep and long-run memory.
4. B4 expansion with real trajectory cheats.
5. B5 noise floor and fourth project.
6. ARIS `experiment-audit` and `result-to-claim` on C1, C2, M; then a
   narrative report for a paper decision.

## Paper options (decide after step 6)

- Workshop paper in the AXLE mould (AI for Math / LLM for code workshops):
  system plus measurements, C1 + C2.
- Tool paper (CAV / TACAS tool track): resident and scoped verifier plus
  trusted check, with the patch as artifact (the user's permission is needed
  before any release).
- Empirical paper on M if B5 holds up across projects.

## Risks

- Shared host (load 250-380): use paired interleaved arms, CPU time and
  exact rlimit, repeated runs; never compare runs taken at different times.
- The patch touches Verus internals; each Verus version needs its own port.
- Slicing can change verdicts (claim M); the slice is only a filter, and the
  final verdict always comes from the full in-repository check.

## Checklist before any claim

- Verdict agreement reported for every speed number.
- Every number traceable to a result file under the run root.
- Same-family review only so far; mark it as such.
