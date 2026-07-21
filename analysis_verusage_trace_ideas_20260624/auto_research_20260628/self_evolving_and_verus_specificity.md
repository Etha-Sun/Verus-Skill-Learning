# Self-evolving 方法调研与 Verus-specific 架构机会

## 0. 当前判断

我们现在的主线可以更精确地表述为：

> 在 proof-repair agent 已经有多种修复策略的背景下，让 harness 学会更好地做 repair decision：什么时候继续当前策略，什么时候切换策略，什么时候召回 skill/lemma/skeleton，什么时候停止重复烧 token。

这不是单纯提升 base model，也不是泛化 agent workflow optimization。它更像：

> self-evolving repair policy + verifier-grounded skill/rule memory。

当前架构不是完全没有 Verus-specific。它已经有浅层 Verus-specific：

- Verus error type 驱动的 agent/action：`PostCondFail`、`PreCondFail`、`AssertFail`、`ArithmeticFlow`、`BitVAssertFail` 等。
- Verus evaluator 反馈：verified/error count/target error improvement。
- Verus action taxonomy：`postcondition_repair`、`precondition_repair`、`USELEMMA`、`INSTANTIATE_FORALL`、`INDUCTION`、`REVEAL_OPAQUE`、`SEQSETMAP` 等。
- safe proof completion check。

但它缺少深层 Verus-specific decision policy：

- 不理解 proof obligation 的结构；
- 不理解 lemma dependency；
- 不理解 quantifier trigger、opaque/reveal、ghost/spec/exec 边界；
- 不知道同一错误-action 反复失败时应该切到哪类 Verus proof motif；
- 没有把成功 trace 蒸馏成可检索 skill/rule。

所以研究机会不是 “给 generic agent 加一点 Verus wrapper”，而是：

> 把 Verus verifier feedback 编译成 self-evolving agent 的记忆、规则和决策信号。

## 1. Self-evolving 代表工作：它们到底创新在哪里

| 工作 | 核心搜索空间 | 反馈/fitness | 经验如何保存 | 方法创新点 | 对我们的启发 |
|---|---|---|---|---|---|
| Reflexion | 不改代码/架构，改 episodic memory 中的文字反思 | task feedback，可是标量或语言 | reflection memory | 用语言反馈替代权重更新，让 agent 下次决策更好 | 我们可以把 Verus failure 总结成 reflection，但必须 verifier-grounded，不能只靠自然语言 |
| Voyager | executable code skills | environment feedback、execution error、self-verification | ever-growing skill library | 自动 curriculum + 可执行 skill 库 + iterative prompting | 我们的成功 proof trace 可以变成 `proof skill` / `lemma skill`，后续检索 |
| Promptbreeder | task prompts + mutation prompts | train set fitness | prompt population | 不只进化 task prompt，还进化“如何变异 prompt”的 mutation prompt | 我们可以不只进化 repair prompt，还进化 “什么情况下选哪个 repair action” 的 rule prompt |
| STOP | scaffolding/improver code | downstream utility function | improved improver versions | scaffold 自己调用 LLM 改进自己 | 我们可以 evolution repair controller，但要强 sandbox 和验证，不能大规模自由改 harness |
| GPTSwarm / Optimizable Graphs | agent graph nodes/edges | benchmark score | graph candidates | 把 agent 变成计算图，优化 node prompt 和 edge connectivity | 我们的 action routing graph 可以优化，但应受 Verus error/motif 约束 |
| ADAS / Meta Agent Search | code-defined whole agent | validation performance | archive of discovered agents | meta-agent 写新的 agent code，从 archive 中学习 | 对我们太大；可借鉴 archive，但不要让 meta-agent 随便重写全部 harness |
| AFlow | code-represented workflow graph | execution feedback / benchmark score | tree-structured experience | MCTS 搜索 workflow 代码 | 我们可以做更小的 Verus action workflow search：error -> action -> verifier delta |
| AlphaEvolve | code blocks / algorithms | machine-gradeable evaluation metrics | program database with scores | LLM + evolutionary computation + automatic evaluator；支持多目标、rich feedback、eval cascade | Verus 是天然 machine-gradeable，比许多 agent task 更适合 self-evolving；但搜索空间应是 rule/skill/action policy，不是任意 patch |
| TACO | terminal observation compression rules | task success + token efficiency | structured compression rules | 从 trajectories 自动发现/细化 compression rules，plug-in 到已有 terminal agent | 最接近我们的 token 降耗思路；我们可以做 Verus-specific compression/reroute rules |
| Lean4Agent | formal workflow/trajectory + evolution | workflow verification + benchmark performance | Lean formal artifacts/workflow updates | 用 Lean formalize agent workflow，并用 LeanEvolve 改 workflow | 说明泛化 workflow formalization 已经有人做；我们必须落在 Verus proof repair |
| AgentSpec | runtime enforcement DSL rules | safety/reliability violations | trigger/predicate/enforcement rules | 用轻量 DSL 做 agent runtime enforcement | 我们可以借 DSL 形式，但 rule 应从 Verus traces self-evolve 出来，并用 verifier 验证 |

## 2. 这些工作的共同模式

做得比较好的 self-evolving 工作通常都有四个要素：

1. **明确 evolution object**
   - prompt、skill、workflow graph、agent code、compression rule、program block。
   - 对我们来说，最合理的 evolution object 不是 whole agent，而是：
     - repair skill；
     - action routing rule；
     - skeleton retrieval key/value；
     - context compression rule。

2. **机器可评价 feedback**
   - AlphaEvolve 的关键是 automatic evaluation；
   - Voyager 有 environment feedback；
   - TACO 有 task success/token；
   - AFlow 有 benchmark execution feedback。
   - 我们的优势是 Verus verifier feedback 很强：verified/error count/target error/type/location。

3. **经验库**
   - Reflexion 存 text reflection；
   - Voyager 存 code skill；
   - ADAS 存 discovered agents；
   - AlphaEvolve 存 scored programs；
   - TACO 存 compression rules。
   - 我们应该存：
     - verified skeleton；
     - failed repetition pattern；
     - error-action-success statistics；
     - project/motif-specific repair rule。

4. **防止退化的选择机制**
   - 不是什么总结都进入知识库。
   - 必须经过 replay、验证、ablation 或小规模 rerun。
   - 对我们来说，可以用 Verus evaluator 和历史 trace replay 过滤坏规则。

## 3. 当前 Verusage 架构的不足

从 trace 和 action 统计看，当前 agent 架构已经有很多 action family：

- `postcondition_repair`
- `precondition_repair`
- `case_analysis`
- `USELEMMA`
- `INSTANTIATE_FORALL`
- `INSTANTIATE_EXISTS`
- `INDUCTION`
- `REVEAL_OPAQUE`
- `REVEAL_WITH_FUEL`
- `SEQSETMAP`
- `BIT_VECTOR_REASONING`
- `NONLINEAR_ARITHMETIC`
- `ADD_TRIGGER_ASSERT`

问题不是没有 action，而是 **action selection 太弱**。

典型失败模式：

- 同一 `(error, action)` 重复很多次。
- `AssertFail + USELEMMA` 一直重复，但成功 trace 可能应该切到 `INSTANTIATE_EXISTS`。
- `PostCondFail + postcondition_repair` 一直重复，但成功 trace 可能应该先引入中间 lemma 或 temporal skeleton。
- AC/NR/OS prompt 巨大，但 harness 没有 project-aware context policy。
- AL/TLA task 有明显 temporal motif，但 controller 没有 TLA-aware action prior。

已有实验支持这一点：

- threshold=8 repetition gate 覆盖 969/1305 个 non-verified trace，估计节省 31.74% non-verified token。
- 372 个 threshold=8 reroute candidates 中，73.66% 的 peer success top action 与失败 trace 正在重复的 action 不同。
- 517 个失败 trace 有其他模型 exact success skeleton，覆盖约 3.78 亿 failed effective tokens。

所以当前架构的真实瓶颈是：

> 它有 Verus-specific tools/actions，但没有 Verus-specific learned policy。

## 4. 哪些 Verus 性质可以结合进来

### 4.1 Verus error state delta

现在只看是否 accepted 或 verified 还不够。应该记录更细的 state delta：

- target error 是否减少；
- error type 是否变化；
- error location 是否前移/后移；
- verified function count 是否增加；
- compilation error 是否引入；
- 当前 patch 是否只是让错误换了表面形式。

可形成 rule：

```text
如果同一 action 连续 N 次没有减少 target error，
则降低该 action prior，触发 skeleton retrieval。
```

### 4.2 Proof obligation type

不同 proof obligation 需要不同策略：

- postcondition failure：可能需要中间 assertion、strengthen ensures、call lemma。
- precondition failure：可能需要证明调用前提，或更换调用位置。
- assert failure：可能需要 lemma instantiation、case split、trigger assert。
- quantifier failure：可能需要 `INSTANTIATE_FORALL` / `INSTANTIATE_EXISTS` / trigger。
- arithmetic：`NONLINEAR_ARITHMETIC` / ring / division/mod lemma。
- bitvector：`BIT_VECTOR_REASONING` / bitvector facts / mask lemma。

当前 action 里有这些类别，但缺少从 obligation 到 strategy 的 learned mapping。

### 4.3 Lemma dependency graph

从 preprocessing 已经能拿到 `Lemmas found`。可以进一步构建：

- 当前目标函数依赖哪些 lemma；
- 哪些 lemma 在成功 trace 中常一起出现；
- 某个 lemma 被调用后是否改变 error state；
- sibling lemma：`lemma_X` / `lemma_X_aux` / `lemma_X_auto`。

可形成 skill：

```text
当目标 lemma 是 foo，
且存在 foo_aux / foo_auto / foo_support，
优先检索并尝试这些 sibling lemmas。
```

### 4.4 Quantifier trigger / instantiation structure

Verus/Z3 很多失败不是“逻辑不会”，而是 SMT 没有正确实例化。

可提取性质：

- 是否存在 `forall` / `exists`；
- 是否出现 trigger 相关错误或 `ADD_TRIGGER_ASSERT` 成功；
- 成功 trace 是否用了 `INSTANTIATE_FORALL`、`INSTANTIATE_EXISTS`；
- 是否需要 assert 某个函数调用来触发量词。

这可以变成 AgentSpec-like rule：

```text
Trigger:
  AssertFail + expression contains forall/exists or quantified lemma nearby
Predicate:
  USELEMMA repeated >= 4 and no error reduction
Enforcement:
  block USELEMMA once; route to INSTANTIATE_FORALL / INSTANTIATE_EXISTS / ADD_TRIGGER_ASSERT
```

### 4.5 Opaque/reveal structure

Verus 有 opaque functions 和 reveal/fuel。当前 action 有 `REVEAL_OPAQUE`、`REVEAL_WITH_FUEL`，但应该把它和函数结构绑定：

- 当前错误表达式是否涉及 opaque function；
- preprocessing 中 opaque function count；
- success trace 是否先 reveal 再 assert；
- fuel 值是否反复增加但没有收益。

### 4.6 Ghost/spec/exec boundary

很多错误来自 proof/spec/exec 之间边界不清：

- ghost state 不可在 exec 中使用；
- spec function 与 exec function 的 view relation；
- tracked/linear ghost resource；
- proof block 中需要建立 view equality。

这比普通 coding agent 更 Verus-specific。可以做 project/motif skill：

```text
当错误涉及 ghost view equality，
优先检索 view_equal / same_view / marshalable skeleton。
```

### 4.7 Induction and recursion

preprocessing 已经输出 recursive functions。可结合：

- 目标 lemma 是否递归；
- 是否有 sequence/map/set recursive definition；
- 成功 trace 是否使用 induction；
- induction 后是否需要 case split。

当前很多 `INDUCTION` 重复失败，说明需要 rule：

```text
INDUCTION 重复失败时，不继续 induction；
检索同类 recursive lemma 的 base/step skeleton。
```

### 4.8 Project/domain motif

Verusage 项目族很有结构：

- `AC`：Kubernetes/controller/liveness/resource_match，prompt 巨大，常见 temporal/resource invariant。
- `AL`：TLA temporal proof，`always/leads_to/tla_forall/weak_fairness`。
- `NR`：page table/refinement/address/mapping，常见 bitvector/arithmetic/indexing lemma。
- `OS`：kernel/process/page table/memory quota，复杂 invariant 与 state transition。
- `MA`：allocator/layout/commit mask，常见 arithmetic/bitvector/layout alignment。
- `NO`：network/object/unbounded log，常见 sequence/set/log induction。

这可以形成 project-aware policy，而不是全局 action policy。

## 5. 推荐的新架构

### 5.1 三层 self-evolving memory

1. **Skill memory**
   - 从 verified trace 总结自然语言或模板 skill。
   - 例：`leads_to_trans skill`、`sibling lemma skill`、`quantifier trigger skill`。

2. **Skeleton memory**
   - 保存 action sequence + lemma sequence + error transition。
   - key：project/motif/error prefix/lemma names。
   - value：successful route。

3. **Decision rule memory**
   - AgentSpec-like 结构化 rule。
   - 包含 Trigger / Predicate / Enforcement / Evidence / Scope。

例子：

```yaml
rule_id: tla_leads_to_repetition_reroute
scope:
  project: AL
  filename_contains: [leads_to, always, tla_forall]
trigger:
  repeated_pair: [AssertFail, USELEMMA]
  count_ge: 8
predicate:
  target_error_not_reduced: true
enforcement:
  block_action_once: USELEMMA
  retrieve_skeleton_tags: [leads_to, tla_forall]
  prefer_actions: [INSTANTIATE_FORALL, INSTANTIATE_EXISTS, CASE_ANALYSIS]
evidence:
  mined_from_success_traces: 12
  offline_false_stop_rate: low
```

### 5.2 Evolution loop

推荐的 self-evolving loop：

1. Run / collect traces。
2. Mine repeated failure and successful skeletons。
3. LLM proposes skills/rules from mined evidence。
4. Offline replay filters rules：
   - 是否覆盖 non-verified token sink；
   - 是否误伤 verified trace；
   - peer success 是否支持 reroute action。
5. Small rerun validates top rules。
6. Accepted rules enter memory。

这比直接让 agent 自己写 harness 更安全，也更容易出表。

## 6. 最值得马上做的三个实验

### 实验 1：Verus-specific rule mining

输入：现有 traces。

输出：

- `candidate_rules.jsonl`
- 每条 rule 包含 trigger/predicate/enforcement/evidence。

目标：证明规则不是手写 intuition，而是从 trace 中挖出来的。

### 实验 2：Rule replay scoring

给每条 candidate rule 打分：

- covered failed traces；
- saved token；
- verified false-stop；
- peer success action agreement；
- project/motif specificity。

目标：筛出高精度规则，而不是一堆泛泛 skill。

### 实验 3：Verus motif ablation

比较三种 policy：

1. generic repetition rule；
2. project-aware rule；
3. Verus-motif-aware rule。

如果第 3 个明显更好，就能证明 Verus-specific property 是必要的。

## 7. 论文角度的主张

可以写成：

> Existing self-evolving agents learn prompts, workflows, skills, or compression rules, but they usually treat environment feedback as generic success/failure signals. In Verus proof repair, verifier feedback exposes rich proof-structural signals. We show that mining these signals enables self-evolved skills and structured decision rules that improve repair strategy selection and reduce repeated failures.

中文：

> 现有 self-evolving agent 多数学习 prompt、workflow、skill 或 compression rule，但它们通常把环境反馈当成泛化的成功/失败信号。Verus proof repair 的特殊性在于 verifier feedback 本身包含 proof structure。我们利用这些结构化反馈自动蒸馏 skill 和决策规则，从而改善修复策略选择并减少重复失败。

这个主张比 “我们做 repetition gate” 更强，也比 “我们做 agent harness verification” 更 grounded。

## Sources

- Reflexion: https://arxiv.org/abs/2303.11366
- Voyager: https://arxiv.org/abs/2305.16291
- Promptbreeder: https://arxiv.org/abs/2309.16797
- STOP: https://arxiv.org/abs/2310.02304
- GPTSwarm / Language Agents as Optimizable Graphs: https://arxiv.org/abs/2402.16823
- ADAS / Meta Agent Search: https://arxiv.org/abs/2408.08435
- AFlow: https://arxiv.org/abs/2410.10762
- AlphaEvolve white paper: https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf
- TACO: https://arxiv.org/abs/2604.19572
- Lean4Agent: https://arxiv.org/abs/2606.06523
- AgentSpec: https://arxiv.org/abs/2503.18666

