# Proof time as evaluation metric and skill learning reward meeting

## Metadata

- project: `verus_self_evolving`
- kind: `meetings`
- created_at: `2026-11-06T15:03:40`
- status: `reviewed_summary`
- sources: user-provided ASR transcript (178 lines, ~26 min, two speakers:
  advisor = speaker 01, student presenter = speaker 02). Transcript SHA-256:
  `ea87598c92cad496c2cb176be98edf99ac030ee0d28fb4adb99732b16d5bd8ef`.
  The transcript is noisy (e.g. "various"/"virus" = Verus, "skill opt" =
  SkillOpt, "卡" = card, "top of verus" = the presenter's Verus project,
  "pro time"/"soft time" = proof/solver time). It stays local and is not
  committed. This is a compressed interpretation, not a verbatim record.

## Main outcome

The advisor proposed adding **verifier (SMT solver) proof time** as a second
cost axis next to agent token cost, first as an evaluation metric and then as
a **skill-learning reward signal**. The user later assigned the
reward-signal direction to Claude (2026-11-06).

## Discussion points

1. **Motivation.** LLM-written Verus proofs can be bloated: redundant asserts,
   many quantifiers, triggers placed where none are needed. Z3 then does heavy
   search or blows up. The advisor sees this as a reason Verus does not scale
   to large projects. An Anthropic Verus effort was cited as reporting about
   30 minutes of verification per round per example (unverified).
   Verification latency also matters for secure or efficient code generation
   checks in other areas.
2. **Current scale is small.** The presenter's statistic: in previous runs,
   the mean vector-stage verification time was 0.72 s and the slowest was 5 s.
   The presenter has seen an unrelated proof run for 6–8 h without finishing.
3. **Immediate measurement ask.** For cells where both arms pass (example:
   no-skill vs card on Unpack), compare proof time. Re-verify each final proof
   about 10 times and take the mean, because single timings are noisy. Even a
   10–20% reduction on 1–2 s proofs is reportable.
4. **End-to-end view.** Count the time the solver spends on every intermediate
   check, including failed attempts. An incremental proof should also "fail
   gracefully": a wrong attempt should give fast feedback. This links to a
   proof **curriculum**: which order of steps reaches success with the least
   total iterative proof time.
5. **SkillOpt skill case study.** SkillOpt skills mainly give a syntax
   framework; they do not teach how to read verifier errors. One flaw: the rule
   to "fix low-confidence trigger warnings" makes agents add trigger
   annotations after verification already passed. The advisor noted that such
   post-success polish could become useful if proof time is optimized.
   Another rule says decreases clauses are needed for recursive specs; it
   triggers rarely and costs little.
6. **Card case study.** A card says: on a precondition failure under an
   implication, state the antecedent explicitly with an `if`. When a card was
   re-injected into its own source trace and the agent re-ran, it sometimes
   failed: the agent wrote `let i = ...`, which shadowed the `forall` binder
   `i`. Conclusion: card usefulness depends on the current proof state
   (*when* to apply the card). SkillOpt does not learn contextualized skills.
7. **Proof time as a learning signal.** Proof time should be optimized during
   skill learning, not only reported. Contrast trajectories that branch from the
   **same node**: one where the prover needs longer and one where it needs less
   time. Hope: this teaches contextualized skills or a good curriculum. Proof time
   should be separated from tokens, because verifier time is not simply
   proportional to tokens.
8. **Fork grouping needs revision.** Current selection prefers plateau starts
   and drops. These are not always found, and every trace currently gets 3
   hinted re-samples even when unnecessary.
9. **Fast or incomplete feedback idea** (presenter): use a partial, unsound,
   or incomplete check, similar to bounded model checking or a learned small
   verifier model, for fast feedback. The advisor's view: useful for training
   rewards, but debatable for evaluation.
10. **Next steps.** Scale the comparison beyond the current 8 settings; treat
    proof time and token cost as key metrics in both training and evaluation.
    The presenter's graduation thesis and camera-ready deadline (Nov 6) were
    mentioned. The GitHub repo and Hugging Face model links are to be posted to
    the group.

## Related evidence already in remote history

- Xinyue Huang `4fc0a16` (2026-10-28), branch
  `feat/skillopt-card-organization-20261014`:
  `research_artifacts/index-guidance-followups-20261028/timing/REPORT.md`.
  Offline timing analysis of 40 runs, Rely/Unpack/De Morgan/Filter:
  - Final Verus check: about 0.6–0.7 s mean.
  - Index v2: end-to-end time ratio 0.919, Verus-command proxy 0.874,
    final Verus check 1.069.
  - G1: all three time ratios worse.
  - Pure SMT time not logged; 10x re-verification not done.
- Card bank references `quantified-proof-antecedent-binder-scope` (shadowing,
  item 6) and `post-verification-cleanup` (trigger polish, item 5) are in
  `research_artifacts/card-organization-20261014/skills/B-grouped/references/`.

## Decision / Next Step

User assigned to Claude (2026-11-06):

- Survey which proof behaviors affect Verus proof time and how to optimize them.
- Use larger, realistic Verus repos.
- Study how an agent (DeepSeek, key in the local config only) can learn to
  write faster proofs.

Follow-up entry: see the proof-time study note created the same day.
