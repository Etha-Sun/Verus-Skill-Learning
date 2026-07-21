# Experiment Code Review

Date: 2026-07-14
Reviewer: GPT-5.5, xhigh, read-only
Scope: Qwen3.6 three-target IG implementation before GPU deployment

## Initial Verdict

`BLOCKING` until the long-target context setting is resolved.

The reviewer found the following implementation areas correct:

- action teacher forcing uses the complete JSON label rather than A-V keys;
- the same six locally accepted states cover action, patch, and full proof;
- patch and full-proof targets come from deterministic source files rather than LLM rewrites;
- evidence artifacts do not read the target action or final proof;
- IG uses `log P(target | state, artifact) - log P(target | state)`;
- vLLM target-position indexing is structurally correct.

The blocker was that the scorer defaulted to `max_model_len=4096` and had no sliding fallback, while long proof cases are much larger.

## Resolution

- The Qwen3.6 tokenizer audit covers every one of the 126 frozen cases.
- Maximum context+target length is 78,392 tokens.
- The scorer default and formal commands now use `max_model_len=131072`.
- Every case therefore uses exact full-context teacher forcing; no sliding approximation is needed in this experiment.
- A preflight check rejects any sequence above the configured limit. It never silently truncates.
- The real vLLM sanity run is the remaining integration check for prompt-logprob indexing.

Resolved verdict: `PASS FOR SANITY DEPLOYMENT`, conditional on the real vLLM prompt-logprob sanity passing.

