# Pre-Idea Draft：Trace-Distilled Proof Skeleton Cache

## 两句话 Pitch

把成功的 Verusage traces 挖掘成 compact proof skeletons，并用 verifier error、project family、target function、附近 lemma names 和 proof-shape 做 key。repair 时先检索 skeleton，再发 full-context LLM prompt，让模型看到真实 proof route，而不是通过重复失败 attempts 重新发现。

## 隐含假设

- 成功 traces 包含可复用 proof structure，而不只是 exact patches。
- 按 project/error/lemma graph 检索 skeleton 比原始 token-similar vstd examples 更有用。
- cache 可以切分，避免评估泛化时 leakage。

## 最强拒绝理由

cache 可能退化成 exact-task memorization。若是这样，它对已知 Verusage instances 有工程价值，但不能作为 capability improvement 的强 claim。

## 最便宜 falsification

离线：

1. 从成功 traces 抽取 skeletons。
2. 对 heldout failed traces，测试 target 所需 action/lemma/witness 是否出现在 retrieved top-k skeletons。
3. 与 generic token-similarity retrieval 和 raw previous-attempt inclusion 对比。

最小在线：

- 运行 20-50 个 high-token failed `AC/NR/OS` tasks，加入 skeleton hints，对比 verified rate 和 total tokens。

## Promotion Verdict

推进，但必须和 leakage-safe splits 以及 repetition gate 一起做。

