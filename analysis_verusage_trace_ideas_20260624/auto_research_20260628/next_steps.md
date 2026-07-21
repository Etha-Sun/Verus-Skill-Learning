# 下一步自动化科研计划

## 1. 研究主张

推荐把项目写成：

> Verusage-specific trace memory and verifier-grounded control for efficient LLM proof repair.

中文解释：

> 针对 Verus proof repair agent 的历史轨迹，蒸馏可复用 proof skeleton、检测 verifier-grounded 重复循环，并按项目族压缩上下文，从而在不训练模型或少量 test-time rerun 的条件下降低 token、提升 repair 成功率。

## 2. 第一优先级：把 gate 从 stop 改成 reroute

不要直接 early-stop，因为 threshold 8 仍有 3.02% verified false-stop。更好的策略：

1. 检测到同一 `(error, action)` 出现 8 次。
2. 不再用同一 action family。
3. 触发以下之一：
   - 检索相似成功 skeleton；
   - 切换到 lemma/dependency repair；
   - 缩短上下文，只保留当前错误、accepted diff、相关 lemma；
   - 要求模型输出 “为什么前 8 次失败” 后再 patch。

离线可先做 counterfactual ranking：在 threshold 8 触发点，统计同 task 其他模型成功 trace 的下一步 action，学习一个 reroute action prior。

## 3. 第二优先级：构建 proof skeleton cache

cache key 不应只用文件名。建议特征：

- project id：`AC/NR/OS/...`
- file token：函数名、模块名、lemma 名；
- Verus error sequence prefix；
- accepted action sequence；
- preprocessing 里的 lemmas/recursive/opaque functions；
- diff 文件名中的 success action：`fix-v*-success-*.rs`。

cache value：

- action skeleton：例如 `postcondition_repair -> case_analysis -> uselemma -> reveal_with_fuel`
- proof motif：assert/forall/reveal/calc/induction/bitvector
- compact patch snippet：从 success diff 中抽象变量名后的模板。

第一版不需要 LLM：先做 retrieval report，证明 query 失败 trace 能检索到同项目、同 action motif 的成功 trace。

## 4. 第三优先级：AC/NR/OS context compaction

从 prompt audit 看，AC/NR/OS 是最该优化的项目族。建议先做 AC：

- AC prompt mean bytes 在失败/timeout 中接近 170k-188k；
- over_100k prompt 数量远高于其他项目；
- verified 率也低，说明上下文大不等于成功。

可做的离线分析：

1. 对 AC prompt 做 section-level fingerprint，找重复 boilerplate。
2. 比较 verified vs failed prompts 的高频块，删除失败中高频但成功无贡献的块。
3. 建一个 static compaction rule：保留 target function、error span、referenced lemmas、accepted diffs，删除重复 full-file boilerplate。

## 5. 最小可运行实验（不需要外部 API）

可以继续用本地 Codex 自动做以下实验：

1. `reroute_prior.csv`：在 gate 触发点，用其他模型成功 trace 估计下一步 action prior。已完成初版：`outputs/reroute_prior_threshold8.csv`。
2. `skeleton_cache.jsonl`：为每个 verified trace 抽取 action skeleton 和 lemma signature。已完成初版：`outputs/skeleton_cache.jsonl`。
3. `prompt_block_audit.csv`：按 project/status 抽取 prompt 重复块，估计可压缩比例。
4. `paper_table.md`：把 gate、coverage、prompt、reroute 四个表格整理成 paper-style evidence。

新增一条更贴近 Kexin 建议的支线：

5. `verus_tla_motif_audit.csv`：只看 AL/TLA-style tasks，统计 `always/leads_to/weak_fairness/tla_forall/init_invariant` 等 motif 对应的 action sequence、错误循环和跨模型成功 skeleton。
6. `verus_tla_rule_sketch.md`：把 AgentSpec-style runtime rule 改写成 Verus/TLA proof agent rule，例如 “连续 N 次 `leads_to`/`always` 相关 assert 失败后，强制调用 `wf1/leads_to_trans/or_leads_to/tla_forall_apply` skeleton retrieval”。

## 6. 需要真实 rerun 时的最小实验

如果后面允许本地模型/Verus rerun，建议只跑很小的切片：

- 选 OS/AC/NR 中 threshold 8 会触发的 20 个失败任务；
- baseline：原始 agent；
- variant A：threshold-8 reroute to skeleton retrieval；
- variant B：variant A + project-aware prompt compaction；
- 指标：verified count、total tokens、attempts、timeout rate。

不要一开始跑全量。先证明 20-task slice 有 token/成功率趋势，再扩大。

## 7. Paper 叙事结构草案

1. Motivation：LLM proof repair 在 Verusage 上不是单纯模型能力问题，大量成本来自 verifier-grounded 重复循环和上下文膨胀。
2. Related position：Lean4Agent/AgentSpec 证明了 agent workflow/specification 方向很热，但它们仍然需要一个 grounded downstream task；Verusage/Verus/TLA proof repair 提供这个落点。
3. Observation：2,996 条 traces 显示 non-verified tasks 中重复 `(error, action)` 循环普遍存在；AC/NR/OS 是主要 token sink；AL/TLA-style tasks 则适合作为 temporal proof skeleton case study。
4. Method：Verifier-grounded trace memory，包括 repetition reroute、skeleton retrieval、project-aware context compaction，以及可选的 verus-tla temporal motif rule。
5. Evaluation：offline replay + small rerun，报告 token reduction、success improvement、false-stop avoidance、project breakdown。
6. Analysis：为什么 Verusage 适合这件事；与 Lean4Agent/AgentSpec 的泛化 agent verification 区分。
