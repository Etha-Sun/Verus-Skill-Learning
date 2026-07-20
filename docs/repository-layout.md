# Repository Layout

## Repository Identity

- GitHub repository: `verus-skill-learning`
- Python distribution: `verus-skill-learning`
- Python import package: `verus_self_evolve`
- visibility: private

Keeping the existing import package avoids a broad mechanical rename while the
research interfaces are still changing.

## Repository Boundary

Commit:

- `src/`, `tests/`, `configs/`, `scripts/`, and `docs/`;
- small deterministic fixtures;
- data schemas, registries, hashes, and split manifests;
- reviewed compact summaries under `results/` when they support a claim.

Do not commit:

- raw Verus trajectories or complete LLM logs;
- sealed-test contents or answers;
- token-level probability tables;
- checkpoints, caches, model weights, or large serialized objects;
- machine-specific `.env` files and absolute paths;
- full run directories that can be regenerated.

Each collaborator selects a local data source through environment variables.
The repository does not prescribe shared storage or require physical data
migration. Experiment outputs go to `VERUS_SKILL_RUN_ROOT`; selected summaries
enter `results/` only after review.

## Code Layers

1. Data contracts: layout discovery, read-only guards, manifests, split and
   leakage checks.
2. Trace processing: parsers, target extraction, feature/motif construction.
3. Skill learning: selection, distillation, rule or skill induction.
4. Evaluation: offline replay, information gain, live hands-off harness.
5. Reporting: aggregate tables, audits, plots, and claim-bounded summaries.

Dependencies should flow downward through these layers. Evaluation code may
consume learned skills; data parsers must not import experiment-specific
evaluation code.

## Development Rules

1. CI and unit tests use synthetic fixtures only.
2. Data readers never write into a selected source.
3. Generated runs stay outside the checkout.
4. No committed file contains a personal absolute path.
5. A result enters Git only when it is compact, reviewed, and supports a
   documented claim.
