# Small-Model Meta-Skill v0

Analyze complete Codex H0 proof-repair traces for reusable guidance that can
increase verifier-safe solve rate of an agentic Qwen3.6-27B solver under a
fixed ten-request budget.

1. Identify decisions that turn verifier feedback into the next smallest
   proof edit.
2. Compile those decisions into short, explicit instructions appropriate for
   a weaker model; do not imitate long Codex narration.
3. Separate reusable proof-repair procedure from task-specific facts.
4. Produce materially different aggressive, conservative, and structural
   skills.
5. State applicability, recovery behavior, and negative scope.
6. Never include task names, identifiers, finished proofs, reference answers,
   or instructions that weaken verification.
7. Optimize solve rate only. Token usage is descriptive and information gain
   belongs to a separate branch.
