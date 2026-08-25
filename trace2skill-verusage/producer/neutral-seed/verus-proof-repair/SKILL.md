---
name: verus-proof-repair
description: Repair incomplete or failing Verus proofs through verifier-guided iteration. Use when a Verus function, lemma, invariant, specification bridge, or arithmetic obligation does not verify.
---

# Verus Proof Repair

Use the current verifier state to make the smallest justified proof change.
This initial skill intentionally contains no task-specific proof mechanisms;
lower-frequency mechanisms may be added to `references/` from observed evidence.

## Core workflow

1. Read the failing function, its contracts, and the immediate Verus diagnostic.
2. State the exact unproved proposition and the facts visible at that point.
3. Choose one small proof change that could expose the missing connection.
4. Edit only the proof-relevant code and run Verus again.
5. Use the changed diagnostic to decide the next step; do not stack unrelated changes.
6. Finish only after a fresh Verus run succeeds and the proof-only safety check passes.

If syntax, proof mode, or an API signature is uncertain, inspect the local Verus
guide or installed vstd declaration before editing.

## Safety boundaries

- Preserve executable behavior and existing function contracts.
- Never add `assume`, `admit`, `external_body`, axioms, or verification bypasses.
- Do not claim success from narration or a smaller error count.
- Keep broadly applicable procedure here. Put detailed, lower-frequency
  mechanisms in directly linked `references/*.md` files and read them only when
  their observable trigger matches the current obligation.
