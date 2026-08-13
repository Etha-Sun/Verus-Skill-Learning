# SkillOpt Pro Reanalysis And Retrieval Audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-08-11T20:49:30-05:00`
- status: `complete`

## Objective

用 `deepseek-v4-pro` 复盘 robust v5 已保存的 40 条训练轨迹，判断更强且不受
人工 output-token cap 限制的 optimizer 能否生成可进入 live gate 的 compact
skill；同时核对 SkillOpt 是否已有可复用的 retrieval 机制。此轮不运行新的 target
task，不打开 held-out test。

## Role And Harness Correction

本地 launcher 原先在 `train.py` 中把 optimizer 和 target 都硬编码为
`deepseek-v4-flash`，因此只改 YAML 的 optimizer model 不会生效。现已按配置分别
传入两个角色，并加入测试。离线复盘工具把 Pro output cap 设置为 provider 最大的
384K，保存 request hash、finish reason、reasoning/content usage 和按 cache
miss/hit 分开的费用估算。

## Pro Results

v1 两次 Pro 调用使用 118,424 prompt 和 3,487 completion tokens，估算
USD 0.054548。它自行以 `stop` 结束，没有接近 384K cap，但 appendix 被错误地
序列化为 Python list 文本，并错误禁止使用原任务中已有的 trusted helper，故作废。

加入 immutable benchmark contract、list normalization 和 trusted-context lint 后，
v2 两次调用使用 120,165 prompt 和 6,642 completion tokens，估算
USD 0.058050，生成 1,646-byte compact candidate。人工 evidence audit 仍发现 Pro
把一个真实结果为 `Verus=false, Lynette=true` 的轨迹归因为 Lynette rejection，
并从单一失败轨迹推广出递归展开限制。该事实矛盾已转化为 deterministic
evidence-label check；20/20 tests、compileall 和 targeted mypy 通过。

v2 candidate 在任何 target gate 前被拒绝。扩大 optimizer token budget 改善了
长度和表面 contract consistency，但没有消除错误因果归纳；384K cap 不是本轮
optimizer 的瓶颈。

## Retrieval Boundary

SkillOpt research engine 没有 runtime retrieval。trainer 把整个
`current_skill` 直接交给每个 target rollout，candidate selection 也同样传入完整
skill。

SkillOpt-Sleep 有 `recall_k`，但它只在 nightly consolidation 时，把新任务和历史
任务的 `intent` 分词后计算 max Jaccard，召回 top-k 历史任务作为额外 train
material；默认值为 0。后续 replay 仍把完整 `skill + memory` 交给 backend。
`skill_hint` grouping 和本地 `SKILL.md` name resolution 也不是语义 proof-state
retrieval。

因此，上游可复用的是一个简单 training-time experience recall baseline，而不是
当前研究需要的 error/proof-state-conditioned clause/card retrieval。

## Decision

不运行 v2 candidate 的 20-task gate，也不继续原配置 epoch 2。下一最小实验应：

1. 保持 838-byte seed 固定；
2. 只保存 verifier-label 和 replay 支持的 typed atomic cards；
3. 在每个有效 Verus checkpoint 按 error/action family、scope/type/mode 和结构锚点
   做 top-1 retrieval，不满足阈值时 abstain；
4. Pro 只负责离线 card proposal/critique，host 做 label、contract、support 和
   replay gate；
5. 先做 card-level shadow replay，再申请 live paired target gate。

这一路线直接针对 v5 的 12.3x global-skill bloat、规则冲突和无关指令干扰；不能把
整个 card bank 再拼回全局 prompt。

## Cost And Safety

两版 Pro 复盘合计估算 USD 0.112598。加上此前 budget ledger 的
USD 8.930733 measured prior-plus-target spend 和 v5 optimizer 的 USD 0.035122，
当前可确认估算总额约 USD 9.078453，低于用户要求的 USD 20 审批线。另有
USD 8.005400 interrupted-call worst-case exposure 尚未确认为 provider charge；即使
保守相加也约 USD 17.083853，仍低于审批线。

所有新模型输出写在 `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/`。原始数据和 sealed
数据保持只读；没有修改、移动、重命名、复制或提交 raw/sealed 数据，也没有运行
新的 target rollout。

## Artifacts

- `skillopt-verusage/src/skillopt_verusage/pro_reanalysis.py`
- `skillopt-verusage/src/skillopt_verusage/train.py`
- `skillopt-verusage/tests/test_pro_reanalysis.py`
- `skillopt-verusage/refine-logs/EXPERIMENT_PLAN_20260811_204930.md`
- `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER_20260811_204930.md`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-reanalysis-v1-20260811/`
- `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-pro-reanalysis-v2-20260811/`
