## Decision: DO_NOT_DEPLOY

### BLOCKING

- The analysis gate does not independently compare intervention-token counts or serialized option targets across artifacts. It trusts `token_match_exact`; adversarial 6×6 matrices with a 99-vs-100 token delta or `A`-vs-`B` target mismatch were accepted. This fails criterion 3. See [ig_analysis.py](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/ig_analysis.py:188).
- Scoring validates prepared format/delta only when metadata exists. Missing `prepared_prompt_format` or `prepared_intervention_token_count` can bypass enforcement. See [logprob_scorer.py](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:326) and [logprob_scorer.py](<workspace>/verus-self-evolve-scaffold/src/verus_self_evolve/logprob_scorer.py:459).

### NON-BLOCKING / VERIFIED

- `chat_direct` ends at the assistant header without `<think>` and the plan honestly calls it a reasoning-suppressed direct-action proxy.
- The run has six states and six distinct non-empty families per state. Independent tokenization confirmed exact common deltas: 124, 160, 144, 125, 124, and 157. Production matching uses truncation only.
- Analysis correctly rejected incomplete matrices, wrong candidate counts, unaccepted actions, changed option-map hashes, false match flags, and wrong prompt formats.
- Recorded case, ontology, tokenizer, and source hashes exist and match current bytes.
- Fifteen runnable probe/scorer tests passed. The analysis integrity and common-truncation paths lack direct regression tests.

No files were modified.