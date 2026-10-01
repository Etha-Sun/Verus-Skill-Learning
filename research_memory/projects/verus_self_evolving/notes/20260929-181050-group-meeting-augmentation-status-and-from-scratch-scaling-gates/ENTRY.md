# Group meeting: augmentation progress and from-scratch scaling gates

## Status and user correction

Reviewed summary and proposed experiments, not a new run authorization.
The user clarified that checkpoint continuation is an augmentation mechanism.
The primary downstream evaluation must start from the original unsolved task,
with frozen train-derived skills/cards and no checkpoint, future hint or answer.
The completed 18-run checkpoint study is auxiliary mechanism evidence only.
This correction supersedes any older next-action text prioritizing additional
checkpoint-local utility tests as the main evaluation.

## Meeting summary

工程可行性已有证据；augmentation 相对 ordinary extraction 的下游增益尚未证明。
研究假设是：受控改变训练题表示或解题分支，可以提供原始轨迹中缺失的可验证
经历，从中提取带 Trigger / Action / Why / Validate / Avoid-when 的 card，
最终改善未参与提炼任务上的 from-scratch 解题。

### Hint route: completed

- IR/AC/AL 三个 train task，19 个 checkpoint；38 条历史 v1/v2 hint
  continuation、19 条 no-hint continuation，以及三条完整 original 已恢复。
  v1/v2 各 18/19 双通过；no-hint 19/19，但存在历史工具链差异，不能当作
  净 hint 效应。独立 source task 仍只有三个。
- 原 prefix、分岔点、hint 和 suffix 可组织成完整证据包；标注 actor 当时
  实际可见内容。拼接给分析器看的完整 trace 不代表续写 actor 看过原对话。
- 同题分组提卡、合并完整分支证据和结构化卡库已打通。最近冻结的卡库为
  original-only 六张、augmented 五张；Astra 已审阅。
- 三道 validation 题、两条件共六次 from-scratch 检索试跑：各成功一题，
  各两次超时，尚无增益。检索弱相关、不检索及绕过工具读全库均有记录。
- 随后的 18 次局部诊断全部双通过，卡能帮助避免部分绕路，但 augmented
  没有证明优于 original。一个无卡样本有过程违规；所有记录和费用保留。
  这些局部结果不代表完整解题效率。
- 用户提供的 train-40 stage1 skill 目前仅作为内容参考，未完成与本轮卡库
  的公平大规模下游比较。

### Obfuscation route: separate branch, newer than old main-branch audit

Read-only cross-branch audit found implemented certified Boolean abstraction at
`feat/obfuscation-certified-predicates`, commit `2ec5b86`.
The earlier main-branch note saying no obfuscation implementation was found is
outdated. Method: `obfuscation-verusage/BOOLEAN_REWRITES.md` on that branch.
The worktree was clean and no branch switch or merge was performed.

- 初始原型：AST 内 P ==> Q 改为 !P || Q，并验证独立规则证书。
- 当前实现：固定业务谓词原子，改写整个共享 Boolean spec 函数的组合形式。
  可生成分支展开/重排，也支持受限 JSON 提案；现有 pilot 未调用 LLM。
- 准入包括结构重建、原子真值等价、原作用域 bool 类型见证，以及 clean、
  type witness、独立等价证书、transformed endpoint 四项 Verus 检查。
  不等同于任意 Rust 程序的通用等价证明。
- 已在 4,863 行 AC endpoint 连续改写三个共享谓词并通过全部检查；该分支
  记录 15 Rust、13 Python 测试通过。本次审计未重新运行这些测试。
- 当前 Boolean 子集库存：AC 10/12 文件有候选（64 sites），AL 0/14，
  IR 1/14（1 site）。这是可选位置统计，不是所有 variant 已获验证准入。
- 未测 normalized VC/trigger 变化、证明难度、actor 解题或提卡收益；
  training task 导出和 proof stripping 尚未实现。4,863 行不等于困难证明。
- 广义词法 rename/control、更一般的量词/时序改写、组合方法仍是后续路线，
  不得描述为都已完成。词法改名需正确名称解析，不能用文本替换冒充。

## Proposed experiment routes

### Hint

1. 将独立训练题从三个扩到约 10–15 个，覆盖真实证明失败、长绕路及不同项目；
   这是建议规模，尚未启动。每题先选少量不同状态的 checkpoint，避免同题大量
   近重复成功充当数据规模。现有选择器按事件/源码状态，不是 progress-aware。
2. 在匹配模型、工具链、预算下生成 hint 和额外 no-hint 采样；保留失败和反例。
   Teacher 可用 train 的 hindsight，评测 actor 只能用冻结 train-derived cards。
3. 完整拼接、标注分岔和可见性，同题分组分析并控制每题总权重。冻结提取器、
   输出格式、卡片提供预算，保留 Trigger/Action/Why/Validate/Avoid-when 和证据。
4. 在 validation 上 from scratch 比较冻结产物；完整过程计费和评分。
   v1/v2 是同一路线的提示版本，不是两类 augmentation。

### Obfuscation

1. 从当前可处理的 AC/少量 IR train 题选实际依赖被改写谓词的目标；保留
   clean / lexical cue control（实现后）/ certified structural variant 对照。
2. 保持等价证书和完整证明对 actor 隐藏，从复制的已验证变体剥离目标证明，
   导出新的无答案训练任务。观察 VC、实际 proof strategy 和工具反馈变化。
3. 对 clean/变体进行匹配的 from-scratch 训练轨迹采样，核查有无新增信息，
   避免只积累 SMT 规范化后等同或对目标无关的文本变化。
4. 通过质量检查的轨迹进入同一提卡流程；最终同样在未参与提炼的任务上
   from scratch 验证 utility。更广泛量词/时序/extensional 改写另立证书范围。

## Shared downstream evaluation and scale gates

Primary matched conditions should separate original-only extraction, extra
unguided samples, hint augmentation and certified obfuscation. Stage these
conditions as inputs become ready rather than requiring all arms immediately.
An ordinary SkillOpt full-skill baseline is also useful, but changing format,
extractor and data together does not isolate the contribution of augmentation.
Use matched source tasks, actor/toolchain/budget, extractor/format, and card
exposure budget; record both task weighting and offline construction expense.

All deployment evaluations start from scratch. Use validation for method
selection, freeze artifacts before final test; do not tune using test answers.
Report budgeted dual-verifier solve rate, paired gains/regressions, input/output
usage, wall time, timeouts and cost for all attempts. Report successful-run costs
alongside failure rates, not as a replacement. Offline teacher/rollout/extraction
cost and online solve/retrieval cost are separate. Retrieval must log actual
exposure and prevent direct whole-bank reads if its budget is claimed enforced.
A shared simple fixed card exposure can first isolate data utility; retrieval
can then be varied independently, with both evaluations still from scratch.

建议扩量门槛：同预算成功率出现可重复提升，或成功率保持时完整解题成本稳定下降；
同时排除数据泄露、提取格式差异、卡片暴露不一致及仅多采样带来的解释。
达到后从中等训练规模扩至 train-40，再扩大变体数和检索卡库。不要把 variant
数量、hint 续写成功率、合成边界通过率当作下游 scale-up 成功标准。

## Meeting decisions to discuss

- 是否认可“受控训练经历带来可迁移决策知识”作为核心研究假设？
- 是否同意先完成 hint 的公平 from-scratch 对照，同时让 obfs 完成 paired
  trajectory feasibility，而后合入同一学习与评测流程？
- 以何种成功率/完整成本证据和可承受预算作为扩大到 train-40 的门槛？

## Pointers and safety

Hint publication: `docs/hint-augmentation-20260916/README.md` and
`INFORMATION_VALUE_AUDIT.md` (historical publication status statements should
be read with newer canonical memory).
External summaries: `skillopt-retrieval-pilot-20260926/ANALYSIS.md` and
`skillopt-card-case-study-20260926/ANALYSIS.md`.
Obfs reviewed record on its branch:
`research_memory/projects/verus_self_evolving/experiments/20260922-203758-certified-boolean-abstraction-for-shared-verusage-predicates/ENTRY.md`.

This pass read existing evidence and wrote only reviewed compact research memory.
No API call, experiment, GPU job, source transformation, git merge or raw/sealed
modification occurred. No full trace, credential, token table or personal path
was added to repository memory. The no-local-GPU constraint remains active.

## Follow-up: ExVerus admission versus the certified extension

The user recalls that ExVerus obfuscation admits a rewritten verified program
when Verus passes, with the original program/proof as generation and repair
guidance; strict pairwise semantic equivalence is not separately established.
Rechecked Appendix E of https://arxiv.org/html/2603.25810v2: it describes LLM
generation of verified/unverified variants and repair using errors plus the
original proof. No per-pair equivalence certificate is reported there. This is
a boundary of the documented method, not evidence that all variants drift.

The current certified Boolean branch adds a stricter design requirement beyond
that ExVerus workflow. It should not be described as required merely to create
useful synthetic training tasks. A proposed simpler baseline is LLM rewritten
code plus a verified reference proof, followed by proof hiding/removal and fresh
actor solution trajectories. Label these as verifier-accepted synthetic tasks
unless equivalence is separately established. Keep certified rewriting as a
controlled alternative; do not silently remove the existing branch's admission
checks. This is a recommendation under discussion, not authorization or an
implemented change. No experiment or raw-data mutation occurred.

## Follow-up: SkillOpt as the main learning pipeline

The user identifies SkillOpt and Trace2Skill as principal comparison pipelines,
and prefers building the augmentation method on SkillOpt. Local pinned code
and fixed80 configs were inspected: each fast step runs train rollout, minibatch
reflection, proposal aggregation, edit ranking/budget, candidate update and a
selection gate. Fast update repeats across steps and epochs. The fixed80 E1
config has train_size=batch_size=40, reflection minibatch_size=8, learning_rate=4,
min_learning_rate=2, cosine scheduler and patch updates. Learning rate bounds
selected edit operations, not model-weight updates or total bank cardinality.

Optional slow update injects only an empty protected block in epoch 1. From
epoch 2 it samples train items (20 in this config), freshly runs prior/current
epoch skills on the same items, analyzes improvement/regression/persistent
failure/stable success and proposes protected slow guidance. Our config gates
that candidate on selection too; meta-skill is disabled. Subsequent epochs
reuse train tasks with the retained skill. Final test is separate.

Recent augmentation work reused reflect/merge for offline card extraction and
small separate deployment diagnostics; it did not complete a new multi-epoch
SkillOpt optimization run. The evidence-bank profile removes the old final
four-edit clipping step, which is a method change rather than native behavior.
Recommended attribution design: first compare original versus augmented train
evidence under matched extraction/update/gate settings; separately measure
changes to task grouping, card-bank format, edit budget and retrieval. No new
training, config change or data mutation was performed in this clarification.

### Reflection minibatch clarification

Verified pinned reflect.py and analyst prompts: baseline partitions successes
and failures first, seeded-shuffles each pool, then groups at most eight traces.
All analysts see the same current skill and their group's trajectories, propose
common generalizable gaps/patterns, and output structured patches. Each group's
proposal cap is the adapter edit_budget (4 here), including possible zero edits;
this is separate from the scheduled final step cap. Failure patches and success
patches are merged separately, then combined with failure priority, deduplication
and conflict handling, before final top-L selection. Group outputs do not each
update the skill. Final merge primarily sees current skill and patch reasoning,
not every original trace. Native output is a skill-edit patch, not a mandated
Trigger/Action/Why card. Grouped fork-card extraction deliberately changes the
evidence unit so same-task positive/negative branches remain together.
