# AC：Initial skill + Hint v1 / v2 逐checkpoint对照

[今日完整hint内容核对及AC审计纠错](../HINT_CONTENT_COMPARISON.md)。完整hint原文是判断提示覆盖范围的依据，不能只取首段。


[原trace＋两版增广：去重后的信息增量审计](../INFORMATION_VALUE_AUDIT.md)。有效材料包括可解释的失败；成功率不等于新增信息量。


本题两组各6条续跑，均装备与原trace相同的initial skill，模型为DeepSeek v4 Pro，checkpoint提取与续跑条件一致。**v1/v2的hint模板不同，每个checkpoint的hint也分别重新生成，没有共用hint。** 两版对应起点的实际hint全文均不相同；文字不同不等于数学策略不同，具体以每点审计为准。

v1要求诊断当前缺口并给出逻辑提示；v2在此基础上要求另行检查有证据支持的结构兼容风险，区分已观察到的Lynette失败、潜在风险和无证据风险，不能泛称所有导入都会失败。两版保持简短逻辑指导，不提供整段最终proof。这里的v1/v2是prompt版本；JSON里的`schema_version: hint-v1`是共用数据格式标识，不代表两版提示内容相同。

[Hint v1模板](../prompts/v1/hint_system.md) · [Hint v2模板](../prompts/v2/hint_system.md) · [原v1详细报告](v1/REPORT.md) · [原v2详细报告](v2/REPORT.md)

| 版本 | 最终Verus＋Lynette通过 | Actor输出token合计 |
|---|---:|---:|
| v1 | 5/6 | 106,677 |
| v2 | 5/6 | 90,178 |

每点只各跑一次，模板版本和生成内容同时变化；同起点对照能描述采纳、失败和成本差异，不能证明哪个提示稳定更优。旧blank组未混入此对照。

![两版同起点对照](v2/comparison_prefix_tokens.png)

横轴为原前缀归属token＋续跑actor输出token；原前缀未实际回放，hint生成成本另计。上图Patch F1是相对原F的参考路径相似度，不是正确性评分；下图为Verus状态，首次Verus通过不等于最终Lynette也通过。

## 先读懂原题与原F

本题要证明：从收到list-pods响应的状态，最终到达收到create-pod成功响应的状态，并把pod数量差从diff推进到diff+1。原文件已有两个消息级组件引理，分别处理“具体list响应→pending create请求”和“具体create请求→成功响应”。当前任务是组合它们，不是重证整个控制器。

令P表示整体list响应状态，Q表示pending create状态，R表示目标成功响应状态。原F的逻辑连接为：`P → 存在具体响应 → Q → 存在具体请求 → R`。消息级leads-to引理经`leads_to_exists_intro`提升后，只证明两个消息族的进展；仍需单独证明P蕴含响应族的`tla_exists`，以及Q蕴含请求族的`tla_exists`。

因此“状态中存在某消息”与“某个temporal family在此execution成立”之间不是靠重述目标就自动打通的：必须在execution的head上得到消息见证、验证具体消息谓词，再建立family实例。响应通常从in-flight/matching/OK条件取choose见证；请求可以直接取已经存在的pending消息。CP2是trigger层，CP3是这两个桥接，CP4还有前提未进入量词proof体，CP5仍缺具体见证，CP6则是正确证明被非法auto属性打断。

[原题源码](original_input.rs) · [原F全文](original_final.rs)

<a id="cp1"></a>
## CP1：同一起点，两版如何处理

**直接对照。** v2 CP1在主体内按两个execution展开分别补见证后成功，没有陷入本点长时间helper改写。相同起点一次成败差异，不能单独归为skill或版本能力。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 36,977 | 18 | 未通过 |
| v2 | 16,735 | 5 | 通过 |

<a id="v1-cp1"></a>
### v1：长时间构造辅助引理，两个桥接未闭合

**客观起点（原trace事件19）。** 空主体，需组合两条已有消息级leads-to组件引理，并与整体存在状态谓词衔接。

**Hint作何判断。** 提示两阶段组合和两处存在见证桥接，数学方向正确。没有虚构顶层导入问题。

**实际编辑与验证顺序。**

| 阶段／事件 | 实际尝试与诊断 | 还未解决的义务 |
|---|---|---|
| 76–85：先立主链 | 引入组件组合，补量词trigger后仍有后置条件／pending桥接失败 | 起始P到响应family尚缺桥接，请求侧也不能直接assert |
| 94–144：拆helper与状态函数 | 先遇含lambda的非法trigger，再遇量词语法和变量作用域问题 | 只是改变表达／模块划分，没有证明temporal existential |
| 158–205：反复改请求侧 | 加分支、直接entailment、family实例和存在断言，仍未验证通过 | 已知状态事实尚未成为所需时序结论，主链不完整 |
| 211–最终：再抽helper | 新helper及调用仍失败，约602秒结束 | helper后置条件、调用前提及主目标均有未闭合错误；Lynette通过不能补足Verus证明 |

**为什么这些修改有效，或仍然失败。** 第一版主链已有两个消息级组件的组合，但起始整体P尚未连到具体响应family；后面大量时间又集中在请求侧pending到tla_exists的helper上。将一条桥接抽成requires/ensures并不自动证明它，仍要在调用处满足前提、在helper体中完成temporal family实例化。结尾这些责任仍未闭合，主目标自然不能借助它们通过。

**Hint究竟起了什么作用。** hint实际已经提示两处桥接，不存在“只让actor证明请求侧”的限制。actor自行偏向helper重构及量词语法试错，没有完成整个提示。失败不能归于Lynette误报，也不能断言提示数学路线错误；更准确的是规划方向正确、执行闭合失败。

**同起点两版对照。** v2 CP1在主体内按两个execution展开分别补见证后成功，没有陷入本点长时间helper改写。相同起点一次成败差异，不能单独归为skill或版本能力。 见[另一版CP1](v2/REPORT.md#cp1)。

**语义审计结论。** 真实失败而非筛查误报。hint方向合理但actor没有完成提示要求；不得作为成功增广，保留失败对照及已验证的局部修复。

**最终检查边界。** 宿主Verus=失败，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。 最终Verus统计为`verification results:: 0 verified, 3 errors`。

```text
error: postcondition not satisfied
error: precondition not satisfied
error: postcondition not satisfied
error: precondition not satisfied
```

<details><summary>本次实际发送的hint全文</summary>

The checkpoint has an empty proof body for lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp, so its final leads-to postcondition is unproved. The next objective is to prove the body as a temporal chain using the two already-trusted component lemmas: first from a specific in-flight list response to a pending create request, then from that specific create request to an OK create response. Introduce an intermediate state predicate for the pending create request, and use existential-introduction and transitivity rules. The main difficulty is proving the two existential liftings: the existential list-response predicate must entail the existential over response-specific predicates, and the pending-create predicate must entail the existential over request-specific predicates. Expand these entailments over executions, choose a witness message from the existential hypothesis, and prove the stronger message-specific predicate for that witness. When writing the quantified implication, ensure the antecedent is available as an assumption. Re-run Verus; success is indicated by the postcondition error disappearing.

</details>

[起点源码](checkpoints/CP01.rs) · [hint原文件](v1/CP01/hint.json) · [全部修改与工具反馈](v1/CP01/PROCESS.md) · [最终源码](v1/CP01/final.rs) · [最终验证](v1/CP01/result.json)


<a id="v2-cp1"></a>
### v2：完成组件组合与两个存在桥接

**客观起点（原trace事件19）。** 空proof，完整leads-to后置条件未证明。

**Hint作何判断。** 两组件、两family和两个见证桥接指向正确。

**实际编辑与验证顺序。** 54构造组合骨架但用保留字final，56失败；62改final_pred，64 trigger失败；69补trigger，71暴露两桥接；80在有if前提保护的execution上选响应见证，82只剩请求；88取pending请求见证，90／95双通过。

**为什么这些修改有效，或仍然失败。** 主链骨架把两个消息组件放到一起，但直接assert两个整体entailment仍缺见证。编译层先修保留字final和trigger后，错误才准确落在这两个桥接；随后第一轮给响应见证，第二轮给pending请求见证，分别填上P与Q进入消息family的缺口。if条件保护了==> proof体中需要的前提，因此即便有该语法warning，最终也不是无前提取choose。

**Hint究竟起了什么作用。** hint三部分——组件组合、响应见证、请求见证——都能找到实际对应；但actor先写高层断言再补细节，仍重现hint已预告的失败。应称最终有效落实，不称一次无错误完成。

**同起点两版对照。** v1本点过度投入请求helper并漏起始桥接，最终失败；v2在主函数完成两边连接。证据支持本次实现更完整，不支持单样本因果结论。 见[另一版CP1](v1/REPORT.md#cp1)。

**语义审计结论。** 核心hint逐层落实，但没有提前规避保留字、trigger及桥接失败；较v1 CP1完成了整条链，不能单次归因为版本。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The remaining failure is the empty body of lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp: Verus reports the final leads-to postcondition is not satisfied. The requires are already sufficient, and the two external-body lemmas already cover the message-level transitions: a specific OK list-pods response leads to a pending create-pod request, and a specific create-pod request leads to an OK create-pod response. The next proof objective is to connect those single-message lemmas to the lemma's existentially quantified initial and final state predicates. Introduce temporal intermediate predicates for the specific response message and the specific request message, instantiate the two external lemmas for arbitrary messages, and lift them with leads_to_exists_intro. Then prove the two existential-state entailments by selecting the existing in-flight message with a choose witness and reasserting the exact single-message predicate; avoid leaving the existential witness for the SMT solver to synthesize. Chain the resulting leads-to facts with leads_to_trans. Run Verus and check that the previously failing postcondition at the bottom of the target lemma disappears, then run Lynette.

</details>

[起点源码](checkpoints/CP01.rs) · [hint原文件](v2/CP01/hint.json) · [全部修改与工具反馈](v2/CP01/PROCESS.md) · [最终源码](v2/CP01/final.rs) · [最终验证](v2/CP01/result.json)

<a id="cp2"></a>
## CP2：同一起点，两版如何处理

**直接对照。** v2也经历前提和assert语法修复，但没有本点长链的状态函数重构，输出明显较少；终点依然同一种见证组合策略。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 24,777 | 7 | 通过 |
| v2 | 11,723 | 5 | 通过 |

<a id="v1-cp2"></a>
### v1：补跑通过，literal_call是筛查误报

**客观起点（原trace事件77）。** forall缺trigger，随后两处存在见证桥接失败。

**Hint作何判断。** 明确标出量词entailment作为trigger并提示两处见证；含较具体表达式而非整段proof。筛查命中不是数学错误，放行记录保留。

**实际编辑与验证顺序。** 37加trigger，40两断言失败；61拆状态函数及见证proof，64触发器失败；77补trigger，80失败；86改closure，89失败；101改implies但仍有局部遮蔽／桥接问题，104失败；110去多余局部声明并直接响应见证，113只剩请求；119补请求见证，122／127双通过。

**为什么这些修改有效，或仍然失败。** trigger修复只让量词被接纳；两条高层entailment仍需实际见证。中间把状态谓词拆开后，又在量词proof体声明同名局部s/ex，造成证明对象与原量词上下文脱节；仅换implies不能替代移除这些多余声明。后面回到给定execution的head取响应，再取pending请求，才真正把两侧family连接完成。

**Hint究竟起了什么作用。** literal_call筛查命中较具体数学表达式属于既有人工放行，不是actor的证明错误。提示预告了正确的下一层，但actor在实现时引入额外变量／closure复杂性，故不能说它提前避开了失败。

**同起点两版对照。** v2也经历前提和assert语法修复，但没有本点长链的状态函数重构，输出明显较少；终点依然同一种见证组合策略。 见[另一版CP2](v2/REPORT.md#cp2)。

**语义审计结论。** 提示预告准确，actor最终落实但绕路较多；不能把筛查误报计作失败。保留原hint不重生成，补跑结果是本点正式结果。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

At this checkpoint the immediate error is missing quantifier triggers, not a missing proof fact. The first forall assertion over resp_msg is intended to establish the quantified precondition needed by leads_to_exists_intro, but Verus cannot infer a trigger and therefore cannot instantiate that assertion against the rule. Add an explicit trigger on the quantified entailment term spec.entails(p_resp(resp_msg).leads_to(q_mid)); apply the analogous trigger to the later forall over req_msg using p_req. Re-run Verus after this change. If it advances to assertion failures on p.entails(tla_exists(p_resp)) or q_mid.entails(tla_exists(p_req)), the next objective is not to add assumptions: unfold the existential temporal predicate at the current ClusterState, name a concrete in-flight Message witness, and use that witness to satisfy the tla_exists predicate rather than trying to discharge the existential directly.

</details>

[起点源码](checkpoints/CP02.rs) · [hint原文件](v1/CP02/hint.json) · [全部修改与工具反馈](v1/CP02/PROCESS.md) · [最终源码](v1/CP02/final.rs) · [最终验证](v1/CP02/result.json)


<a id="v2-cp2"></a>
### v2：trigger后分两侧补见证

**客观起点（原trace事件77）。** 量词trigger失败。

**Hint作何判断。** 准确预告随后两处entailment义务，无凭据的结构风险未加入。

**实际编辑与验证顺序。** 34补trigger，36两断言失败；48响应见证但无有效前提上下文，50失败；56改implies且补existential，58语法失败；63修assert语法，65只剩请求；71补pending请求，73／78双通过。

**为什么这些修改有效，或仍然失败。** 量词trigger只是指定实例化入口，不能提供具体消息。修完后actor按提示选响应，却最初没把源谓词前提带入proof体；改implies后又写错assert exists语法，这两个错误都属于actor实现。修复后响应侧闭合，最后pending请求实例补上另一侧。

**Hint究竟起了什么作用。** 提示同时预告两处桥接，最终执行确实覆盖两边，没有数学误报；但“预告准确”没有转化成“第一次就避开这些错误”。中间语法失败不能被画成已经取得的新证明事实。

**同起点两版对照。** v1也完成同一链但进行了更多状态谓词与局部变量改写；本版更直接，并非另一个数学策略。 见[另一版CP2](v1/REPORT.md#cp2)。

**语义审计结论。** 提示有效但落实有实现错误；与v1相比少绕几轮，没有新数学策略。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current blocker is a quantifier-trigger inference failure in the forall assertion that establishes the premise for leads_to_exists_intro over response messages. Add an explicit trigger annotation to the quantified expression that mentions spec.entails, and do the same for the analogous request-message forall assertion. Re-run Verus; this should move the proof past trigger inference. The next likely failures will be the two implication checks from the overall predicate to the existential versions of the response-family and request-family predicates. To close those, expand each implication over an arbitrary execution, expose the current state, prove the concrete in-flight message exists from the source predicate, and name that message with a choose expression. Then assert that the chosen message satisfies the corresponding specific predicate (the in-flight list response predicate, or the in-flight create request predicate), which gives the witness for tla_exists. After Verus accepts the proof, run Lynette; no structural compatibility change outside this proof body is apparent in the current checkpoint.

</details>

[起点源码](checkpoints/CP02.rs) · [hint原文件](v2/CP02/hint.json) · [全部修改与工具反馈](v2/CP02/PROCESS.md) · [最终源码](v2/CP02/final.rs) · [最终验证](v2/CP02/result.json)

<a id="cp3"></a>
## CP3：同一起点，两版如何处理

**直接对照。** v2 CP3另造专用／泛型桥接后超时，本版就地增加前提保护已成功。说明相同可行提示可以引出差异很大的实现路径。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 10,609 | 2 | 通过 |
| v2 | 33,852 | 11 | 未通过 |

<a id="v1-cp3"></a>
### v1：见证路线正确，第一次缺前提

**客观起点（原trace事件84）。** 主链已存在，两个entailment断言未闭合。

**Hint作何判断。** 指出在满足源谓词的execution上选择已有消息，数学判断正确。

**实际编辑与验证顺序。** 56补两个forall见证，但==>未把前提带入proof体，58失败；64给两个主体增加对应if前提保护，66／71双通过。

**为什么这些修改有效，或仍然失败。** choose需要源状态前提来保证存在消息；最初forall虽写了==>，proof体没有自动取得前件，因此不能无条件用head中的消息。加if后，选响应和请求都处于相应源谓词成立的分支，family实例才能有根据。这个if不是缩小原定理要求：它正对应要证明的蕴含前件。

**Hint究竟起了什么作用。** hint要求“在满足P/Q的execution上”推理，actor第一次未忠实编码这一条件，第二次才完成。提示数学正确，首个实现不正确；报告不把后者当合理已证事实。

**同起点两版对照。** v2 CP3另造专用／泛型桥接后超时，本版就地增加前提保护已成功。说明相同可行提示可以引出差异很大的实现路径。 见[另一版CP3](v2/REPORT.md#cp3)。

**语义审计结论。** 合理的上下文修复；失败起于actor未落实“满足源谓词”的局部条件。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The remaining two failures are witness-introduction goals for `tla_exists`, not complex temporal-reasoning gaps. The high-level composition structure is already present. For `p.entails(tla_exists(p_resp))`, reason over an arbitrary execution whose head satisfies `p`. That head gives `exists_resp_in_flight_at_after_list_pods_step`, whose definition already contains an existential response message with the in-flight, response-match, and OK-list-response conditions. Bind that existing response message as a named witness, then show it satisfies the exact pointwise predicate behind `p_resp`; the `num_diff_pods_is` part follows from `p`. For `q_mid.entails(tla_exists(p_req))`, do the analogous step: the head satisfying `q_mid` gives `pending_req_in_flight_at_after_create_pod_step`, whose definition contains the pending in-flight create request and the `AfterCreatePod(d)` step. Bind that request as the witness and show it satisfies the pointwise predicate behind `p_req`. After these witness introductions, the existing exists-intro and leads-to-trans rules should close the main goal. Re-run Verus: the two previously failing entailments should pass, leaving only any pre-existing trigger notes.

</details>

[起点源码](checkpoints/CP03.rs) · [hint原文件](v1/CP03/hint.json) · [全部修改与工具反馈](v1/CP03/PROCESS.md) · [最终源码](v1/CP03/final.rs) · [最终验证](v1/CP03/result.json)


<a id="v2-cp3"></a>
### v2：抽象化泛型桥接后超时

**客观起点（原trace事件84）。** 原两处存在状态到tla_exists的entailment失败。

**Hint作何判断。** 明确两个见证及implies，数学方向成立；没有要求泛化出通用引理。

**实际编辑与验证顺序。**

| 阶段／事件 | 实际尝试与诊断 | 为什么还不够 |
|---|---|---|
| 56–61：两个专用helper | 将两处entailment移到辅助函数，调用后trigger推断失败 | helper合同也必须证明，拆函数不自动产生存在见证 |
| 69–91：改量词表达 | 改implies、trigger和状态量词，先解析失败再断言失败 | 在合法表达式中证明状态／时序桥接仍未完成 |
| 100–112：新增泛型提升 | 引入state存在性→tla_exists通用helper，处理其trigger | 多了通用合同和调用处实例化义务，部分断言／后置条件仍失败 |
| 117–133：补存在实例 | 添加existential、trigger，再命名temporal family | 两个专用helper调用通用helper的前提及自身后置条件仍未通过 |
| 最终宿主验证 | 2 verified,2 errors；Lynette通过 | 只有部分函数被验证，整个目标未完成，不得把两项局部通过当作成功终点 |

**为什么这些修改有效，或仍然失败。** 专用helper试图把两处execution级entailment移出主函数；之后又抽象成对任意state_pred和消息族都适用的泛型提升引理。这扩大了当前要管理的closure、trigger和合同实例化范围。结尾泛型调用的前提在两个专用helper处未被验证，专用helper后置条件也未通过；因此即便验证统计有2 verified，整体任务仍未解。

**Hint究竟起了什么作用。** hint推荐的是在当前execution上取具体消息，没有要求这层泛化。泛化方向本身不能仅因超时判为数学错误，但本次实现未证成；不能把helper的ensures当现成事实输入训练。日志不支持将失败归为Lynette，因为它最终通过。

**同起点两版对照。** v1同点在原主体用if保护两个见证即成功。本点较有诊断价值的对照是“就地补上下文”与“额外泛化并承担新合同”，不是正确hint与错误hint的简单二分。 见[另一版CP3](v1/REPORT.md#cp3)。

**语义审计结论。** 真实未解。泛型化是actor自行扩展，不能说hint误导添加错误公理；也不能把2 verified当整体成功。本点仅作失败对照。

**最终检查边界。** 宿主Verus=失败，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。 最终Verus统计为`verification results:: 2 verified, 2 errors`。

```text
error: postcondition not satisfied
error: precondition not satisfied
error: postcondition not satisfied
error: precondition not satisfied
```

<details><summary>本次实际发送的hint全文</summary>

Your two remaining failures are the semantic entailments `p.entails(tla_exists(p_resp))` and `q_mid.entails(tla_exists(p_req))`. The surrounding `leads_to` composition is already present; Verus sees the bundled existential state predicates but cannot automatically choose a message witness satisfying the stronger per-message predicate used by `tla_exists`. Next, prove each entailment by expanding it over an arbitrary execution and naming the witness explicitly from the head state. For the first: from `p`'s list-response existential, select the response that is in flight, matches the pending list request, and carries the OK-list-pods payload; then establish the concrete condition `resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step` and conclude `p_resp(resp_msg)` holds on that execution. For the second: from `q_mid`'s create-request conditions, select the message that is the controller's pending create-pod request and satisfies `AfterCreatePod(d)`; then establish the concrete request predicate and `p_req(req_msg)`. Re-run Verus after both expansions. If you write `assert forall`, use `implies` for the antecedent. The deprecation warning is pre-existing and not the blocker.

</details>

[起点源码](checkpoints/CP03.rs) · [hint原文件](v2/CP03/hint.json) · [全部修改与工具反馈](v2/CP03/PROCESS.md) · [最终源码](v2/CP03/final.rs) · [最终验证](v2/CP03/result.json)

<a id="cp4"></a>
## CP4：同一起点，两版如何处理

**直接对照。** 两版都覆盖前提和响应／请求见证；v2把源谓词到具体见证的对应写得更紧凑明确。actor少了一些直接choose强谓词的试错，但不是v2独有第二层数学目标。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 16,692 | 5 | 通过 |
| v2 | 13,338 | 4 | 通过 |

<a id="v1-cp4"></a>
### v1：前提与见证两层均有提示，actor延迟落实

**客观起点（原trace事件92）。** forall ==>导致proof体无前提；修后还有存在桥接。

**Hint作何判断。** 全文第一段要求implies引入前提，第二段明确预告tla_exists的存在见证问题，要求对响应或请求按底层条件命名见证并建立具体消息谓词。旧审计漏读第二段，不能称提示只覆盖第一层。

**实际编辑与验证顺序。** 44改implies，46仍两失败；52直接choose强谓词，54失败；60重述existential，62失败；83改从原始in-flight/matching/OK条件取响应见证，85仍有未闭合义务；94补pending请求和family实例，96／100双通过。

**为什么这些修改有效，或仍然失败。** 改implies恢复源状态假设，只能让已有事实进入上下文，并不能自动把打包存在谓词转换成目标强消息谓词。直接choose目标强谓词等于先要求证明尚未建立的存在性，因此重写assert仍无帮助。必须回到已知的in-flight/matching/OK条件选响应，随后建立family；请求侧也要明确取pending消息，才能闭合主链。

**Hint究竟起了什么作用。** 完整hint已明确预告存在桥接。actor先修implies，随后数轮才从底层消息条件落实见证，属于延迟落实而非自行发现未提示的问题。第一段的component assertions应解决只宜解释为前提相关断言，不能截掉第二段后作整体判断。

**同起点两版对照。** 两版都覆盖前提和响应／请求见证；v2把源谓词到具体见证的对应写得更紧凑明确。actor少了一些直接choose强谓词的试错，但不是v2独有第二层数学目标。 见[另一版CP4](v2/REPORT.md#cp4)。

**语义审计结论。** 两层提示均有依据；actor直接choose强谓词及重述存在断言的绕路，不能归因为hint未提醒见证。最终修复合理，仍需区分提示采纳与actor的具体实现选择。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failures are proof-context failures, not missing mathematical facts. The verifier warns that the spec-level implication in `assert forall` does not assume its antecedent inside the proof body. In the two entailment proofs, the body tries to use the assumptions `p.satisfied_by(ex)` and `q_mid.satisfied_by(ex)` to prove the corresponding conjuncts, but those assumptions are not available. Rewrite the outer implication in each `assert forall` to the constructive implication form that makes the antecedent available (`implies`). After that, the component assertions should be discharged.

The next expected obstacle is the existential goal for `tla_exists`: Verus will not synthesize the message witness from the expanded predicate alone. Explicitly assert the existential over an in-flight response or request matching the expanded conditions, name a witness using `choose`, and then assert the corresponding `..._is_the_...` predicate for that witness. Check with Verus; the target is `verification results:: 1 verified, 0 errors`, then run Lynette.

</details>

[起点源码](checkpoints/CP04.rs) · [hint原文件](v1/CP04/hint.json) · [全部修改与工具反馈](v1/CP04/PROCESS.md) · [最终源码](v1/CP04/final.rs) · [最终验证](v1/CP04/result.json)


<a id="v2-cp4"></a>
### v2：按两层提示逐步完成

**客观起点（原trace事件92）。** forall缺前提，之后需具体消息见证。

**Hint作何判断。** 同时覆盖implies和两侧见证；v1全文第二段也有该预告，两版主要差别是表达具体程度，不能称v2才覆盖完整义务。

**实际编辑与验证顺序。** 49改implies，51仍失败；70按底层条件构造响应见证，72仍失败；78补响应family与tla_exists实例，80仍失败；86补pending请求各性质及family，88／93双通过。

**为什么这些修改有效，或仍然失败。** 先用implies拿到P/Q前提，再展开响应原始条件，只解决了状态层一部分。还必须把这个响应带回p_resp(resp).satisfied_by，并使tla_exists在同一execution成立；只证明消息属性不能替代时序family衔接。最后对pending请求补同样连接，两条桥接才都完整。

**Hint究竟起了什么作用。** hint明确给出前提和见证两层，actor方向一致，但响应family直到下一轮才显式补上。两次响应侧编辑并不代表hint提了两个不同策略，而是同一桥接分步落实。

**同起点两版对照。** v1全文也包含见证提醒。v2更明确串起P/Q与相应消息见证；观察到较少直接猜强谓词的尝试，但不能从本次执行差异证明提示增量的因果作用。 见[另一版CP4](v1/REPORT.md#cp4)。

**语义审计结论。** 每次修改有明确目标，最终对应hint要求；首次失败仍在，不能写成提前避开。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Verus is not assuming the antecedent of the two `assert forall` implications because they are written with `==>`. Consequently, inside the proof of `p.entails(tla_exists(p_resp))`, the antecedents `exists_resp_in_flight_at_after_list_pods_step(...)` and `num_diff_pods_is(...)` are not available, so those assertions fail. Change these proof-local implications to Verus's logical `implies` so the antecedent is assumed. Then use the assumed `p` to name a concrete response message satisfying the in-flight/response-match/ok-list-response conditions, and show that same message satisfies `resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step`, giving the `tla_exists(p_resp)` witness. Apply the same pattern to the later `q_mid.entails(tla_exists(p_req))`: name the concrete create-request message from `pending_req_in_flight_at_after_create_pod_step` and prove the stronger per-message predicate. Run Verus after the implication fix; any next failures should point to the witness-extraction step.

</details>

[起点源码](checkpoints/CP04.rs) · [hint原文件](v2/CP04/hint.json) · [全部修改与工具反馈](v2/CP04/PROCESS.md) · [最终源码](v2/CP04/final.rs) · [最终验证](v2/CP04/result.json)

<a id="cp5"></a>
## CP5：同一起点，两版如何处理

**直接对照。** v2 CP5在主函数里直接写两侧见证，没有抽helper；两者可对比证明分解方式，但不是不同控制器进展定理。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 13,864 | 2 | 通过 |
| v2 | 11,692 | 2 | 通过 |

<a id="v1-cp5"></a>
### v1：把两个见证抽成有证明体的辅助引理

**客观起点（原trace事件100）。** 整体存在状态到具体消息family未桥接。

**Hint作何判断。** 提示按底层条件命名见证，并处理响应、请求两侧。

**实际编辑与验证顺序。** 68新增两个有requires/ensures和完整proof体的消息见证引理；71在主证明调用并实例化family；74 Verus报告3 verified,0 errors，79 Lynette通过。

**为什么这些修改有效，或仍然失败。** 两个helper把“从状态条件取出具体消息”单独做成可验证合同：响应helper展开匹配和OK列表内容，请求helper取pending请求并核对来源／类型／阶段。主函数再用helper的存在结论选择消息，证明对应family在execution成立。这样分层隔开状态推理与时序组合，但没有跳过任何合同证明。

**Hint究竟起了什么作用。** helper这一模块化组织由actor选择，hint只要求命名见证及建立强谓词。两者数学一致，最后3 verified表明新增helper也在本次验证范围，不能将它们误认作新增未证明公理。

**同起点两版对照。** v2 CP5在主函数里直接写两侧见证，没有抽helper；两者可对比证明分解方式，但不是不同控制器进展定理。 见[另一版CP5](v2/REPORT.md#cp5)。

**语义审计结论。** 较有价值的证明分解样本；不是新增external_body公理。数学核心仍是见证桥接，只是模块化方式不同。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The remaining failure is the embedding from an anonymous existential in the hypothesis p into the tla_exists family p_resp. You know exists_resp_in_flight_at_after_list_pods_step holds at state s, so there is some in-flight message satisfying the matching-response and ok-list-response conditions. Verus does not automatically infer the stronger predicate resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step for that same message. Next objective: after unfolding p for an arbitrary execution, explicitly assert the existential over the primitive in-flight/matching/ok-list-response conditions, then name that existential witness and use it to prove the stronger concrete list-response predicate. That gives tla_exists(p_resp) a witness and closes the first entailment assertion. Apply the same named-witness pattern to the analogous q_mid to tla_exists(p_req) step, where the pending create request is the witness. Rerun Verus; the two current assertion failures should disappear. Avoid adding trigger-only workarounds before establishing the named witnesses.

</details>

[起点源码](checkpoints/CP05.rs) · [hint原文件](v1/CP05/hint.json) · [全部修改与工具反馈](v1/CP05/PROCESS.md) · [最终源码](v1/CP05/final.rs) · [最终验证](v1/CP05/result.json)


<a id="v2-cp5"></a>
### v2：响应侧展开更具体，也提醒了请求侧

**客观起点（原trace事件100）。** 起点两处断言失败。

**Hint作何判断。** 全文第二段明确要求取响应见证、建立具体谓词及family.satisfied_by，并提醒q_mid到tla_exists(p_req)也很可能需要同样处理。覆盖两侧，但请求侧措辞较条件化；旧审计仅据首段判为遗漏请求侧，现纠正。

**实际编辑与验证顺序。** 55完整补响应见证和family实例，57仍失败；63补请求源、in-flight、类型及family，65／70双通过。请求侧修复与hint后段提醒相符，具体直接取pending消息由actor实现。

**为什么这些修改有效，或仍然失败。** 响应侧从实际in-flight/matching/OK条件取见证，再逐项恢复强消息谓词和family实例，这一链合理。请求侧不必机械再写choose：pending消息已经由源状态指定，只要验证阶段、in-flight、来源及请求类型，就能作为同一存在目标的见证。两种取见证方式都不添加新假设。

**Hint究竟起了什么作用。** hint全文已预告请求侧，因此actor第二次修复与提示方向对应；提示没有规定helper还是内联，也没有提供全部请求代码，具体实现选择仍由actor完成。

**同起点两版对照。** 两版都提醒两侧见证。v1强调两侧都需命名见证并抽出helper；v2更显式写响应family在execution上的实例，actor内联完成。区别是展开粒度及证明分解，而非有没有请求侧提醒。 见[另一版CP5](v1/REPORT.md#cp5)。

**语义审计结论。** 有用的两侧桥接提示，响应侧较详细、请求侧较简略。第二次修复可以视为响应了提示中的请求侧预告，不能再判为完全未被提示的自行推进。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is in proving `p.entails(tla_exists(p_resp))`. The antecedent `p` provides `exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)` and `num_diff_pods_is(vrs, diff)(s)`, while the goal is an existential over a response satisfying `resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step`. Verus does not automatically connect these because the target predicate bundles several conditions under one named spec function; the current proof asserts the bundled existential directly without naming a witness.

Next objective: extract the response already asserted by `exists_resp_in_flight_at_after_list_pods_step` as an explicit in-flight response whose `resp_msg_matches_req_msg` and `resp_msg_is_ok_list_resp_containing_matching_pods` conditions hold, then prove that this same response satisfies `resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step`. The required step and diff facts are already available from `p`; after that, `p_resp(resp_msg).satisfied_by(ex)` follows and discharges `tla_exists(p_resp)`. The same witness-naming approach will likely be needed later for `q_mid.entails(tla_exists(p_req))`. Check by rerunning Verus; the expected change is that the failing existential assertions disappear, possibly leaving only trigger notes.

</details>

[起点源码](checkpoints/CP05.rs) · [hint原文件](v2/CP05/hint.json) · [全部修改与工具反馈](v2/CP05/PROCESS.md) · [最终源码](v2/CP05/final.rs) · [最终验证](v2/CP05/result.json)

<a id="cp6"></a>
## CP6：同一起点，两版如何处理

**直接对照。** v2同样只删两处属性，差异主要在输出长度与运行时间。

| 版本 | Actor输出token | 源码变化次数 | 最终双通过 |
|---|---:|---:|---|
| v1 | 3,758 | 1 | 通过 |
| v2 | 2,838 | 1 | 通过 |

<a id="v1-cp6"></a>
### v1：只回退非法auto属性

**客观起点（原trace事件123）。** choose内部两处#![auto]不能识别；此前证明已经验证。

**Hint作何判断。** 正确区分trigger notes与错误，要求仅删非法属性。

**实际编辑与验证顺序。** 31删除两处属性，33／38双通过，未为清除提示继续改正确证明。

**为什么这些修改有效，或仍然失败。** 原轨迹为消除低置信trigger提示加了choose内部auto属性，反而引发解析错误。删掉两处非法标注保留原见证、前提和leads-to链，所以是恢复此前正确代码，不是重新解决存在桥接。剩余trigger notes不妨碍验证，不需为了“输出干净”继续破坏证明。

**Hint究竟起了什么作用。** 提示相当具体且直接被采纳；它展示的是区分warning/note与error、避免过度修复的价值，不能当作新数学策略发现。

**同起点两版对照。** v2同样只删两处属性，差异主要在输出长度与运行时间。 见[另一版CP6](v2/REPORT.md#cp6)。

**语义审计结论。** 具体语法修复而非新数学路径，适合诊断纠错材料。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is syntactic, not a proof gap: Verus rejects two `#![auto]` trigger annotations inside `choose` witness expressions with `cannot find attribute auto in this scope`. These annotations were added only to quiet low-confidence trigger notes; in this Verus version, that annotation form is not accepted inside `choose` closures. The proof immediately before that change already verified the lemma with `1 verified, 0 errors`, producing only informational trigger notes on the two witness selections and the pre-existing `#[is_variant]` deprecation warning. Therefore, the next objective is to restore that verified structure by removing the two invalid `#![auto]` annotations while keeping the surrounding existential-witness extraction and leads-to composition unchanged. Re-run Verus and expect it to return to `1 verified, 0 errors` with only the same informational notes and warning; then re-run Lynette, which should still pass. Do not modify specifications, behavior, or the existing proof strategy.

</details>

[起点源码](checkpoints/CP06.rs) · [hint原文件](v1/CP06/hint.json) · [全部修改与工具反馈](v1/CP06/PROCESS.md) · [最终源码](v1/CP06/final.rs) · [最终验证](v1/CP06/result.json)


<a id="v2-cp6"></a>
### v2：保留证明，仅删非法属性

**客观起点（原trace事件123）。** 两处choose内auto属性导致编译错误。

**Hint作何判断。** 诊断准确、变更范围清晰。

**实际编辑与验证顺序。** 26删除两处属性，28／32双通过。

**为什么这些修改有效，或仍然失败。** 删除auto属性没有改变见证选择条件，也没有改requires/ensures；数学主干沿用已有正确版本。Verus通过后Lynette也通过，说明这次最小源码变更同时满足两项任务要求。信息性trigger提示不是失败，不该继续为消提示增加无关代码。

**Hint究竟起了什么作用。** hint准确指出“没有新的数学缺口”，actor保持原结构，没有额外绕到存在性或导入问题。它是工具诊断的正例，增广价值在避免不必要修改。

**同起点两版对照。** v1相同起点、相同类型的一次属性删除，不能称为新的解法路线。 见[另一版CP6](v1/REPORT.md#cp6)。

**语义审计结论。** 与v1同种工具修复，未产生新策略。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The proof itself is already complete; the current blocker is a Verus syntax/attribute error, not a missing logical fact. The two `auto` attributes just added to the witness-choosing `choose` bodies are not recognized in this Verus version, as the diagnostic reports. Remove only those two annotations and keep the surrounding `choose`/witness extraction proof structure unchanged. That restores the earlier state which Verus accepted with zero errors; the remaining low-confidence quantifier trigger notes are informational, not failures. After the removal, rerun Verus first: expect verification to pass with zero errors and possibly the same trigger notes. Then rerun Lynette to confirm the edit remains proof-only. No structural compatibility concern is supported here; the same proof-only change was accepted by Lynette after restoring that state.

</details>

[起点源码](checkpoints/CP06.rs) · [hint原文件](v2/CP06/hint.json) · [全部修改与工具反馈](v2/CP06/PROCESS.md) · [最终源码](v2/CP06/final.rs) · [最终验证](v2/CP06/result.json)

## 使用与证据边界

逐点结论针对保存的真实代码和工具反馈。成功终点可进入待格式整理的训练候选，但失败中间态必须标错，不能把hint预测、错误API或actor自述当成有效事实。AC v1 CP1与v2 CP3为未解对照，不混入成功数据。尚未评估SkillOpt收益。

本报告整合两版已有详细审计，未重新运行实验；完整hint、每次编辑、工具反馈、最终源码与验证仍可从各点链接打开。所有本地链接使用相对路径，原数据未修改。
