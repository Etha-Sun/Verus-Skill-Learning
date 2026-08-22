# Research Contract: V-FACE

> Active working contract for the selected idea. Load this file, not the full candidate pool, when implementing the next phase.

## Selected Idea

- **Description**: V-FACE freezes three typed proof-action templates, compiles them into checkpoint-local proof-only edits, records Build forced-validity and randomized exposure evidence, and predicts whether the template should be exposed at unseen checkpoints. Forced edits, exposure ITT and adoption telemetry remain separate.
- **Source**: `idea-stage/IDEA_REPORT.md`, Idea #1.
- **Selection rationale**: it directly addresses the observed credit-unit failure; whole-document routing has zero selection headroom; a 1/8 naive extraction pilot makes its central compiler assumption immediately falsifiable. Novelty remains partial, so selection is for Phase-0 feasibility only.

## Core Claims

1. The frozen three-family compiler can instantiate local, semantically faithful, Lynette-valid proof edits at the preregistered rate.
2. Conditional on Claim 1, Build-only typed forced/exposure evidence predicts unseen checkpoint exposure harm/benefit more safely than budget-matched observational or generic replay baselines at ≥40% decisive coverage.
3. If Claim 2 fails but forced validity and exposure systematically disagree, the valid output is a formal-skill audit/benchmark, not a new optimizer.

## Method Summary

`CardTemplate` is cross-checkpoint and contains family, typed roles, trigger, action semantics and adoption signature. `CardInstantiation` is checkpoint-local and contains resolved symbols, source hash, proof-only anchor and typed edit AST. Evaluation decisions may use only `instantiate_static` output; forced Verus/Lynette execution is Build-only before decisions.

The first DSL supports only existing-lemma calls, exact-predicate binding plus call, and two-way extensional witnesses. A frozen rule emits ADMIT/REJECT/UNKNOWN from Build support, forced validity and exposure evidence. NON_INSTANTIABLE cases are compatibility statistics only; decisive coverage is computed over STATIC_INSTANCE pairs.

## Experiment Design

- **Datasets**: historical 40+20 retrospective only; new audited Build; sealed Evaluation; existing test-20 diagnostic only.
- **Baselines**: whole-skill outcome, atomic observational, CAR-like, TRACE-like, forced-only, exposure-only.
- **Primary metrics**: compiler gates; HARMFUL recall, false admission, balanced accuracy, decisive coverage≥40%.
- **Secondary metrics**: retained-success regression, valid success, cost ROPE, adoption telemetry, actor/API/verifier/wall cost.
- **Compute budget**: compiler CPU-only; later bounded pilots ≤8 GPUh/API-equivalent total, only after gates.

## Baselines

| Method | Dataset | Metric | Score | Source |
|---|---|---|---|---|
| Best monolithic candidate | historical selection | valid solved | 15/20 | existing SkillOpt run |
| Oracle union of 9 whole skills | historical selection | valid solved | 15/20 | offline pilot 1 |
| V-FACE | new Evaluation | prospective admission | not run | this contract |

## Current Results

| Method | Dataset | Metric | Score | Notes |
|---|---|---|---|---|
| Structured event compiler | historical selection traces | size reduction | 532.94× | interface feasibility only |
| Naive near-miss extractor | historical mixed-outcome tasks | clean action contrast | 1/8 | below 4/8 gate |

## Key Decisions

- Do not implement a whole-skill router; existing oracle headroom is zero.
- Do not call forced verifier outcome a card causal effect.
- Do not add runtime retrieval, learned calibration, RL/GNN or more patch families before Phase 0 passes.
- Treat all-UNKNOWN or <40% decisive coverage as failure.
- Never use the inspected test-20 for method selection or confirmatory claims.

## Minimum Convincing Evidence

- Compiler: ≥18/30 instantiable; ≥90% blind semantic correctness; 100% Lynette fidelity; out-of-region≤5%.
- Admission: coverage≥40%; lower false admission with non-inferior harm recall vs strongest equal-budget baseline; not explained by forced-only/exposure-only.

## Next-Step Pointer

`refine-logs/EXPERIMENT_PLAN.md`, runs R001–R005 only.

## Status

- [x] Idea selected for Phase 0
- [ ] Compiler gate passed
- [ ] Prospective admission pilot passed
- [ ] Main method implemented
- [ ] New sealed evaluation preregistered
- [ ] Paper claim promoted
