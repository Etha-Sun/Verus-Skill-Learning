# Idea Discovery Report: Verus verification speed

**Direction**: make Verus verification faster for LLM-written and human proofs, from single-file tasks to whole repositories
**Date**: 2026-11-22
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → pilot (ARIS idea-discovery, adapted)
**Evidence status**: pilots complete on NRKernel and Anvil; no agent run; no second Verus/Z3 version
**Process deviations from ARIS**: no Codex MCP reviewer and no `run_state.py` gate were available. The novelty check and critical review were done by one fresh Claude subagent with web search, so this is a same-family review (`REVIEW_UNAVAILABLE` for the cross-model slot). Most related-work statements come from search snippets; the subagent read four pages in full (marked below).

Measured numbers and scripts: `verus-speed/README.md`.

## Literature landscape

| Work | What it does | Relation to us | Source read? |
|---|---|---|---|
| Tunable Automation in Automated Program Verification (arXiv 2512.03926) | Tunes quantifier-instantiation automation in Verus; includes a linear assert / assert-by deleting minimizer on IronKV, Splinter, Anvil, CapybaraKV | States that fewer assertions does not necessarily reduce verification time, left as future work; measures wall clock, not rlimit | page read |
| VeruSAGE-Bench (arXiv 2512.18436) | 849 single-file tasks extracted from Verus projects with dependent proof bodies stubbed | Never claims the extracted file costs the same as the in-repository function; reports no solver cost | page read |
| SeVerus (arXiv 2611.07194) | Whole-project Verus benchmark generator | Criticises single-file design for agent difficulty only; no solver-cost measurement | page read |
| Proof localization, Axolocl (CAV 2025) | Speeds up verification by localizing proofs at the Boogie/axiom level, Dafny and Viper | Strongest competing speed-up; works on the query, not the source proof; no Verus | author blog read |
| Mariposa, Shake, Cazamariposas | SMT proof instability; about 78% attributed to irrelevant context; context pruning | The mechanism behind context-dependent proof cost | snippet |
| Fewer Hints, Shakier Proofs? (WAVE 2027) | Dafny hint minimization hurts stability; a ten-seed acceptance rule avoids it | Our 3-seed confirmation is a weaker version of an existing rule | snippet |
| KVerus (arXiv 2605.03822) | Another Verus assert-deleting minimizer | Baseline | snippet |
| Dafny `measure-complexity`, `dafny-reportgenerator`, DARUM; F* hint replay | Resource count as a CI metric with caps | Prior art for exact-cost measurement | snippet |
| ProofOptimizer (ICLR 2026), ImProver, Lean Refactor (arXiv 2605.20244), LeanLean | LLM proof shortening and compile-cost optimization in Lean, up to repository scale | Same goal in a different prover; cost is elaboration, not SMT search | snippet |

## Ranked ideas

### Idea 1 (recommended): proof cost does not transfer between an extracted benchmark task and its repository

- **Claim**: the cost of a proof, the effect of a rewrite, and sometimes whether it verifies, depend on the surrounding context. Results measured on single-file extractions (VeruSAGE-style) do not carry over to the same function in its repository.
- **Evidence so far** (all on one Verus/Z3 version):
  - Rewrites found on single-file tasks, re-applied in the repository: the heaviest Anvil lemma went from 0.67x on the task to 1.36x in the repository; one deletion broke a proof; on NRKernel 3 of 9 measurable transplants helped clearly, 2 did nothing, 2 got slower.
  - The same search run inside the repository found confirmed improvements on 14 of 22 NRKernel functions and 13 of 20 Anvil functions.
  - Batching single files into one crate flipped one verdict (a proof near its limit).
- **Novelty** (subagent): novel as a measured result, medium confidence; the mechanism is known.
- **Risk**: may be an extraction artifact or seed noise rather than a general property.
- **Next experiment**: same Verus/Z3, at least four projects; fraction of edits whose sign flips against a multi-seed noise floor; diff the two SMT queries and add context back step by step to find the cause.

### Idea 2: cost-guided, in-repository proof minimization

- **Claim**: unguided assertion deletion does not reliably speed up verification (already shown by Tunable Automation), but a search that keeps an edit only if exact cost drops in the repository context does reduce per-function cost.
- **Evidence so far**: per-function exact-cost ratios 0.25x to 0.99x on 27 functions. Whether this changes whole-repository time is the open pilot question; see "Pilot results".
- **Novelty** (subagent): the positive half is new for Verus but a small step over existing minimizers.
- **Risk**: rlimit on one configuration is not robust speed; hint-stripped proofs may be less stable or harder to maintain.
- **Next experiment**: Mariposa-style mutants and a second Z3/Verus version on before/after proofs; head-to-head against the unguided minimizer and spinoff-everything; re-verify on later repository commits.

### Idea 3: slicing a repository function into a minimal single-file check for agent iteration

- **Claim**: a light function costs 6 to 16 s to re-verify in a repository (whole-crate front end) and 0.6 to 2 s as a single-file task. An automatic slicer would make agent iteration on large repositories several times faster.
- **Evidence so far**: the two timings above; no slicer built.
- **Risk**: Idea 1 says the slice can disagree with the repository, so the slice can only be a filter with a final in-repository check. Heavy engineering; may belong in Verus itself as front-end caching.
- **Status**: not piloted.

## Eliminated ideas

| Idea | Why dropped |
|---|---|
| Text skills that make an LLM write cheaper proofs | Measured earlier: about 1.0x on heavy tasks |
| Result cache for agent loops | About 8% repeat calls and Verus is 1% of episode time |
| Upgrade Verus to speed up | 0.2026.11.02 is 2.1x slower per file here and breaks 43% of tasks |
| One-solve capped costing as a contribution | Subagent: incremental engineering; keep as tooling |
| "Heavy functions bound wall time" as a contribution | Subagent: known engineering fact; keep as motivation |

## External critical review (same-family subagent)

Verdict: **PROCEED WITH CAUTION**. Recommended positioning: an empirical measurement paper (Idea 1) with the cost-guided minimizer answering the future work Tunable Automation left open (Idea 2). A "system" framing would be compared with proof localization and existing minimizers and looks thin.

Strongest objections:
1. rlimit on one configuration is not robust speed (seed or version overfitting; rlimit is not wall time).
2. The context effect may be an extraction artifact.
3. Weak baselines and a small edit space (deletions plus `spinoff_prover`).

## Pilot results

Whole-repository pilot of Idea 2 (details in `verus-speed/README.md` section 6):

| Project | Functions made cheaper | Whole-repository exact rlimit | Untouched functions |
|---|---|---|---|
| NRKernel | 14 of 22 searched | 0.917x | 1.001x |
| Anvil controller | 13 of 20 searched | 0.932x | 0.932x |

What the pilot changes:

- **Idea 2 is weak as a speed result.** 7 to 8% of solver cost per project is
  too small to carry a paper on its own, and it cost about 1.5 hours of summed
  search time per project.
- **Idea 1 got stronger.** A third context appeared: the per-function ratios
  measured in the repository (0.25x to 0.99x) do not add up to the
  whole-repository ratio, because functions in a module share a solver
  process; an untouched Anvil lemma changed by 20 million rlimit when a
  neighbour was moved out with `spinoff_prover`. Cost is now shown to differ
  across single-file task, function alone in the repository, and full check.
- **For raw speed, Idea 3 (slicing) and single-function re-verification are
  the large levers**: about 10x for one edit in a large crate, against 0.92x
  from rewriting.

- **Stability (objection 1, in part)**: on five unseen seeds, 26 of 27
  rewritten functions pass every run like their originals; one NRKernel
  rewrite fails 2 of 5. Three-seed confirmation is too weak, which matches
  the Dafny result in "Fewer Hints, Shakier Proofs?".

Updated ranking: Idea 1 (measurement study, with Idea 2 as its constructive
half) for research value; Idea 3 for performance.

## Suggested execution order

1. Done: stability on five unseen seeds (26 of 27 stable). Still open for objection 1: mutants and a second Z3/Verus version.
2. Idea 3 pilot: slice 20 light functions of NRKernel and Anvil into single-file checks, measure time and agreement with the repository verdict.
3. Idea 1 on IronKV and Node Replication to reach four projects, with a multi-seed noise floor.
4. Unguided-minimizer baseline on the same functions (answers objection 3).


## Round 2 (2026-11-22, after reading AXLE's primary sources)

The first round framed the problem as making proofs cheaper. Reading AXLE in
full (`verus-speed/AXLE_FOR_VERUS.md`) showed its speed comes from the
service, not from proofs: a warm cached environment, a response cache, no
environment replay, and elaborating only what is asked for. Its proof tools
(simplify, repair, lemma extraction) serve data and agent workflows.

### Ranked ideas, round 2

1. **Resident Verus verifier** (AXLE's warm environment). Built and measured:
   light files and failing attempts take about half the time (paired
   geomean 0.53x and 0.49x on 547 and 200 requests), verdicts identical on
   1049 requests. Next: remove the remaining per-request costs (the lifetime
   child process; VIR passes that re-check vstd every time), concurrency
   sweep, port to the newer Verus.
2. **Trusted check for Verus proofs** (AXLE's verify_proof). Built: 0 of 288
   accepted cheats slip through, against 45 for VeruSAGE's check; same
   honest acceptance. Next: SeVerus-style call-graph scope, a larger honest
   set, real LLM cheating attempts from our trajectories.
3. **Function slicer for repository iteration** (AXLE's extract_decls /
   names selection). Motivation measured: a single-function check in a
   repository is 3.5-13.5 s, almost all whole-crate front end; the same
   function as a single-file task is about 1 s. Verus's logs are pruned per
   module, not per function, so this needs its own reachability pass. Not
   built.
4. **Lemma extraction** (`assert ... by` → lemma; AXLE's have2lemma). No
   Verus tool exists; it would serve decompose-solve-merge agents and
   possibly cost (helper lemmas verified in a small context). Not built.
5. Proof-cost rewriting (round 1) stays a minor lever: 0.92-0.93x at
   repository scale.

Evaluation now covers 8 projects on the current Verus and 4 on the newer
one (`verus-speed/README.md` section 7.3).
