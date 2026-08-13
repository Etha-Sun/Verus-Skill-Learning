# Weekly Research Update: SkillOpt on VeruSAGE

Period: 2026-08-10 to 2026-08-12

## Copy-Ready Text Update

本周完成了 SkillOpt 在 VeruSAGE 上的首个可靠单轮复现和两次 stronger-optimizer
诊断。修正后的 DeepSeek-V4-Flash harness 采用 60-worker pool，并按 phase 实际运行
20/40/20 并发；80 个任务 ledger 全部完成，长度截断和空响应均被显式拒绝并恢复，
没有 silent truncation、invalid task 或 task requeue。初始 838-byte skill 在 frozen
selection set 上为 6/20，40 个训练 rollout 为 8/40，Flash optimizer 生成的
10,322-byte candidate 为 4/20，因此被 gate 拒绝。

失败分析表明，Flash candidate 不只是“没有帮助”：它把一个正确训练轨迹错误概括
成 false `fold_left` identity，并把原任务中已有的 trusted helper 错误视为违规；skill
同时膨胀 12.3 倍，使 candidate gate 相比初始 skill 增加了搜索和 prompt 成本。因此
不能直接继续 epoch 2。

随后用 DeepSeek-V4-Pro 对已保存的 40 条训练轨迹做了两轮离线复盘，不增加 target
rollout。Pro 生成的 skill 更短，但仍出现 evidence attribution 和单轨迹过度泛化，
两版 candidate 都在 live gate 前被拒绝；这也说明 optimizer output-token cap 不是
主要瓶颈。源码审计同时确认：主 SkillOpt workflow 没有 runtime retrieval，
SkillOpt-Sleep 的 `recall_k` 只是 nightly training-time task-intent Jaccard recall，
不是 proof-state-conditioned retrieval。

最后，将 optimizer 换成本地 Codex GPT-5.6 Sol，并严格复用原生 SkillOpt 的
reflection、merge、ranking 和 patch-application。8 次 optimizer 调用生成了通过自动
和人工 contract audit 的 3,490-byte candidate，但在同一 frozen 20-task Flash gate
上仍为 4/20，对比 S0 的 6/20，没有新增 solve、出现两个 pass-to-fail，因此再次拒绝。
这说明 stronger optimizer 修复了明显的语义和长度问题，但不足以让 monolithic
global skill 有效。

当前 validation-best 仍是 838-byte S0。没有运行 epoch 2，也没有打开 40-task
held-out test。下一步应先做同一 S0 的 A/A 重复来估计 Flash 随机波动，再测试带
abstention 的 typed、replay-supported、proof-state-conditioned top-1 retrieval
cards，而不是继续扩写全局 skill。

## Key Numbers

| Milestone | Result | Usage / Cost | Decision |
|---|---|---|---|
| Robust Flash epoch 1 | S0 6/20; train 8/40; candidate 4/20 | 4,184 target requests; 35.528M prompt + 14.403M completion; target + optimizer USD 5.232176 | Reject candidate |
| Flash failure audit | 14 fail-to-fail, 0 fail-to-pass, 2 pass-to-fail, 4 pass-to-pass | Candidate grew from 838 to 10,322 bytes | Do not run epoch 2 unchanged |
| Pro offline reanalysis | v1 invalid; v2 rejected before target gate | 4 calls across two versions; USD 0.112598 | Token cap was not the bottleneck |
| GPT-5.6 Sol native replay | Audit-clean 3,490-byte candidate; gate 4/20 vs. S0 6/20 | 8 local-quota optimizer calls; Flash gate USD 2.022979 | Reject candidate |

The three principal completed components above used an estimated USD 7.367753
of metered DeepSeek spend. The broader SkillOpt workstream's confirmed estimated
spend is USD 11.101432. Including USD 8.005400 of earlier interrupted-call
worst-case exposure gives a conservative USD 19.106832; the interrupted amount
is not a confirmed provider charge. Both totals remain below the user's USD 20
approval threshold.

## Evidence Boundary

- This is a valid negative selection result, not held-out-test evidence.
- There was no fresh S0 A/A repeat, so target stochasticity remains a causal
  confounder for the two paired regressions.
- No claim is made that SkillOpt generally fails, or that retrieval cards will
  improve solved rate.
- Raw and sealed datasets remained read-only. Complete traces, workspaces, and
  per-call cost ledgers stayed below `${VERUS_SKILL_RUN_ROOT}`.

## GitHub Publication Audit

结论：本周没有在关键节点分批 commit，也没有把本周 SkillOpt 工作 push 到 GitHub。

- GitHub `main` 当前最新 commit 是 `deefdab` (`Migrate full hands-off log
  fidelity audit`)，GitHub 时间为 2026-07-26 UTC。
- 本地 `main` 为 `1071cac`，相对 `origin/main` ahead 2；这两个尚未发布的本地
  commit 都来自 2026-07-26，分别是 `2c85643 Add isolated skill evolution
  pilot` 和 `1071cac Add audited Qwen agentic runner`。
- `git log` 在 2026-08-10 至 2026-08-12 之间没有 commit。
- 父仓库目前将整个 `skillopt-verusage/` 视为 untracked；本周三条 SkillOpt
  research-memory entry 也仍未跟踪，`CURRENT.md` 和 `INDEX.md` 有未提交改动。
- 当前工作树混有大量更早的已修改和未跟踪文件，不能安全地做一个笼统的
  `git add .` 或单次大 commit。
- 当前普通 `.git/` 为空，历史 Git 元数据位于 `.git_disabled/`；本次审计只用
  read-only `--git-dir=.git_disabled --work-tree=.`。在正式 commit 前需要先确认并
  恢复 canonical Git 元数据布局。

本轮只做了只读 Git/GitHub 审计；“有没有 commit”不视为创建 branch、stage、commit
或 push 的授权，因此没有执行这些写操作。

## Recommended Commit Boundaries

在用户明确授权并确认 mixed worktree 范围后，建议从新 feature branch 按以下节点
补做 commits；每批只 stage 显式路径，不包含 raw run、secret、`.env`、`.aris/`、
`.git_disabled/` 或上游 `skillopt-verusage/SkillOpt/`：

1. `skillopt: add VeruSAGE integration (milestone 2026-08-06)`
   - adapter、proxy、runner、config 和 model-free tests。
2. `skillopt: harden DeepSeek runner and record epoch 1 (milestone 2026-08-10)`
   - reviewed tracker/README、compact result and failure-analysis memory；不包含完整
     run directory。
3. `skillopt: add Pro optimizer audit and evidence checks (milestone 2026-08-11)`
   - optimizer/target role separation、Pro offline analyzer、deterministic evidence
     lints 和 tests。
4. `skillopt: add native Codex replay and gate (milestone 2026-08-12)`
   - native replay/gate code、tests、GPT-5.6 Sol compact result、weekly closeout and
     rebuilt memory index。

每个 commit body 应使用以下字段，避免把补做 commit 的当前时间误写成实验完成时间：

```text
Milestone completed: YYYY-MM-DD HH:MM:SS America/Chicago
Committed at: <Git records this automatically>
Work completed: <concrete implementation, validation, or experiment result>
Evidence: <reviewed repository paths and external run pointer>
Validation: <tests, integrity checks, and claim boundary>
Data safety: no raw/sealed data or complete run directories committed
```

如果 durable artifact 没有可靠的秒级完成时间，则只写可证实的日期，不根据文件
mtime 猜测时间。Git author/committer date 保持实际补做 commit 的时间，不 backdate；
原里程碑时间记录在 message body 中。

## Durable Pointers

- Robust epoch: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/deepseek-v4-flash-e1-corrected-v5-20260810/`
- GPT-5.6 Sol replay: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/codex-gpt56sol-reopt-v5-20260811/`
- Experiment tracker: `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`
- GPT-5.6 Sol memory: `research_memory/projects/verus_self_evolving/experiments/20260812-000000-skillopt-gpt56sol-native-replay/ENTRY.md`
