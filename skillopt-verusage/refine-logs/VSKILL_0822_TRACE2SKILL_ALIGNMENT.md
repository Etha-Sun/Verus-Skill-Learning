# Vskill-0822 Trace2Skill Alignment

日期：2026-08-22

## 结论

本分支选择性迁移了上游 commit
`92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e` 中可复用的 Trace2Skill
执行合同，没有整棵合并实验目录。test-20 的历史数字不会被回写；下一次正式运行必须使用新的
Verus pin、计分合同和 bridge actor isolation，因此它将是一轮新的可比实验，而不是历史 run
的原地续跑。

## 迁移边界

| 上游能力 | 本分支处理 | 原因 |
|---|---|---|
| candidate schedule 与 snapshot lineage | 迁移并本地化 | schedule、M-core、payload、parent/candidate tree 均做 hash 校验；复用现有 held-out gate |
| held-out promotion gate | 复用现有 gate，不复制第二套 policy | 本仓库已有 selection gate；双实现会造成阈值和恢复语义漂移 |
| actor mount/network/seccomp isolation | 迁移并接入 bridge runner | bridge actor 默认外层 isolation，内层 Codex 使用 `danger-full-access`；manifest 记录精确配置 |
| construction/materialization/memories/shared_train | 不整包迁移 | 依赖旧 Skill Evolver tree，并会复制完整 trajectory/raw training artifacts，不符合当前数据边界 |
| provider-specific experiment drivers | 只合并通用合同 | 保留本仓库已审计 bridge；只对齐已确认的 GLM 429 和 actor contract 差异 |

## 为什么同一 test-20 仍会出现 token/time/performance 差异

1. **先前的 correctness 与 trace fidelity 混在一起。** V0 结果即使 final Verus、
   Lynette 和 input safety 通过，也会从 solved 中排除；direct/bridge adapter 还可能只因为
   V0 再付费运行一次。现在 proof correctness、`within_budget`、input safety、V0/V1/V2
   分开记录。V0 只表示 trace 不完整，不再自动否决 proof 或触发 retry。
2. **timeout 的 endpoint 与预算概念不同。** actor 在600秒被停止后，host 仍会独立验证最后的
   `candidate.rs`。如果三项 final check 通过，它应计入 solved；同时
   `within_budget=false`。把 timeout 一律当 failure 会低估 performance，把 host final-check
   时间忽略又会低估 wall time。
3. **GLM reference profile 曾关闭有针对性的 HTTP 429 重试。** bridge 本身已经实现
   `Retry-After`/指数 backoff，但 launcher 只在非 reference profile 打开。现在两个 profile
   都使用12次、1至30秒的 429 backoff；429 不触发扩大 output-token budget。该修复可能增加
   某些成功请求的 wall time，却避免把可恢复限流变成短 trajectory 或失败。
4. **actor sandbox 不同。** 上游是外层只暴露 task/tools/local bridge 的 namespace，内层
   Codex 为 `danger-full-access`；本仓库过去直接使用 `workspace-write`。新 bridge run 已对齐
   上游结构并禁止访问 repository、split、sibling runs 和外网。GPT direct 暂无 local
   bridge，仍明确记录为 non-isolated；这是剩余差异，不应静默宣称完全 parity。
5. **Verus binary 不同会改变搜索反馈和最终分数。** 正式合同现固定为
   `release/0.2025.09.12.bb1f342` / commit
   `bb1f342683fd26de011825725a55325b65e7d359`，而历史 VeruSAGE comparator 是
   `ddc66116`，July binary 又不同。新 evaluator 会在模型调用前检查 binary JSON identity。
   run manifest 另外 hash 真正的 sibling `rust_verify` implementation；只 hash `verus`
   launcher 不够，因为 ddc66116 与 bb1f342 的 launcher bytes 相同。
6. **cached token 是消耗的一部分，不只是价格项。** cache hit 降低计费和部分延迟，但 provider
   仍报告这些 token 作为输入上下文处理量。图中因此用 `cached + uncached = total input` 堆叠；
   output 单独画，reasoning 仅作为 output 子集，绝不重复相加。
7. **ledger scope 不完全相同。** bridge token 总数含 archived/replaced attempts；GPT direct
   当前是 retained Responses usage。比较 provider 间绝对 token 前必须保留此注记。删除 archived
   usage 会低估费用，反过来把 bridge complete ledger 与 GPT retained ledger当成完全同口径也不成立。
8. **仍有运行时方差。** 单次 rollout、provider alias/seed、服务竞争、Qwen BF16 对上游 FP8，
   以及绝对 verifier path 导致的 prompt bytes 差异都可能改变搜索轨迹。对齐代码合同只能消除
   系统性偏差，不能把一次 test-20 变成确定性测量。

## 当前验收结果

- 所有 `skill-evolution-pilot/tests` 与 `skillopt-verusage/tests`：146 passed。
- actor isolation：user/mount namespace、private network relay、capability drop 和 seccomp 的
  model-free end-to-end smoke 通过。
- Verus 9-12 binary identity 精确匹配；两个已知 version-sensitive retained candidate 在
  ddc66116 与 bb1f342 下均为2/2通过。
- token figure 使用 canonical `reference_july` matrix 的12个 `model × condition` rows，
  每个 row 均为 `n=20`；PDF 已经 Ghostscript render 后检查。

## 剩余的正式实验门槛

在任何付费 rerun 前，先运行 `--check-only` 并保存 Verus identity、actor isolation preflight、
split/skill hash 和 bridge manifest。正式结果必须同时报告 solved、timeout-solved、
within-budget-solved、fidelity counts、cached/uncached input、output/reasoning subset 和完整 ledger
口径。单次 test-20 只能作为对齐后的 point estimate，不能直接归因于 skill 文本。
