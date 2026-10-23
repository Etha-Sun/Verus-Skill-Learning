# Whole-card P2-style pseudocode conversion contract

This contract describes the representation used in this offline variant. Codex authored
and source-reviewed the 20 routes; this is not a record of a paid optimizer request.
Historical P2 supplied the organization reference, not extra mathematical content.

## Input and knowledge boundary

Convert exactly one frozen card. Its title, prose, and lossless private source-clause
index are the only sources of card-specific knowledge. No validation/test questions,
actor solutions, diagnostics, benchmark outcomes, or other cards enter the conversion.
The present author has already seen aggregate development results; therefore this
variant is not an independently blinded or held-out design.

Preserve applicability, actions, premises, claims, causal uncertainty, validation,
and rejection conditions. Preserve strong old claims as source claims; do not quietly
repair the old arm or strengthen the new arm while changing representation.

## Required actor-facing form

1. Applicability: preserve the source conditions, including important qualifiers.
2. Proof skeleton: a fenced `text` block carrying the actual proof/check route.
3. Rationale and evidence limits: preserve what is known and what is not established.
4. Validation and rejection limits: preserve the source checks and stopping boundaries.

The skeleton is non-executable pseudocode. It must show the card's own supported
proof organization rather than a numbered checklist of English sentences:

- Put the relevant diagnostic/goal in an entry guard.
- Nest arbitrary-variable binders and justified-premise scopes where the source
  supports them. A branch premise is not a new trusted assumption.
- Express proof directions, base/recursive cases, alternatives, and fallback branches
  only when supported by this particular source.
- Put unresolved proof connections in `<...>` slots. Do not turn slots into APIs,
  paste a historical successful formula, or fill a missing proof with an assumption.
- Keep dependent facts in scope; show closure/checks before their consequences are used.
- Preserve diagnostic inspection and stopping steps, not only successful proof steps.
- Keep reasoning and uncertainty beside the route or in the preserved supporting text.

Formatting in a code fence is necessary but insufficient. If removing the fence leaves
only the same sequence of prose bullets, or indentation conveys no proof dependency,
reject the conversion. Conversely, do not force an equality/entailment template onto
recursion, serialization, or syntax-repair cards for visual similarity.

No O1/O2/S1/S2 identifiers in actor prose. All source tracking belongs in private metadata.
Do not require every line to have a displayed obligation number. Do not invent formal
notation just to shorten a sentence; use descriptions of actual locally bound objects.

## Private mapping and review

For every source clause, give the exact source span and all output line locations.
Every substantive pseudocode line must have source support. Record scope or ambiguity
limits explicitly. Coverage alone is not semantic equivalence.

Before accepting a card, inspect source and rendered output side by side:

- Can the entry be satisfied under exactly the original applicability conditions?
- Are all current actions represented without adding a stronger remedy or a new lemma?
- Are universal scopes, antecedents, current objects/indices, and branch alternatives preserved?
- Is every helper application still conditional on its justified premises?
- Are failure paths and uncertain mechanisms preserved, including old overclaims?
- Does the code block visibly carry the dependencies, not merely paraphrase the text?
- Is every mathematical detail supported by this card instead of the P2 example?

Freeze the paired retrieval index and unchanged prose separately. Do not overwrite
an earlier evaluated bank; create a new representation version. Structural checks do
not establish verifier correctness or downstream benefit. No automatic actor launch.
