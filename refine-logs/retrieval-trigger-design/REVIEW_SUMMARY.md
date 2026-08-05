# Review Summary

## Outcome

- Final score: `9.06 / 10`
- Verdict: `READY`
- Blocking issues: `NONE`
- Meaning: implementation-ready as a narrow, falsifiable mechanism study; no
  claim that selective retrieval improves live Verus outcomes.

## Resolved Blockers

1. Search now runs invisibly at every valid verifier checkpoint; the
   deterministic FSM controls injection rather than whether candidates exist.
2. Search and injection are separate executable functions and ledgers.
3. Filters use `VALID / INVALID / UNKNOWN`; only proven invalidity is removed,
   and unknown bindings are not injectable.
4. `O_train(s)` is constructed only from frozen train-bank cards exhaustively
   replayed on eval pre-states, independently of retrieval.
5. Withheld eval actions are isolated ceiling evidence.
6. `shadow -> active` occurs only on `D_val` and requires strict diagnostic
   frontier and safety non-regression.
7. Raw hashes are provenance-only; transferable fingerprints and structural
   anchors are frozen before eval.
8. Every exact, FTS or dependency hit explicitly projects to a card ID.
9. `R-1` transfer opportunity prevents conditional recall from hiding a
   nearly empty useful-memory denominator.

## Non-Blocking Execution Clarifications

- Author normalization/binding algorithms on `D_train`, select only
  predeclared choices on `D_val`, then content-hash the configuration.
- Define validation-state scope mechanically before replay results are seen.
- Freeze tie-breaking, binding cap, repetitions, context budget, ECTS
  censoring and rollback semantics.
- Physically isolate offline eval oracle outputs from live-arm workspaces.

## Final Artifact

- `FINAL_PROPOSAL.md`

