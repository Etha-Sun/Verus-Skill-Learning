# Cross-task semantic-v4 M-core prompts

This directory is the complete prompt bundle used by `code/build_m_core.py`.
The builder reads these files directly and performs no runtime text replacement.
Every formal run snapshots the prompt text and SHA-256 hashes below its external
run directory.

The files were copied from the earlier IronKV semantic-v4 experiment and then
adapted for the heterogeneous cross-task M-core experiment. The adaptation keeps
the original discovery, hierarchical taxonomy, family consolidation, global
semantic-equivalence reconciliation, and layout stages, while changing the
evidence and transfer contract:

- project and task-family labels are provenance, not grouping keys;
- cross-project cards merge only when trigger, missing bridge, mechanism, and
  applicability match;
- narrow and rare mechanisms remain valid singletons;
- failed and policy-violating trajectories cannot establish a positive repair;
- project-specific preconditions must not be generalized away;
- every synthesized skill remains transfer-untested until held-out evaluation;
- the layout internally retains `R_analysis` for organization and provenance,
  but only the self-contained `M_core` root is rendered for the baseline actor.

The JSON schemas remain interface-compatible with the earlier semantic-v4
implementation. Schema field names such as `reference_families` and
`references` therefore describe internal organization and do not imply that
