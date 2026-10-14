# Specialized recursive lemmas for concrete fold bounds

## Scope

- Consult when: Generic higher-order fold lemmas do not connect to concrete fold expressions
- Consult when: Concrete fold-bound or append-length obligations remain
- Consult when: Element type supports recursive empty/nonempty decomposition
- Not for: Generic lemma already instantiates correctly
- Not for: Recursive structure lacks a decreasing well-founded measure

## Rules

- [Specialized recursive lemmas for concrete fold bounds](#specialized-fold-bound-lemmas-verbatim)

<a id="specialized-fold-bound-lemmas-verbatim"></a>
## Specialized recursive lemmas for concrete fold bounds

Source cards: card-022

**Trigger:** Generic higher-order fold lemmas discharge their own preconditions, but their postconditions do not connect to later concrete fold expressions. Concrete fold-bound and append-length obligations continue to fail even after those generic lemmas are invoked.

**Action:** Introduce specialized recursive lemmas over the concrete element type. In the empty case, unfold the fold with enough fuel and prove the zero or empty result. In the nonempty case, remove the final element, establish the elementwise facts for the shortened sequence, call the lemma on the remainder, unfold the fold again, and add the final element's contribution to the bound. Include preconditions that every element is well-formed for serialization and that each element satisfies the chosen numeric bound.

**Why:** The concrete fold expression matches the specialized lemma's conclusion exactly, whereas the higher-order lemma retains an abstract function argument that the solver does not rewrite into the concrete folding function.

**Validate:** The previously failing concrete fold-bound and append-length assertions discharge after replacement. Verus reports no errors and the proof-only safety comparison passes.

**Avoid when:** The generic lemma already instantiates correctly, or the recursive structure does not provide a decreasing well-founded measure.

- Distinguish from [finite-set-fold-cardinality-induction](finite-set-fold-cardinality-induction.md): Finite-set route targets fold over finite sets; this route targets concrete sequence element bounds and recursive element facts.

- Related [finite-set-fold-cardinality-induction](finite-set-fold-cardinality-induction.md): Finite-set route targets fold over finite sets; this route targets concrete sequence element bounds and recursive element facts.

- Related [sequence-fold-concat-equality](sequence-fold-concat-equality.md): Specialized-bound route creates concrete recursive lemmas for element bounds; concat route proves distribution over sequence append.
