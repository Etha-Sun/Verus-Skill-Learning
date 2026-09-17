# IR · Initial skill + Hint v1：逐checkpoint语义审计

**本版全部6条过程审计完成，待用户复核。** 审查保存的起点、hint正文、每次源码变化、实际工具反馈及最终宿主验证；本次没有重新调用模型或验证器。最终正确与中间每一步正确分开判断。

两版均6/6。v1的CP1/2/5与v2的CP1/2/3复用同一个vstd定理，其余非末尾点保留双向见证；CP6仅修兼容。没有证据称v2始终避免导入错误：CP4/5仍先经历Lynette失败。

## 先读懂原题与原F

目标是`(s1 + s2).map(f) == s1.map(f) + s2.map(f)`，即“先取并集再映射”与“分别映射再取并集”相等。原F采用集合外延性：固定输出元素x，分别证明左右成员关系。正向从并集的映像中取a，利用a属于s1或s2；逆向从某一侧映像取a，再把a放回并集。两方向都必须先获得成员条件，才能合法选择存在见证。

原trace的CP1为空证明；CP2卡宏名称；CP3卡成员等价；CP4首先卡非法trigger；CP5缺choose所需前提；CP6数学已经成立，只剩宏引用／结构兼容。它们不是六道独立题，也不是六个从零解题样本。另一条合法路线是直接复用vstd中已经证明同一分配律的`lemma_map_union_commute`：这是证明依赖的变化，不是绕过验证。

## 图与版本对照

![同initial skill的两版hint对照](../v2/comparison_prefix_tokens.png)

两版actor输出合计：v1 **50,950**，v2 **50,657**（-0.6%）。包括失败续跑和结束说明，hint生成另计。上图为相对原F的Patch F1，即参考路径相似度；下图为同一观测的Verus状态。横轴包含原前缀归属token，但actor并未回放原前缀；彩色竖虚线仅标首次提取到的Verus通过，不等于Lynette／整个任务完成。

[本版单组图](hint_prefix_tokens.png) · [v1审计](REPORT.md) · [v2审计](../v2/REPORT.md) · [图表数据](../comparison.json)

## 数据和条件核对

来源为Yuechun固定train40中本题的step_0001 DeepSeek v4 Pro原轨迹。全部起点沿用冻结的Yuechun checkpoint提取逻辑；没有按结果另选checkpoint。原轨迹和本轮actor均通过工作区SKILL.md装备同一initial skill，SHA256为`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`。本版每条实际读取全文的事件见下表；不是仅根据文件存在推断使用。

Actor获原题、完整checkpoint代码、fresh hint和skill；hint agent可看原完整轨迹与F。没有把原完整对话或F直接发给actor。38个hint全新生成，旧blank组保持不动。新旧同时变化了skill和hint样本，不能把actor差异单独归因于skill；本轮v1/v2也仅各一次采样，不支持稳定因果结论。

[原题规格与源码](../original_input.rs) · [原trace最终源码F](../original_final.rs) · [原轨迹](../ORIGINAL_CHANGES.md) · [Skill装备核对](../../SKILL_PARITY.md)

## 本版逐点结果

| CP | Actor输出token | 源码变化次数 | 读取skill事件 | 最终Verus＋Lynette |
|---|---:|---:|---|---|
| [CP1](#cp1) | 9,201 | 1 | 18 | 通过 |
| [CP2](#cp2) | 8,408 | 2 | 11 | 通过 |
| [CP3](#cp3) | 6,449 | 1 | 18 | 通过 |
| [CP4](#cp4) | 16,649 | 1 | 15 | 通过 |
| [CP5](#cp5) | 7,167 | 1 | 6 | 通过 |
| [CP6](#cp6) | 3,076 | 1 | 5 | 通过 |

事件编号使用本条agent_events.jsonl的event_index；源码变化取snapshot差分事件，工具编号取完成命令事件，可能与图中随后保存的verifier事件相差1，不是不同轨迹。源码变化次数不是提取后的checkpoint数。

同版本旧blank审计另见旧v1报告（未随本次发布的本地材料）。下面的逐点版本对照均指**本轮两个initial-skill组**，不混用旧blank结果。

## 逐checkpoint语义审计

<a id="cp1"></a>
### CP1：转用标准库定理

**客观起点（原trace事件24）。** 空proof，目标为集合映射对并集的分配律。

**Hint作何判断。** 建议外延性、双向成员关系和受前提保护的见证；兼容句建议限定宏路径。数学方向正确，但不是唯一解法。

**实际编辑与验证顺序。** 事件73直接调用s1.lemma_map_union_commute(s2,f)，75 Verus、80 Lynette通过。此前查阅vstd，未手写hint建议的双向见证，也未新增导入。

**为什么这些修改有效，或仍然失败。** 这里没有发生“把choose证明压缩成一句无依据断言”。调用的是允许库内已有定理，其合同覆盖当前分配律；Verus负责检查调用和当前目标的衔接。因而与原F相比，关键变化是由本地双向见证转为定理复用，而不是省略一个必须由本题重新证明的事实。

**Hint究竟起了什么作用。** hint提供的是可行手写路线，actor没有实现它。可以观察到actor遵守了不新增导入的边界，但不能由此推出hint促成了库检索或替它选出了该定理。

**同起点两版对照。** 本轮v2也走库路线，但先猜错自由函数路径再改方法调用；两者终点策略相同，过程错误不同。 见[另一版CP1](../v2/REPORT.md#cp1)。

**语义审计结论。** 合法库定理复用；与原F的见证构造不同。数学hint未直接落实，不能说提示教会了该定理。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The empty body gives Verus no proof of the set equality. Prove it by set extensionality: for an arbitrary element x, show x is in (s1 + s2).map(f) exactly when x is in s1.map(f) + s2.map(f). Work one implication at a time. In each direction, make the membership hypothesis active with an explicit case split before eliminating the existential witness; otherwise choose cannot prove that the witness exists. For image membership, the witness is an a with a in s1 + s2 and f(a) == x; split on whether a lies in s1 or s2 to conclude membership in the corresponding image union. In the reverse direction, split on which image supplies the witness. Invoke the vstd set-extensionality mechanism by full path rather than adding a top-level import, because an added import can change generated Rust and fail the Lynette comparison. Check with run_verus after this, then run_lynette.

</details>

[起点源码](../checkpoints/CP01.rs) · [hint原文件](CP01/hint.json) · [全部修改与工具反馈](CP01/PROCESS.md) · [最终源码](CP01/final.rs) · [最终验证](CP01/result.json)

<a id="cp2"></a>
### CP2：先修宏，再换为库证明

**客观起点（原trace事件33）。** 未限定的集合相等宏无法解析。

**Hint作何判断。** 正确指出宏作用域，且预告修复后还需成员等价／见证桥接。

**实际编辑与验证顺序。** 27改全限定宏，29暴露断言失败；53以库定理替换整个宏证明，55／60双通过。

**为什么这些修改有效，或仍然失败。** 限定宏路径解决的是名称解析，只让真正的成员等价义务暴露出来，并没有自动证明集合相等。第二次编辑改变了证明计划：移除未闭合的宏体，用覆盖整个目标的库定理结束，所以无需再逐个修原choose分支。

**Hint究竟起了什么作用。** 对“当前编译错误”和“随后数学缺口”的分层判断得到实际反馈支持。actor只直接采用第一项建议，第二层转用另一种证明依赖；不能把这两种行为一概写成“完全遵循hint”。

**同起点两版对照。** v2同样先修宏再查库，且保留了额外目标assert；该assert不是第三种策略。 见[另一版CP2](../v2/REPORT.md#cp2)。

**语义审计结论。** 第一层诊断准确且被执行；数学部分转用替代路线，失败预告被验证但并未被提前避开。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current blocker is name resolution: the `assert_sets_equal` macro is not in scope under the prelude. First make the invocation resolve through vstd, preferably by qualifying the macro path rather than adding a top-level `use`, because the Lynette comparison is sensitive to extra generated Rust from imports. Re-run Verus to confirm resolution. The next proof objective is to establish extensional equality of the two set images for an arbitrary x. The current single membership equivalence is unlikely to be automatic: the SMT solver will not unfold the existential in `map` and union on its own. Work in two directions. For `(s1+s2).map(f)` containing x, expose a witness a with f(a)=x and a in s1+s2; split whether a is in s1 or s2 and conclude x lies in the corresponding image, then use union membership. For the reverse direction, split which image contains x and use that witness to show membership in the union image. Keep the witness-existence hypotheses explicit before eliminating them so the solver can use them. Check with Verus for assertion/postcondition satisfaction, then run Lynette.

</details>

[起点源码](../checkpoints/CP02.rs) · [hint原文件](CP02/hint.json) · [全部修改与工具反馈](CP02/PROCESS.md) · [最终源码](CP02/final.rs) · [最终验证](CP02/result.json)

<a id="cp3"></a>
### CP3：一次补双向见证及兼容清理

**客观起点（原trace事件40）。** 成员等价断言未证明，起点另含顶层宏导入。

**Hint作何判断。** 提示分解两个方向、在成员前提下选择见证，并清理导入。

**实际编辑与验证顺序。** 31同时删除导入、限定宏并补两个有前提分支的见证证明；33／38双通过。

**为什么这些修改有效，或仍然失败。** 正向分支先假设x属于并集映像，才能选择映射到x的a，并按a在s1还是s2分情况。逆向则先确定x在哪个映像中，再选择对应a放入并集。事件31在一轮编辑里补齐这条完整链；一轮编辑包含多个有依赖关系的事实，不等于“只复制结论”。

**Hint究竟起了什么作用。** hint的双向分解、前提保护和限定宏三项都能对应到实际差分，且随后两检查通过。这支持“提示被落实”的判断；没有对actor是否独立想到这条路线作不可验证推断。

**同起点两版对照。** v2在同起点直接转库定理，因此这里是本轮能明确区分证明实现的配对点。 见[另一版CP3](../v2/REPORT.md#cp3)。

**语义审计结论。** 提示与修改直接对应，整段修复的论证链合理；一次修改不等于逻辑跳步。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Verus is failing the single equality inside the set-extensionality macro because it cannot automatically relate the existential membership condition of (s1 + s2).map(f) to the disjunctive membership condition of s1.map(f) + s2.map(f). The next proof objective is to discharge the extensionality argument as two separate implications. For left-to-right, when x is in the left image, unfold that membership to obtain a witness a in s1 + s2 with f(a) = x, then split on whether a lies in s1 or s2 and use the corresponding image membership to prove x is in the right union. For right-to-left, assume x is in the right union and split on which image witnesses it, then reuse that witness to prove x is in the left image. Important: put the antecedent into context with an explicit case split before using choose; otherwise Verus cannot prove the witness exists. Also avoid the extra top-level import for the extensionality macro in the final candidate, because it changes generated Rust compared with input.rs; call the macro by an absolute path instead.

</details>

[起点源码](../checkpoints/CP03.rs) · [hint原文件](CP03/hint.json) · [全部修改与工具反馈](CP03/PROCESS.md) · [最终源码](CP03/final.rs) · [最终验证](CP03/result.json)

<a id="cp4"></a>
### CP4：保留原见证路线，一次修两层错误

**客观起点（原trace事件48）。** choose上的非法trigger阻塞编译；其后还需前提保证见证存在。

**Hint作何判断。** 提示删除非法trigger、补双向成员前提，避免顶层导入。

**实际编辑与验证顺序。** 78一次去导入和错误trigger，补受保护的choose及并集成员关系，使用已有axiom_set_union；80／85双通过。

**为什么这些修改有效，或仍然失败。** 非法trigger与缺见证前提是两个问题：去掉错误标注使代码可检查，成员条件分支才给choose存在性依据。补入的并集公理调用用于把并集成员关系与两侧成员关系联系起来；它来自vstd，未添加新假设。清导入只影响引用方式，不改变上述论证。

**Hint究竟起了什么作用。** 这次actor把hint预告的后续问题一起修掉，因此修后未经历中间choose和Lynette失败。但前面有大量查阅，不能用一次snapshot变化来代表一次很小、很快的推理。

**同起点两版对照。** v2将同一修复拆成trigger、前提、兼容三轮，逐层报错；两版数学路线相同，修复组织不同。 见[另一版CP4](../v2/REPORT.md#cp4)。

**语义审计结论。** 数学和兼容提醒均落实。虽一次编辑，前置检索耗时较长，不能等同低成本或瞬间完成。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is a trigger-syntax rejection: #[trigger] is attached to the whole existentially quantified condition involving a union membership and f(a) == x, but Verus triggers must be a function call, field access, or arithmetic operator. The immediate objective is to make each choose expression syntactically legal by removing that invalid trigger annotation. After that, the proof still has a logical gap: choose must establish that a witness exists, and inside the implication proof blocks the antecedent is not automatically assumed. Before selecting a witness, case-split explicitly on the relevant image-membership hypothesis so its existential witness is available. Then propagate that witness through the union and image definitions. For the image-of-union to union-of-images direction, split on whether the witness lies in s1 or s2; for the reverse direction, split on which image contains the value. Also keep the set-equality macro invocation fully qualified rather than adding a new top-level import to avoid deghosting differences later. Re-run Verus after the change; once it passes, run the comparison check.

</details>

[起点源码](../checkpoints/CP04.rs) · [hint原文件](CP04/hint.json) · [全部修改与工具反馈](CP04/PROCESS.md) · [最终源码](CP04/final.rs) · [最终验证](CP04/result.json)

<a id="cp5"></a>
### CP5：放弃未完成见证，复用库定理

**客观起点（原trace事件55）。** choose缺少可用的存在前提，起点有额外宏导入。

**Hint作何判断。** 建议补成员条件分支并清理导入。

**实际编辑与验证顺序。** 43删除整段见证证明和导入，改为map-union库定理；45／50双通过。

**为什么这些修改有效，或仍然失败。** 原路线在没有获得成员前件时取choose，存在性无法保证。actor没有把缺前提的choose包装成“已知”，而是删除该未完成实现，改调用库定理。最终依赖合法，原未通过语句不会因最终成功而被追认为正确。

**Hint究竟起了什么作用。** hint的具体见证方案未采纳；清导入的兼容方向被落实。这是一条可用的替代证明实现，但对“hint使原路线更顺畅”的支持较弱。

**同起点两版对照。** v2本点保留见证并补if条件，之后再清导入；因此CP5两版采用不同实现。 见[另一版CP5](../v2/REPORT.md#cp5)。

**语义审计结论。** 终点正确、库调用合法；没有照hint逐步补原证明，而是更换实现。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Your current failure is not the set equality itself: both choose expressions fail because their existential hypotheses are not available. In the first direction, the block proves an implication, but Verus does not automatically assume the antecedent (s1 + s2).map(f).contains(x) inside that block, so choose cannot establish a witness satisfying (s1 + s2).contains(a) && f(a) == x. The next objective is to make that membership hypothesis explicit before eliminating the existential. Put the witness elimination inside a branch guarded by the map-membership condition. Similarly, for the converse, guard on (s1.map(f) + s2.map(f)).contains(x) and then distinguish which image supplies the witness before choosing from s2. This should eliminate the cannot-prove-exists choose notes. After Verus passes, run Lynette; the current top-level use vstd::assert_sets_equal may be reported as a source difference, so prefer a fully qualified macro invocation instead.

</details>

[起点源码](../checkpoints/CP05.rs) · [hint原文件](CP05/hint.json) · [全部修改与工具反馈](CP05/PROCESS.md) · [最终源码](CP05/final.rs) · [最终验证](CP05/result.json)

<a id="cp6"></a>
### CP6：仅修工具兼容性

**客观起点（原trace事件63）。** 起点Verus已通过，宏顶层导入可能导致结构比较失败。

**Hint作何判断。** 准确区分数学证明与Lynette，建议删除导入、使用全限定宏。

**实际编辑与验证顺序。** 11 Verus通过，15 Lynette失败；21仅删除导入并限定宏；23／27双通过。

**为什么这些修改有效，或仍然失败。** Verus已验证的主体无需补新事实。首次Lynette失败表明当前提交形状不符合结构检查；删除顶层宏导入并把宏引用写成全限定形式，保留相同证明体，解决的是这一层要求。不能把Lynette失败解释成分配律证明不成立。

**Hint究竟起了什么作用。** 提示与后续最小修复完全对应，但actor先复现错误再改，属于确认诊断后修复，不是从未发生兼容失败。

**同起点两版对照。** v2也先复现同类错误再做相同改动；两者只适合作工具修复对照。 见[另一版CP6](../v2/REPORT.md#cp6)。

**语义审计结论。** 没有新数学证明。属于已有正确证明的工具兼容修复，不能算新的解题策略。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current proof already passes Verus, but that is not the terminal condition: Lynette compares the deghosted/generated Rust against input.rs. This candidate introduces a top-level import of the set-equality macro that input.rs does not have, which is likely to make Lynette report `Files are different`. The next repair objective is a compatibility fix, not further mathematical proof: retain the existing set-extensionality argument and its case-splitting witnesses unchanged, but eliminate the extra top-level import's effect on generated Rust by referring to the macro through its full qualified path at the one call site. Then rerun Verus to confirm the proof still verifies, and especially rerun Lynette to confirm generated-Rust equivalence. Do not add any other top-level declaration absent from input.rs.

</details>

[起点源码](../checkpoints/CP06.rs) · [hint原文件](CP06/hint.json) · [全部修改与工具反馈](CP06/PROCESS.md) · [最终源码](CP06/final.rs) · [最终验证](CP06/result.json)

## 可用于训练的范围

本版最终双通过项可作为待格式整理的训练候选，必须携带题目规格、完整checkpoint起点和真实编辑／工具结果。失败中间态保留失败标签，不把未验证断言、错误API、actor自述或hint的诊断预测变成已证明事实。终点正确不表示每个中间尝试都正确；失败后的有效修复本身可有价值。AC v1 CP1、AC v2 CP3只作失败对照，不混入成功样本。

逐条核对了checkpoint hash、最终candidate与宿主验证hash、input未变化及skill一致性。源码差分中未发现新增assume/admit/external_body/unimplemented绕过标记；AC题目原有组件stub不算本轮新增。见[source_checks.json](source_checks.json)。这些检查与源码阅读不等于对任意工具行为的安全证明；本报告不把一次通过当作下游skill收益证据。

本题策略差异依赖核心引理、见证与证明分解判断，不用hash/F1代替语义审计。所有hint也并非“纯数学”：宏限定、implies、删除非法属性等含实现指导，但未给出可直接粘贴的完整最终proof。成功的hint采纳只能说明行为对应，不能证明提速因果或跨题稳定性。

## Hint生成成本

| CP | 输入token | 输出token |
|---|---:|---:|
| [CP1](#cp1) | 38,098 | 2,058 |
| [CP2](#cp2) | 38,101 | 3,017 |
| [CP3](#cp3) | 38,085 | 3,218 |
| [CP4](#cp4) | 38,427 | 2,835 |
| [CP5](#cp5) | 38,986 | 2,232 |
| [CP6](#cp6) | 38,300 | 2,848 |

保留的自动证据原稿（未随本次发布的本地材料） · [结构化语义审计](semantic_audit.json)
