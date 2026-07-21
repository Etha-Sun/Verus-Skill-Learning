# PlugMem decision information gain and memory density mapping

## Scope

Does PlugMem (arXiv:2603.03296) cite InfoGain-RAG, do its
information-theoretic metrics match the VeruSAGE skill-evaluation problem, and
which parts should update the project metric contract?

## Sources

| source | link | why it matters |
|---|---|---|
| PlugMem | https://arxiv.org/abs/2603.03296 | Defines decision information gain and memory information density for agent memory |
| InfoGain-RAG | https://arxiv.org/html/2509.12765v1 | Prior reference used by this project for context-conditioned ground-truth likelihood gain |
| PlugMem arXiv source | temporary extraction at `/tmp/arxiv260303296/` | Allowed full-text, bibliography, formula, and implementation inspection |

## Method Patterns

- No occurrence of `2509.12765`, `InfoGain-RAG`, or a matching reference entry
  appears in the inspected PlugMem source or bibliography.
- Decision Information Gain:
  `PMI(a*;m|s) = log2 P_mem(a*|s,m) / P_base(a*|s)`.
- Per-instance information density:
  `rho = PMI / |m|`, measured in bits per injected memory token.
- Global density uses the more stable ratio of sums:
  `rho_global = sum_i PMI_i / sum_i |m_i|`.
- Additional diagnostics include a high-prior redundancy filter,
  utility-cost/token-budget curves, entropy reduction over the full action
  distribution, confidence-validity quadrants, and a validity-adjusted
  distributional density.
- Operational caveat: LongMemEval substitutes binary judge correctness for
  probability; HotpotQA substitutes answer F1; WebArena uses task success, all
  with additive smoothing. These are not model token logprobs.

## Takeaways For This Project

PlugMem independently uses a metric mathematically equivalent to this project's
action IG, but in base-2 units and with memory/skill token cost made explicit.
The strongest transferable idea is information density: evaluate not only
whether a retrieved skill raises the probability of the correct repair action,
but how much decision information it provides per injected skill token.

Metric hierarchy to adopt:

1. Primary offline utility: normalized-action Decision IG/PMI.
2. Primary efficiency: skill information density, using the global
   ratio-of-sums for aggregate reporting.
3. Secondary diagnostic: action-distribution entropy change and PMI/entropy
   quadrants.
4. Budget analysis: sweep skill token budget or retrieved top-k and plot the
   utility-cost frontier.
5. Primary system evidence remains held-out verifier solved rate, total agent
   tokens, attempts, and repetition; IG is a promotion/ranking proxy.

## Gaps / Risks

- Do not copy PlugMem's binary/F1-as-probability operationalization when direct
  action logprobs are available.
- Verifier success is a separate end-task outcome unless repeated sampling is
  used to estimate a success probability.
- The appendix's validity-adjusted density is a useful conceptual diagnostic
  but is more heuristic than basic PMI; it is not a first-pass metric.
- Our existing QwQ action-IG scorer must fix context-target tokenization and
  prompt/chat formatting, or preferably score a normalized canonical VeruSAGE
  action distribution, before these metrics are meaningful.
