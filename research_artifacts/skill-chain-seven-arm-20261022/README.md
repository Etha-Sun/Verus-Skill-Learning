# Prompt-chain extraction and seven-arm skill comparison

This package contains the exact skill bundles used in the completed October 22
on-demand development experiment, plus the code used for extraction and evaluation.
It does not contain raw training trajectories, provider requests/responses,
credentials, candidate proofs, or validation/test reference answers.

## Read the skills

Each skill arm has **10 cards**. `SKILL.md` is the main instruction and card index;
`cards.json` contains the bodies, read on demand through `card_read.py`.
The combined Markdown views below are for human inspection, not injected prompts.

| Arm | Main file | All card bodies |
|---|---|---|
| No skill | [SKILL.md](bundles/no_skill/SKILL.md) | Shared executive only |
| Old prose | [SKILL.md](bundles/old_prose/SKILL.md) | [10 cards](material-views/old_prose--all-cards.md) |
| Old structured | [SKILL.md](bundles/old_skeleton/SKILL.md) | [10 cards](material-views/old_skeleton--all-cards.md) |
| Old pseudocode | [SKILL.md](bundles/old_pseudocode/SKILL.md) | [10 cards](material-views/old_pseudocode--all-cards.md) |
| New prose | [SKILL.md](bundles/new_prose/SKILL.md) | [10 cards](material-views/new_prose--all-cards.md) |
| New structured | [SKILL.md](bundles/new_skeleton/SKILL.md) | [10 cards](material-views/new_skeleton--all-cards.md) |
| New pseudocode | [SKILL.md](bundles/new_pseudocode/SKILL.md) | [10 cards](material-views/new_pseudocode--all-cards.md) |

The historical directory name `skeleton` means the **numbered structured** version
in this experiment. It is distinct from the later P2-inspired pseudocode version.
O1, O2, etc. identify obligations/checks; they are not executable code.
Within each content family, all three `SKILL.md` files are byte-identical.
The old and new families have different card descriptions and coverage, so their
comparison includes retrieval differences as well as content differences.

## Where the content came from

- **Old:** ten selected cards reused from the existing repaired 78-card library;
  the prose bodies were not re-extracted for this experiment.
- **New:** ten training tasks, each with its original trajectory and three
  augmented branches: 40 logical trajectories in total. Full histories were
  retained; the chain splits responsibilities, not long trajectories.
- **A — facts:** extract trace-grounded observations, code changes and verifier
  outcomes, with evidence references.
- **B — explanations:** interpret the reviewed facts, qualifying scope and
  uncertainty rather than treating bundled changes as isolated causal evidence.
- **C — actions:** derive conditional instructions to inspect, bind, compare,
  probe and validate. Instantiation guidance emphasizes current declarations,
  premises, expression forms and proof scope rather than copied solution formulas.

The extractor was DeepSeek V4 Pro. Outputs were reviewed between stages.
Of the ten selected new cards, eight received semantic revisions (24 field edits)
and two retained their content. The new content is therefore **prompt-chain
extraction plus Codex review/revision**, not an isolated test of chaining alone.

Prose and structured versions share reviewed content; whole-card structured
conversion used DeepSeek followed by representation review. Pseudocode routes
were written and checked by Codex offline, with source-clause mappings.
The task-specific branches, checks and obligations are organized per card; there
is no single generic skeleton prepended to all cards.

[Source cards](source-cards/), [pseudocode routes](pseudocode-routes.txt), and
[conversion rules](PSEUDOCODE_CONVERSION.md) document the offline transformation.
The conversion-rules document is a historical preparation document; its statements
about no actor launch refer to that stage, not the completed experiment.

## Main code

Paths below are relative to the repository root. Prompts and output contracts are
in the listed Python modules, alongside the stage drivers.

| Step | Driver | Prompt / contract |
|---|---|---|
| A: facts | [run_ten_card_facts.py](../../scripts/run_ten_card_facts.py) | [extract_chained_full_traces.py](../../scripts/extract_chained_full_traces.py) |
| B: explanations | [run_ten_card_interpretations.py](../../scripts/run_ten_card_interpretations.py) | [interpret_full_trace_facts.py](../../scripts/interpret_full_trace_facts.py) |
| C: actions | [run_ten_card_actions.py](../../scripts/run_ten_card_actions.py) | Same driver, with [design_full_trace_actions.py](../../scripts/design_full_trace_actions.py) |
| Structured conversion | [run_ten_card_representations.py](../../scripts/run_ten_card_representations.py) | Same module |
| Pseudocode rendering | [render_reviewed_pseudocode.py](../../scripts/render_reviewed_pseudocode.py) | Reviewed routes and source clauses in this package |
| Seven-arm actor evaluation | [evaluate_ten_card_seven_arm.py](../../scripts/evaluate_ten_card_seven_arm.py) | Seven-arm schedule, shared executive, optional card reader |
| Interrupted-run recovery | [resume_ten_card_seven_arm.py](../../scripts/resume_ten_card_seven_arm.py), [second recovery](../../scripts/resume_ten_card_seven_arm_second.py), [budget-raised recovery](../../scripts/resume_ten_card_seven_arm_budget_raised.py) | Preserve completed cells and historical spend; do not select best attempts |

The historical drivers require locally prepared data, verifier installations,
review receipts, frozen contracts and guarded budget ledgers. This is a code and
skill publication, not a self-contained copy of the private run directories.
Historical authorization strings and budgets describe that experiment; they are
not permission to make new API calls. No API call is needed to inspect the cards
or reproduce the pseudocode bodies.

From the repository root, read one card:

```bash
python3 research_artifacts/skill-chain-seven-arm-20261022/bundles/new_skeleton/card_read.py new-005
```

Render the twenty reviewed pseudocode bodies into a fresh output directory:

```bash
python3 scripts/render_reviewed_pseudocode.py \
  --sources research_artifacts/skill-chain-seven-arm-20261022/source-cards \
  --routes research_artifacts/skill-chain-seven-arm-20261022/pseudocode-routes.txt \
  --output /tmp/verus-reviewed-pseudocode
```

Publication checks verify exact bundle hashes, paired index equality and exact
reproduction of all twenty pseudocode card bodies. Extraction/evaluation tests
use synthetic fixtures and mocks; they do not launch paid inference.

## Experiment scope and result

Seven arms x eight selected validation development tasks x two repeats = 112
valid episodes. Actor: DeepSeek V4 Pro; 600-second limit; two concurrent workers.
Each skill arm could choose whether to read card bodies. Ordinary timeouts and
failures were retained. Six infrastructure/budget-blocked attempts were tracked
separately, rather than counted as valid comparison cells.

| Arm | Dual verification and actor exit within 600 s | Dual verification observed within 600 s |
|---|---:|---:|
| No skill | 12/16 | 12/16 |
| Old prose | 12/16 | 12/16 |
| Old structured | 12/16 | 12/16 |
| Old pseudocode | 12/16 | 12/16 |
| New prose | 14/16 | 14/16 |
| New structured | 13/16 | 14/16 |
| New pseudocode | 13/16 | 13/16 |

Dual verification means Verus and Lynette passed on the same candidate. One new
structured run reached both checks within the deadline but did not exit in time.
Some new structured runs showed clear use of card guidance, fewer tokens or an
additional pass. Reading a card does not by itself establish adoption or causality.
Differences in runs with no card-body exposure are treated as performance
variation. Pseudocode showed no consistent advantage. These are small, repeatedly
examined development results, not held-out test evidence or a general superiority claim.

The bundle source paths (relative to the run-root alias) and SHA-256 hashes are in
[manifest.json](manifest.json). All published bundle bytes match the evaluated
artifacts; raw datasets and historical runs remain unchanged.

## Later index and main-text comparisons

See the [v2 index and G1/G2 follow-up publication](../index-guidance-followups-20261028/README.md)
for the exact subsequent bundles, intervention diffs, reviewed results and per-task timing ratios.
