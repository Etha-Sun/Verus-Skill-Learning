# Round 3 Refinement — Protocol Cleanup

## Problem Anchor

- **Bottom-line problem**: 从已有 SkillOpt self-evolution 与多模型 test 失败轨迹出发，找出 SkillOpt 在 Verus task-specific 场景中的机制性缺陷，并形成可执行、可检验的改进路线。
- **Must-solve bottleneck**: whole-skill、whole-trajectory 的单一成功分数无法区分环境有效性、局部 proof action 有效性、模型采用和 exposure 后行为漂移。
- **Non-goals**: 不把普通 retrieval/abstention/checkpoint schema 包装成创新；不使用已查看 test-20 调参；不在无 prospective 结果时声称性能或因果收益。
- **Success condition**: typed executable Build evidence 能在独立 checkpoints 上以非退化 coverage 改善 harmful/beneficial admission 决策。

## Final Design Cleanup

以下内容替换 Round-2 proposal 中相应协议；其余 `CardTemplate/CardInstantiation`、三类 DSL、adoption telemetry、baselines 与 stop rules 不变。

### 1. Separate static instantiation from forced execution

```text
instantiate_static(template, checkpoint_public_features)
  -> NON_INSTANTIABLE(reason)
  -> STATIC_INSTANCE(
       resolved_roles,
       typed_edit_ast,
       proof_only_anchor,
       symbol/type/ghost/locality audit
     )

execute_forced_edit(static_instance, private_source)
  -> parser/Verus/Lynette result + verifier delta
```

- Build：两步都可运行，forced result 进入 Template evidence。
- Evaluation decision 前：只由 data steward 运行 `instantiate_static`，方法只看到 public non-outcome features 与 static audit；禁止运行、缓存或泄露 Verus delta。
- 所有方法提交 `ADMIT/REJECT/UNKNOWN` 后：才运行 Evaluation exposure；forced execution 仅作 post-hoc mechanism analysis，不回流 decision。
- `locality_valid` 是静态 diff-region property；`Lynette fidelity-valid` 属于 execution result，decision 前不可见。Evaluation static incompatibility 只基于 symbol/type/ghost/locality，不基于 outcome。

### 2. Frozen exposure label without artificial pairing

每个 checkpoint-template pair 的 core 与 exposure 各运行 3 个独立 replicates，condition/run order 在 pair 内随机。令 `S_core`、`S_exposure` 为各自 Lynette-valid Verus success count：

- `BENEFICIAL` iff `S_exposure ≥ 2` 且 `S_core ≤ 1`。
- `HARMFUL` iff `S_core ≥ 2` 且 `S_exposure ≤ 1`，或 exposure 独有的同类 fidelity-invalid terminal 在 ≥2 replicates 重复。
- `INCONCLUSIVE` otherwise。

不使用“某个 seed 从失败变成功”的措辞。若 provider 不支持 seed，三次只是独立重复；随机化顺序和时间 block 被记录。Cost 仅在 hard label inconclusive 且两组 success count 相同的 pair 上按 ±15% ROPE 作次要描述。

### 3. Frozen selective coverage gate

- `decisive coverage = (#ADMIT + #REJECT) / #eligible Evaluation pairs`。
- Primary claim 只有在 decisive coverage ≥40% 时才允许检验。
- coverage <40%：方法判为 **non-deployable / claim fail**，无论 false-admission 多低。
- 同时报告 selective risk–coverage table at fixed cut points 40/60/80%，但不在 Evaluation 后选择 operating point。
- `UNKNOWN` 永不重编码为正确 reject。

### 4. Resource accounting and equal-budget envelope

每个方法分别记录四个预算轴：

| Budget axis | Primary constraint |
|---|---|
| Actor rollouts | Build 与 Evaluation 的完整 agent rollouts 数相同 |
| API/model work | 同 actor/model，报告 input/output tokens、requests、USD；主比较使用相同 request/token cap |
| Verifier work | 分开报告 Verus/Lynette invocations 与 CPU seconds；V-FACE 的额外 forced checks不得隐藏 |
| Wall time | 报告 end-to-end 与可并行 critical-path time |

主公平性约束是相同 actor-rollout 与 API envelope。CPU verifier overhead 作为 method cost 显式报告，不用“一次 replay call”等同一次 agent rollout。CAR-like baseline 若消耗更多 roll-forward，只能在相同 actor envelope 内减少其他 replay；V-FACE 不能把 CPU checks 换算成免费 LLM calls。

### 5. Final frozen admission rule

Build support、harm 与 forced validity 条件沿用 Round 2：少于 8 valid instantiations/4 tasks 为 UNKNOWN；稳定 forced/exposure harm 为 REJECT；全 Build fidelity-valid、至少两个 forced improve、零 worsen、至少一个 exposure BENEFICIAL、零 HARMFUL 且 Evaluation static trigger exact-match 才 ADMIT。Evaluation 的 forced delta 与 Lynette execution result不进入 decision。

## Final Thesis and Boundary

**Thesis**: V-FACE tests whether a frozen typed proof-artifact template can use Build-only executable evidence to make non-degenerate, prospective exposure-admission decisions on unseen Verus checkpoints more safely than budget-matched observational or generic trajectory replay.

这是一个可证伪的 formal-skill evaluation/admission protocol。它不是新的 retrieval paradigm；若 compiler gate、40% coverage 或 equal-budget prospective comparison任一失败，就报告 negative audit，不升级成 optimizer claim。

## Status

**Design-frozen for Phase 0; empirical verdict REVISE.** 不再增加模块或修改阈值。下一步只能是 inventory/contamination audit 与 30-checkpoint compiler gate。
