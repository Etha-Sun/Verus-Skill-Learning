# 候选方向

## 原始候选 Slate

1. **Trace-distilled proof skeleton cache**  
   将成功 traces 抽取为紧凑 proof plans，用 project、file family、target lemma/function、error type、helper-lemma graph 和 final patch motif 做 key。

2. **Repetition gate / loop-aware action router**  
   检测重复 `(error signature, action, local outcome)` 循环，强制换路线、检索 proof-plan、缩小 context 或 early stop。

3. **Project-family prompt compaction**  
   为 `AC`、`NR`、`OS`、`MA`、`AL` 等建立不同 prompt policies；用聚焦 target slice 和 helper lemma summaries 替代 full-code replay。

4. **Final-verification-aware reward shaping**  
   惩罚那些被 local acceptance 接受但制造 persistent downstream `AssertFail` loop 的修复；奖励朝 `VERIFIED` 的单调进展，而不是只奖励 target-error removal。

5. **Action-policy learner from existing traces**  
   基于本地 trace features 训练轻量 router：project、error type、function name、known lemmas、previous action failures、token budget。

6. **Cross-model proof distillation set**  
   使用一个模型成功、其他模型失败的样本，为 heldout-family evaluation 生成 compact teacher proof plans。

7. **用 Verusage helper-lemma retrieval 替换 generic vstd retrieval**  
   按 spec-shape 索引本地成功 helper lemmas 和 external-body lemmas，而不是只按 vstd token overlap。

8. **Budgeted two-stage repair**  
   先要求 proof diagnosis 和 skeleton；只有当 skeleton 命名了具体 lemmas/witnesses/cases 时，才生成代码。

## 严肃候选 Frontier

| candidate | relevance | feasibility | upside | token-saving potential | risk | verdict |
|---|---:|---:|---:|---:|---|---|
| trace skeleton cache + repetition gate | high | high | high | high | 如果 exact-task 评测会 leakage | select |
| project-family prompt compaction | high | medium | medium-high | high | 需要谨慎 slicer | defer as component |
| final-verification-aware reward shaping | high | medium | medium | medium | 需要设计 progress metric | defer |
| standalone action-policy learner | medium | medium | medium | medium | 可能过拟合当前 logs | reject as first step |

## 最终选择

选择 **trace-distilled proof skeleton cache + repetition gate** 作为下一个可执行路线。

选择理由：

- 直接针对最大浪费：重复高 token failures。
- 使用当前数据中已经存在的 Verusage-specific evidence。
- 可以在昂贵新模型运行前离线 falsify。
- 同时改善 capability 和 cost：proof skeletons 可指导难题，repetition gates 可阻止已知坏循环。

## 暂缓

- Project-family prompt compaction 应在所选方向中作为组件实现，前提是先定义 skeleton keys。
- Final-verification-aware reward shaping 应在观察到 local-success loops 仍然存在后跟进。

## 暂时拒绝

- 纯 action-policy learning 太可能在没有稳定 trace signatures 的情况下学习表面相关性。
- 更多 generic retrieval examples 不太可能修复 AC/NR/OS failures，因为抽样 prompts 已经显示 generic examples 缺少 project-specific temporal/spec structure。

