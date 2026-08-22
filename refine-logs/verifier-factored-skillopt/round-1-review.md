# Round 1 Review

**Reviewer**: independent GPT-5.5 xhigh
**Overall**: 6.10/10
**Verdict**: REVISE
**Anchor**: preserved

<details>
<summary>Full raw review</summary>

## 总评

V-FACE 抓住了真实且重要的问题：SkillOpt 的 whole-skill reward 把工具链失效、动作有效性、模型采用和上下文诱发漂移混在一起。轨迹证据具体，负向 pilot 也被诚实使用。但当前“three-effect decomposition”在因果上并不成立；其中只有 exposure 是随机化处理，forced edit 是另一种人工干预，adoption 只是处理后的观测变量。再加上与 Causal Agent Replay、Credit Without Ground Truth、TRACE、WML/WGSO 的明显重叠，现阶段更像一个形式化 proof-skill audit protocol，而非已站稳的新 optimizer。

| 维度 | 分数 | 评价 |
|---|---:|---|
| Problem Fidelity (15%) | 9 | 与用户问题和具体失败轨迹高度一致 |
| Method Specificity (25%) | 6 | schema 清楚，但 compiler、placebo、estimand 和标签真值未定义到可复现程度 |
| Contribution Quality (25%) | 5 | verifier-mediated atomic artifact intervention 有潜力，但独立新意仅属 partial |
| Frontier Leverage (15%) | 7 | 正确利用 verifier、fidelity checker 和 executed replay，且没有滥加 RL/GNN |
| Feasibility (10%) | 5 | 1/8 的抽取结果直接威胁核心 action compiler；新未见任务来源也未落实 |
| Validation Focus (5%) | 5 | ablation 方向合理，但 attribution accuracy 的 ground truth 存在循环定义 |
| Venue Readiness (5%) | 4 | 尚无 prospective 数据、identification argument 或足量 benchmark |
| **OVERALL** | **6.10/10** | **REVISE** |

### 必须修复

- P0：冻结 3–5 类 typed AST patch，定义 deterministic compiler、edit locality、placebo 与失败语义。
- P0：把唯一 thesis 收窄为 formal verifier 可执行的 atomic artifact intervention/admission benchmark。
- P0：先做 compiler go/no-go，未通过前不实现 retrieval/calibration/full optimizer。
- P0：用 build 的有限干预预测完全独立 evaluation checkpoint 的 replicated exposure ITT sign，避免循环定义。
- P1：若只能形成诊断工具，按 formal-methods tooling/audit 定位。

### 可识别性

不能称为“三效应分解”。应改为“两类干预 + 一个采用观测”：随机化 exposure ITT、compiler-dependent forced-edit verifier contrast、以及 post-treatment adoption telemetry。`incorporation failure` 和 `control drift` 只能是诊断假设。

### 最高风险与 gate

在全新 development split 盲取 30 个 eligible checkpoints；冻结 3–5 类 compiler；至少 18/30 可实例化、其中 ≥90% 经盲审符合 card、100% Lynette fidelity、越界/无关 edit ≤5%，且 mismatch/placebo 不应系统性改善。任一关键门槛失败则停止 optimizer/retrieval，转为 extractor/benchmark。

</details>
