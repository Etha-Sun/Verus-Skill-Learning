# Architecture

## Goal

Build a bounded self-evolving scaffold for Verus proof repair decisions.

The scaffold assumes the base agent already has many repair actions. The system
improves *when to use which action* by mining verifier-grounded trajectories.

## Pipeline

```text
raw Verusage traces
  -> parser
  -> skeleton cache
  -> candidate rule miner
  -> offline replay scorer
  -> policy ablation
  -> selected rules for future live rerun
```

## Main Modules

- `data.py`: reads `results.csv` and `verus-repair.log`; never writes raw data.
- `motifs.py`: maps file/lemma names into Verus motifs such as temporal,
  quantifier, arithmetic, bitvector, sequence/set/map, induction, refinement,
  and state-machine.
- `mining.py`: mines generic, project-aware, and motif-aware candidate rules.
- `scoring.py`: estimates failed-token coverage, false-stop risk, and
  peer-success reroute support.
- `report.py`: emits a compact experiment report.

## Rule Shape

Candidate rules are AgentSpec-like, but scoped to proof repair:

```yaml
trigger:
  repeated_error: AssertFail
  repeated_action: USELEMMA
  threshold: 8
scope:
  project: AC
  motif: temporal
enforcement:
  prefer_actions:
    - INSTANTIATE_EXISTS
    - ADD_TRIGGER_ASSERT
evidence:
  support_traces: 4
  peer_success_actions: ...
```

## Verus-Specific Hooks

Current implementation:

- error/action repetition,
- project family,
- filename/lemma motifs,
- recursive/opaque preprocessing output,
- peer successful action sequence.

Planned hooks:

- precise verifier error-state delta,
- lemma dependency graph,
- quantifier trigger detection,
- opaque/reveal/fuel effectiveness,
- ghost/spec/exec boundary motifs,
- temporal proof motif rules for `AL` / verus-tla style tasks.

