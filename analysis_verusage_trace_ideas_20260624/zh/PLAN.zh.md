# Idea Node Plan 中文版

## 瓶颈

Verusage agents 会在稳定 verifier errors 上重复低价值 repair actions，从而浪费 tokens；同时它们没有跨模型/跨 run 复用成功 proof structure。

## 候选 Families

- live：trace-distilled proof skeleton cache；
- live：repetition gate / loop-aware action router；
- component：project-family prompt compaction；
- deferred：final-verification-aware reward shaping；
- deferred：trace signatures 稳定后再做 learned action policy。

## Selection Gate

只有满足以下条件的方向才应被选择：

- 只使用当前 Verusage traces 和现有 verifier outcomes；
- 可以在昂贵运行前离线 falsify；
- 同时针对 verified rate 和 token cost；
- 避免 exact-task leakage，以便做模型能力评估。

## 当前结果

已选择 `verusage_trace_skeleton_gate_20260624`。

下一阶段：先实现 offline replay 和 skeleton extraction，再修改 live repair agent。

