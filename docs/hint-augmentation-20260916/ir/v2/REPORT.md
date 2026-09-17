# IR · Initial skill + Hint v2：逐checkpoint语义审计

**本版全部6条过程审计完成，待用户复核。** 审查保存的起点、hint正文、每次源码变化、实际工具反馈及最终宿主验证；本次没有重新调用模型或验证器。最终正确与中间每一步正确分开判断。

两版均6/6。v1的CP1/2/5与v2的CP1/2/3复用同一个vstd定理，其余非末尾点保留双向见证；CP6仅修兼容。没有证据称v2始终避免导入错误：CP4/5仍先经历Lynette失败。

## 先读懂原题与原F

目标是`(s1 + s2).map(f) == s1.map(f) + s2.map(f)`，即“先取并集再映射”与“分别映射再取并集”相等。原F采用集合外延性：固定输出元素x，分别证明左右成员关系。正向从并集的映像中取a，利用a属于s1或s2；逆向从某一侧映像取a，再把a放回并集。两方向都必须先获得成员条件，才能合法选择存在见证。

原trace的CP1为空证明；CP2卡宏名称；CP3卡成员等价；CP4首先卡非法trigger；CP5缺choose所需前提；CP6数学已经成立，只剩宏引用／结构兼容。它们不是六道独立题，也不是六个从零解题样本。另一条合法路线是直接复用vstd中已经证明同一分配律的`lemma_map_union_commute`：这是证明依赖的变化，不是绕过验证。

## 图与版本对照

![同initial skill的两版hint对照](comparison_prefix_tokens.png)

两版actor输出合计：v1 **50,950**，v2 **50,657**（-0.6%）。包括失败续跑和结束说明，hint生成另计。上图为相对原F的Patch F1，即参考路径相似度；下图为同一观测的Verus状态。横轴包含原前缀归属token，但actor并未回放原前缀；彩色竖虚线仅标首次提取到的Verus通过，不等于Lynette／整个任务完成。

[本版单组图](hint_prefix_tokens.png) · [v1审计](../v1/REPORT.md) · [v2审计](REPORT.md) · [图表数据](../comparison.json)

## 数据和条件核对

来源为Yuechun固定train40中本题的step_0001 DeepSeek v4 Pro原轨迹。全部起点沿用冻结的Yuechun checkpoint提取逻辑；没有按结果另选checkpoint。原轨迹和本轮actor均通过工作区SKILL.md装备同一initial skill，SHA256为`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`。本版每条实际读取全文的事件见下表；不是仅根据文件存在推断使用。

Actor获原题、完整checkpoint代码、fresh hint和skill；hint agent可看原完整轨迹与F。没有把原完整对话或F直接发给actor。38个hint全新生成，旧blank组保持不动。新旧同时变化了skill和hint样本，不能把actor差异单独归因于skill；本轮v1/v2也仅各一次采样，不支持稳定因果结论。

[原题规格与源码](../original_input.rs) · [原trace最终源码F](../original_final.rs) · [原轨迹](../ORIGINAL_CHANGES.md) · [Skill装备核对](../../SKILL_PARITY.md)

## 本版逐点结果

| CP | Actor输出token | 源码变化次数 | 读取skill事件 | 最终Verus＋Lynette |
|---|---:|---:|---|---|
| [CP1](#cp1) | 8,635 | 2 | 17 | 通过 |
| [CP2](#cp2) | 7,313 | 2 | 9 | 通过 |
| [CP3](#cp3) | 10,562 | 1 | 21 | 通过 |
| [CP4](#cp4) | 14,265 | 3 | 22 | 通过 |
| [CP5](#cp5) | 6,281 | 2 | 12 | 通过 |
| [CP6](#cp6) | 3,601 | 1 | 12 | 通过 |

事件编号使用本条agent_events.jsonl的event_index；源码变化取snapshot差分事件，工具编号取完成命令事件，可能与图中随后保存的verifier事件相差1，不是不同轨迹。源码变化次数不是提取后的checkpoint数。

同版本旧blank审计另见旧v2报告（未随本次发布的本地材料）。下面的逐点版本对照均指**本轮两个initial-skill组**，不混用旧blank结果。

## 逐checkpoint语义审计

<a id="cp1"></a>
### CP1：库路线先猜错API再修正

**客观起点（原trace事件24）。** 空proof，目标分配律未建立。

**Hint作何判断。** 仍建议外延性和双向见证，兼容提醒不加顶层导入。

**实际编辑与验证顺序。** 63猜自由函数vstd::set_lib::lemma_map_union_commute，65报E0425；71改成s1的方法调用，73／78双通过。

**为什么这些修改有效，或仍然失败。** 第一次库调用使用了不存在的自由函数入口，因而不是一个已完成的合法证明。后面改用Set对象的方法接口，才让Verus检查真实定理合同并完成目标。错误在API位置／调用形式，不在分配律本身，也不能拿第一次调用当可复用知识。

**Hint究竟起了什么作用。** actor避开新增导入，但没有按照hint构造双向见证。不能把API修正说成hint已经预先解决的问题；该错误是在实际检索和编译反馈后修好的。

**同起点两版对照。** v1直接使用正确方法接口，少一次编译失败；本点不能用来宣称v2过程普遍优于v1。 见[另一版CP1](../v1/REPORT.md#cp1)。

**语义审计结论。** 合法库路线最终成立；错误API来自actor实现，未采用hint的手写路线。错误调用应保留失败标签。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is a bare proof body: Verus cannot discharge the set-equality postcondition without proof steps. The next objective is to reduce the set equality to membership equivalence: for arbitrary x, x is in (s1+s2).map(f) exactly when x is in s1.map(f)+s2.map(f). Prove each implication separately. For left-to-right, unfold map and union membership to obtain a domain element a with f(a)=x and a in s1 or a in s2; split that disjunction and show the witness places x in the corresponding image. For right-to-left, if x belongs to either image, extract a witness from s1 or s2, then show that same a belongs to s1+s2 and maps to x. Use Verus's choose mechanism to eliminate existential map-membership hypotheses, but place it under an explicit case split so the existence assumption is available. Look for a vstd set-extensionality helper to assert equality from membership equivalence. If you use that helper, avoid adding a separate top-level import: a later state with one made Lynette report different generated Rust, while using the full path passed. Check with run_verus.sh, then run_lynette.sh.

</details>

[起点源码](../checkpoints/CP01.rs) · [hint原文件](CP01/hint.json) · [全部修改与工具反馈](CP01/PROCESS.md) · [最终源码](CP01/final.rs) · [最终验证](CP01/result.json)

<a id="cp2"></a>
### CP2：宏修复后改库定理

**客观起点（原trace事件33）。** 宏不在作用域。

**Hint作何判断。** 宏诊断与下一层成员证明预告正确。

**实际编辑与验证顺序。** 19限定宏，21断言失败；48换库定理并附目标断言，50／54双通过。

**为什么这些修改有效，或仍然失败。** 全限定宏使代码从名称错误进入证明错误；随后库定理承担了整个等式。保留在后面的assert只是重申当前结论，既不提供新前提，也不是与库定理不同的数学路径。

**Hint究竟起了什么作用。** 第一层宏提示明确被采纳，第二层数学预告也确实发生，但actor没有用hint给的手写修复来解决它。评价应是“诊断正确、数学路线改用库”。

**同起点两版对照。** v1过程结构相同，两版差异主要是搜索／输出成本和冗余断言。 见[另一版CP2](../v1/REPORT.md#cp2)。

**语义审计结论。** 和v1同类路径，没有新策略；附加assert是冗余确认，不是新的核心论证。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The immediate blocker is a macro-scope error: the set-equality macro is not in scope, so Verus stops before checking the proof. Make the macro reachable, but avoid adding a new top-level import just for it if possible; a recorded attempt with that import passed Verus but failed Lynette's generated-Rust comparison, while a qualified vstd-path invocation later passed both. After it compiles, the current single membership-equality assertion is insufficient. The next proof objective is set extensionality by proving the two membership directions separately for an arbitrary x. For x in (s1 + s2).map(f), explicitly assume/branch on that antecedent, extract a witness a with f(a)=x and a in s1 or s2, then case split on which set contains a and rebuild membership in the corresponding image. Prove the reverse direction similarly, branching on whether x comes from s1.map(f) or s2.map(f). Run Verus after the logical change and run Lynette to check generated-Rust equivalence.

</details>

[起点源码](../checkpoints/CP02.rs) · [hint原文件](CP02/hint.json) · [全部修改与工具反馈](CP02/PROCESS.md) · [最终源码](CP02/final.rs) · [最终验证](CP02/result.json)

<a id="cp3"></a>
### CP3：一次转库并清理导入

**客观起点（原trace事件40）。** 成员等价断言失败，另有顶层宏导入。

**Hint作何判断。** 建议双向见证及兼容清理，前者可行而非必须。

**实际编辑与验证顺序。** 79删除导入并以库定理取代宏证明，81／86双通过。

**为什么这些修改有效，或仍然失败。** 本点原代码已经有宏和未闭合成员等价，但actor将整段改为库定理。该方法直接覆盖目标，因而不需要继续构造a的见证。删除额外导入与更换数学实现同轮发生，后续双通过支持最终版本合规。

**Hint究竟起了什么作用。** 提示的兼容检查原则得到落实，外延见证方案没有得到落实。一次成功不应写成actor逐条遵循数学hint，更不能仅凭低F1说它离正确性更远。

**同起点两版对照。** v1本点一次构造了双向见证；两版都是正确终点，差异在证明所依赖的知识。 见[另一版CP3](../v1/REPORT.md#cp3)。

**语义审计结论。** 只落实兼容原则，数学路线转库；与本轮v1 CP3的手写见证形成实质实现差异。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is not just a missing import: the extensionality branch asserts a pointwise Boolean equality of the two membership predicates, and Verus cannot unfold map/union membership through that single assertion. Prove the pointwise membership equivalence as two separate implication directions. In each direction, once the membership antecedent is in context, expose the existential witness behind the relevant map membership and case-split on the union or image side that produced it. For left-to-right, a witness in the union is either in s1 or s2, and each case proves membership in the corresponding image. For right-to-left, split whether the witness originates from s1 or s2, then lift it back into the union before showing membership in the mapped union. Run Verus after this change; the failing Boolean equality should be replaced by a provable pointwise equivalence. Compatibility: the current added top-level macro import may affect Lynette; a later verified state with that import failed the comparison, while the final proof used a fully qualified macro path and passed, so avoid keeping that extra top-level import and rerun Lynette.

</details>

[起点源码](../checkpoints/CP03.rs) · [hint原文件](CP03/hint.json) · [全部修改与工具反馈](CP03/PROCESS.md) · [最终源码](CP03/final.rs) · [最终验证](CP03/result.json)

<a id="cp4"></a>
### CP4：提示准确，分层失败仍发生

**客观起点（原trace事件48）。** 非法trigger，其后还有见证前提与额外导入。

**Hint作何判断。** 三层问题均有提示。

**实际编辑与验证顺序。** 70删trigger，72 choose失败；78补成员前提分支，80 Verus通过；85 Lynette失败；91删导入并限定宏，93／97双通过。

**为什么这些修改有效，或仍然失败。** 事件70只去非法trigger，未改变choose所在的逻辑上下文，所以随后存在性失败是可预期的。事件78补成员条件，才使选择见证有依据；数学通过后剩下导入差异，事件91再改变宏引用方式。三个阶段分别解决解析、证明和结构检查，不能合写成一轮正确推导。

**Hint究竟起了什么作用。** hint已提及三层问题，但actor分次落实且没有提前清导入。正向作用是提供了正确修复方向，不是避免所有失败；判断应保留这种局部性。

**同起点两版对照。** v1同点一次合并修复而双通过。v2虽然actor输出较少，仍经历更多失败状态，成本与修复轮数不是同一指标。 见[另一版CP4](../v1/REPORT.md#cp4)。

**语义审计结论。** 修复顺序合理，但不能称hint提前避免了后两层失败。v1本点一次合并修复，v2反而分三次。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current Verus error is not yet about the set-equality proof itself: a choose expression is applying #[trigger] to a compound membership condition, which Verus does not accept as a valid trigger. First make the choose condition syntactically valid by removing that trigger annotation or moving it to a legal subterm. After that, do not rely on the implication proof block to supply the existential membership hypothesis; Verus needs an explicit case split on the antecedent before choosing an existential witness. In each direction, branch on the relevant membership fact, then choose the witness for the contains predicate and propagate it through set union and image membership. For the forward direction, split on mapped-union membership, obtain a witness in the union, and then case on which set contains that witness. For the reverse direction, split on union-image membership, then on which image contains x. Re-run Verus after each change to see whether the choose existence conditions and postcondition close. Compatibility reminder: the current extra top-level assert_sets_equal import is a likely Lynette difference risk; later evidence showed an imported-macro version failing Lynette while the fully qualified macro path passed, so plan to remove that import before final Lynette.

</details>

[起点源码](../checkpoints/CP04.rs) · [hint原文件](CP04/hint.json) · [全部修改与工具反馈](CP04/PROCESS.md) · [最终源码](CP04/final.rs) · [最终验证](CP04/result.json)

<a id="cp5"></a>
### CP5：先补前提，再修导入

**客观起点（原trace事件55）。** choose的存在性缺少局部前提。

**Hint作何判断。** 提示双方向前提保护，并在Verus之后处理兼容检查。

**实际编辑与验证顺序。** 21加前提分支，23 Verus通过；28 Lynette失败；38删除导入、限定宏，40／45双通过。

**为什么这些修改有效，或仍然失败。** 新增if成员分支提供choose所需的存在性来源，使两方向见证都在有效前提下进行。之后宏路径清理没有新增数学事实；它只把已经通过的证明恢复为允许的文件结构。

**Hint究竟起了什么作用。** 该hint允许先处理数学、再查Lynette，因此后修导入不一定违背提示。不过提示也没有帮助本次直接避免Lynette失败，应与“预防成功”区别记录。

**同起点两版对照。** v1选择库定理并一并删导入；v2保留原手写路线，两者终点相似度差异有真实策略依据。 见[另一版CP5](../v1/REPORT.md#cp5)。

**语义审计结论。** 数学hint落实；兼容处理延迟但与该提示顺序相容。保留原路线，不是新策略。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Your current proof has the right set-extensionality structure, but the `choose` expressions are introduced before their existence assumptions are available. In an implication assertion, the antecedent is not automatically assumed inside the `by` proof block; the diagnostics at both failing chooses reflect exactly that missing witness-existence context. First case-split on `((s1 + s2).map(f)).contains(x)` before choosing a witness from the union map in the left-to-right direction. In the reverse direction, case-split first on `(s1.map(f) + s2.map(f)).contains(x)`, then split within that case on which image contains `x` before choosing the corresponding `s1` or `s2` witness. This should make the existing membership-propagation assertions discharge. After Verus passes, check compatibility: the extra top-level `use vstd::assert_sets_equal;` differs from the original input, and a later verified version with that import was observed to fail Lynette. Verify with `./tools/run_lynette.sh` and consider invoking the macro through its module path instead of adding that top-level import.

</details>

[起点源码](../checkpoints/CP05.rs) · [hint原文件](CP05/hint.json) · [全部修改与工具反馈](CP05/PROCESS.md) · [最终源码](CP05/final.rs) · [最终验证](CP05/result.json)

<a id="cp6"></a>
### CP6：复现兼容错误后最小清理

**客观起点（原trace事件63）。** 起点数学已通过。

**Hint作何判断。** 提示不重做数学，只清理额外导入及限定宏。

**实际编辑与验证顺序。** 19 Verus通过、23 Lynette失败；29清理，32／37双通过。

**为什么这些修改有效，或仍然失败。** 同一候选先Verus通过、后Lynette失败，证明数学与结构判定各有职责。最后仅移除导入并限定宏，说明无需重证分配律；把这条续跑算作新的证明发现会夸大增广多样性。

**Hint究竟起了什么作用。** hint准确指向该最小修复，actor也没有额外重写正确主体。它的价值更接近工具使用经验，而非新的数学分解。

**同起点两版对照。** v1同样先复现后修复；v2输出略多，不能从相同成功终点反推提示更有效。 见[另一版CP6](../v1/REPORT.md#cp6)。

**语义审计结论。** 与v1同类兼容修复，不能计为证明创新。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Verus already verifies this checkpoint, so the remaining issue is the proof-only compatibility check, not further mathematical proof. The current candidate adds a top-level macro import for set extensionality; with exactly this source, Lynette compare against input.rs was observed to fail with 'Files are different'. Repair this by avoiding that added top-level import and invoking the macro through its qualified module path at the use site instead. After the minimal change, rerun Verus to confirm it still reports 1 verified, 0 errors, then rerun Lynette and confirm it no longer reports 'Files are different' and exits successfully. Do not change the function signature, specification, or executable behavior; the proof body can remain logically unchanged. If Lynette still reports a difference, inspect the generated-Rust comparison rather than weakening or assuming the proof goal.

</details>

[起点源码](../checkpoints/CP06.rs) · [hint原文件](CP06/hint.json) · [全部修改与工具反馈](CP06/PROCESS.md) · [最终源码](CP06/final.rs) · [最终验证](CP06/result.json)

## 可用于训练的范围

本版最终双通过项可作为待格式整理的训练候选，必须携带题目规格、完整checkpoint起点和真实编辑／工具结果。失败中间态保留失败标签，不把未验证断言、错误API、actor自述或hint的诊断预测变成已证明事实。终点正确不表示每个中间尝试都正确；失败后的有效修复本身可有价值。AC v1 CP1、AC v2 CP3只作失败对照，不混入成功样本。

逐条核对了checkpoint hash、最终candidate与宿主验证hash、input未变化及skill一致性。源码差分中未发现新增assume/admit/external_body/unimplemented绕过标记；AC题目原有组件stub不算本轮新增。见[source_checks.json](source_checks.json)。这些检查与源码阅读不等于对任意工具行为的安全证明；本报告不把一次通过当作下游skill收益证据。

本题策略差异依赖核心引理、见证与证明分解判断，不用hash/F1代替语义审计。所有hint也并非“纯数学”：宏限定、implies、删除非法属性等含实现指导，但未给出可直接粘贴的完整最终proof。成功的hint采纳只能说明行为对应，不能证明提速因果或跨题稳定性。

## Hint生成成本

| CP | 输入token | 输出token |
|---|---:|---:|
| [CP1](#cp1) | 38,545 | 3,538 |
| [CP2](#cp2) | 38,548 | 3,027 |
| [CP3](#cp3) | 38,532 | 2,477 |
| [CP4](#cp4) | 38,874 | 2,993 |
| [CP5](#cp5) | 39,433 | 3,476 |
| [CP6](#cp6) | 38,747 | 2,605 |

保留的自动证据原稿（未随本次发布的本地材料） · [结构化语义审计](semantic_audit.json)
