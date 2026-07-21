# 紧凑相关工作 Grounding

这是面向 optimization brief 的 targeted search，不是完整论文综述。

## 复用/本地覆盖

本地 traces 已经定义了相关系统：基于 Verus 的 repair agents，使用 verifier feedback 和专门 action routing。

## 新检查的外部工作

1. Lattuada et al. 2023, "Verus: Verifying Rust Programs using Linear Ghost Types." arXiv:2303.05491. https://arxiv.org/abs/2303.05491
   - 建立了 Verus 作为基于 SMT 的 Rust verification system。相关性在于 Verusage 任务是 Verus proof/program repair，而不是 Lean 风格 tactic script。

2. Shinn et al. 2023, "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366. https://arxiv.org/abs/2303.11366
   - 支持用 verbal feedback memory 改进 language agents 的一般思路。Verusage 需要更结构化的版本：不是自由文本 reflection，而是 verifier/error/action memory。

3. Xin et al. 2024, "DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search." arXiv:2408.08152. https://arxiv.org/abs/2408.08152
   - 表明 proof-assistant feedback 和 search 能提升 theorem proving。Verusage 的区别在于 repair actions 是 code-level Verus edits，token 成本主要来自反复 full-context repair prompts。

4. Ji et al. 2025, "Leanabell-Prover-V2: Verifier-integrated Reasoning for Formal Theorem Proving via Reinforcement Learning." arXiv:2507.08649. https://arxiv.org/abs/2507.08649
   - 与 verifier-integrated multi-turn reasoning 相关。可迁移思想是优化 verifier interactions；Verusage-specific gap 是 action-loop detection 和从 repair traces 中复用 proof skeleton。

5. Tan 2026, "Automating Formal Verification with Reinforcement Learning and Recursive Inference." arXiv:2605.30914. https://arxiv.org/abs/2605.30914
   - 与 verified programs/proofs 的 verifier-guided inference scaffold 相关。本地 trace evidence 指向一个具体 scaffold 改进：project-specific proof-plan caches 和 repetition gates。

## Closest-Prior-Work 对比

| prior mechanism | overlap | remaining Verusage gap |
|---|---|---|
| Reflexion-style memory | 使用过去 feedback 指导未来 agent 决策 | 本地 traces 需要 typed verifier signatures，而不只是文本 reflections |
| Proof-assistant feedback RL/MCTS | 用 verifier signals 优化 proof attempts | Verusage repair 有 action-specific loops 和高 input-token replay，需要 cost-aware routing |
| Verifier-guided recursive inference | 用 verifier feedback 分解和修复 proofs | 当前 Verusage 数据暴露了确切的 project-family proof skeletons 和 negative loops，可离线挖掘 |

## Novelty / Value 边界

所选方向不应声称为广义全新。它的价值是 **transfer-to-new-setting 和 infrastructure/platform value**：

- Verus/Rust repair tasks 不同于 Lean mathematical theorem proving。
- 本地数据集有重复 project families（`AC`、`NR`、`OS` 等），存在可复用 lemma/action motifs。
- traces 同时包含正向 proof skeletons 和负向 loop signatures。
- 直接收益是 heldout Verusage tasks 上可测的 token reduction 和 success lift。

## 未解决缺口

- 这次 targeted pass 没有找到直接的 Verusage-specific paper。
- 如果要做论文级 claim，需要更完整搜索 Verus repair、LLM program repair with compiler feedback 和 formal-verification benchmarks。

