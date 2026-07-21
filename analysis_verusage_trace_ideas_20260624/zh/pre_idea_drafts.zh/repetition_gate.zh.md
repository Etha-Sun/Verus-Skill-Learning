# Pre-Idea Draft：Repetition Gate

## 两句话 Pitch

增加一个 controller-level gate，用来检测重复的 `(normalized error, action, local outcome)` cycle，防止 agent 在同一个 proof state 上继续调用同一个 action。它不会再发一个大 prompt，而是强制切换路线：检索 proof skeleton、请求 diagnosis-only plan，或者在 expected value 低时停止。

## 隐含假设

- 重复 action loop 在少数几次失败后大多低产出。
- Error signatures 可以足够稳健地 normalize，抵抗小的 line-number changes。
- 强制换路线不会过多压制 late successful attempt。

## 最强拒绝理由

一些难题可能确实需要很多看起来相似的 attempts 才能成功；严格 gate 可能降低 verified rate。

## 最便宜 falsification

离线 replay logs：

- 模拟在 2、3、4 次 repeated same-action failures 后 gate。
- 估计节省的 token calls。
- 统计多少真实 successful runs 会被提前停止。

## Promotion Verdict

如果 offline replay 显示高 token savings 且 false-stop rate 低，则作为低风险 efficiency component 推进。

