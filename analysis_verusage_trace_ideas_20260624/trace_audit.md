# Trace Audit

## Data Surface Inspected

Local files inspected by script and sampling:

- 30 top-level `*_analysis_results.csv`.
- 23 top-level `*_action_counts.csv`.
- 4 model batch folders under `all_batch_results-*`.
- 2,996 `verus-repair.log` files.
- representative `llm-prompts/*.txt`, `reasoning/*.txt`, and `fix-v*-success-*` files.

Machine-readable summaries are in `tables/`.

## Quantitative Findings

### 1. Failure Is Much More Expensive Than Success

From 20-minute batch summaries:

| model | avg verified tokens | avg non-verified tokens | ratio |
|---|---:|---:|---:|
| claude | 110,999 | 1,010,949 | 9.1x |
| claude-s4 | 125,725 | 998,522 | 7.9x |
| gpt5 | 64,134 | 256,202 | 4.0x |
| o4mini | 107,696 | 558,247 | 5.2x |

This makes loop prevention as important as proof generation.

### 2. The Hard Subsets Are Project-Family Specific

20-minute verified rates:

| project | claude | claude-s4 | gpt5 | o4mini |
|---|---:|---:|---:|---:|
| AC | 37% | 21% | 27% | 19% |
| NR | 58% | 55% | 48% | 30% |
| OS | 61% | 53% | 44% | 37% |
| NO | 97% | 100% | 83% | 72% |
| MA | 84% | 75% | 72% | 62% |

`AC`, `NR`, and `OS` should get different routing, context compaction, and retrieval policies from `NO`, `MA`, and `AL`.

### 3. Repeated Action Loops Are Common

From 2,996 parsed logs:

- `AssertFail` is the dominant target error for all models.
- `PostCondFail` is the second-most common.
- 1,010 logs repeat the same primary action at least 8 times.

Example high-loop patterns:

- `seqsetmap` repeated 19 times on `OS__slinkedlist__...remove_helper*`.
- `induction` repeated 19 times on `VE__regular__repetition__...prefix_secure_helper`.
- `instantiate_forall` repeated 18-19 times on `AL__tla_forall...`.
- `uselemma` repeated 17-19 times on `NR__extra__aligned...`.

### 4. Cross-Model Disagreements Reveal Reusable Proof Plans

Examples from `tables/top_100_cross_model_disagreements.csv`:

- `AC__...lemma_from_after_receive_create_pod_resp_to_receive_create_pod_resp.rs`
  - `gpt5`: verified with about 340k tokens.
  - `claude-s4`: failed with about 3.37M tokens.
- `OS__kernel__create_and_share_pages__impl0__share_mapping.rs`
  - `gpt5`: verified with about 231k tokens.
  - `claude`/`claude-s4`: failed around 1.94M/2.64M tokens.
- `NR__impl_u__wrapped_token__impl2__register_failed_map.rs`
  - `gpt5`: verified with about 160k tokens.
  - `claude`/`claude-s4`/`o4mini`: failed with 0.95M-1.61M tokens.

These are direct evidence that the dataset contains reusable successful proof structure not being transferred across runs.

## Qualitative Findings

### AC Temporal Proofs Need Structure, Not More Generic Examples

In the sampled AC liveness lemma, GPT-5 succeeded after identifying that the proof needed:

- existential witness extraction from an in-flight OK response,
- use of two phase-progress lemmas,
- leads-to transitivity/composition.

The failing Claude-S4 trace repeated `postcondition_repair` and `uselemma` for 20 attempts. It accepted only one repair and consumed about 5.58M input tokens in the log.

The prompt included full code and generic vstd examples. The vstd token-similarity examples were mostly about sequences/sets/pow2, not the Kubernetes temporal proof structure. This suggests a Verusage-specific helper-lemma graph is more valuable than generic token-similar snippets.

### Local Repair Success Can Be Misleading

A repair can remove a target `PostCondFail` and introduce a persistent `AssertFail` on the inserted assertion. If the controller only sees local target-error improvement, it may accept a change that increases downstream search cost.

### Prompt Cost Is Mostly Input Repetition

For large AC prompts, a single input prompt can be 180k+ characters and 40k-60k input tokens. Many failed runs repeat this dozens of times. This makes compact proof-state memory and prompt deltas more promising than output-length control.

