# Verus Syntax, Macro, Crate, and Type-Environment Repairs

**Consult when:** Verus fails to compile or emits syntax/deprecation/type-inference/trait-contract/macro-availability errors before the intended proof gap is reachable.

**Do not consult when:** The file already compiles and the remaining failure is a logical proof obligation, not an environment or syntax error.

<a id="verus-global-074"></a>

## verus_global_074 — Replace deprecated Verus `is_None()` syntax with modern `is None` pattern matching

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** Verus verification succeeds or nearly succeeds, but emits a deprecation warning for legacy `is_None()` on an Option value.

**Obstacle:** Legacy `is_None()` method syntax triggers Verus deprecation warnings in otherwise verified code, leaving a noisy or unclear verification environment.

**Mechanism:** Rewrite the deprecated method call to modern Verus pattern syntax `if <option> is None`.

**Procedure:**
1. Locate the deprecated `is_None()` call in the function or file.
2. Replace it with the modern pattern form `if <option> is None`, preserving the same control-flow meaning.
3. Re-run Verus and ensure the function still verifies without the deprecation warning.

**Why:** Removing syntax deprecation warnings keeps the verified file aligned with current Verus expectations and prevents stale warnings from obscuring real proof status later.

**Check:** Verus reports 0 errors and no deprecation warning for the modified Option emptiness check.

**Avoid or stop:**
- Do not treat warning-only syntax changes as satisfying remaining proof obligations.

<a id="verus-global-075"></a>

## verus_global_075 — Rename quoted quantifier-bound variables to Rust 2021-compatible identifiers

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A Verus proof block uses a quantifier closure such as `forall|s'| ...` or `exists|s'| ...` and compilation fails under Rust 2021 because of single quotes in the closure parameter name.

**Obstacle:** Rust 2021 lexical rules reject single quotes in closure parameter names, so Verus quantifiers with quoted bound variables fail to compile before proof checking can begin.

**Mechanism:** Rename each quoted bound variable to a plain identifier and update all references in the quantifier body.

**Procedure:**
1. Find every `forall` or `exists` quantifier whose bound variable name contains a single quote.
2. Rename the bound variable to a plain identifier such as `<old-name>_witness`.
3. Update all references to the renamed variable inside the quantifier body.
4. Re-run Verus to clear the compilation error.

**Why:** Verus proof closure parameters are Rust closure parameters, so they must follow Rust 2021 identifier restrictions; plain names remove a pure syntax blocker without changing the proof meaning.

**Check:** Verus compilation proceeds past quantifier parsing and no single-quote closure parameter error remains.

**Avoid or stop:**
- Do not choose a new name that duplicates an existing binder or accidentally changes scoping.

<a id="verus-global-076"></a>

## verus_global_076 — Resolve Verus type-inference failures for ambiguous generic constructors and sequence literals with explicit annotations

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** Verus reports cannot-infer-type errors for generic proof/spec constructors such as `Map::empty()`, `Seq::empty()`, or untyped integer sequence literals such as `seq![0]` in ghost/proof code.

**Obstacle:** Ambiguous generic type parameters or numeric literal element types in Verus ghost/spec constructors prevent type checking and block verification.

**Mechanism:** Add explicit type parameters to generic constructor calls and explicit integer suffixes or annotations to sequence literals, preserving the intended spec type.

**Procedure:**
1. Locate the generic or numeric spec constructors for which Verus cannot infer the type.
2. For empty generic collection constructors, apply explicit type parameters using Verus generic syntax such as `Map::<K, V>::empty()` or `Seq::<T>::empty()`.
3. For ambiguous integer sequence literals, add an explicit integer type suffix such as `seq![0u8]` instead of `seq![0]`.
4. Re-run Verus to confirm the inference errors are cleared and the surrounding proof remains valid.

**Why:** Explicit type annotations give the Verus type system enough information at the constructor site without changing the logical or executable semantics.

**Check:** Verus no longer emits cannot-infer-type errors for the annotated constructors, and the rest of the function verifies with the intended types.

**Avoid or stop:**
- Do not choose a type merely to silence inference if it changes the intended abstract or concrete spec type.

<a id="verus-global-077"></a>

## verus_global_077 — Remove duplicated trait requires/ensures clauses from implementation methods

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** A Verus `exec fn` implements a trait method and repeats the trait's `requires`/`ensures` contract in the implementation, causing a contract redeclaration error.

**Obstacle:** Verus rejects trait impl methods that redeclare the trait contract header instead of inheriting it.

**Mechanism:** Delete the duplicated `requires`/`ensures` clauses from the implementation method and let proof blocks rely on the inherited trait contract.

**Procedure:**
1. Compare the implementation method signature with the corresponding trait method declaration.
2. Remove duplicate `requires` and `ensures` clauses from the `impl` method.
3. Keep proof annotations that use the inherited contract terms, but do not redeclare the contract itself.
4. Re-run Verus to confirm the redeclaration error is gone and the method verifies.

**Why:** In a trait implementation, the contract belongs to the trait method declaration; redeclaring it in the impl method is a Verus syntax/contract error and blocks verification.

**Check:** Verus no longer emits the cannot-redeclare error and the implementation verifies using the inherited trait contract.

**Avoid or stop:**
- Do not remove the trait declaration's original contract.
- Do not delete necessary assertions that reason from the inherited contract.

<a id="verus-global-078"></a>

## verus_global_078 — Avoid introducing invalid nested proof constructs during proof search

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** While searching for a proof, edits introduce unsupported or invalid Verus constructs such as a nested `proof fn` inside another function or invalid use of `vstd::pervasive::unreached()` in a `proof fn` context.

**Obstacle:** Invalid proof syntax creates unrelated Verus errors that obscure the actual logical gap and waste proof-search effort.

**Mechanism:** Restrict edits to permitted Verus proof syntax, remove invalid constructs, and refocus on the real proof obligation.

**Procedure:**
1. Identify whether the current proof-search edit uses a disallowed construct such as a nested `proof fn` or invalid `unreached()`.
2. Remove or replace the invalid construct with an allowed Verus proof idiom.
3. Refocus on the underlying logical gap using lemmas, assertions, or valid spec reasoning.
4. Re-run Verus to ensure only relevant proof obligations remain.

**Why:** Unsupported proof constructs add syntax noise and do not contribute to the actual proof, so eliminating them makes the remaining verification task visible.

**Check:** Verus errors no longer include invalid-construct messages; remaining errors concern the actual proof goal.

**Avoid or stop:**
- Do not use invalid constructs as placeholders or suppress real proof obligations.

<a id="verus-global-079"></a>

## verus_global_079 — Repair Verus macro/crate environment, or manually expand macros with validation

**Status:** `candidate_unvalidated` · `multiple_trajectories` · `untested`

**When:** A Verus file fails to compile because macros reference `::builtin_macros::verus!` or an unavailable procedural macro, especially when the file is invoked standalone rather than inside a minimal Cargo project; if the macro environment cannot be repaired, the file must be made self-contained by expanding macros to concrete Verus items.

**Obstacle:** Unresolved macro paths or unavailable procedural macros prevent Verus from compiling the file, making later proof annotations untestable; manual expansion can also lose semantic equivalence, generated spec details, correct ordering, or proof support.

**Mechanism:** First restore macro availability through invocation, import, or crate-structure fixes; in the internal-path case replace `::builtin_macros::verus!` with the public `verus!` and prefer preserving macro-generated proofs. If preservation is impossible, replace each macro invocation with the concrete trait impls, spec functions, and match expressions it would generate; validate key abstract views against the original intent; then verify the entire file.

**Procedure:**
1. Run `verus --no-verify` on the file to separate compilation failures from proof failures.
2. For `cannot find macro 'builtin_macros'` errors, inspect internal path usage and replace `::builtin_macros::verus!` with `verus!` where appropriate.
3. Check whether the file should be placed in a minimal Cargo project with the correct Verus dependency and crate type.
4. Investigate simple command-line, import, and crate-structure fixes before rewriting or deleting macros.
5. Preserve macros that provide proof-critical support unless every reasonable way to make them available has been ruled out.
6. If macro availability still cannot be restored after those fixes, use existing verified files or macro definitions to determine the intended concrete expansion pattern.
7. Replace every macro invocation with explicit generated items rather than partial approximations; prefer direct source edits or a reliable expander over fragile multi-line regex rewriting for complex macros.
8. Validate key generated abstract/trait views against the original macro-derived definitions before main proof work.
9. Run Verus on the entire file to catch missing trait impls, duplicate definitions, parse errors, and type mismatches.

**Why:** Macro failures are often caused by the invocation or project environment rather than the source macro itself; preserving macros avoids losing generated proof support. When preservation is impossible, manual expansion removes the dependency on unavailable macro bodies and gives direct control over the resulting spec code, but only works if the replacement preserves generated abstractions and proof support.

**Check:** The original file compiles under `verus --no-verify` after path, import, or crate correction; if the macro-preservation path is conclusively ruled out, the expanded file must compile and verify as a whole with 0 errors, with no mismatches between handwritten impls and the original abstract/Trait views.

**Avoid or stop:**
- Do not immediately abandon the original file because the first macro invocation fails.
- Do not manually expand macros just to avoid checking build flags, imports, or Cargo setup.
- Do not choose manual expansion before exhausting environment/crate repair where macros can be preserved.
- Do not layer proof annotations on top of a still-uncompilable file.
- Do not use regular-expression-only rewriting for nested multi-line macros with deep brace structure.
- Do not proceed with proof work when the expanded abstract or trait views cannot be validated against the original intention.

<a id="verus-global-080"></a>

## verus_global_080 — Avoid regex-based Verus macro expansion for nested multiline braces; prefer direct edits with incremental verification

**Status:** `candidate_unvalidated` · `single_trajectory` · `untested`

**When:** An agent considers or uses a regex/script to remove or expand multi-line `macro_rules!` Verus macros with deeply nested brace-heavy bodies.

**Obstacle:** Regular expressions cannot reliably track nested braces in macro definitions, so repeated pattern tweaks produce stray braces, missing blocks, and hidden parse errors.

**Mechanism:** Avoid regex as the primary expansion strategy; if an automated transform is attempted, verify the generated file incrementally and abandon repeated pattern-matching failures quickly.

**Procedure:**
1. For complex or nested Verus macros, avoid starting with regex substitution as the primary strategy.
2. If a scripted attempt is made, run Verus after each small generated-file change rather than batching many edits.
3. On persistent parse/brace errors or repeated pattern adjustments, stop tweaking the script and abandon the regex approach.
4. Directly edit macro invocations to concrete generated Verus items using source-level manual expansion.
5. Re-run Verus after the alternative edit to catch syntax or type errors early.

**Why:** Multi-line macros with deeply nested braces make regex patterns fragile; direct edits and incremental verification prevent cascading hidden syntax errors and wasted time.

**Check:** After switching away from regex-based rewrites, the generated file has balanced braces, no macro remnants, and Verus compiles or verifies.

**Avoid or stop:**
- Do not keep adjusting regex patterns after repeated failures.
- Do not batch changes without running Verus between changes.
