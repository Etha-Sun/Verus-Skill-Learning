# 当前状态包

## 现有行为

当前 agent loop 的基本流程是：运行 Verus，分类 target error，路由到专门的 repair agent，用完整 code/error/context 提示 LLM，应用一个或多个 candidates，接受局部 verification improvement，然后重复直到 attempt budget 用完。

代表性 actions 包括：

- `postcondition_repair`
- `uselemma`
- `instantiate_exists`
- `instantiate_forall`
- `case_analysis`
- `seqsetmap`
- `nonlinear_arithmetic`
- `add_trigger_assert`
- `bit_vector_reasoning`

## 决定性本地结果

来自 `all_batch_results-*/all_results_with_breakdown_20min.csv` 的 20 分钟模型级摘要：

| model | verified | total | rate | total tokens |
|---|---:|---:|---:|---:|
| claude | 565 | 849 | 66.5% | 349.8M |
| claude-s4 | 487 | 849 | 57.4% | 422.7M |
| gpt5 | 460 | 849 | 54.2% | 129.2M |
| o4mini | 345 | 849 | 40.6% | 318.5M |

项目级模式：

- `AC`：最难、token 最贵。20 分钟内最好成功率是 `claude` 的 23/63；`o4mini` 是 12/63。
- `NR` 和 `OS`：大 token sink，成功率中低。
- `NO`、`MA`、`AL`、`VE`：明显更容易，通常低 token。

## 当前瓶颈

昂贵失败区域不只是生成能力弱，而是 **brittle inference control**：

- 重复 same-action loops；
- 成功 traces 没有迁移复用；
- generic retrieval examples 不匹配 Verusage project structure；
- local-improvement acceptance 可能增加后续 proof burden。

## 应避免的旧路线

- 简单增加 max attempts。日志已经显示很多 20-attempt loops。
- 添加更多 generic vstd examples。部分 AC prompt 已经检索到 vstd examples，但它们和 Kubernetes temporal proof obligations 的结构不匹配。
- 只奖励 action success，而不看 final verification。
- 所有项目统一对待；token/success 分布有强 project-family 依赖。

