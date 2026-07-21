# Pre-Idea Draft：Project-Family Context Compaction

## 两句话 Pitch

用 project-family context profiles 取代一刀切 full-code prompts：`AC` 给 temporal phase lemmas 和 state predicates；`OS` 给 linked-list/page-table invariants；`NR` 给 refinement 和 bit/address facts。目标是在提高 proof context 相关性的同时减少 input-token replay。

## 隐含假设

- Project-family structure 足够稳定，可以定义 reusable context profiles。
- 相关 helper lemmas 可以自动提取。
- 更小 prompt 节省 token 的同时不会删掉必要 context。

## 最强拒绝理由

糟糕 slicing 可能漏掉必需 definition，导致 per-call tokens 降低但失败 attempts 增多。

## 最便宜 falsification

对一组固定成功 traces：

- 重建 final patch 实际引用的最小 definitions/lemmas。
- 测量 proposed slicer 覆盖它们的频率。
- 将 prompt size 与原始 `llm-prompts/*-input.txt` 对比。

## Promotion Verdict

先暂缓，等 skeleton extraction 明确哪些 context elements 反复有用后，再作为组件推进。

