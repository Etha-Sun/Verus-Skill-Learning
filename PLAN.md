# Plan

## 1. Identity

- parent_map_node: hands-off trace distillation roadmap
- loop_id: m1-distillation
- run_id: handsoff-distill-m1-r040-r041
- stage: train-only prompt distillation
- active_item: R041

## 2. Objective

Complete R041 by distilling the canonical R040 train-only selection into two
frozen prompt artifacts:

- H2: trace-derived global Verus guidance, at most 800 prompt tokens.
- H1: generic Verus guidance length-matched to H2 within +/-5% provider tokens.

The deliverable is an auditable prompt package, not evidence of downstream
agent improvement. R042 remains blocked until the prompts are frozen and a
frontier-model endpoint is authenticated.

## 3. Evidence And Data Boundary

- Use only canonical R040 attempt3: 30 successful train traces from Anvil and
  IronKV, balanced across five frontier models.
- Read train logs and their paired verified files only.
- Do not inspect sealed memory-allocator or NR trace content.
- Treat raw data below `VERUS_SKILL_DATA_ROOT` as read-only.
- Write generated artifacts only below `VERUS_SKILL_RUN_ROOT`.
- Do not treat keyword motif labels as validated taxonomy labels.
- Do not claim solved-rate or token-efficiency improvement from R041 alone.

## 4. Inputs And Outputs

Canonical legacy inputs:

- `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/selected_traces.jsonl`
- `${VERUS_SKILL_DATA_ROOT}/verus-self-evolve-scaffold/runs/handsoff_distill_20260719/m1/r040_selection_attempt3/selection_summary.json`

New output root:

- `${VERUS_SKILL_RUN_ROOT}/handsoff_distill_20260719/m1/r041_prompt_distillation/`

Required compact artifacts:

- frozen H1 and H2 prompt text
- evidence table linking each H2 claim to selected trace IDs
- prompt and source SHA-256 hashes
- byte, word, and tokenizer/provider-token counts
- prohibited-term and executable-code-preservation checks
- one-time distillation cost record
- run manifest and concise reviewed summary

## 5. Execution Contract

1. Load only the frozen R040 attempt3 manifest and verify its recorded hash.
2. Extract recurring verifier-grounded guidance with trace-ID provenance.
3. Remove task-specific proof text and unsupported generalizations.
4. Freeze H2 at no more than 800 prompt tokens.
5. Construct H1 without trace-derived knowledge and match its provider-token
   length to H2 within +/-5%. Until provider tokens are available, report byte,
   word, and tokenizer-proxy counts without claiming the match is final.
6. Record distillation model/tool, input/output tokens or an explicit
   unavailable state, wall time, and human editing separately from later
   inference cost.
7. Scan both prompts for `assume`, `admit`, `external_body`, instructions to
   weaken specifications, and instructions that discard executable code.
8. Freeze hashes only after all checks pass.

## 6. Success And Stop Conditions

Success requires:

- R040 source hash and all 30 selected trace IDs are accounted for.
- Every H2 claim has one or more trace-ID citations.
- H2 is at most 800 provider tokens.
- H1 is within +/-5% of H2 provider tokens.
- Safety scans pass and source/prompt hashes are durable.
- Distillation cost is recorded separately from inference cost.

Stop without launching R042 if:

- any sealed content would need to be read;
- provenance cannot be reconstructed;
- H1/H2 length matching or safety validation fails; or
- frontier-model authentication is unavailable.

## 7. Current Checklist

- [x] R040 canonical attempt3 selected and audited.
- [ ] Verify the R040 manifest and source hash from the legacy archive.
- [ ] Distill provenance-linked H2.
- [ ] Construct length-controlled H1.
- [ ] Run length, hash, provenance, and safety validation.
- [ ] Freeze the R041 package and update research memory.
- [ ] Decide whether R042 prerequisites are satisfied.

## 8. Next Route

- On success: prepare the same-model H0/H1/H2 dev comparison contract for
  R042, but launch it only after frontier authentication is confirmed.
- On failure: repair or simplify R041 while preserving the same train-only and
  sealed-data boundary.

## 9. Revision Log

| Date | Change | Reason |
|---|---|---|
| 2026-07-20 | R040 attempt3 frozen | 30 unique verified train traces passed selection and leakage checks |
| 2026-07-21 | Replaced mixed M0/M1 plan with an R041-only contract | prevent stale M0 tasks, paths, and metrics from steering the next agent |
