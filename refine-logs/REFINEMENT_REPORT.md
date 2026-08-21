# Refinement Report

**Problem:** Verus-specific per-file memory + RAG skill-system design  
**Initial Approach:** 从每个文件提取 memory，再做高度 domain-specific RAG  
**Date:** 2026-08-04  
**Rounds:** 3 / 5  
**Final Score:** 9.10 / 10  
**Final Verdict:** READY

## Final Thesis

- 每文件 memory 是合理 ingestion/cache 形式，但不是正确 retrieval unit。
- 静态 Verus hybrid retrieval 是必要 substrate 和强 baseline，已不构成新颖性。
- 最小研究机制是 replay-validated selective lemma-transition retrieval。
- MVP 只研究一个 repository/version/error family 和 `invoke_lemma`。
- 10–20-state pilot 只作 kill gate，不支持 population claim。

## Score Evolution

| Round | Problem Fidelity | Method Specificity | Contribution Quality | Frontier Leverage | Feasibility | Validation Focus | Venue Readiness | Overall | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 9 | 6 | 5 | 7 | 5 | 6 | 5 | 6.20 | REVISE |
| 2 | 10 | 8 | 7 | 8 | 6 | 8 | 6 | 7.75 | REVISE |
| 3 | 10 | 9 | 9 | 9 | 9 | 9 | 8 | 9.10 | READY |

## Output Files

- Clean proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Round reviews/refinements: `refine-logs/round-*.md`
- Score history: `refine-logs/score-history.md`

## Remaining Weaknesses

没有 implementation blocker。论文级 claim 仍取决于 kill gate 和随后更大规模、leakage-safe、matched live evaluation；当前没有 solved-rate 或 token-efficiency 改善证据。
