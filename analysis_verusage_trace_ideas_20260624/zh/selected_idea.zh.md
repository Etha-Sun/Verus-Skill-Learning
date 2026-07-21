# 最终选择的 Idea：Verusage Trace-Distilled Skeleton Cache With Repetition Gate

## Idea ID

`verusage_trace_skeleton_gate_20260624`

## 选择的路线

构建一个 Verusage-specific repair controller layer，它会：

1. 从成功本地 traces 中蒸馏 compact proof skeletons；
2. 根据 normalized verifier state 和 project-family features 检索 skeletons；
3. 当本地证据显示某个 same-action loop 低价值时，阻止继续重复；
4. 将下一次 prompt 路由到 skeleton-guided code generation、diagnosis-only planning 或 early stop。

## 为什么现在做

当前工作区已有足够 trace 数据可以挖掘正向和负向模式：2,996 个 repair logs、65k reasoning files、104k prompt files，以及同一 849-task benchmark 上的跨模型运行。

## 核心假设

在 Verusage 上，高成本失败常常来自 proof structure 的紧凑迁移不足和 repeated low-value actions，而不是完全没有成功 proof route。trace-distilled skeleton cache 加 repetition gate 应该能降低 failed tasks 的 token 使用，并提升 `AC`、`NR`、`OS` 等 project families 的成功率。

## 机制草图

### Skeleton Record

每条成功或局部有用 trace 被压缩成：

- project family：`AC`、`NR`、`OS` 等；
- target name 和 normalized file/function family；
- verifier error sequence；
- action sequence；
- accepted/rejected local outcomes；
- 实际使用的 helper lemmas/functions；
- proof-shape tags，例如 `exists-witness`、`leads_to_trans`、`seqsetmap`、`bitvector-bound`、`postcondition-split`；
- compact final patch diff summary；
- 成功前观察到的 anti-patterns。

### Retrieval Key

使用结构化 key，而不是 raw token similarity：

`project + normalized target name + error type + nearby lemma names + spec-shape + prior failed actions`。

### Repetition Gate

Normalize 当前 error signature，并跟踪：

- same target error after same action；
- candidate rejected for same reason；
- accepted local repair followed by persistent `AssertFail`；
- repeated action count per state。

超过阈值后，controller 停止重复 action，并强制执行以下之一：

- 检索 skeleton，并要求模型使用命名 lemmas/witnesses 写代码；
- 请求 diagnosis-only proof plan；
- 切换 action family；
- 如果 expected value 很低，则终止。

## 代码层落点

可能需要的 repair system 组件：

- trace parser，解析 `verus-repair.log`、`reasoning/*.txt`、`fix-v*-success-*` 和 result CSVs；
- skeleton index builder；
- action selection 前的 controller hook；
- 支持 compact skeleton、并禁止重复 rejected attempts 的 prompt template；
- offline replay evaluator。

## 最小验证

### 先离线

1. 从成功 traces 建 skeletons。
2. 在现有 logs 上模拟 repetition gates。
3. 报告：
   - threshold 2/3/4 下节省的 token calls；
   - 会被错误提前停止的真实 successful runs；
   - heldout traces 上 top-k skeleton retrieval hit rate；
   - retrieved skeleton actions 和实际成功 actions 的重合。

### 小规模在线 Smoke

运行 20-50 个 heldout high-token tasks，来自 `AC`、`NR` 和 `OS`。

比较：

- verified rate；
- total tokens；
- average non-verified tokens；
- attempts to first accepted globally useful patch；
- repeated-action loops 数量。

## 成功标准

最低有用结果：

- non-verified average tokens 降低至少 30%，且 verified rate 不下降。

强结果：

- non-verified average tokens 降低至少 50%，并在 `AC/NR/OS` 中恢复额外 verified tasks。

## 放弃条件

如果出现以下情况，放弃或降级：

- offline replay 显示很多 successful runs 需要超过 proposed gate 的 repeated same-action attempts；
- skeleton top-k retrieval 很少匹配 useful successful actions；
- online smoke 只是通过更早放弃本可验证任务来减少 tokens；
- 在 leakage-free split 下收益只来自 exact-task patch memorization。

## Anti-Win Condition

如果这个路线只是通过更早放弃来降低 token，而 verified rate 下降，或者依赖为评测任务检索 exact final patches，那就不算赢。

## 最强替代假设

真正瓶颈可能是 prompt slicing，而不是 proof-plan memory。如果更小的 project-family contexts 单独就解决问题，那么 skeleton indexing 可能是不必要复杂度。

## References

1. Andrea Lattuada et al. "Verus: Verifying Rust Programs using Linear Ghost Types." arXiv:2303.05491. https://arxiv.org/abs/2303.05491
2. Noah Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366. https://arxiv.org/abs/2303.11366
3. Huajian Xin et al. "DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search." arXiv:2408.08152. https://arxiv.org/abs/2408.08152
4. Xingguang Ji et al. "Leanabell-Prover-V2: Verifier-integrated Reasoning for Formal Theorem Proving via Reinforcement Learning." arXiv:2507.08649. https://arxiv.org/abs/2507.08649
5. Max Tan. "Automating Formal Verification with Reinforcement Learning and Recursive Inference." arXiv:2605.30914. https://arxiv.org/abs/2605.30914

