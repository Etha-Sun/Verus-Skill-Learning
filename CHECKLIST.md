# Main Experiment Checklist

## Identity

- parent_map_node: hands-off trace distillation roadmap
- loop_id: m1-distillation
- run_id: handsoff-distill-m1-r040-r041
- stage: M1 train-only prompt distillation
- active_item: R041

## Completed Prerequisites

- [x] R036 corpus inventory completed.
- [x] R037 split and leakage audit completed.
- [x] R038 unified harness implemented and tested.
- [x] R039 mechanical smoke completed; no method-effect claim made.
- [x] M0 classified GO for train-only R040-R041.
- [x] R040 canonical attempt3 selected 30 unique verified train traces.
- [x] Sealed trace-content reads remained zero.

## R041 In Progress

- [ ] Verify the canonical R040 manifest and hash.
- [ ] Distill an H2 prompt of at most 800 provider tokens.
- [ ] Link every H2 claim to one or more selected trace IDs.
- [ ] Construct a generic H1 prompt within +/-5% of H2 provider tokens.
- [ ] Record bytes, words, provider/tokenizer counts, and SHA-256 hashes.
- [ ] Record model/tool, token usage, wall time, and human editing cost.
- [ ] Scan for prohibited proof bypasses and executable-code removal guidance.
- [ ] Freeze H1/H2, the evidence table, manifest, and reviewed summary.
- [ ] Update `research_memory/CURRENT.md` and rebuild the memory index.

## Blocked

- [ ] R042-R044 frontier dev evaluation requires frozen H1/H2 and working
  frontier-model authentication.
- [ ] R050-R053 sealed confirmation remains blocked until dev-only selection
  and all predeclared promotion gates pass.

## Claim Boundary

- [x] R041 is prompt construction, not downstream effectiveness evidence.
- [x] Information gain remains a secondary offline diagnostic.
- [x] No solved-rate or token-efficiency improvement claim is currently valid.
