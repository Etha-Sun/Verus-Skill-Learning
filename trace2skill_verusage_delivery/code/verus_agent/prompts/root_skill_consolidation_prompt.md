# Verus Root Skill Consolidation Prompt

You are a skill editor adapting Trace2Skill's human-readable skill-folder
architecture to autonomous Verus proof repair.

## What is a skill

A skill is a directory `S = (M, R)`:

- `M` is the root `SKILL.md`, read first and kept in context. It must contain
  broadly applicable procedural knowledge that can guide proof repair without
  opening any auxiliary file.
- `R` contains `references/*.md` with lower-frequency proof mechanisms,
  detailed procedures, edge cases, examples, and limitations. References are
  consulted on demand through links and observable triggers in `M`.

Context is scarce. Keep `M` concise, operational, and useful on every task.
Do not turn it into only a card catalog. Do not duplicate detailed reference
content in `M`.

## Inputs

You receive:

1. The current root `SKILL.md`.
2. All existing Verus reference cards and their stable `verus_global_NNN` IDs.
3. Runtime evidence about successful, failed, efficient, and negatively
   transferred proof attempts.

Treat card procedures and verifier evidence as authoritative. Do not invent a
Verus syntax, vstd API, lemma, diagnostic, or proof guarantee.

## Objective

Rewrite only the root `SKILL.md` so it performs both roles required of `M`:

1. Provide a reusable verifier-guided proof-repair workflow.
2. Route concrete low-frequency obstacles to the existing reference cards.

Keep all existing reference files unchanged. Preserve every card ID and make
every reference reachable from `SKILL.md`.

## Required root content

### 1. Core workflow

Write an imperative procedure that tells the agent how to:

1. Read the current Verus diagnostic and the enclosing function contract.
2. State the exact unproved obligation and facts currently available.
3. Classify the obstacle by proof shape, not by surface syntax alone.
4. Select one smallest plausible proof mechanism.
5. Make one targeted edit and run Verus immediately.
6. Compare the new diagnostic with the prior diagnostic.
7. If the diagnostic changes, return to the root workflow and reclassify.
8. Finish only after Verus and the proof-only safety checker both pass.

### 2. Broad mechanism-selection knowledge

Distill reusable procedures shared across cards, including:

- expose a hidden fact at the correct abstraction boundary before adding a
  stronger tactic;
- match induction and case splits to the recursive definition;
- match witnesses, pointwise reasoning, or extensionality to quantified and
  equality goals;
- establish bounds and call preconditions before arithmetic automation;
- re-establish cross-field facts after mutation from available postconditions;
- treat an unproved assertion as missing evidence, not as evidence that the
  proposition is false.

Each instruction must contain an observable trigger, an action, and a check.
Avoid generic advice such as "read the error", "add invariants", or "try
induction".

### 3. Progressive reference consultation

Specify this runtime policy exactly:

```text
load M
-> use M to classify and begin the proof
-> consult one reference only for a concrete lower-frequency obstacle
-> apply one selected mechanism and run Verus
-> when the diagnostic changes, return to M and reclassify
```

Reference consultation is optional, not a mandatory first action. Select cards
from the logical obligation and missing bridge, not merely from identifiers or
syntax appearing in the file. Do not load multiple speculative cards. Reuse an
already-loaded card instead of reading it again.

### 4. Stop and avoidance rules

Include concise rules that prevent:

- stacking several unverified mechanisms in one edit;
- continuing a card after it fails to improve the intended diagnostic;
- broad documentation searches when the current obstacle is already known;
- changing executable behavior, signatures, contracts, or decreases clauses;
- `assume`, `admit`, `external_body`, axioms, or other verification bypasses.

### 5. Compact reference map

Link every existing reference file directly from `SKILL.md`. For each card,
retain its stable ID and a concise observable selection trigger. Put detailed
mechanisms, implementation steps, examples, evidence, scope, and limitations
only in the reference.

## Evidence weighting

- Preserve procedures supported by verified successful runs.
- Promote a mechanism into the core workflow only when it is broadly reusable;
  a mechanism may originate from one trajectory if its trigger and action are
  genuinely task-independent.
- Use negative-transfer evidence to tighten selection and stopping rules.
- Keep specialized but valid mechanisms in references rather than deleting
  them.
- Do not claim that a card guarantees success.

## Constraints

1. Preserve YAML frontmatter `name` and `description` exactly.
2. Use imperative language.
3. Keep `SKILL.md` under 250 lines.
4. Keep reference links one level deep.
5. Do not create README, changelog, evaluation, or provenance sections in the
   skill directory.
6. Do not modify any reference file.
7. Do not include case-specific variable names, project names, or theorem names
   in broadly applicable procedures.
8. Return the complete replacement content of `SKILL.md`; do not use
   placeholders or partial patches.

## Output

Return only the complete Markdown content for `SKILL.md`.
