# Verusage Trace Ideas 中文导读

这个目录是我对当前文件夹里 agent trajectories / traces / batch results 做的独立分析，所有新文件都放在：

`analysis_verusage_trace_ideas_20260624/`

没有改动原始 `result-*`、`all_batch_results-*`、`claude_sonnet_gpt5/` 数据。

## 建议阅读顺序

如果你只想快速知道我做了什么，按下面顺序读：

1. `README.md`
   - 最短总览。
   - 说明这次分析的目标、主结论、目录结构。

2. `trace_audit.md`
   - 信息量最高。
   - 这里记录了我从本地 traces 中抽到的关键统计和失败模式。
   - 包括 token 消耗、不同模型/项目成功率、重复 action loop、跨模型同题分歧。

3. `selected_idea.md`
   - 最终推荐方向。
   - 重点是 `trace-distilled proof skeleton cache + repetition gate`。
   - 里面写了机制、验证方式、成功标准、失败条件。

4. `candidates.md`
   - 如果你想看我为什么选这个方向，而不是其他方向，读这个。
   - 里面有候选 idea、筛选标准、被推迟/拒绝的方向。

5. `tables/`
   - 如果你想自己复核数字，读这些 CSV。
   - 最有用的是：
     - `model_project_20min_summary.csv`
     - `top_100_cross_model_disagreements.csv`
     - `log_loop_summary.csv`

## 我做了什么

我主要做了四件事：

1. 盘点当前结果目录结构
   - 发现这里不是源码仓库，而是结果仓库。
   - 主要数据来自：
     - `result-*`：早期多 agent/candidate/patch/action summary。
     - `all_batch_results-*`：后期更完整的 prompt、output、reasoning、repair log、token 统计。
     - `claude_sonnet_gpt5/`：跨模型结果和额外统计。

2. 做只读统计
   - 汇总了 `*_analysis_results.csv`。
   - 汇总了 `*_action_counts.csv`。
   - 解析了 `all_batch_results-*/all_results_with_breakdown_20min.csv`。
   - 解析了 2,996 个 `verus-repair.log`。

3. 抽样看具体失败轨迹
   - 特别看了高 token 失败样本。
   - 重点看了跨模型分歧样本：同一个 Verusage 文件，一个模型成功，另一个模型烧很多 token 失败。
   - 看了 prompt、reasoning、repair log，确认失败不是单纯题目难，而是存在重复 action loop 和 proof-plan 迁移不足。

4. 收敛成一个可执行 idea
   - 推荐方向不是“再加一个 generic repair action”。
   - 推荐做一个 Verusage-specific controller/data 方向：
     - 从成功 traces 蒸馏 proof skeleton。
     - 从失败 traces 提取 repeated-loop negative signal。
     - 修复时优先检索 skeleton。
     - 如果同一 error/action 重复失败，就 gate 掉，不继续烧大 prompt。

## 最核心发现

### 1. 失败比成功贵很多

在 20min batch 结果里，失败样本平均 token 明显高于成功样本：

- `claude`: verified 平均约 111k tokens，non-verified 平均约 1.01M tokens。
- `claude-s4`: verified 平均约 126k，non-verified 约 999k。
- `gpt5`: verified 平均约 64k，non-verified 约 256k。
- `o4mini`: verified 平均约 108k，non-verified 约 558k。

所以降低 token 的关键不是只压 output，而是避免高成本失败循环。

### 2. AC / NR / OS 是主要瓶颈

`AC`、`NR`、`OS` 项目消耗最多 token，成功率也低。  
`NO`、`MA`、`AL`、`VE` 相对容易。

这说明 Verusage 不能所有项目用同一种 prompt/context/action policy。  
应该按 project family 做不同策略。

### 3. 很多失败是重复 action loop

我解析的 2,996 个 `verus-repair.log` 中：

- `AssertFail` 是最常见 target error。
- `PostCondFail` 第二常见。
- 1,010 个 logs 中，同一个 primary action 至少重复 8 次。

典型模式：

- `postcondition_repair` 修掉 postcondition，但引入新的 assertion，然后反复卡在 `AssertFail`。
- `seqsetmap` 在 OS linked-list helper 上反复调用。
- `instantiate_forall` 在 AL temporal lemma 上反复调用。
- `uselemma` 在 NR alignment/bitvector 类任务上反复调用。

这非常适合做 repetition gate。

### 4. 跨模型分歧说明存在可迁移 proof plan

很多同一文件上：

- 一个模型几十万 token 验过；
- 另一个模型几百万 token 失败。

这说明“题目本身无解/太难”不是全部原因。  
成功模型的轨迹里有可复用的信息，比如：

- 该用哪些 helper lemma；
- 是否需要 existential witness；
- 是否需要 `leads_to_trans`；
- 是否要拆 postcondition；
- 哪些 action 尝试是无效循环。

所以我推荐把成功轨迹压缩成 proof skeleton cache。

## 最终推荐方向

**Verusage trace-distilled proof skeleton cache + repetition gate**

中文可以理解为：

**从 Verusage 成功/失败轨迹中蒸馏 proof skeleton，并给 agent 加一个重复失败拦截器。**

### 它做什么

对成功 trace 提取：

- project family，比如 `AC` / `NR` / `OS`；
- target function / lemma 名；
- verifier error sequence；
- action sequence；
- 真正用到的 helper lemmas；
- proof shape，比如 `exists-witness`、`leads_to_trans`、`seqsetmap`、`bitvector-bound`；
- 最终 patch 的简短结构摘要。

对失败 trace 提取：

- 哪些 error/action 组合会反复失败；
- 哪些 local repair 会制造后续 assertion loop；
- 哪些 action 在某些项目 family 上低效。

修复新任务时：

- 先检索相似 skeleton；
- 如果同一 error/action 重复失败，禁止继续无脑采样；
- 改走 skeleton-guided generation、diagnosis-only plan、换 action，或者提前停止。

## 为什么我觉得这个最有信息量

它同时解释两个现象：

1. 为什么有些任务 token 巨贵但仍失败：agent 在重复局部修复循环。
2. 为什么同题不同模型差异很大：成功轨迹中有没被复用的 proof structure。

而且它不需要新数据。可以先完全 offline 验证：

- replay 现有 logs，看 gate 能省多少 token；
- 看 gate 是否会误杀真实成功 run；
- 从成功 traces 建 skeleton index；
- 在 heldout high-token failures 上测 top-k skeleton 是否命中真实成功 action/lemma。

## 不建议优先读的文件

- `objective_contract.md`
  - 是形式化目标约束，适合后续写实验计划时看。

- `current_board_packet.md`
  - 是当前状态压缩版，和 `README.md` / `trace_audit.md` 有重叠。

- `literature_survey.md`
  - 只是轻量外部对照，不是这次最核心的证据。

- `pre_idea_drafts/`
  - 是候选 idea 的 challenge memo。
  - 如果你想审查“这个 idea 有没有 hidden assumption”，再看。

## 一句话版本

这批 Verusage traces 最有价值的信息不是单个 patch，而是：  
**哪些 proof route 曾经成功、哪些 action loop 会烧 token 失败。**  
最值得做的是把这些轨迹变成一个 proof-skeleton retrieval + loop gate，让 agent 少重复失败、多复用成功证明结构。

