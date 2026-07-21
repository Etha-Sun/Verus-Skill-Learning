# VeruSAGE Repair Scaffold Provenance Audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-03T09:31:15`
- status: `complete`

## Objective

Answer whether the repair-agent architecture discussed in the VeruSAGE/Verusage
trace analysis is an ad hoc scaffold, a latest VeruSAGE paper architecture, or
Microsoft-maintained code; identify the relevant source code paths.

## Context

The research direction proposes a self-evolving decision layer over the current
repair traces. The user raised a provenance concern: if we optimize within an
existing architecture, that architecture should not be an unsupported invention.

## Method / Actions

Checked local source and public sources:

- Local code under `<scratch-root>/RL-verus-1129/autoverus/verusage`.
- Local git remote under `<scratch-root>/RL-verus-1129/autoverus`.
- Public repository `https://github.com/microsoft/verus-proof-synthesis`.
- Public VeruSAGE paper page `https://arxiv.org/abs/2512.18436`.
- Public Verus Proof Synthesis leaderboard/about page.

Commands used included:

```bash
find <scratch-root>/RL-verus-1129/autoverus/verusage -maxdepth 3 -type f
sed -n '1,300p' <scratch-root>/RL-verus-1129/autoverus/verusage/ARCHITECTURE.md
sed -n '1,340p' <scratch-root>/RL-verus-1129/autoverus/verusage/agents/main_loop.py
sed -n '1,280p' <scratch-root>/RL-verus-1129/autoverus/verusage/agents/__init__.py
sed -n '1,340p' <scratch-root>/RL-verus-1129/autoverus/verusage/agents/base_agent.py
sed -n '1,260p' <scratch-root>/RL-verus-1129/autoverus/verusage/agents/actions/action_types.py
git -C <scratch-root>/RL-verus-1129/autoverus remote -v
git -C <scratch-root>/RL-verus-1129/autoverus status --short
```

## Evidence

Local code paths:

- `<scratch-root>/RL-verus-1129/autoverus/verusage/README.md`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/ARCHITECTURE.md`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/repair_runner.py`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/agents/main_loop.py`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/agents/__init__.py`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/agents/base_agent.py`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/agents/actions/action_types.py`
- `<scratch-root>/RL-verus-1129/autoverus/verusage/agents/actions/README.md`

Public source links:

- `https://github.com/microsoft/verus-proof-synthesis`
- `https://github.com/microsoft/verus-proof-synthesis/tree/main/verusage`
- `https://raw.githubusercontent.com/microsoft/verus-proof-synthesis/main/verusage/ARCHITECTURE.md`
- `https://microsoft.github.io/verus-proof-synthesis/about.html`
- `https://arxiv.org/abs/2512.18436`

Key local implementation facts:

- `RepairRunner` initializes `AgentOrchestrator` and `RepairMainLoop`.
- `RepairMainLoop.repair_veval` runs Verus, selects one failure using a fixed
  priority order, routes it to the agent framework, validates candidate edits,
  and accepts changed code only after safety validation.
- `_get_one_failure` prioritizes `MismatchedType`, `PreCondFailVecLen`,
  `ArithmeticFlow`, `InvFailFront`, `InvFailEnd`, then defaults to the first
  failure.
- `AgentOrchestrator` instantiates specialized agents including assertion,
  postcondition, precondition, invariant, arithmetic, type, method-not-found,
  bit-vector, termination, decreases, loop-decreases, other, and unsupported
  bit-vector agents.
- `BaseAgent` implements the observation-reasoning-action cycle and optional
  tree-search over primary and secondary actions.
- `ActionType` enumerates concrete repair actions such as
  `instantiate_forall`, `case_analysis`, `uselemma`, `postcondition_repair`,
  `precondition_repair`, `invariant_front_repair`, `type_repair`, etc.

Git caveat:

- Local remote is `https://github.com/microsoft/verus-proof-synthesis`.
- Local git status shows `autoverus/`, `verusage/`, and several benchmark/output
  directories as untracked in this checkout. Therefore the local copy should be
  treated as a working copy matching the public design, not as clean commit-level
  provenance.

## Result

The architecture is not something invented in our trace analysis. It exists as
code and documentation in a Microsoft GitHub repository named
`microsoft/verus-proof-synthesis`, and the public repository describes two
systems: AutoVerus for smaller algorithm-level tasks and VeruSAGE for
repository-level systems verification. Public docs describe VeruSAGE as an
agentic framework with an observation-reasoning-action loop.

The local architecture we analyzed is best described as the VeruSAGE repair
scaffold used in the local experiments/logs. It is related to the latest
VeruSAGE paper/codebase, not the older AutoVerus-only architecture. It is also
not merely "the Verusage dataset"; VeruSAGE-Bench is the benchmark, while
VeruSAGE is the repair/proof-synthesis system.

Conservative claim boundary:

- Safe to claim: our self-evolving policy is built over observed VeruSAGE-style
  repair traces and public VeruSAGE source-code architecture.
- Safe to claim: the current baseline decision flow is error-priority selection
  plus specialized-agent routing plus LLM action choice plus verifier/safety
  acceptance.
- Not safe without deeper paper reading: every detail of the local untracked
  working copy exactly matches the paper's evaluated system.
- Not safe to claim: the scaffold is a formal optimal architecture. It is a
  strong, real baseline, but still has hand-coded prioritization and agent/action
  taxonomy choices.

## Decision / Next Step

Do not frame the research as being constrained by an arbitrary scaffold. Frame it
as a verifier-grounded decision layer that improves a real VeruSAGE-style
architecture, while remaining portable to other Verus repair agents that expose:

1. structured Verus errors,
2. repair actions or proof tactics,
3. verifier feedback,
4. repair history.

Next technical step: add a short `baseline_provenance.md` or paper-method note in
the scaffold repo before writing claims, and run split-safe experiments so the
self-evolving rules are not just overfitting this baseline's quirks.
