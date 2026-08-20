# SkillOpt x VeruSAGE

本目录记录将 Microsoft SkillOpt 接入 VeruSAGE repair scaffold 的可行性方案。

## 当前状态

- 上游源码已 clone 到 `SkillOpt/`。
- 固定上游 commit：`9639719632daecacd1baaa47fe781f3c0253600a`。
- 已在 `src/skillopt_verusage/` 实现最小接入层：frozen split loader、
  DeepSeek skill-injection proxy、隔离 VeruSAGE runner、独立 Verus/Lynette
  final judge 和自定义 SkillOpt launcher。
- 已增加 DeepSeek-V4-Flash 单 epoch 配置：20-task selection baseline、40-task
  train rollout、20-task candidate gate；epoch 1 slow update 只写空 placeholder。
- 模型无关验证已通过：24/24 标准库单元测试与 `compileall`。
- robust v5 已完成有效的 40/20 单 epoch：S0 selection 6/20，train 8/40，
  Flash optimizer candidate 4/20，被 gate 拒绝；40-task held-out test 未运行。
- 已复用相同 40 条训练轨迹，以本地 Codex GPT-5.6 Sol 执行原生
  reflect/merge/rank/update。3,490-byte candidate 通过合约审计，但同一 frozen
  Flash selection gate 仍为 4/20，对比 S0 6/20；配对为 0 个新增、2 个回退，
  因而拒绝并继续保留 838-byte S0。
- GPT-5.6 Sol optimizer 使用本地额度：8 calls、246,313 input、11,184 output。
  新 gate 使用 1,627 个 Flash requests、12.925M prompt、5.447M completion，
  成本 USD 2.022979；20/20 为 V2_TRACE，零 silent truncation/invalid/uncertain。
- 完整逐调用账本和原始运行仅位于外部 `${VERUS_SKILL_RUN_ROOT}`。
- `SkillOpt/` 是独立上游 checkout，并被父仓库 `.gitignore` 排除；集成代码应
  放在本目录的 `src/` 和 `tests/` 中，而不是直接修改上游 checkout。

## 主要文件

- `refine-logs/EXPERIMENT_PLAN.md`：claim-driven proposal、接入协议、实验矩阵、
  预算和 stop/go gate。
- `refine-logs/EXPERIMENT_TRACKER.md`：最小可执行顺序。
- `configs/verusage_deepseek_v4_flash_e1.yaml`：本次 40/20 单 epoch 配置。
- `src/skillopt_verusage/`：不修改上游的本地 adapter/runner。
- `src/skillopt_verusage/codex_reoptimize.py`：stored-rollout 到原生 Codex
  optimizer candidate 的断点续跑入口。
- `src/skillopt_verusage/codex_selection_gate.py`：candidate 的 frozen 20-task
  Flash gate、恢复和配对汇总。
- `tests/`：模型无关 guard 和 central skill injection 测试。
- `SkillOpt/`：只用于审计和运行的 Microsoft SkillOpt 上游 checkout。

外部运行指针：

- split：`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/split-100-seed42-20260806`
- robust epoch：`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-flash-e1-corrected-v5-20260810`
- GPT-5.6 Sol replay：`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-gpt56sol-reopt-v5-20260811`
- 成本账本：各 run 目录下的 `cost_ledger.json`

## 数据与输出边界

- 原始数据和 sealed 数据保持只读。
- 完整 VeruSAGE/SkillOpt rollout、prompt、response、token ledger、临时 workspace
  和 split manifest 只能写到 `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/`。
- 本目录只保留代码、测试、配置模板、hash、proposal 和审核后的紧凑摘要。

## GLM API 配置

固定 test-20 launcher 通过 Z.AI 的通用 OpenAI-compatible API 调用 GLM。
把密钥只写入仓库根目录的 `.env`（不要提交）：

```bash
ZAI_API_KEY=your-key
ZAI_BASE_URL=https://api.z.ai/api/paas/v4
SKILLOPT_MODEL_CATALOG_PATH=/absolute/path/to/reviewed/models.json
```

launcher 会把 sourced `.env` 中的密钥显式 export 给 bridge，因此带或不带
`export` 前缀均可。Z.AI 当前公开文档列出的最新文本模型是 `glm-5.1`，而本
实验冻结的是 `glm-5.3`；正式运行前应在账号控制台确认该 ID，或先发一个极小
的 Chat Completion smoke。如果账号不可见，不要在某一个实验 arm 中静默替换
模型。运行命令为：

```bash
skillopt-verusage/scripts/run_s2_fixed_test20.sh glm {blank|s2}
```

远程 API arm 可以在启动时设为 20 个 actor task 并发：

```bash
SKILLOPT_TEST_WORKERS=20 \
  skillopt-verusage/scripts/run_s2_fixed_test20.sh glm {blank|s2}
```

本地 Qwen vLLM 仍使用 `SKILLOPT_TEST_WORKERS=4`，与服务端的
`--max-num-seqs 4` 保持一致。

## 研究边界

本方案的第一阶段只做 Anvil/IronKV effective-train 内的 task-held-out
feasibility gate，不产生跨项目或 sealed-test 主张。R041 仍是当前既定下一步，
R042 尚未完成；本次只运行 selection/train/candidate gate，未运行冻结的 40-task
test，因此不会把该 pilot 伪装成 R042 或 task-held-out 效果证据。
