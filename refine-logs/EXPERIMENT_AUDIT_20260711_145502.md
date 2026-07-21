# Experiment Integrity Audit

**Verdict: FAIL for method claims; PASS for engineering feasibility.**

The independent read-only reviewer verified the scorer equations, reran all original tests, and recomputed every R016/R017 PMI/entropy value. Maximum PMI discrepancy was `5.6e-16`; entropy discrepancy was zero.

Claim-blocking issues were: logged actions mislabeled as ground truth, one rejected target action, an evaluation-derived four-action candidate set, density based only on artifact text tokens, a word-count rather than tokenizer-matched neutral control, and missing durable paired statistics. These issues are corrected in code/protocol for future runs, but the old GPU results are not retroactively promoted.

R017 supports only: local teacher-forced action-distribution scoring is feasible, and current outputs are highly prompt/artifact sensitive. It supports no reusable-skill quality or downstream solve-rate claim.
