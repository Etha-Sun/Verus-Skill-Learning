# Pre-Idea Draft: Project-Family Context Compaction

## Two-Sentence Pitch

Replace one-size-fits-all full-code prompts with project-family context profiles: `AC` gets temporal phase lemmas and state predicates; `OS` gets linked-list/page-table invariants; `NR` gets refinement and bit/address facts. The goal is to reduce input-token replay while increasing relevance of retrieved proof context.

## Hidden Assumptions

- Project-family structure is stable enough to define reusable context profiles.
- The relevant helper lemmas can be extracted automatically.
- Token savings from smaller prompts will not remove necessary context.

## Strongest Rejection Case

Poor slicing can omit a required definition, leading to more failed attempts despite lower per-call tokens.

## Cheapest Falsification

For a fixed set of successful traces:

- Reconstruct the minimal definitions/lemmas actually referenced in the final patch.
- Measure how often a proposed slicer includes them.
- Compare prompt size against original `llm-prompts/*-input.txt`.

## Promotion Verdict

Defer as a component after skeleton extraction identifies which context elements are repeatedly useful.

