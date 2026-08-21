# 三指标 Skill 讲解提纲

## 1. Token：R3-A 好在哪里，R3-C 为什么变坏

- 指标：fresh H0 ETtS 87,312.7；R3-A `local-proof-surface-cap` 单次筛选 61,232（-29.87%）；同轮 R3-C `three-fact-witness-note` 119,638（+37.02%）。A 比 C 少 58,406 tokens（-48.82%）。
- 行为：A 是 2 次 Verus、0 个新 helper、139 行新增；C 约 6 次 Verus、4 个新 helper、302 行新增。两者都通过 Verus、Lynette、F3，不是靠“失败得快”省 token。
- 最清楚的原文差异：A 要求 “every return path”，同时覆盖 true path 和 false path；C 只提醒 “every false return”。A 管完整 proof surface，C 只提醒一个局部知识点。
- 第二个差异：A 的 “initial new-helper budget at zero” 是硬边界；C 的 “Add a helper only for a fact reused at least twice” 仍给 solver 留出了扩建 helper architecture 的入口。
- 第三个差异：A 规定 “Repair only the reported local premise or syntax item”；C 没有同等强度的局部 delta 限制。A 在 verifier 后收缩搜索，C 的 trajectory 则不断把局部问题外化成新 helper。
- A/C/S：R3-A 很典型地体现 A。这里 aggressive 不是提供更多知识，而是主动砍掉 source reread、helper、未闭合分支和 verifier cycle。R3-C 形式上符合 C，但它错误假设总体 proof architecture 已经清楚。
- 泛化：可泛化的是 branch ledger、zero-helper first patch、local-delta repair；不可直接泛化的是 lower inclusion、strict upper inclusion、abstract disagreement 这三个 IronKV witness facts。
- Meta-evolution：meta-agent 确实把 R2-C 的 witness-completeness 洞察升级成了 R3-A 的 hard cap，这是有价值的候选生成；但三次确认只有 82,391（-5.64%），小于 H0 自身 12,908-token range，所以不能讲成稳定的演化成功。
- 一句话讲法：两个 skill 都“知道 witness”，真正拉开成本的是 A 把知识变成了可执行的 proof-surface 预算。

R3-A 原文。原始文件存在重复渲染，以下逐字保留其中完整的主 policy block：

```markdown
# Local Proof-Surface Cap

## Applicable state

Use when a visible proof-only Boolean implementation can be related to its specification with existing contracts, local assertions, and constructive counterexamples.

## Ordered policy

1. Quietly compare immutable input and candidate. If identical, read only the candidate; inspect the target, relevant contracts, and checker wrappers once, then lock the commands.
2. Skip the untouched baseline when the visible body already exposes the failed postcondition and helper preconditions.
3. List every return path in a compact ledger. Name existing coverage facts for true paths and, for each false path, a witness with lower inclusion, strict upper inclusion, and abstract disagreement. Classify an exact upper endpoint as excluded.
4. Make one proof-only patch confined to the existing target body. Reuse supplied lemmas and keep the initial new-helper budget at zero. Cover every ledger row before invoking Verus.
5. Preflight quantified assertions, reveals, casts, endpoint strictness, and call preconditions.
6. Run Verus. Repair only the reported local premise or syntax item. Permit one helper only if the same fact is required at least twice and factoring it reduces total proof text.
7. At first success, run the policy checker once on the unchanged candidate and stop.

## Stop/self-disable condition

Self-disable if any ledger row needs semantics unavailable from visible contracts or if a local proof would duplicate a substantial derivation. Continue normal proof-safe solving without enforcing the cap.

## Predicted token-saving mechanism

This removes duplicate source context, an unnecessary baseline, large one-use helpers, and verifier turns over knowingly incomplete branches while keeping later candidate context small.

## Known failure risk

A strict locality bias can produce brittle SMT assertions or obscure a genuinely reusable invariant. The self-disable condition must take precedence over the size target.
```

R3-C 原文。原始文件存在重复渲染，以下逐字保留其中完整的主 policy block：

```markdown
# Three-Fact Witness Note

## Applicable state

Use when a Boolean proof plan is already clear but a false branch or excluded endpoint could be missed.

## Ordered policy

1. Read the checker wrappers and lock their exact commands. If input and candidate are identical, read only one full source.
2. Before editing, record for every false return one witness and three facts: lower inclusion, strict upper inclusion, and abstract-value disagreement. Check an exact upper endpoint separately.
3. Prefer existing lemmas and assertions inside the target body. Add a helper only for a fact reused at least twice.
4. Run a baseline only if the obligation is unclear. Otherwise make the local proof edit, run Verus, apply only the reported correction, then run the policy checker once and stop.

## Stop/self-disable condition

Self-disable when there is no constructive false path or when all three witness facts are immediate and need no reminder.

## Predicted token-saving mechanism

The small injection preserves the successful local-witness behavior while preventing duplicate reads, late endpoint discovery, and unnecessary helper growth.

## Known failure risk

This note supplies little architectural guidance when representation-to-spec transfer requires a substantial new proof.
```

## 2. Small-model：没有涨 solve rate，C 只是比 A 少伤害

- 指标：H0 为 2/4 solved、29 requests、312,656 tokens；R2-C `verus-contract-match-loop-r2` 为 2/4、29、321,998（+2.99%）；R2-A `verus-eight-plus-two-ladder-r2` 为 2/4、29、490,164（+56.77%）。
- 正确讲法：R2-C 不是主指标赢家，只是 least-harmful。它比同轮 A 少 168,166 tokens（-34.31%），但仍没有超过 H0，也没有新增 solve。
- 最清楚的原文差异：C 把动作压成 “Pick the lemma” → “at most one bridge” → “Run Verus immediately”；A 要模型维护十请求阶段、BEST、四类 transition 和多种 decomposition。
- 两者 requests 都是 29，token 差距却很大。这说明问题不只是调用次数，而是每轮要维护和回灌多少控制状态。
- C 的 “same outer operator” 让 lemma 选择可操作；“second failed bridge” 是清楚的停止条件。A 的 request ladder 看起来纪律更强，但纪律全部写在 prompt 中，没有 host 真正保证 rollback。
- A/C/S：C 更符合小模型的容量约束；A 的复杂 controller 虽然符合 aggressive 的形式，却增加了工作记忆负担。S 型大 DAG 若全部写进 prompt，也可能有同样问题。
- 泛化：C 可能泛化到 visible lemma 与 goal 近似同构、只缺一个 quantified instance 或一个 bridge 的状态；不适用于真正的多层 representation correspondence。
- Meta-evolution：R2 meta 学会了减少 R1 的控制协议负担，但只做到 damage control；R3-C 基本停滞，solve subset 始终不变。
- 一句话讲法：小模型需要的是一个可执行动作和外部 rollback，不是把完整 agent controller 再写成一篇 skill。

R2-C 原文：

```markdown
# One-Lemma Contract Match Loop

## Applicability
Use when the target postcondition is close to an in-scope lemma's `ensures` clause.

## Loop

1. Read the target and visible lemma contracts. Run Verus once. Keep the exact compiling proof body as `BEST`.
2. Pick the lemma whose `ensures` has the same outer operator as the goal. Prefer an exact contract match over an assertion you hope automation will prove.
3. Call that lemma and add at most one bridge:
   - instantiate its quantified result at the needed term;
   - call it separately for each component;
   - state one equality, bound, or cast already justified by the current requires; or
   - for an encoding, establish one field boundary and invoke the existing proof for that field.
4. Run Verus immediately.
5. If Verus passes, run the policy checker and stop. If a compile, type, recommendation, or unknown-name error appears, restore BEST. If the original logical error is unchanged, remove the bridge and try one different bridge class once.
6. After the second failed bridge, stop stacking facts. Preserve BEST and switch to semantic decomposition. Reserve the last two requests for Verus and the policy checker.

## Recovery
Use only identifiers visible in the task or an exact compiler suggestion. One missing name ends name guessing. A helper is forbidden until a concrete instance verifies and repeats. An assertion that merely repeats a precondition or the goal is no progress and must be removed.

## Verifier safety
Change proof code only. Preserve executable behavior, signatures, requires, ensures, and decreases. Never use assumptions, admissions, axioms, external bodies, or bypasses. Report success only when Verus and the policy checker pass on the same candidate.

## Negative scope
This loop does not solve genuinely multi-layer correspondence by itself and does not authorize external inspection, contract changes, executable edits, or policy-only success.
```

R2-A 原文：

```markdown
# Eight-Plus-Two Reversible Verifier Ladder

## Applicability
Use for a proof-only Verus repair with at most ten model requests.

## Safety
Edit only permitted proof code. Preserve executable behavior, signatures, contracts, and decreases. Never add an assumption, admission, axiom, external body, or verification bypass. A solve requires both Verus and the policy checker to pass on the same candidate.

## Requests 1-8: work phase

1. Read the task, candidate, immutable input, and skill in one request. Write a private three-line inventory: exact goal; visible lemma ensures that share its outer shape; exact editable proof body.
2. Run Verus. Save `BEST` as the exact current proof body plus its compile status, verified count, and first diagnostic.
3. Choose exactly one move:
   - quantified implication: call the closest lemma, then instantiate it at the required witness;
   - conjunction or product: apply the matching lemma once per required component;
   - encoded concatenation: expose one field boundary with a visible bridge, prove the corresponding field encodings equal, then call existing field injectivity;
   - subset or nested interpretation: introduce one arbitrary witness and connect one semantic representation layer.
4. Make one reversible proof-only edit and run Verus immediately.
5. Classify the transition mechanically:
   - PASS: save BEST and stop substantive editing;
   - PROGRESS: the blocking diagnostic moved closer to the postcondition without new compile/type/recommendation failures; save BEST;
   - NO-PROGRESS: the same logical diagnostic remains; undo the edit before trying one different move;
   - REGRESSION: any syntax, type, recommendation, unknown-symbol, or increased independent-obligation failure; undo immediately to BEST.
6. Never guess a second spelling after an unknown identifier. Use only a name visible in the files or an exact compiler suggestion. Do not replace one guessed sequence or prover API with another.
7. After two equivalent logical diagnostics, restore BEST and change decomposition. For nested proofs, close one layer from witness selection to child or terminal fact before copying that verified pattern. For arithmetic, prove only the cast or bound required by the current semantic step.
8. Freeze the strongest compiling candidate. Add a helper only if one concrete instance already verifies and the identical obligation occurs again. Otherwise keep the concrete fact at its use site.

## Requests 9-10: protected checks

9. Run final Verus on the frozen candidate. Do not add a new idea in this request.
10. If request 9 regressed, restore BEST first and rerun Verus; then run the policy checker on that exact candidate. If Verus passed at request 9, run only the policy checker. Report a solve only if both pass.

## Recovery summary
Unknown symbol: revert, then use an exact visible or compiler-suggested name. Same diagnostic once: revert and change move. Same diagnostic twice: restore BEST and change decomposition. New helper failure: delete the helper. Never finish on a non-compiling edit when BEST compiles.

## Negative scope
This skill is not permission for broad refactoring, contract weakening, executable edits, external research, reference-proof inspection, or success claims based on policy safety alone.
```

## 3. InfoGain：pre 需要 S，post 需要 C

- 指标：pre winner 是 R1-S `dependency_bridge_map`，四任务 macro +0.070516 bits/target token；post winner 是 R1-C `minimal_sufficient_rationale`，macro +0.219801。
- Pre 的 caveat：R1-S 的正 macro 主要来自两个 marshal tasks；IronKV hard 为 -0.12647，按全部 9,354 target tokens pooled 后约为 -0.0587。它是 task-family specialist，不是通用 pre memory。
- Post 的 caveat：R1-C 四任务 post 都为正，但它是在 proof 已完成后写出的 hindsight summary。它支持 memory compression，不支持 live solve/token improvement。
- 最清楚的原文差异：S 用 “root node”“bridge edges”“topologically” 组织尚未解决的 proof；C 用 “smallest high-confidence set”“only the mismatch”“five short lines” 压缩已经解决的 proof。
- A/C/S：S 很好地体现结构化 proof-state 组织，适合多表示层 pre retrieval；C 很好地体现最小充分写回，适合 post memory。这里不存在一个同时统治 pre/post 的统一 profile。
- 什么策略 benefit pre：只检索与当前 representation transition 匹配的 bridge/dependency card，并允许 abstain。
- 什么策略 benefit post：只写 exact obligation、actually-used lemma、decisive bridge、verifier outcome，删除失败猜测与调试历史。
- 泛化：S 的结构可能泛化到 representation-heavy proof，但当前正值集中在 marshal family；C 的压缩 schema 更可能跨任务泛化，但只限于 post representation。
- Meta-evolution：R1 产生了这两个 winner；R2 三 skill 平均 post 从 0.2149 降到 0.1805，且所有 R2 pre macro 为负。meta-agent 的分析更复杂，但指标没有累积改善。
- 一句话讲法：pre memory 应该像地图，post memory 应该像压缩后的答案索引；把两者写成同一个大 skill 会互相污染。

R1-S pre skill 原文：

```markdown
# Dependency and Bridge Map for Verus Proofs

## Objective
Expose the topological structure of the proof: what each obligation depends on, which invariants connect layers, and which bridge closes each branch. Optimize only full-proof information gain.

## Applicability
Use when the target spans multiple abstractions or requires several helper facts, boundary cases, or implication directions.

## Negative scope
Do not reproduce the finished proof or task-specific identifiers. Do not add speculative nodes, chronological debugging narration, irrelevant warnings, or efficiency advice. For a direct corollary, use a minimal rationale instead.

## Required workflow
1. Create a root node for each target conjunct or implication direction. For a Boolean equality, create separate soundness and completeness roots.
2. Add premise nodes for requires clauses, recommendations, validity predicates, order laws, domain facts, length bounds, and branch guards.
3. Decompose each validity predicate into the invariant actually consumed by the proof. Distinguish structural invariants from semantic invariants.
4. Add bridge edges wherever adjacent nodes use different representations: component to aggregate, closed to exposed specification, encoded prefix to payload, index to key, stored value to abstract map value, local gap to global range, or branch guard to logical case.
5. For every bridge edge, identify a confirmed lemma, explicit quantified instantiation, witness, unfolding permission, injectivity argument, extensionality argument, or contradiction. An edge without such support is the current blocker.
6. Order helper lemmas topologically. Establish foundational order and membership facts first; then representation correspondence; then forward preservation; then converse or witness facts; finally branch assembly.
7. Make boundary nodes explicit: empty intervals, terminal sentinels, inclusive versus exclusive endpoints, equal indices, and the last stored element. State which invariant closes each.
8. Map executable branches to specification cases. True branches require constructive forward paths; false branches require a converse theorem or an internal counterexample witness.
9. After each verifier run, mark proven nodes and report only the lowest unresolved dependency. Do not treat downstream failures as independent until their prerequisites verify.

## Terminal repair summary
End with:
- Diagnosed obligation: root obligations and the last unresolved dependency.
- Key lemmas/invariants: a topologically ordered list of dependency nodes and roles.
- Decisive proof bridge: the critical representation or implication edge, followed by the branch-assembly chain.
- Verifier outcome: exact verification and structural-check results.
- Unresolved blocker: `none`, or the first unsupported edge in the dependency graph.
```

R1-C post skill 原文：

```markdown
# Minimal Sufficient Proof Rationale

## Objective
Retain the smallest high-confidence set of facts sufficient to explain a complete Verus proof. Optimize reference-proof information gain, not brevity for its own sake, solve rate, or token cost.

## Applicability
Use for direct lemma applications, explicit quantifier instantiations, component-wise contract propagation, or a short confirmed representation-to-goal bridge.

## Negative scope
Do not compress away unresolved branch directions, required invariants, recommendations, casts, or representation boundaries. Do not list guessed APIs, routine tool failures, task identifiers, finished proofs, reference answers, or evaluator-only information.

## Required workflow
1. State the exact failing obligation in normalized form.
2. Select the strongest already-confirmed contract whose conclusion nearly matches the target.
3. Record only the mismatch between that conclusion and the target: a particular quantified instance, component decomposition, side condition, representation bridge, injectivity step, or extensional equality.
4. Prefer direct contract application over introducing a new helper. For composite values, invoke the component contracts and state how their conclusions reconstruct the composite property.
5. If the specification is closed or otherwise opaque, use only a verifier-confirmed bridge to an exposed representation; retain the representation fact it unlocks and discard failed name guesses.
6. Re-run the verifier. If new independent branches or invariants appear, stop using this profile and switch to a structural rationale.
7. Preserve a failed approach only when it identifies the unresolved blocker or establishes that a tempting bridge is unavailable.

## Terminal repair summary
End with five short lines:
- Diagnosed obligation: the target and the one missing step.
- Key lemmas/invariants: only those actually used, with their roles.
- Decisive proof bridge: one minimal implication chain.
- Verifier outcome: exact verification and structural-check results.
- Unresolved blocker: `none` or one precise missing fact.
```
