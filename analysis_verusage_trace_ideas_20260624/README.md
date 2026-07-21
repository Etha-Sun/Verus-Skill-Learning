# Verusage Trace Idea Brief

Date: 2026-06-24

This folder is a separate analysis artifact. It does not modify the original `result-*`, `all_batch_results-*`, or `claude_sonnet_gpt5/` data.

## Output Type

This is an algorithm-first idea brief, not a paper-ready novelty package. The immediate goal is to extract Verusage-specific directions from local agent trajectories, traces, prompts, and result CSVs that can improve agent capability or reduce token consumption under the existing dataset/evaluation contract.

## Main Conclusion

The strongest next direction is:

**Verusage trace-distilled proof skeleton cache with a repetition gate.**

The core observation is that many failures are not simply hard tasks. For the same Verusage file, one model often verifies with far fewer tokens while another spends millions of tokens and fails. The local logs show repeated action loops such as `postcondition_repair -> assert fail -> uselemma -> same postcondition/assert fail`, often for 20 attempts. This suggests the dataset contains reusable proof plans and negative loop signatures that are not being represented compactly enough for the agent.

## Key Local Evidence

- `all_batch_results-*` contains 849 task rows per model under the 20-minute breakdown.
- `all_batch_results-*` contains 2,996 `verus-repair.log` files.
- The workspace contains 65,370 `reasoning/*.txt` files and 104,759 `llm-prompts/*.txt` files.
- In 20-minute results, average non-verified token use is much higher than verified token use:
  - `claude`: 110,999 avg verified tokens vs 1,010,949 avg non-verified tokens.
  - `claude-s4`: 125,725 vs 998,522.
  - `gpt5`: 64,134 vs 256,202.
  - `o4mini`: 107,696 vs 558,247.
- `AC`, `NR`, and `OS` dominate token sinks and have much lower success rates than `NO`, `MA`, `AL`, and `VE`.
- Across all parsed logs, `AssertFail` dominates target errors, followed by `PostCondFail`.
- 1,010 logs repeat the same primary action at least 8 times, which is a direct token-saving opportunity.

## Files

- `objective_contract.md`: target, constraints, false-progress signals.
- `current_board_packet.md`: current state reconstructed from local data.
- `trace_audit.md`: quantitative and qualitative trace findings.
- `literature_survey.md`: compact related-work grounding.
- `limitations.md`: bottleneck map.
- `candidates.md`: bounded idea slate and scoring.
- `selected_idea.md`: selected idea handoff.
- `pre_idea_drafts/`: challenge memos for the serious candidates.
- `tables/`: machine-readable summary CSVs generated from local result files.

