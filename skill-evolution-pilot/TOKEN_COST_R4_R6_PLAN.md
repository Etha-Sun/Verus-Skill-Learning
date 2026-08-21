# Token-Cost Evolution R4-R6

## Claim under test

Textual agent-design principles from `tmp.txt` can reduce verifier-safe
uncached token cost on the frozen four-task Verus repair matrix.

## Frozen protocol

- Solver: the same Codex model and harness used by the existing token branch.
- Tasks: the existing four frozen tasks; no task replacement or resampling.
- Each round: one meta-agent reflection, three generated skills, and
  3 skills x 4 tasks = 12 solver runs.
- R4 sees H0, the full R3 aggregate, selected R3 diagnostic traces, and the
  design brief. R5 and R6 receive the immediately preceding round in the same
  form.
- GPT-5.5 is run once on a canonical task only for log inspection. It is not
  included in the R4-R6 comparison.

## Acceptance

Each candidate must have 4/4 verifier success, 4/4 F3 fidelity, and complete
terminal token usage. The primary target is below H0 ETtS 52,350 uncached
tokens; the stronger target is below the prior best of about 51,497.

## Decision after R6

- Accept a mechanism only if a complete matrix beats H0.
- Treat task-specific wins with aggregate regressions as routing evidence, not
  as a token-efficiency improvement.
- If no candidate beats H0, conclude that universal prompt injection is the
  wrong control surface and test a leakage-safe router next.
