# Token-Cost Design Brief v1

This brief converts the design ideas reviewed in `tmp.txt` into hypotheses
that can be tested fairly by an injected textual skill. It is not evidence.

## Fixed objective and constraints

- Primary endpoint: expected primary uncached Codex tokens to a verifier-safe
  solution over the frozen four-task matrix.
- Hard constraints: 4/4 Verus and Lynette success, 4/4 F3 fidelity, and one
  complete terminal usage record per run.
- Diagnose uncached input and output tokens separately. A failed, timed-out,
  or incomplete-ledger run cannot count as a saving.
- Stop immediately after both verifiers pass.

## Skill-expressible hypotheses

1. Minimal permanent kernel: retain only the goal, safety boundary, output
   contract, and stop condition. Remove ceremony and repeated restatement.
2. Direct-first solving: attempt the smallest locally justified repair before
   broad exploration. Escalate only after an informative verifier failure.
3. Compact planning: use a one-to-three-step plan, a bounded retry budget, and
   an explicit pivot trigger. Do not narrate a long chain of thought.
4. Local working set: inspect the target obligation, nearby contracts, and the
   smallest relevant dependency slice before reading broad files.
5. Differential diagnostics: after the first full verifier result, focus on
   the changed error block and code diff instead of re-reading unchanged
   context.
6. External execution: use Verus and Lynette as the source of truth; do not
   simulate them or add redundant checks.
7. Conditional guidance: preserve a direct/no-skill path for tasks where
   additional procedure would cost more than it saves.

## Excluded confounds

The textual skill cannot change provider prefix caching, harness layout,
deferred tool schemas, solver model, reasoning effort, multi-agent
parallelism, or model routing. Candidates must not claim these mechanisms.
They must not omit safety checks, verifier output, or the final proof.

## Evolution guidance

- Round 4 should isolate distinct mechanisms rather than bundle all of them.
- Later rounds may combine mechanisms only when prior matrix evidence supports
  the combination.
- Use the aggregate summary for full-matrix claims and representative traces
  for causal diagnosis.
- Report which tasks benefit, which regress, and whether the change came from
  input-token reduction or output-token reduction.
