# Vskill 0822 evaluation alignment branch

## Decision

Create and activate `Vskill-0822` from one reviewed checkpoint commit on
`feature/skillopt-verusage-20260812`. The branch is the integration line for
evaluation-contract alignment; do not merge the external Trace2Skill branch
wholesale.

The aligned evaluation contract separates three independent judgments:

- `proof_solved`: independent Verus and Lynette checks pass and safety holds,
  including a candidate that is verified after the actor timeout;
- `within_budget`: `proof_solved` and the actor did not time out;
- trace fidelity: V0 invalid/unusable trace, V1 truncated trace, or V2 complete
  auditable trace. Fidelity controls trajectory reuse, not proof correctness.

The branch will also enable the existing GLM-specific HTTP 429 retry/backoff
inside the reference-aligned profile, add a reproducible two-panel cumulative
input/output token figure with cached input retained as part of total input,
and pin the formal Verus release
`release/0.2025.09.12.bb1f342` (`bb1f342683fd26de011825725a55325b65e7d359`).

## Alternatives Considered

- Merge `feature/trace2skill-verusage-20260813` wholesale: rejected because it
  includes a different directory layout and many run/document artifacts that
  are not required for the aligned evaluator.
- Continue directly on `feature/skillopt-verusage-20260812`: rejected because
  verifier, scoring, bridge, and figure changes need a bounded integration and
  review surface.
- Keep Verus `ddc66116`: retained as the exact VeruSAGE benchmark comparator,
  but not selected as the new formal-release default. It is one commit before
  the September 12 point release.

## Evidence

- `skillopt-verusage/refine-logs/SKILLOPT_S1_S2_CROSS_MODEL_FINAL_REPORT_20260821.md`
- `skillopt-verusage/refine-logs/JULY_VERUS_RESULT_AND_REGRESSION_ANALYSIS_20260821.md`
- `CROSS_PROVIDER_EVALUATION_SETUP_AND_API_BRIDGES.md`
- `skillopt-verusage/src/skillopt_verusage/test_eval.py`
- `skillopt-verusage/src/skillopt_verusage/codex_deepseek_bridge.py`
- `skillopt-verusage/scripts/run_s2_fixed_test20.sh`

## Risk

Changing the verifier, scoring policy, and provider retry behavior at once can
make old and new scores look directly comparable when they are different
treatments. Every new result must record the Verus commit and binary hash,
timeout outcome, fidelity, bridge/config hashes, and cumulative usage fields.
The September 12 release must first be compared with `ddc66116` using a
verifier-only gate before any full paid rerun.

## Next Action

After the checkpoint commit and branch creation, implement the four bounded
changes with tests, then run the verifier-only `ddc66116` versus `bb1f342`
test-20 comparison. Do not start paid model reruns until that gate and the
revised scoring contract pass review.
