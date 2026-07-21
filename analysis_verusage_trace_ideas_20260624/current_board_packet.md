# Current Board Packet

## Incumbent Behavior

The current agent loop runs Verus, classifies the target error, routes to a specialized repair agent, prompts the LLM with full code/error/context, applies one or more candidates, accepts local verification improvements, and repeats up to the attempt budget.

Representative actions include:

- `postcondition_repair`
- `uselemma`
- `instantiate_exists`
- `instantiate_forall`
- `case_analysis`
- `seqsetmap`
- `nonlinear_arithmetic`
- `add_trigger_assert`
- `bit_vector_reasoning`

## Decisive Local Results

20-minute model-level summary from `all_batch_results-*/all_results_with_breakdown_20min.csv`:

| model | verified | total | rate | total tokens |
|---|---:|---:|---:|---:|
| claude | 565 | 849 | 66.5% | 349.8M |
| claude-s4 | 487 | 849 | 57.4% | 422.7M |
| gpt5 | 460 | 849 | 54.2% | 129.2M |
| o4mini | 345 | 849 | 40.6% | 318.5M |

Project-level pattern:

- `AC`: hardest and most token-expensive. Best observed 20-minute success is `claude` at 23/63; `o4mini` is 12/63.
- `NR` and `OS`: large token sinks with low-to-mid success.
- `NO`, `MA`, `AL`, `VE`: much easier and often low-token.

## Active Bottleneck

The expensive failure region is not only weak generation. It is **brittle inference control**:

- repeated same-action loops,
- insufficient transfer from successful traces,
- generic retrieval examples that do not match Verusage project structure,
- local-improvement acceptance that can increase downstream proof burden.

## Stale Routes To Avoid

- Simply increasing max attempts. The logs already show many 20-attempt loops.
- Adding more generic vstd examples. Some AC prompts already retrieve vstd examples that are structurally irrelevant to Kubernetes temporal proof obligations.
- Rewarding action success without final verification.
- Treating all projects uniformly; the token/success distribution is strongly project-family dependent.

