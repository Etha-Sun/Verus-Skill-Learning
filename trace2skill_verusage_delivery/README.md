# IronKV Trace2Skill-Style Skill Learning: Preliminary Baseline Report

## Executive summary

This report documents a preliminary, held-out evaluation of two ways to turn
Claude Sonnet-4.5 Verus trajectories into an `(M, R)` skill directory for
IronKV proof repair.  `M` is the root `SKILL.md` with broadly applicable
procedure; `R` is a set of lower-frequency reference files.

The main findings so far are:

1. The literal Trace2Skill-style MAP/REDUCE consolidation ran end-to-end, but
   on heterogeneous IronKV proof mechanisms it over-compressed the library:
   its final skill has one broad root document plus one catch-all reference.
   On the strict held-out 15, it solved 7/15 versus 8/15 for no-skill.
2. A second, data-driven semantic organization retained a root procedure plus
   14 semantically bounded references and 88 cards. Its initial 40-turn run
   solved 7/15; after correcting a host-side false stop and rerunning task 15,
   the recorded result is 8/15. The successful-task set changed rather than
   simply expanding: semantic-v4 newly solved task 3, which no-skill did not
   solve, but did not solve no-skill-only task 6. Among the seven tasks solved
   by both conditions, semantic-v4 used fewer turns on five; their combined
   turn count fell from 155 to 123 (mean 22.1 to 17.6 turns).
3. A focused fresh 60-turn resampling of six semantic-v4 failures gave
   semantic-v4 3/6 and no-skill 1/6.  The three semantic-v4 successes were
   independently rechecked with Verus, Lynette, and contract-preservation
   comparison; no task replacement or contract weakening was found.  This is
   encouraging evidence, but it is small, selected, and should not be
   aggregated with the 40-turn run as a single unbiased 15-task score.

The experiment is therefore best interpreted as a baseline study of skill
*organization*, not a final claim that skills robustly improve IronKV solving.

## 1. Data split and leakage controls

### Training trajectories

The training input consists of 77 complete HandsOff trajectories produced by
Claude Sonnet-4.5 for IronKV tasks.  Each complete trajectory was analyzed as
one unit; no held-out trajectory or verified solution was supplied to either
skill-construction pipeline.

The 77 trajectories were routed according to audited outcomes:

| Route | Count | Meaning |
|---|---:|---|
| Success analysis / Success Memory | 53 | 43 official `TRUE` successes plus 10 trivial direct-pass tasks outside the official 118-task IR benchmark |
| Failure Cause / Failure Memory | 24 | Official `FALSE` or `CHEAT`-labelled trajectories |
| Total | 77 | All available selected IronKV training trajectories |

This distinction matters: “success” here means the trajectory was routed to
the success-memory side, not that every one of the 53 is a nontrivial official
benchmark proof.  The ten external trivial direct-pass cases are retained in
the training provenance and explicitly flagged by the audit.

### Held-out evaluation tasks

From the remaining pool, a deterministic module-stratified selection chose 15
officially `TRUE` IronKV tasks.  Every evaluation task satisfies all of the
following offline checks:

- its current official source is a nontrivial Verus failure;
- the paired dataset solution from the Claude trajectory verifies with Verus
  and passes Lynette, used only for qualification;
- no exact task ID, canonical target, official-source hash, or leakage
  component overlaps the 77 training tasks;
- the runtime agent receives only the public incomplete source file—not the
  held-out trajectory or verified solution.

The selection contains distinct leakage components (`0` duplicate components)
and all 15 rows have official label `TRUE`.  Thus the evaluation questions are
all problems that Claude originally solved, while the student agent is not
shown Claude’s trajectory or final answer.

Public-safe split artifact: [`results/split_and_leakage_audit.json`](results/split_and_leakage_audit.json).  The raw task files, trajectories, and verified solutions remain outside this repository.

## 2. Agent / harness design

The evaluated student is `deepseek-v4-pro` in a single long-lived ReAct-style
conversation per task.  The implementation follows the relevant Trace2Skill
skill-directory policy rather than feeding all cards at once:

```text
load root M (SKILL.md)
  -> inspect current task and Verus diagnostic
  -> choose one small proof edit
  -> run Verus
  -> interpret the changed diagnostic and return to M
  -> only for a concrete, lower-frequency obstacle, open one R reference
```

The root document is therefore intended to guide common proof repair and
navigation; references are intended for specialized mechanisms.  This is a
Trace2Skill-style `(M, R)` harness, not a byte-for-byte reuse of the original
spreadsheet agent implementation.

### VeruSAGE HandsOff adaptation

The harness preserves the HandsOff spirit of a single model autonomously using
tools, while adapting it to proof repair:

- read/search the target and local Verus/vstd documentation;
- structured line-level edits only in a copied `candidate.rs`; the original
  source is immutable;
- run Verus after proof edits;
- run Lynette `compare -t` as the proof-only cheat check;
- maintain one conversation, current code state, and full diagnostics across
  turns;
- require a fresh successful Verus run and a fresh Lynette pass before an
  explicit completion signal;
- host-side loop guards detect repeated format/tool failures and prolonged
  lack of evidence-backed progress, while allowing grounded exploration.

**Loop-control note.** This progress guard was added after early exploratory
runs showed that an agent could repeatedly read documentation or search tools
without making another proof edit, consuming the turn budget without advancing
the candidate. After an effective edit-to-Verus cycle, the current guard stops
the run after 13 consecutive tool turns without material proof progress. It is
applied identically to all conditions. It bounds known idle loops, but an
early-stop failure is not equivalent to exhausting the full turn cap: it may
also censor a genuinely promising but as-yet-unverified reasoning branch.

All evaluated arms were serial, used no automatic API retries, and had a
per-request maximum output of 8192 tokens.  The requested temperature was
`0.2`; DeepSeek thinking mode did not accept/send temperature, so manifests
correctly record `temperature_effective: null`.  The model and reasoning mode
were otherwise identical across arms: `deepseek-v4-pro`, thinking enabled,
high reasoning effort.

**Turn definition.** One turn is one model response containing a valid tool
`Action`, followed by the host executing that action and returning one
`Observation`. Thus a 40-turn or 60-turn cap limits effective agent actions,
not Verus invocations or wall-clock minutes. `run_verus`, a file read, a search,
an edit, a reference read, and the explicit completion signal each consume a
turn. A malformed model response can create an additional API request and a
format-error observation, but does not consume the effective Action-turn
budget; this is why `request_count` can be slightly higher than the reported
turn count.

**Validation note.** A recorded success requires the candidate’s current hash
to have both Verus pass and Lynette pass, and the original source hash to be
unchanged.  For the three newly successful 60-turn semantic cases, I also
performed an independent post-hoc source-vs-candidate comparison: all original
function signatures and `requires`/`ensures`/`recommends` clauses were
preserved.  This extra audit is important because Lynette alone does not prove
that every conceivable target-replacement attack is impossible.

Relevant implementation: `Trace2Skill/verus_agent/`, especially
`verus_agent/agent.py`, `verus_agent/workspace.py`, `verus_agent/loop_control.py`,
and `verus_agent/tools.py`.

## 3. Two skill-construction conditions

Both conditions use the same 77 training trajectories, DeepSeek V4 Pro as the
analysis/evolution model, complete-trajectory analysis, and no held-out
inputs.  They differ in how they consolidate extracted memories into the
skill’s `(M, R)` structure.

### 3.1 Native Trace2Skill-style hierarchical compression

This condition follows the upstream Trace2Skill consolidation shape as closely
as practical for Verus:

```text
complete success trace -> up to 3 Success Memory items
complete failure trace -> Failure Cause + up to 3 Failure Memory items
77 trace analyses -> MAP patches
hierarchical REDUCE (batches of 5, at most 5 levels)
-> TRANSLATE/APPLY patches -> validate M/R skill directory
```

The run produced 77 MAP patches.  Its configured target was at most 5
references, and the model collapsed the proposed detailed documents into:

```text
verus-proof-repair/
  SKILL.md
  references/verus-proof-patterns.md
```

The root contains an eight-step generic workflow; the single reference contains
loop, set equality, quantifier, trait, induction, vector, ordering, macro, and
other patterns together.

#### Why this became over-compressed

This was not a filesystem accident.  The merge output explicitly says it
“deduplicat[ed] 20+ proposed reference documents into one” and created one
“comprehensive reference file.”  Patch-level REDUCE is good at resolving
overlapping textual edits to a shared skill, but it does not inherently
preserve a semantic partition when the source mechanisms are heterogeneous.
IronKV mixes serialization, maps/ranges, quantifiers, induction, collections,
loop invariants, syntax/environment problems, and structural proofs.  In this
run, the reducer treated many detailed reference proposals as redundant
additions to a generic workflow, producing a catch-all reference rather than
several selective ones.  Consequently, the resulting M/R hierarchy has weak
reference-level selectivity.

Public-safe delivery artifacts:

- Native final skill: [`skills/native_compressed/verus-proof-repair/`](skills/native_compressed/verus-proof-repair/)
- Native-evolution compact audit: [`results/native_evolution_summary.json`](results/native_evolution_summary.json)
- Trace2Skill evolver implementation and prompts: [`code/skill_evolver/`](code/skill_evolver/)

### 3.2 Semantic-v4: data-driven semantic organization

The second condition keeps Trace2Skill’s overall `(M, R)` idea—root procedure
first, detailed references on demand—but uses a different consolidation
strategy to preserve mechanism boundaries.

1. Start from the same 77 trajectory-derived records (284 memory items).
2. Ask DeepSeek to induce open mechanism labels from the IronKV memories.  No
   host-provided nine-family taxonomy or keyword routing is used.
3. Allow the model to create/split ambiguous groups and retain singletons.
4. Consolidate within semantically coherent groups instead of immediately
   reducing all edits through one shared patch stream.
5. Reconcile the groups globally, merge only clearly overlapping groups, then
   let the model decide the final M/R layout.

The final audited library contains:

| Item | Count |
|---|---:|
| Input trajectory records | 77 |
| Extracted memory items | 284 |
| Candidate semantic families | 100 |
| Global cards | 88 |
| Model-merged groups | 11 |
| Singleton promotions retained | 77 |
| References | 14 |

The final root `M` is a compact procedural playbook: ground the exact
diagnostic, classify the missing proof bridge, choose one smallest mechanism,
run Verus, then return to M.  Its 14 references are bounded by observable
mechanism families:

1. ordering / sortedness / range proofs;
2. finite-set membership, cardinality, equality;
3. recursive sequence and fold induction;
4. pointwise, universal, and extensional closure;
5. quantifier triggers and concrete instantiation;
6. closed definitions and broadcast boundaries;
7. ghost snapshots and spec views;
8. lemma reuse and specification inventory;
9. loop invariants and termination;
10. branch/return postcondition closure;
11. structural Option/struct/enum decomposition;
12. serialization and marshalability;
13. syntax/macro/crate environment;
14. verification workflow soundness.

This is deliberately a different hypothesis from native REDUCE: rather than
asking the reducer to preserve all diversity implicitly, it asks the model to
make mechanism boundaries explicit before consolidation.

Public-safe delivery artifacts:

- Semantic-v4 final skill: [`skills/semantic_v4/verus-proof-repair/`](skills/semantic_v4/verus-proof-repair/)
- Semantic-consolidation compact audit: [`results/semantic_v4_consolidation_audit.json`](results/semantic_v4_consolidation_audit.json)
- Semantic organization implementation, prompts, and schemas: [`code/verus_agent/experiments/ironkv_semantic_skill_deepseek_v4pro/`](code/verus_agent/experiments/ironkv_semantic_skill_deepseek_v4pro/)

## 4. Held-out results

### Stage A: fixed strict held-out 15, 40-turn budget

The original native-skill comparison is a 30-arm paired run: each of the 15
tasks is run once no-skill and once with the native compressed skill.  The
semantic-v4 condition is a separate 15-arm run on the same frozen tasks and
settings, so it should be read as a stochastic matched-task comparison, not a
same-request pair.

| Condition | Tasks | Max turns | Successes | Interpretation |
|---|---:|---:|---:|---|
| No skill | 15 | 40 | 8/15 | Paired control for native skill |
| Native Trace2Skill compressed skill | 15 | 40 | 7/15 | Same paired experiment |
| Semantic-v4 skill | 15 | 40 | 8/15 | Same frozen tasks; task 15 completed in 21 turns |

The next table reports **turns used**, not check marks. A bare number is a
verified success; `F` means the arm ended without a valid proof. Bold indicates the smallest successful turn count in that row.

| 题号 | Baseline | 原生 skill | Semantic-v4 |
|---:|---:|---:|---:|
| 1 | 40 (F) | 40 (F) | 40 (F) |
| 2 | 21 | 18 | **8** |
| 3 | 40 (F) | 40 (F) | **23** |
| 4 | 36 | 24 | **19** |
| 5 | 40 (F) | 40 (F) | 40 (F) |
| 6 | **18** | 28 | 40 (F) |
| 7 | 40 (F) | 40 (F) | 40 (F) |
| 8 | **16** | 40 | 20 |
| 9 | 40 (F) | 40 (F) | 40 (F) |
| 10 | **25** | 40 (F) | 32 |
| 11 | 19 | 19 | **14** |
| 12 | 39 (F) | 40 (F) | 40 (F) |
| 13 | 14 | 20 | **9** |
| 14 | 40 (F) | 40 (F) | 25 (F) |
| 15 | 24 | 25 | **21** |

The native compression condition therefore did not improve success rate in this
strict test (7/15 vs 8/15 no-skill) and consumed more tokens. Semantic-v4
obtained new successful tasks relative to both no-skill/native (#3), but also
missed several tasks; 8/15 is not an overall-improvement claim because this
condition is a separate stochastic sample.

#### Reference consultation during held-out solving

The table below is taken from each arm’s host-recorded `reference_reads` list.
`—` means no auxiliary reference was opened; every model received its condition’s
root M at the start. The semantic-v4 entry for task 15 is its final 21-turn run.

| 题号 | Native compressed skill: opened R | Semantic-v4: opened R |
|---:|---|---|
| 1 | `verus-proof-patterns.md` | `finite_set_membership_equality.md` |
| 2 | — | — |
| 3 | `verus-proof-patterns.md` | `pointwise_sequence_set_equality_closure.md` |
| 4 | — | — |
| 5 | `verus-proof-patterns.md` | `pointwise_sequence_set_equality_closure.md` |
| 6 | — | — |
| 7 | — | — |
| 8 | — | — |
| 9 | `verus-proof-patterns.md` | `finite_set_membership_equality.md` |
| 10 | `verus-proof-patterns.md` | — |
| 11 | — | — |
| 12 | `verus-proof-patterns.md` | `finite_set_membership_equality.md` |
| 13 | — | — |
| 14 | `verus-proof-patterns.md` | — |
| 15 | — | — |
| **Total reference-read actions** | **7 actions; 7/15 tasks; 1 distinct file** | **5 actions; 5/15 tasks; 2 distinct files** |

This is useful evidence about M/R behavior. Native compression has a generic M
and only one R, so its seven consultation actions cannot express fine-grained
selection. Semantic-v4 selected a bounded reference only when it classified a
concrete set/extensionality obstacle. However, all seven native successes used
M without R; among the final eight semantic-v4 successes, only task 3 used R.
The current successful cases therefore mainly demonstrate the usefulness of the
root procedure M. They do **not** yet demonstrate that auxiliary references are
the cause of the improvement.

### Stage B: targeted 60-turn paired resampling of semantic-v4 failures

To test whether some semantic-v4 failures were budget-limited rather than
mechanism-limited, six Stage-A semantic failures were rerun as fresh,
alternating no-skill/semantic-v4 pairs with `max_turns=60`:

`#1, #5, #6, #7, #9, #12`.

Again, numbers are turns used; `F` is an unsuccessful arm. Four `F` entries
ended early through the shared 13-turn no-progress guard rather than the
60-turn cap: baseline #7 (28), baseline #9 (41), semantic-v4 #1 (58), and
semantic-v4 #12 (35).

| 题号 | Baseline (60-turn cap) | Semantic-v4 (60-turn cap) |
|---:|---:|---:|
| 1 | 60 (F) | 58 (F) |
| 5 | 60 (F) | **34** |
| 6 | 60 (F) | **51** |
| 7 | 28 (F) | **55** |
| 9 | 41 (F) | 60 (F) |
| 12 | **42** | 35 (F) |
| **Success total** | **1/6** | **3/6** |

7,884,780 (semantic-v4).  The paired discordance is: three semantic-only
successes, one no-skill-only success (#12), and two failures in both arms.

The three semantic-only successes were:

- `delegation_map_v__impl5__delegate_for_key_range_is_host_impl`;
- `host_impl_v__impl2__effect_of_delegation_map_set`;
- `seq_is_unique__test_unique`.

All three were independently re-run after the experiment and passed Verus
(`1`, `2`, and `3 verified; 0 errors`, respectively), Lynette, source-hash
checks, and function-contract preservation comparison.  Their final diffs add
proof blocks/assertions or loop invariants/decreases; they do not replace the
task function or modify pre/postconditions.

**Important interpretation:** Stage B is a selected, fresh resampling of
Stage-A failures.  It shows a promising local advantage under the longer
budget; it must not be added to Stage A as “11/15 semantic successes,” because
the API samples and turn budgets differ.

Public-safe evaluation artifact: [`results/heldout_results.json`](results/heldout_results.json).
It records the frozen-task outcomes, action-turn counts, and verification status.
Raw tool traces, candidates, API payloads, usage records, and original tasks are
intentionally excluded under this repository's data policy.

## 5. Conclusions

1. **End-to-end feasibility is established.** Complete Claude trajectories can
   be converted into success/failure memories, consolidated into an `(M, R)`
   Verus skill directory, and evaluated without exposing held-out traces or
   answers to the proof agent.
2. **The organization of a skill library is a material experimental variable.**
   Literal patch-oriented hierarchical compression produced a useful generic
   workflow but one over-broad reference.  Its held-out result did not beat
   no-skill.  This is concrete evidence that merely applying MAP/REDUCE does
   not automatically yield selective references for heterogeneous Verus
   proofs.
3. **Semantic organization is the more promising direction, not yet a final
   win.** The 14-reference semantic library preserves mechanism boundaries and
   produced three credible semantic-only successes in the focused 60-turn
   resample. Its corrected 15-task result is 8/15, equal to the historical
   8/15 no-skill control, and it uses more tokens. The correct conclusion is
   “promising signal, insufficient evidence,” not a claimed aggregate gain.
4. **The observed value appears to come from M's core procedure, but M's
   embedded reference index is the dominant always-on context cost.** In the
   three 60-turn semantic successes, the agent did not open an auxiliary R
   file (`reference_reads` was empty); it advanced using the preloaded root M.
   That root has two separable parts: approximately 1,410 tokens of broadly
   applicable procedure, and approximately 6,609 tokens (about 82% of M) of
   reference-map/navigation content—reference descriptions, `consult when` /
   `do not consult when` boundaries, and card-level index entries. The latter
   is helpful for deciding what R to open, but is resident in every request
   even when no R is opened and is not the content that visibly drove these
   three successes. Thus an M-only core-procedure condition without the full
   reference index could substantially reduce prompt-token cost; it should be
   evaluated separately from M+index+R. More broadly, the semantically
   organized `(M, R)` form remains a promising substrate for iterative skill
   self-evolution: later trace-derived updates could selectively refine the
   core procedure, index boundaries, or one semantic reference rather than
   collapsing all mechanisms into one document. This is a motivated next
   direction, not yet an experimentally established gain.

## Public delivery layout

| Purpose | Included location |
|---|---|
| Detailed report | `README.md` |
| Trace2Skill-style Verus harness and experiment scripts | `code/verus_agent/` |
| Trace2Skill hierarchical evolver | `code/skill_evolver/` |
| Offline harness tests | `tests/` |
| Native MAP/REDUCE final skill | `skills/native_compressed/` |
| Semantic-v4 final skill | `skills/semantic_v4/` |
| Compact split, training, and held-out result audits | `results/` |

Raw trajectories, verified solutions, complete agent runs, API request/response
payloads, usage records, caches, and credentials are intentionally excluded.
