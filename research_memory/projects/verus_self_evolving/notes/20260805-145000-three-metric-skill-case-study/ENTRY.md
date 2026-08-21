# Three-Metric Skill Case Study

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-05T14:50:00`
- status: `complete`

## Objective

Audit the most prominent positive and negative skills separately for token
ETtS, small-model verifier-safe solve rate, and pre/post InfoGain. Determine:

1. what behavior distinguishes the best same-round skill from a bad one;
2. whether the observed advantage generalizes;
3. whether it is evidence of successful meta-skill evolution;
4. whether the observed behavior matches the intended aggressive,
   conservative, or structural profile.

## Evidence

### Token ETtS

The strongest same-round mechanism contrast is the single-problem IronKV R3:

| Condition | Slot | Verifier-safe | Primary uncached tokens | Versus fresh H0 | Solver Verus | New helpers | Diff additions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `local-proof-surface-cap` | A | yes | 61,232 | -29.87% | 2 | 0 | 139 |
| `three-fact-witness-note` | C | yes | 119,638 | +37.02% | 6 | 4 | 302 |

Both skills mention the three false-branch witness facts. The A skill differs
by requiring a ledger for every true and false return path, confining the
first patch to the target body, setting the initial helper budget to zero, and
repairing only the reported local delta. The trace complies with those rules.
The C trace expands from a local witness attempt into four helpers.

This supports a mechanism hypothesis that obligation completeness plus a hard
proof-surface cap can reduce helper proliferation and repeated context. It
does not establish causality: each screen condition has one trajectory and
there is no component ablation.

Fresh three-run confirmation for R3-A is 82,391 ETtS versus H0 87,312.7
(-5.64%), but the improvement is smaller than H0's 12,908-token range.
The correct endpoint is `inconclusive_within_h0_range`.

The four-task aggregate winner is R1-A `bounded-exploration-gate`, 51,497
ETtS versus H0 52,350 (-1.63%), 4/4 verifier-safe. It helps two task roles and
harms two. Its symbol evidence gate, repeated-proof-shape cutoff, and
unchanged-state rule are candidate retrieval atoms, not a general skill.

### Small model

No complete skill condition improves the primary solve-rate metric. H0 and
all complete R1-R3 skill conditions solve the same 2/4 subset.

The least harmful skill is R2-C `verus-contract-match-loop-r2`: 321,998
provider tokens versus H0 312,656 (+2.99%). It is useful only as a same-round
negative-control contrast with R2-A `verus-eight-plus-two-ladder-r2`:
490,164 tokens (+56.77%). Both solve 2/4 with 29 requests.

The C skill's one-lemma/one-bridge/two-failure policy reduces control-protocol
load. The A skill's ten-request state machine increases prompt and reasoning
cost without enforcing final rollback. This supports damage reduction relative
to A, not a small-model benefit claim.

Post-hoc snapshot/verifier analysis adds two non-primary diagnostics. H0,
R2-C, and R2-A each retain and ever introduce 0.00 new proof-function helpers
per trajectory, so the C/A token gap is not helper proliferation. On the hard
task, H0 and R2-C finish in a compiling 47-verified/1-logical-error state,
while R2-A finishes compile-invalid on an unsupported prover name. On the
closest task, H0, C, and A all finish compile-invalid with one, two, and four
reported compile errors respectively. These are final-state diagnostics, not
a normalized proof-progress score.

### InfoGain

Pre and post select different organization policies:

- R1-S `dependency_bridge_map` has the best four-task pre macro,
  +0.070516 bits/target token. The positive macro is driven by two marshal
  tasks; hard IronKV is negative and the token-weighted pooled score is about
  -0.0587.
- R1-C `minimal_sufficient_rationale` has the best normalized post macro,
  +0.219801, and is positive on all four tasks. It is a hindsight terminal
  summary, so it is evidence for episode compression, not pre-solve benefit.

R2's three-skill mean post falls from about 0.2149 to 0.1805 and all R2 pre
macros are negative. R3 is incomplete. The data do not support monotonic
InfoGain meta-evolution.

## Result

The strongest claim supported across all three objectives is:

> The meta-loop can generate locally interpretable mechanism hypotheses, but
> it has not produced stable, cumulative, or generalizable performance
> improvement.

The most useful positive/negative case study is R3-A versus R3-C. Its central
lesson is that a complete obligation ledger and executable proof-surface
budget matter more than a generic reminder of domain facts. The lesson should
be tested as small versioned atoms rather than copying the monolithic skill.

The A/C/S roles are metric- and state-dependent:

- A benefits token cost only when aggression means observable search caps.
- C best controls small-model prompt damage and post-proof compression.
- S is promising for pre-proof retrieval on layered representation proofs.

These are router hypotheses, not global prompt recommendations.

## Claim Gate

An independent secondary Codex review reached the same boundary:

- R3-A proof-surface mechanism: `partial`;
- stable R3-A ETtS improvement: `no`;
- R1-A as successful token evolution: `no`;
- R2-C as small-model improvement: `no`;
- R2-C damage reduction versus R2-A: `yes`, limited to the current matrix;
- R1-S general pre memory: `no`;
- R1-C post-proof compression schema: `yes`, offline descriptive scope;
- monotonic InfoGain evolution: `no`.

No unified `EXPERIMENT_AUDIT.json` covers this three-experiment synthesis, so
the claim verdict is provisional. The underlying selected runs still have the
reported run-level F3, input-integrity, Verus, and Lynette evidence.

Review trace:
`.aris/traces/result-to-claim/2026-08-05_run01/`

## Artifacts

- Full Chinese report:
  `skill-evolution-pilot/results/three_metric_skill_case_study.zh.md`
- Concise Chinese talk notes with large verbatim skill blocks:
  `skill-evolution-pilot/results/three_metric_skill_talk_notes.zh.md`
- Concise English talk notes with metric tables and verbatim skill blocks:
  `skill-evolution-pilot/results/three_metric_skill_talk_notes.en.md`
- Prior shortlist with exact skill hashes:
  `research_memory/projects/verus_self_evolving/notes/20260805-135628-standout-skill-memory-case-study-shortlist/ENTRY.md`
- Failure-mechanism diagnosis:
  `research_memory/projects/verus_self_evolving/notes/20260804-173507-self-evolving-failure-mechanism-case-study/ENTRY.md`

## Next Step

Decompose `local-proof-surface-cap` into branch-ledger, true/false coverage,
zero-helper, and local-delta-repair atoms. Run matched repetitions and
component ablations on held-out multi-branch tasks. Move small-model rollback
into the harness and separate InfoGain pre retrieval from post writeback.

No raw dataset or sealed input was modified, moved, or copied.
