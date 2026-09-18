# AC · Initial skill + Hint v1：逐checkpoint语义审计

**本版全部6条过程审计完成，待用户复核。** 审查保存的起点、hint正文、每次源码变化、实际工具反馈及最终宿主验证；本次没有重新调用模型或验证器。最终正确与中间每一步正确分开判断。

两版均5/6，但失败点不同：v1 CP1、v2 CP3，均约600秒actor超时且最终Verus失败、Lynette通过。v1 CP2筛查误报已补跑成功。核心难点是将状态层消息存在性落实到temporal family见证，不能把失败笼统归为兼容提醒。

## 先读懂原题与原F

本题要证明：从收到list-pods响应的状态，最终到达收到create-pod成功响应的状态，并把pod数量差从diff推进到diff+1。原文件已有两个消息级组件引理，分别处理“具体list响应→pending create请求”和“具体create请求→成功响应”。当前任务是组合它们，不是重证整个控制器。

令P表示整体list响应状态，Q表示pending create状态，R表示目标成功响应状态。原F的逻辑连接为：`P → 存在具体响应 → Q → 存在具体请求 → R`。消息级leads-to引理经`leads_to_exists_intro`提升后，只证明两个消息族的进展；仍需单独证明P蕴含响应族的`tla_exists`，以及Q蕴含请求族的`tla_exists`。

因此“状态中存在某消息”与“某个temporal family在此execution成立”之间不是靠重述目标就自动打通的：必须在execution的head上得到消息见证、验证具体消息谓词，再建立family实例。响应通常从in-flight/matching/OK条件取choose见证；请求可以直接取已经存在的pending消息。CP2是trigger层，CP3是这两个桥接，CP4还有前提未进入量词proof体，CP5仍缺具体见证，CP6则是正确证明被非法auto属性打断。

## 图与版本对照

![同initial skill的两版hint对照](../v2/comparison_prefix_tokens.png)

两版actor输出合计：v1 **106,677**，v2 **90,178**（-15.5%）。包括失败续跑和结束说明，hint生成另计。上图为相对原F的Patch F1，即参考路径相似度；下图为同一观测的Verus状态。横轴包含原前缀归属token，但actor并未回放原前缀；彩色竖虚线仅标首次提取到的Verus通过，不等于Lynette／整个任务完成。

[本版单组图](hint_prefix_tokens.png) · [v1审计](REPORT.md) · [v2审计](../v2/REPORT.md) · [图表数据](../comparison.json)

## 数据和条件核对

来源为Yuechun固定train40中本题的step_0001 DeepSeek v4 Pro原轨迹。全部起点沿用冻结的Yuechun checkpoint提取逻辑；没有按结果另选checkpoint。原轨迹和本轮actor均通过工作区SKILL.md装备同一initial skill，SHA256为`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`。本版每条实际读取全文的事件见下表；不是仅根据文件存在推断使用。

Actor获原题、完整checkpoint代码、fresh hint和skill；hint agent可看原完整轨迹与F。没有把原完整对话或F直接发给actor。38个hint全新生成，旧blank组保持不动。新旧同时变化了skill和hint样本，不能把actor差异单独归因于skill；本轮v1/v2也仅各一次采样，不支持稳定因果结论。

[原题规格与源码](../original_input.rs) · [原trace最终源码F](../original_final.rs) · [原轨迹](../ORIGINAL_CHANGES.md) · [Skill装备核对](../../SKILL_PARITY.md)

## 本版逐点结果

| CP | Actor输出token | 源码变化次数 | 读取skill事件 | 最终Verus＋Lynette |
|---|---:|---:|---|---|
| [CP1](#cp1) | 36,977 | 18 | 19 | 失败：Verus未解、Lynette通过 |
| [CP2](#cp2) | 24,777 | 7 | 9 | 通过 |
| [CP3](#cp3) | 10,609 | 2 | 11 | 通过 |
| [CP4](#cp4) | 16,692 | 5 | 8 | 通过 |
| [CP5](#cp5) | 13,864 | 2 | 15 | 通过 |
| [CP6](#cp6) | 3,758 | 1 | 16 | 通过 |

事件编号使用本条agent_events.jsonl的event_index；源码变化取snapshot差分事件，工具编号取完成命令事件，可能与图中随后保存的verifier事件相差1，不是不同轨迹。源码变化次数不是提取后的checkpoint数。

同版本旧blank审计另见旧v1报告（未随本次发布的本地材料）。下面的逐点版本对照均指**本轮两个initial-skill组**，不混用旧blank结果。

## 逐checkpoint语义审计

<a id="cp1"></a>
### CP1：长时间构造辅助引理，两个桥接未闭合

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

**同起点两版对照。** v2 CP1在主体内按两个execution展开分别补见证后成功，没有陷入本点长时间helper改写。相同起点一次成败差异，不能单独归为skill或版本能力。 见[另一版CP1](../v2/REPORT.md#cp1)。

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

[起点源码](../checkpoints/CP01.rs) · [hint原文件](CP01/hint.json) · [全部修改与工具反馈](CP01/PROCESS.md) · [最终源码](CP01/final.rs) · [最终验证](CP01/result.json)

<a id="cp2"></a>
### CP2：补跑通过，literal_call是筛查误报

**客观起点（原trace事件77）。** forall缺trigger，随后两处存在见证桥接失败。

**Hint作何判断。** 明确标出量词entailment作为trigger并提示两处见证；含较具体表达式而非整段proof。筛查命中不是数学错误，放行记录保留。

**实际编辑与验证顺序。** 37加trigger，40两断言失败；61拆状态函数及见证proof，64触发器失败；77补trigger，80失败；86改closure，89失败；101改implies但仍有局部遮蔽／桥接问题，104失败；110去多余局部声明并直接响应见证，113只剩请求；119补请求见证，122／127双通过。

**为什么这些修改有效，或仍然失败。** trigger修复只让量词被接纳；两条高层entailment仍需实际见证。中间把状态谓词拆开后，又在量词proof体声明同名局部s/ex，造成证明对象与原量词上下文脱节；仅换implies不能替代移除这些多余声明。后面回到给定execution的head取响应，再取pending请求，才真正把两侧family连接完成。

**Hint究竟起了什么作用。** literal_call筛查命中较具体数学表达式属于既有人工放行，不是actor的证明错误。提示预告了正确的下一层，但actor在实现时引入额外变量／closure复杂性，故不能说它提前避开了失败。

**同起点两版对照。** v2也经历前提和assert语法修复，但没有本点长链的状态函数重构，输出明显较少；终点依然同一种见证组合策略。 见[另一版CP2](../v2/REPORT.md#cp2)。

**语义审计结论。** 提示预告准确，actor最终落实但绕路较多；不能把筛查误报计作失败。保留原hint不重生成，补跑结果是本点正式结果。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

At this checkpoint the immediate error is missing quantifier triggers, not a missing proof fact. The first forall assertion over resp_msg is intended to establish the quantified precondition needed by leads_to_exists_intro, but Verus cannot infer a trigger and therefore cannot instantiate that assertion against the rule. Add an explicit trigger on the quantified entailment term spec.entails(p_resp(resp_msg).leads_to(q_mid)); apply the analogous trigger to the later forall over req_msg using p_req. Re-run Verus after this change. If it advances to assertion failures on p.entails(tla_exists(p_resp)) or q_mid.entails(tla_exists(p_req)), the next objective is not to add assumptions: unfold the existential temporal predicate at the current ClusterState, name a concrete in-flight Message witness, and use that witness to satisfy the tla_exists predicate rather than trying to discharge the existential directly.

</details>

[起点源码](../checkpoints/CP02.rs) · [hint原文件](CP02/hint.json) · [全部修改与工具反馈](CP02/PROCESS.md) · [最终源码](CP02/final.rs) · [最终验证](CP02/result.json)

<a id="cp3"></a>
### CP3：见证路线正确，第一次缺前提

**客观起点（原trace事件84）。** 主链已存在，两个entailment断言未闭合。

**Hint作何判断。** 指出在满足源谓词的execution上选择已有消息，数学判断正确。

**实际编辑与验证顺序。** 56补两个forall见证，但==>未把前提带入proof体，58失败；64给两个主体增加对应if前提保护，66／71双通过。

**为什么这些修改有效，或仍然失败。** choose需要源状态前提来保证存在消息；最初forall虽写了==>，proof体没有自动取得前件，因此不能无条件用head中的消息。加if后，选响应和请求都处于相应源谓词成立的分支，family实例才能有根据。这个if不是缩小原定理要求：它正对应要证明的蕴含前件。

**Hint究竟起了什么作用。** hint要求“在满足P/Q的execution上”推理，actor第一次未忠实编码这一条件，第二次才完成。提示数学正确，首个实现不正确；报告不把后者当合理已证事实。

**同起点两版对照。** v2 CP3另造专用／泛型桥接后超时，本版就地增加前提保护已成功。说明相同可行提示可以引出差异很大的实现路径。 见[另一版CP3](../v2/REPORT.md#cp3)。

**语义审计结论。** 合理的上下文修复；失败起于actor未落实“满足源谓词”的局部条件。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The remaining two failures are witness-introduction goals for `tla_exists`, not complex temporal-reasoning gaps. The high-level composition structure is already present. For `p.entails(tla_exists(p_resp))`, reason over an arbitrary execution whose head satisfies `p`. That head gives `exists_resp_in_flight_at_after_list_pods_step`, whose definition already contains an existential response message with the in-flight, response-match, and OK-list-response conditions. Bind that existing response message as a named witness, then show it satisfies the exact pointwise predicate behind `p_resp`; the `num_diff_pods_is` part follows from `p`. For `q_mid.entails(tla_exists(p_req))`, do the analogous step: the head satisfying `q_mid` gives `pending_req_in_flight_at_after_create_pod_step`, whose definition contains the pending in-flight create request and the `AfterCreatePod(d)` step. Bind that request as the witness and show it satisfies the pointwise predicate behind `p_req`. After these witness introductions, the existing exists-intro and leads-to-trans rules should close the main goal. Re-run Verus: the two previously failing entailments should pass, leaving only any pre-existing trigger notes.

</details>

[起点源码](../checkpoints/CP03.rs) · [hint原文件](CP03/hint.json) · [全部修改与工具反馈](CP03/PROCESS.md) · [最终源码](CP03/final.rs) · [最终验证](CP03/result.json)

<a id="cp4"></a>
### CP4：前提与见证两层均有提示，actor延迟落实

**客观起点（原trace事件92）。** forall ==>导致proof体无前提；修后还有存在桥接。

**Hint作何判断。** 全文第一段要求implies引入前提，第二段明确预告tla_exists的存在见证问题，要求对响应或请求按底层条件命名见证并建立具体消息谓词。旧审计漏读第二段，不能称提示只覆盖第一层。

**实际编辑与验证顺序。** 44改implies，46仍两失败；52直接choose强谓词，54失败；60重述existential，62失败；83改从原始in-flight/matching/OK条件取响应见证，85仍有未闭合义务；94补pending请求和family实例，96／100双通过。

**为什么这些修改有效，或仍然失败。** 改implies恢复源状态假设，只能让已有事实进入上下文，并不能自动把打包存在谓词转换成目标强消息谓词。直接choose目标强谓词等于先要求证明尚未建立的存在性，因此重写assert仍无帮助。必须回到已知的in-flight/matching/OK条件选响应，随后建立family；请求侧也要明确取pending消息，才能闭合主链。

**Hint究竟起了什么作用。** 完整hint已明确预告存在桥接。actor先修implies，随后数轮才从底层消息条件落实见证，属于延迟落实而非自行发现未提示的问题。第一段的component assertions应解决只宜解释为前提相关断言，不能截掉第二段后作整体判断。

**同起点两版对照。** 两版都覆盖前提和响应／请求见证；v2把源谓词到具体见证的对应写得更紧凑明确。actor少了一些直接choose强谓词的试错，但不是v2独有第二层数学目标。 见[另一版CP4](../v2/REPORT.md#cp4)。

**语义审计结论。** 两层提示均有依据；actor直接choose强谓词及重述存在断言的绕路，不能归因为hint未提醒见证。最终修复合理，仍需区分提示采纳与actor的具体实现选择。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failures are proof-context failures, not missing mathematical facts. The verifier warns that the spec-level implication in `assert forall` does not assume its antecedent inside the proof body. In the two entailment proofs, the body tries to use the assumptions `p.satisfied_by(ex)` and `q_mid.satisfied_by(ex)` to prove the corresponding conjuncts, but those assumptions are not available. Rewrite the outer implication in each `assert forall` to the constructive implication form that makes the antecedent available (`implies`). After that, the component assertions should be discharged.

The next expected obstacle is the existential goal for `tla_exists`: Verus will not synthesize the message witness from the expanded predicate alone. Explicitly assert the existential over an in-flight response or request matching the expanded conditions, name a witness using `choose`, and then assert the corresponding `..._is_the_...` predicate for that witness. Check with Verus; the target is `verification results:: 1 verified, 0 errors`, then run Lynette.

</details>

[起点源码](../checkpoints/CP04.rs) · [hint原文件](CP04/hint.json) · [全部修改与工具反馈](CP04/PROCESS.md) · [最终源码](CP04/final.rs) · [最终验证](CP04/result.json)

<a id="cp5"></a>
### CP5：把两个见证抽成有证明体的辅助引理

**客观起点（原trace事件100）。** 整体存在状态到具体消息family未桥接。

**Hint作何判断。** 提示按底层条件命名见证，并处理响应、请求两侧。

**实际编辑与验证顺序。** 68新增两个有requires/ensures和完整proof体的消息见证引理；71在主证明调用并实例化family；74 Verus报告3 verified,0 errors，79 Lynette通过。

**为什么这些修改有效，或仍然失败。** 两个helper把“从状态条件取出具体消息”单独做成可验证合同：响应helper展开匹配和OK列表内容，请求helper取pending请求并核对来源／类型／阶段。主函数再用helper的存在结论选择消息，证明对应family在execution成立。这样分层隔开状态推理与时序组合，但没有跳过任何合同证明。

**Hint究竟起了什么作用。** helper这一模块化组织由actor选择，hint只要求命名见证及建立强谓词。两者数学一致，最后3 verified表明新增helper也在本次验证范围，不能将它们误认作新增未证明公理。

**同起点两版对照。** v2 CP5在主函数里直接写两侧见证，没有抽helper；两者可对比证明分解方式，但不是不同控制器进展定理。 见[另一版CP5](../v2/REPORT.md#cp5)。

**语义审计结论。** 较有价值的证明分解样本；不是新增external_body公理。数学核心仍是见证桥接，只是模块化方式不同。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The remaining failure is the embedding from an anonymous existential in the hypothesis p into the tla_exists family p_resp. You know exists_resp_in_flight_at_after_list_pods_step holds at state s, so there is some in-flight message satisfying the matching-response and ok-list-response conditions. Verus does not automatically infer the stronger predicate resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step for that same message. Next objective: after unfolding p for an arbitrary execution, explicitly assert the existential over the primitive in-flight/matching/ok-list-response conditions, then name that existential witness and use it to prove the stronger concrete list-response predicate. That gives tla_exists(p_resp) a witness and closes the first entailment assertion. Apply the same named-witness pattern to the analogous q_mid to tla_exists(p_req) step, where the pending create request is the witness. Rerun Verus; the two current assertion failures should disappear. Avoid adding trigger-only workarounds before establishing the named witnesses.

</details>

[起点源码](../checkpoints/CP05.rs) · [hint原文件](CP05/hint.json) · [全部修改与工具反馈](CP05/PROCESS.md) · [最终源码](CP05/final.rs) · [最终验证](CP05/result.json)

<a id="cp6"></a>
### CP6：只回退非法auto属性

**客观起点（原trace事件123）。** choose内部两处#![auto]不能识别；此前证明已经验证。

**Hint作何判断。** 正确区分trigger notes与错误，要求仅删非法属性。

**实际编辑与验证顺序。** 31删除两处属性，33／38双通过，未为清除提示继续改正确证明。

**为什么这些修改有效，或仍然失败。** 原轨迹为消除低置信trigger提示加了choose内部auto属性，反而引发解析错误。删掉两处非法标注保留原见证、前提和leads-to链，所以是恢复此前正确代码，不是重新解决存在桥接。剩余trigger notes不妨碍验证，不需为了“输出干净”继续破坏证明。

**Hint究竟起了什么作用。** 提示相当具体且直接被采纳；它展示的是区分warning/note与error、避免过度修复的价值，不能当作新数学策略发现。

**同起点两版对照。** v2同样只删两处属性，差异主要在输出长度与运行时间。 见[另一版CP6](../v2/REPORT.md#cp6)。

**语义审计结论。** 具体语法修复而非新数学路径，适合诊断纠错材料。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is syntactic, not a proof gap: Verus rejects two `#![auto]` trigger annotations inside `choose` witness expressions with `cannot find attribute auto in this scope`. These annotations were added only to quiet low-confidence trigger notes; in this Verus version, that annotation form is not accepted inside `choose` closures. The proof immediately before that change already verified the lemma with `1 verified, 0 errors`, producing only informational trigger notes on the two witness selections and the pre-existing `#[is_variant]` deprecation warning. Therefore, the next objective is to restore that verified structure by removing the two invalid `#![auto]` annotations while keeping the surrounding existential-witness extraction and leads-to composition unchanged. Re-run Verus and expect it to return to `1 verified, 0 errors` with only the same informational notes and warning; then re-run Lynette, which should still pass. Do not modify specifications, behavior, or the existing proof strategy.

</details>

[起点源码](../checkpoints/CP06.rs) · [hint原文件](CP06/hint.json) · [全部修改与工具反馈](CP06/PROCESS.md) · [最终源码](CP06/final.rs) · [最终验证](CP06/result.json)

## 可用于训练的范围

本版最终双通过项可作为待格式整理的训练候选，必须携带题目规格、完整checkpoint起点和真实编辑／工具结果。失败中间态保留失败标签，不把未验证断言、错误API、actor自述或hint的诊断预测变成已证明事实。终点正确不表示每个中间尝试都正确；失败后的有效修复本身可有价值。AC v1 CP1、AC v2 CP3只作失败对照，不混入成功样本。

逐条核对了checkpoint hash、最终candidate与宿主验证hash、input未变化及skill一致性。源码差分中未发现新增assume/admit/external_body/unimplemented绕过标记；AC题目原有组件stub不算本轮新增。见[source_checks.json](source_checks.json)。这些检查与源码阅读不等于对任意工具行为的安全证明；本报告不把一次通过当作下游skill收益证据。

本题策略差异依赖核心引理、见证与证明分解判断，不用hash/F1代替语义审计。所有hint也并非“纯数学”：宏限定、implies、删除非法属性等含实现指导，但未给出可直接粘贴的完整最终proof。成功的hint采纳只能说明行为对应，不能证明提速因果或跨题稳定性。

## Hint生成成本

| CP | 输入token | 输出token |
|---|---:|---:|
| [CP1](#cp1) | 234,418 | 2,537 |
| [CP2](#cp2) | 235,493 | 3,012 |
| [CP3](#cp3) | 235,823 | 2,477 |
| [CP4](#cp4) | 236,868 | 2,724 |
| [CP5](#cp5) | 236,222 | 2,250 |
| [CP6](#cp6) | 236,290 | 2,848 |

保留的自动证据原稿（未随本次发布的本地材料） · [结构化语义审计](semantic_audit.json)

[CP2筛查误报审计](CP02_SCREEN_AUDIT.md) · CP2补跑状态（未随本次发布的本地材料）。旧batch_status中的首次拦截是历史状态，不能覆盖本次成功结果。
