---
name: verus-proof-repair
description: Repair incomplete or failing Verus proofs through verifier-guided iteration. Use when a Verus function, lemma, invariant, specification bridge, or arithmetic obligation does not verify.
---

# Verus Proof Repair

Use the current verifier state to make the smallest justified proof change.
This initial skill intentionally contains no task-specific proof mechanisms;
lower-frequency mechanisms may be added to `references/` from observed evidence.

## Core workflow

0. **Compile and verify current state.** Run `verus` on the original file. If it succeeds, stop—no repair is needed. If compilation fails, fix the error first (see Pre‑check: compilation).
1. **Understand the obligation.** Read the failing function, its contracts, the definitions of any called functions appearing in the proof obligation, and the fresh Verus diagnostic. List every proof function, lemma, and specification predicate already in the file—reuse them before introducing new reasoning.
2. **Pinpoint the gap.** State the exact unproved proposition and the facts visible at that point. If it is a postcondition, note which conjunct fails (e.g., `is_marshalable()` or a size bound).
3. **Prepare for quantifier or inductive goals.** If the obligation involves universal quantifiers or induction, use these techniques:
   - For `forall` postconditions or assertions that need instantiation, provide an explicit witness and call the relevant lemma within an `assert forall` block.
   - For opaque recursive definitions, use `by(compute_only)` to reveal the function’s structure. Isolate base cases as separate, trivial lemmas; an empty proof body is acceptable if the obligation follows directly from definitions.
4. **Choose one small proof change.** Options:
   - Call an existing lemma whose conclusion implies the goal.
   - For a composite type, invoke its field lemmas.
   - If the diagnostic involves a loop, ensure the loop has a `decreases` clause and invariants strong enough to prove the postcondition directly.
   - If a loop uses `break`, capture the break reason with a ghost variable and strengthen the invariant accordingly.
5. **Edit only proof‑relevant code** and run Verus again.
6. **React to the new diagnostic.** Use the changed output to decide the next step. Do not stack unrelated changes. If the same proof step fails after three attempts that differ only in minor details (fuel, trigger placement, assertion formulation), abandon that step and design a fundamentally different strategy.
7. **Close the proof.** Once a fresh Verus run succeeds, remove any assertions that duplicate already‑proven facts to keep the proof minimal. Then perform a safety check: confirm that no prohibited constructs (new axioms, `assume`, `admit`, empty lemmas) were introduced.
8. **Finish** only after the proof‑only safety check passes.

If syntax, proof mode, or an API signature is uncertain, inspect the local Verus
guide or installed vstd declaration before editing.

## Safety boundaries

- Preserve executable behavior and existing function contracts.
- Never add `assume`, `admit`, `external_body`, axioms, or verification bypasses.
- Never introduce a lemma or proof function whose body is empty or consists only of comments. Every new lemma must contain actual proof steps and be verified before it is called elsewhere.
- Never use a lemma annotated `#[verifier::external_body]` or with an `unimplemented!()` body as a proof step; such functions are axioms even if named `lemma`.
- Do not create renamed copies of the source file (e.g., `_verified.rs`). All proof edits must be made directly to the supplied file.
- Never insert a large batch of untested proof annotations in a single edit. Add one small change and re‑run the verifier before adding more.
- Before calling any lemma or function from vstd or another library, verify its existence by searching the installed source files and ensure it has a verifier‑checked body. Do not invent lemma names.
- Do not claim success from narration or a smaller error count.
- Keep broadly applicable procedure here. Put detailed, lower‑frequency mechanisms in directly linked `references/*.md` files and read them only when their observable trigger matches the current obligation.



## New Section

## Common pitfalls and proof patterns

When a proof stalls, check the most frequent root causes:

- **Compilation first**: A file that does not compile cannot be verified. Fix any build errors before adding proof annotations.
- **Exact failing conjunct**: Always identify which part of a postcondition is unproved; do not add speculative lemmas.
- **Macro‑generated proofs**: Preserve macros like `builtin_macros::verus!`. Fix missing imports or crate features rather than expanding them manually, unless the macro is unavailable and a manual expansion is the only viable path (then verify the expansion immediately with Verus).
- **Size‑bound obligations**: When proving a bound like `len_a + len_b <= usize::MAX`, chain explicit lemmas that link each component’s serialization length to concrete constants.
- **Loop break conditions**: If a postcondition depends on why a loop broke, capture the reason with a ghost variable and strengthen the loop invariant to record it. Do not try to re‑evaluate the break condition after the loop.
- **Induction pitfalls**: Match induction to the function’s recursive structure (use `by(compute_only)` if the definition is opaque). Do not rely on unprovable decomposition lemmas (e.g., prefix‑suffix splitting of `fold_left`).
- **Stuck patterns**: If after three iterations you are still adding more auxiliary lemmas for the same goal, pause and redesign the proof with a simpler induction or element‑by‑element argument.

For detailed, proven recipes covering all the above (set equality, loop invariants, universal quantifiers, trait/serialization proofs, ordering, vector subrange reasoning, and more), consult **[references/verus-proof-patterns.md](references/verus-proof-patterns.md)**. Open it only when the current obligation matches one of the described triggers.
## New Section

## Pre-check: compilation

Before adding any proof annotations, ensure the file compiles:
- Run `verus --no-verify` (with appropriate Cargo flags if needed). If compilation fails, fix the compilation error first.
- Common issues: missing crate dependencies, macro errors like `builtin_macros` (often need a proper Verus crate or manual macro expansion), unresolved imports.
- Do not write proof annotations until the file compiles successfully.