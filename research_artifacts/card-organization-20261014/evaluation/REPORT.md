# Four-Arm Task Outcome Comparison

## Shared Setup: Yuechun's Recommended Baseline

**Baseline recipe: shared corrected TASK + original Executive + repaired78 short index + matched tool/library permissions.** Arm A implements this recipe directly. Arms B and C retain the same task instructions and Executive, but change the knowledge organization and reading interface as described below; the index itself is therefore not identical across A/B/C.

- **TASK and Executive:** The shared corrected TASK defines the proof-repair task and constraints. The original VeruSAGE Executive supplies the general solving instructions; the diagnostic-first Executive variant is not used. These are solving instructions, not checkpoint augmentation hints.
- **Model and harness:** DeepSeek V4 Pro (`deepseek-v4-pro`), reasoning effort `max`, Codex 0.147.0, native Responses transport. Context limit: 1,048,576 tokens; output limit: 131,072 tokens per model request, not per episode.
- **Evaluation:** The same fixed validation20 tasks, one fresh run per task per arm, a 600-second actor budget, and two concurrent workers. All runs start from the original unverified task, not a selected checkpoint. Success requires passing both Verus verification and the Lynette proof-only safety check within budget.
- **Tools and permissions:** The same proof-editing and verification tools, installed `vstd` read access, and isolation policy in every arm. Executable behavior and specifications must be preserved; verification bypasses are forbidden. Reading knowledge is optional, with no mandatory retrieval or oracle-selected cards.
- **Knowledge source:** All variants derive from the same repaired78 bank. B and C reorganize that bank rather than adding a new training source.

All arms use the same local Verus version, `0.2025.09.12.bb1f342`. Its binary hash differs from Yuechun's historical build, so these runs share a matched local environment rather than being bit-identical historical replays.

## A/B/C Variants

| Variant | Knowledge organization | What the solving agent reads |
|---|---|---|
| **A: Flat 78-card baseline** | Yuechun's repaired78 cards with the compact flat index in the main skill file. | The agent optionally selects individual cards from the index and reads their bodies. |
| **B: Grouped, whole-reference reading** | Trace2Skill-inspired offline clustering and within-group consolidation: 78 source cards become 72 rules organized into 37 references, with a compact reference index in the main skill file. | Selecting a reference returns its full content, including all rules in that reference. There is no within-reference rule-selection step. |
| **C: Grouped, selective reading + navigation revision** | The same 37 groups and 72 rule bodies as B. Adds internal navigation, revises 23 rule cues, adds relationship notes to 21 multi-rule groups, and corrects 5 shared Scope descriptions. | The 16 single-rule references return their bodies directly. The 21 multi-rule references first expose a directory; the agent may then read selected rules or request the full reference. |

The router is used offline to organize the bank; no additional routing model is called during proof solving. C is a **combined reading-interface and navigation intervention**, not a pure reading-granularity ablation.

### How References Are Organized

A reference is a **small family of related proof-repair rules**, not a training-task transcript or one indiscriminately merged card. Cards are grouped offline by the proof situation and repair mechanism (for example, quantifier instantiation, opaque-spec unfolding, or reuse of an existing lemma). Within each group, compatible redundant guidance is consolidated; distinct premises, proof directions, and exceptions remain separate rules with source-card IDs.

The main `SKILL.md` provides a compact index of the 37 families. Each reference contains shared **Scope** information followed by its rules and their applicability, actions, validation guidance, and exclusions. In C, a multi-rule reference first presents short **When/Avoid** cues and a **Relationship** note; the full rule bodies remain separately accessible.

For example, `direct-existing-lemma-bridge` contains three distinct entries: reuse a matching library lemma; derive equal views from marshalability and equal serialization; or derive equal marshalability from equal views. B exposes all three together. C lets the agent select the entry matching its current premise-to-goal direction, while retaining a full-reference fallback.

## Experimental Rounds

- **Round 1:** R1-A versus R1-B — flat cards versus grouped whole-reference reading.
- **Round 2:** R2-B versus R2-C — grouped whole-reference reading versus selective reading plus navigation revisions.
- **R1-B and R2-B have identical skill-package hashes and fixed settings.** R2-B is a fresh control run, not a new B variant or a reused R1-B result. There are three configurations across four experimental arms, each evaluated on the same 20 tasks.

Fixed validation20 set, with one run per task per arm. Success requires passing both Verus and Lynette checks within the 600-second budget.

**Flat 78-card baseline (R1-A): 13/20; R1-B: 14/20; R2-B: 14/20; R2-C: 14/20.**

## Table 1. Gains and Losses Relative to the Flat 78-Card Baseline

| Compared with the flat baseline | Solved by both | Newly solved | Baseline successes lost |
|---|---:|---:|---:|
| R1-B Whole-reference reading | 13 | 1 | 0 |
| R2-B Whole-reference reading | 12 | 2 | 1 |
| R2-C Selective reading | 11 | 3 | 2 |

## Table 2. Tasks with Different Outcomes Across Arms

✓ denotes success within budget; ✗ denotes an unsuccessful run. All ✗ entries below are timeouts. Task names omit shared prefixes.

| Task | Flat 78 cards | R1-B Whole-reference | R2-B Whole-reference | R2-C Selective |
|---|:---:|:---:|:---:|:---:|
| `tla_forall_not_equality` | ✗ | ✗ | ✗ | ✓ |
| `Rely condition equivalence` | ✗ | ✗ | ✓ | ✓ |
| `unpack_conditions_from_spec` | ✓ | ✓ | ✓ | ✗ |
| `delegation_map::impl4::new` | ✗ | ✓ | ✓ | ✓ |
| `always_distributed_by_and` | ✓ | ✓ | ✓ | ✗ |
| `keys_in_index_range_agree` | ✓ | ✓ | ✗ | ✓ |

Remaining tasks: **10 were solved by all four arms, and 4 timed out in all four arms.**

**Takeaway:** R1-B retains every baseline success and solves one additional task. R2-B gains two and loses one; R2-C gains three and loses two. Each arm therefore solves one more task overall than the flat baseline.

**Comparison scope:** Only R1-A and R1-B form a within-round comparison against the flat baseline; comparisons of the R2 arms with that baseline are descriptive cross-round comparisons. R1-B and R2-B use the same skill configuration. The tables do not additionally exclude successes with editing-protocol violations. Under strict V2 compliance, the success counts for R1-A, R1-B, R2-B, and R2-C are 13, 13, 14, 14, respectively (each out of 20).

Resource usage, costs, paired statistics, and methodological notes are available in the [detailed statistical appendix](DETAILS.md) (Chinese). Per-task data are in [episodes.csv](episodes.csv).
