# Refinement Report

## Initial Proposal

The initial design proposed a broad multi-index Verus memory platform with
seven retrieval views, five card types and event-driven search/injection.

## Round 1 Changes

- separated harness, resource and semantic failure routes;
- made search invisible and always-on at valid checkpoints;
- made the FSM an injection policy;
- introduced tri-state compatibility;
- replaced a single oracle card with replay/ablation-certified oracle sets;
- reduced the MVP to one `invoke_lemma` transition-card type and three search
  channels.

## Round 2 Changes

- froze `D_train / D_val / D_eval` access and execution order;
- defined oracle sets solely from train cards replayed on eval pre-states;
- isolated withheld eval exact actions as a ceiling;
- added leakage-safe validation-only card promotion;
- required strict full diagnostic-frontier non-regression;
- separated raw provenance from normalized retrieval fingerprints;
- required mechanically valid binding and structural anchor for injection;
- made exact/FTS/dependency channels return card IDs through explicit
  projections;
- added `R-1` transfer opportunity and all-eval earliest-loss accounting.

## Final Result

The final design is implementation-ready with an independent score of
`9.06 / 10` and no blocking issue. It remains an experiment contract, not
evidence of downstream solved-rate or token-efficiency improvement.

