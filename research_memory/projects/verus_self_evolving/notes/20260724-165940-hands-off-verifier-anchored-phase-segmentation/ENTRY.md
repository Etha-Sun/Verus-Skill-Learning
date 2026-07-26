# R040 30-trace hands-off phase-segmentation pilot

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-07-24T16:59:40`
- status: `complete`

## Objective

Use the 30-trace R040 train selection to pilot whether hands-off trajectories
should be segmented by every tool call, every code edit, or every verifier
invocation. This entry is a phase-design pilot, not a corpus-wide fidelity
audit.

## Context

The audit used only the leakage-safe 30-trace R040 train selection: 15 Anvil
and 15 IronKV traces, with six traces from each of Opus 4.5, Sonnet 4, Sonnet
4.5, GPT-5, and o4. No sealed MA/NR content was read.

Relevant provenance:

- R040 selection:
  `research_memory/projects/verus_self_evolving/experiments/20260720-164228-r040-leakage-safe-stratified-train-trace-selection/ENTRY.md`
- selected-trace manifest:
  `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/selected_traces.jsonl`
- source corpus:
  `${VERUS_SKILL_DATA_ROOT}/claude_sonnet_gpt5/`

## Method / Actions

Inspected the ordered event structure of all 30 selected logs. For plain CLI
logs, detected read/search/copy, edit/create, Verus, and checker labels. For o4
JSONL logs, used completed `command_execution` and `file_change` events and
matched the executed command to Verus versus `verus-checker`/Lynette.

Compared three candidate boundaries:

1. every tool call;
2. every edit-labelled or completed file-change event;
3. every Verus result associated with the current code snapshot.

Also inspected missing-event cases rather than assuming all logs expose the
same instrumentation.

## Evidence

- Format split: 24 plain-text CLI logs and 6 structured o4 JSONL logs.
- Detectable tool/edit sequences exist in 28/30 logs. An explicit Verus
  invocation is detectable in 27/30. These are parser-coverage numbers, not
  claims that the other logs performed no work.
- The missing/partial cases are materially different:
  - one Opus trace is a reasoning-heavy summary with no raw tool events;
  - one GPT-5 trace exposes only read/create events and no verification;
  - one GPT-5 file contains raw Verus diagnostics rather than an agent event
    stream.
- Across the six exact JSONL logs:
  - 168 completed command executions;
  - 61 completed file-change events;
  - 55 Verus executions;
  - 8 checker executions.
- Of the 55 JSONL Verus boundaries, 46 had exactly one file-change event since
  the previous Verus call, 5 had multiple edits, and 4 had no edit. Therefore
  edit and verifier calls are closely related but not one-to-one.
- The plain-text marker audit found far more observation/tool labels than
  verifier labels and many cases with multiple edit labels before a Verus
  call. Exact counts are heuristic because display formats differ and failed
  `Edit` events can appear in the text; they must not be used as paper metrics.

### Sample-level fidelity observations

The 30 selected traces are not representative enough to estimate
corpus-wide fidelity. Within this sample:

- Hidden/internal reasoning is generally absent. The six o4 JSONL traces
  contain command, file-change, and final-agent-message items but no reasoning
  items, despite reporting 12k-30k output tokens per trace.
- Plain Copilot displays expose selected assistant narration, not raw hidden
  thinking. Token footers can be much larger than the visible transcript: one
  GPT-5 trace reports 10.6k output tokens but has only 641 bytes of visible
  log; one Opus trace reports 71.3k output tokens but has a 33.5 KB log.
- Some tool outputs are summarized as line counts or abbreviated snippets.
  Structured o4 `file_change` events preserve the changed path and
  `add`/`update` kind, but not the patch.
- Representative result directories preserve only the original source, final
  verified file, and log. They do not preserve every intermediate code
  snapshot, so exact historical code states cannot generally be reconstructed.
- Recursive search commands can inject unrelated repository/log/script content
  into `aggregated_output`, including sensitive credentials. Raw logs therefore
  require redaction and command-output filtering before any prompt construction,
  training, or public artifact.

The later 9,383-log full audit supersedes any corpus-level inference from
these observations. It found that displayed UI diff-box Edit events are
usually highly complete: 60,581/60,740 (99.74%) match their declared line
counts, and 60,581/75,904 (79.81%) of all successful Edit events have exact
line-level diffs. The remaining losses are concentrated in summary-only Edit,
Create, and o4 `file_change` formats.

Canonical full audit:

- `research_memory/projects/verus_self_evolving/notes/20260725-215004-full-hands-off-log-fidelity-audit-migration/ENTRY.md`
- `docs/hands_off_log_fidelity_audit.zh.md`

## Result

Use a **verifier-anchored code-state transition** as the target primary phase
unit. The boundary is the completed verifier result for a particular code
snapshot, not the raw call start. For historical logs without a reconstructable
snapshot, downgrade this to a `verifier_anchored_text_segment` rather than
claiming an exact state transition.

Recommended hierarchy:

```text
trajectory
  orientation: start -> first Verus result
  repair transition i:
    input checkpoint: (code hash/version, Verus diagnostics)
    investigation: read/search/other tool events
    action: one or more successful code edits
    output checkpoint: next (code hash/version, Verus diagnostics)
  safety validation: Verus pass -> verus-checker/Lynette result
  terminal: verified / failed / timeout / unverified tail
```

Interpretation of the three candidates:

| Candidate | Use | Problem as primary boundary |
|---|---|---|
| Tool call | within-phase micro-event | too fine; reads/searches dominate and vendor formats differ |
| Code edit | transition action | multiple edits may implement one repair; failed edits are not state changes; an edit has no grounded outcome |
| Verus result | primary checkpoint | strongest formal feedback and supports error-delta reward; needs code-snapshot identity and missing-log fallbacks |

`verus-checker` and Lynette should remain a separate safety-validation event,
not be merged with Verus proof progress. Consecutive Verus calls on the same
code hash can be collapsed as a recheck when their diagnostics are equivalent.
An edit after the last Verus result is an `unverified_tail`, not a successful
repair phase.

This representation directly supports skill learning:

```text
S_i = verifier-grounded proof state
A_i = investigation tools + edit batch
S_{i+1} = next verifier-grounded proof state
reward = error delta / pass / safety status / cost
```

## Decision / Next Step

Treat verifier checkpoints as the provisional macro segmentation contract
suggested by this 30-trace pilot, and preserve tool calls plus successful
edits as nested events. Before population use, a parser should:

1. normalize structured JSONL and plain CLI displays into one event schema;
2. track code hashes or reconstruct versions after successful edits;
3. attach exact Verus diagnostics to the evaluated code version;
4. emit `exact`, `heuristic`, or `narrative_only` provenance confidence;
5. refuse to invent intermediate phases for summary-only logs.

Before scaling, manually label 10-20 heterogeneous traces and measure boundary
precision/recall for the parser.

For future hands-off collection, persist per tool call:

- full structured event type, command, return code, and bounded/redacted output;
- pre/post code hash and actual patch;
- full Verus diagnostics tied to the post-edit hash;
- checker result;
- provider-reported visible-output and hidden-reasoning token counts separately
  when available.

Do not attempt to collect or reconstruct hidden chain-of-thought. Preserve only
model-provided summaries or explicit rationales intended for logging.
