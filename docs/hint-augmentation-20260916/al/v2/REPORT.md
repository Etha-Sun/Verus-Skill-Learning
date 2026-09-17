# AL · Initial skill + Hint v2：逐checkpoint语义审计

**本版全部7条过程审计完成，待用户复核。** 审查保存的起点、hint正文、每次源码变化、实际工具反馈及最终宿主验证；本次没有重新调用模型或验证器。最终正确与中间每一步正确分开判断。

两版均7/7，主要保持“长度消去＋前缀逐点相等＋外延性”同一数学路线。v2 CP3/5直接成功，部分点仍有量词／导入返工。v1 CP1首个无依据的相等断言是错误尝试，须在训练整理中明确标失败。

## 先读懂原题与原F

目标为`s1 == s2 <==> s1 + suffix == s2 + suffix`。正向只需等式替换；逆向不能直接从拼接相等跳到前缀相等，原F补了两个桥梁：由拼接长度相等消去共同suffix长度，得到s1、s2等长；然后对前缀范围内的i，用拼接索引定律把两侧元素还原为s1[i]与s2[i]，最后用序列外延性。

CP1为空proof，CP2逆向缺事实，CP3使用不可解析的引理，CP4长度／索引桥接未补全，CP5改猜对象方法仍失败，CP6外延宏内缺逐点事实，CP7数学已通过。宏、局部broadcast和显式forall是表达该路线的不同方式，不应仅凭源码不同称作新数学策略。额外顶层导入可能不影响Verus证明，却影响本实验Lynette的结构比较。

## 图与版本对照

![同initial skill的两版hint对照](comparison_prefix_tokens.png)

两版actor输出合计：v1 **65,299**，v2 **54,141**（-17.1%）。包括失败续跑和结束说明，hint生成另计。上图为相对原F的Patch F1，即参考路径相似度；下图为同一观测的Verus状态。横轴包含原前缀归属token，但actor并未回放原前缀；彩色竖虚线仅标首次提取到的Verus通过，不等于Lynette／整个任务完成。

[本版单组图](hint_prefix_tokens.png) · [v1审计](../v1/REPORT.md) · [v2审计](REPORT.md) · [图表数据](../comparison.json)

## 数据和条件核对

来源为Yuechun固定train40中本题的step_0001 DeepSeek v4 Pro原轨迹。全部起点沿用冻结的Yuechun checkpoint提取逻辑；没有按结果另选checkpoint。原轨迹和本轮actor均通过工作区SKILL.md装备同一initial skill，SHA256为`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`。本版每条实际读取全文的事件见下表；不是仅根据文件存在推断使用。

Actor获原题、完整checkpoint代码、fresh hint和skill；hint agent可看原完整轨迹与F。没有把原完整对话或F直接发给actor。38个hint全新生成，旧blank组保持不动。新旧同时变化了skill和hint样本，不能把actor差异单独归因于skill；本轮v1/v2也仅各一次采样，不支持稳定因果结论。

[原题规格与源码](../original_input.rs) · [原trace最终源码F](../original_final.rs) · [原轨迹](../ORIGINAL_CHANGES.md) · [Skill装备核对](../../SKILL_PARITY.md)

## 本版逐点结果

| CP | Actor输出token | 源码变化次数 | 读取skill事件 | 最终Verus＋Lynette |
|---|---:|---:|---|---|
| [CP1](#cp1) | 9,994 | 3 | 33 | 通过 |
| [CP2](#cp2) | 5,967 | 1 | 14 | 通过 |
| [CP3](#cp3) | 6,053 | 1 | 5 | 通过 |
| [CP4](#cp4) | 13,508 | 3 | 6 | 通过 |
| [CP5](#cp5) | 5,575 | 1 | 6 | 通过 |
| [CP6](#cp6) | 8,819 | 2 | 8 | 通过 |
| [CP7](#cp7) | 4,225 | 1 | 17 | 通过 |

事件编号使用本条agent_events.jsonl的event_index；源码变化取snapshot差分事件，工具编号取完成命令事件，可能与图中随后保存的verifier事件相差1，不是不同轨迹。源码变化次数不是提取后的checkpoint数。

同版本旧blank审计另见旧v2报告（未随本次发布的本地材料）。下面的逐点版本对照均指**本轮两个initial-skill组**，不混用旧blank结果。

## 逐checkpoint语义审计

<a id="cp1"></a>
### CP1：无额外导入，仍有API与前提返工

**客观起点（原trace事件21）。** 空proof。

**Hint作何判断。** 正确给出长度消去与逐点相等，当前未观察到结构差异。

**实际编辑与验证顺序。** 59补主体但broadcast组未限定且forall用==>；61解析失败；67限定组，69索引断言失败；75改implies，77／82双通过。

**为什么这些修改有效，或仍然失败。** 第一次主体采用了正确双向分解，却同时引入名称和前提实现错误。限定broadcast后，索引断言才被真正检查；将forall的==>改为implies，让“i在前缀范围”进入证明块，才能合法使用拼接索引关系。这说明报错层级推进不等于每个阶段都已证明正确。

**Hint究竟起了什么作用。** 数学主线与hint一致，但hint没让actor一次写对API和量词。未新增顶层导入是本次事实，不能进一步声称新提示能普遍阻止所有兼容问题。

**同起点两版对照。** v1最初还写了错误逆向断言，v2没有；两者均为最终成功的纠错过程，而不是每一步都正确的演绎稿。 见[另一版CP1](../v1/REPORT.md#cp1)。

**语义审计结论。** 最终符合数学路线；v2没有消除名称和前提错误，但没有本轮v1 CP1的无依据逆向断言。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The empty proof body gives Verus nothing to establish the biconditional, so the postcondition is completely unproved. Split the proof into two implications. Forward: from s1 == s2, derive equality of s1 + suffix and s2 + suffix by congruence, since appending the same suffix preserves equality. Backward: start from s1 + suffix == s2 + suffix. First derive equal concatenation lengths, use the fact that concatenation length is the sum of component lengths, cancel suffix length, and obtain s1.len() == s2.len(). Then show the prefixes agree pointwise: for every index in s1's range, relate indexing into a concatenation at an index below the first sequence's length to indexing into the first sequence, so equality of the concatenations yields equality of corresponding prefix elements. Finish by sequence extensionality: equal lengths plus pointwise equality imply s1 == s2. Run Verus after the edit; the backward direction should fail if length cancellation or prefix index unfolding is missing. This checkpoint has no structural difference from input.rs requiring a separate compatibility fix.

</details>

[起点源码](../checkpoints/CP01.rs) · [hint原文件](CP01/hint.json) · [全部修改与工具反馈](CP01/PROCESS.md) · [最终源码](CP01/final.rs) · [最终验证](CP01/result.json)

<a id="cp2"></a>
### CP2：一次补齐逆向证明

**客观起点（原trace事件28）。** 逆向缺等长和前缀逐点事实。

**Hint作何判断。** 数学诊断准确，没有要求具体可复制proof。

**实际编辑与验证顺序。** 32补拼接长度消去、forall implies下的索引关系及外延结论；34／39双通过。

**为什么这些修改有效，或仍然失败。** 本次直接补上“等长→同一索引两侧有效→元素相等”的桥梁。implies保证索引范围前提在proof块内可用，不需额外假设；外延结论依赖这两类事实而非直接照写目标。

**Hint究竟起了什么作用。** hint的两项证明义务都得到代码落实，且第一次修改后双通过。可以作为紧凑但逻辑完整的展开，不应因为只有一次修改就判为跳步。

**同起点两版对照。** v1同点也是一次修复，仅具体库事实激活形式不同；没有证据认定为两种不同数学策略。 见[另一版CP2](../v1/REPORT.md#cp2)。

**语义审计结论。** 直接采纳，合理展开；两版均一次源码修复。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The forward direction is already accepted. The remaining gap is the backward direction: from equality of the concatenated sequences, Verus cannot directly conclude s1 == s2 by a raw equality assertion. Prove sequence equality by extensionality instead. First establish that s1 and s2 have equal lengths by combining the fact that equal sequences have equal length with the relation between a concatenation length and the lengths of its parts, then cancel the common suffix length. Next, for an arbitrary valid index i of s1, show s1[i] == s2[i]. The equal concatenated sequences have equal values at i, and because i is within the prefix length, each concatenation's value at i reduces to the corresponding prefix element. With equal lengths and pointwise equality for all valid indices, conclude sequence equality via extensionality. Re-run Verus; the previous raw equality failure should be replaced by verification success or by a more local length/index failure rather than the original assertion failure. Keep the function signature and specification unchanged.

</details>

[起点源码](../checkpoints/CP02.rs) · [hint原文件](CP02/hint.json) · [全部修改与工具反馈](CP02/PROCESS.md) · [最终源码](CP02/final.rs) · [最终验证](CP02/result.json)

<a id="cp3"></a>
### CP3：一次去错调用、补证明并删导入

**客观起点（原trace事件36）。** 不可用lemma调用阻塞解析。

**Hint作何判断。** 建议真实拼接事实替代猜测API，并清理无用导入。

**实际编辑与验证顺序。** 35一次删除错误调用与导入，补长度和索引证明；37／42双通过。

**为什么这些修改有效，或仍然失败。** 一次编辑承担三件有区别的事：去掉当前接口不可用的调用；用显式长度／索引事实补回其预期证明作用；去掉多余导入以满足提交结构。只做第一项是不够的，本次三项同时完成，之后直接双通过。

**Hint究竟起了什么作用。** 与hint内容有较强的一一对应，既解决当前名称错误，也没有重现后续缺事实和导入失败。不过“该调用在此环境不可用”不应扩大为所有版本都没有这类引理。

**同起点两版对照。** v1同点先删调用、再补长度、最后删导入；本点支持观察到更完整的一次修复，但尚不能分离fresh hint与actor采样的贡献。 见[另一版CP3](../v1/REPORT.md#cp3)。

**语义审计结论。** 比本轮v1减少分层失败，代码证据支持提示被落实；单样本不能证明prompt的因果收益。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Verus is currently blocked before proof verification by unresolved helper names: the calls for concatenation length and concatenation indexing are not present in this version's vstd::seq_lib. Do not keep guessing alternate helper names. Establish the needed mathematics directly: equality of the concatenations implies their lengths are equal, which yields equal lengths for s1 and s2; and for any index within the first operand's range, the concatenation at that index equals the corresponding prefix element. Use those facts to prove pointwise equality of s1 and s2, then close by sequence extensionality. Re-run Verus to confirm the name-resolution errors disappear and any remaining diagnostic is a proof obligation rather than API misuse. The added vstd::seq_lib import is not in the original input and may become unused after removing those calls; run Lynette afterward, but do not assume the import itself caused a compatibility failure without a Lynette diagnostic.

</details>

[起点源码](../checkpoints/CP03.rs) · [hint原文件](CP03/hint.json) · [全部修改与工具反馈](CP03/PROCESS.md) · [最终源码](CP03/final.rs) · [最终验证](CP03/result.json)

<a id="cp4"></a>
### CP4：前提修复后才处理导入

**客观起点（原trace事件48）。** 长度桥接、索引推理未完成，起点有导入。

**Hint作何判断。** 数学目标及导入兼容提醒正确。

**实际编辑与验证顺序。** 69补长度与forall ==>，71索引失败；77改implies，79 Verus；84 Lynette失败；90删导入，92／96双通过。

**为什么这些修改有效，或仍然失败。** actor已按数学提示补长度和逐点证明，却使用==>让索引范围未成为proof体假设；改implies后数学通过，说明核心缺口是前提传递而非需要新的序列定理。之后Lynette才要求删顶层导入，证明这条兼容提醒并未提前落实。

**Hint究竟起了什么作用。** 提示同时涉及数学及兼容，但执行结果是分阶段修复而非预防失败。“最终照做了”与“提前规避了”是两个不同结论，此点只支持前者。

**同起点两版对照。** v1多出broadcast名称和两轮导入修复；v2过程较短，但仍有实际前提错误和一次Lynette失败。 见[另一版CP4](../v1/REPORT.md#cp4)。

**语义审计结论。** 数学／兼容均最终落实，提醒没有提前规避所有错误。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

In the backward direction, start from the concatenation equality and derive that the concatenated values have the same length. Then unfold the length of each concatenation into prefix length plus suffix length, cancel the common suffix length, and only then conclude the prefix lengths are equal. The current first failure arises because this length argument is skipped. Next, prove the prefixes agree pointwise: for an arbitrary prefix index, compare the concatenated values at that index and unfold both concatenation index accesses to reduce them to the corresponding prefix elements. After that, close under sequence extensionality. The sequence-library equality macro cannot supply these missing index-shift and length facts, so establish them before invoking it or switch to explicit extensionality. Re-run Verus and expect the remaining failures to resolve. Compatibility note: this state adds a sequence-library import relative to the input; if it becomes unused after restructuring, remove it before the final Lynette check, but no Lynette failure is observed for the current state.

</details>

[起点源码](../checkpoints/CP04.rs) · [hint原文件](CP04/hint.json) · [全部修改与工具反馈](CP04/PROCESS.md) · [最终源码](CP04/final.rs) · [最终验证](CP04/result.json)

<a id="cp5"></a>
### CP5：一次替换不可用方法

**客观起点（原trace事件55）。** 方法解析失败；目标需长度消去和索引相等。

**Hint作何判断。** 数学诊断正确；“当前仅unused-import warning”的措辞应与原诊断分开，不能由导入未使用就推定Verus已经报告该warning。

**实际编辑与验证顺序。** 22去错误方法与导入，补长度、两侧合法索引及逐点事实；24／29双通过。

**为什么这些修改有效，或仍然失败。** 去掉对象方法以后，显式长度消去确保s1和s2索引范围一致，再用拼接索引等式取得逐点相同；因此替换不是把失败调用删掉就宣称目标成立。导入也同轮删除，第一次修改后双通过。

**Hint究竟起了什么作用。** 数学建议准确且被执行。hint把导入描述成“当前unused-import warning”应有实际诊断支持；即使导入确实多余，也不能把自然语言措辞当作Verus已输出该warning的证据。

**同起点两版对照。** v1也是一次合并修复，两版数学核心相同；本次主要体现修复模式能再次被执行，而非新策略。 见[另一版CP5](../v1/REPORT.md#cp5)。

**语义审计结论。** 直接成功。保留有效数学指导；hint关于warning的说法不作为工具事实或训练知识。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The checkpoint currently fails at name resolution, not at the target logical obligation: the calls to lemma_seq_add_len and lemma_seq_add_index are not available in this Verus version, so no proof progress is being made. Instead proceed directly with the built-in concatenation facts: under the hypothesis that s1 + suffix equals s2 + suffix, first obtain that their lengths are equal and that the length of a concatenation is the sum of component lengths, hence s1 and s2 have equal length. Then, for any index i in the prefix range, use the fact that indexing the concatenation at i yields the original prefix element for both sides; this gives pointwise equality of s1 and s2. Close by sequence extensionality. After removing the nonexistent lemma calls, rerun Verus; success would be 1 verified, 0 errors. The extra seq_lib import is currently only an unused-import warning in Verus, but remove it once it is no longer used and run Lynette on the cleaned candidate rather than assuming it is safe.

</details>

[起点源码](../checkpoints/CP05.rs) · [hint原文件](CP05/hint.json) · [全部修改与工具反馈](CP05/PROCESS.md) · [最终源码](CP05/final.rs) · [最终验证](CP05/result.json)

<a id="cp6"></a>
### CP6：数学先通过，导入仍后修

**客观起点（原trace事件62）。** 宏内缺逐点事实，已有顶层宏导入。

**Hint作何判断。** 提示数学补足；“不再使用时才删导入”的兼容建议偏窄，仍使用宏也可改限定路径。

**实际编辑与验证顺序。** 42补宏内索引，44 Verus；49 Lynette失败；59删导入并限定宏，61／65双通过。

**为什么这些修改有效，或仍然失败。** 宏内补索引事实解决了数学义务，但宏仍通过顶层导入获得名称，所以Verus通过后结构检查依旧可能失败。删导入不意味着禁用宏，改全限定宏即可保留整段证明。这正是“没用的导入才删”表述不足以覆盖的情况。

**Hint究竟起了什么作用。** hint有实际数学指导，但兼容建议边界较窄；actor最终在Lynette反馈后完成路径修复。不能把这次失败解释成actor完全无视所有hint，也不能声称hint提前避免了它。

**同起点两版对照。** v1先多一轮broadcast名称错误；v2少了那一层，宏导入问题仍一样存在。 见[另一版CP6](../v1/REPORT.md#cp6)。

**语义审计结论。** 兼容风险没有被提前解决；最终修复合理，不是hint导致全程无失败。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is no longer about lengths: the length assertions before line 19 are accepted, but the macro cannot close sequence equality because it lacks the pointwise fact that s1[i] == s2[i] for every prefix index i. Next prove that for every i with 0 <= i < s1.len(), the two prefixes agree at i. From the branch hypothesis s1 + suffix == s2 + suffix, you can compare the concatenated sequences at index i; since i lies in the prefix range, the concatenation at i equals the corresponding prefix element for both s1 and s2. Then use sequence extensionality to conclude s1 == s2 from that pointwise equality. Re-run Verus and expect the macro failure to disappear. If the new proof no longer uses the seq_lib import, clean it up before Lynette; the final validated state has no such extra import, but there is no recorded Lynette result for the current import-bearing state.

</details>

[起点源码](../checkpoints/CP06.rs) · [hint原文件](CP06/hint.json) · [全部修改与工具反馈](CP06/PROCESS.md) · [最终源码](CP06/final.rs) · [最终验证](CP06/result.json)

<a id="cp7"></a>
### CP7：主动复现结构错误后清理

**客观起点（原trace事件69）。** 起点数学正确。

**Hint作何判断。** 提醒验证结构差异，不要求另造数学证明。

**实际编辑与验证顺序。** 20 Verus通过，24 Lynette失败；31删除导入，33／37双通过。

**为什么这些修改有效，或仍然失败。** 这里没有还没证明的长度或索引事实。actor先对同一候选得到Verus通过和Lynette失败，定位为结构层，再删导入重验。没有把“证明已通过”误当作“整个任务已完成”，这段诊断顺序有独立价值。

**Hint究竟起了什么作用。** 提示要求核对兼容风险，actor确实验证后做最小改动。它约束了不必要的数学重写，但不是产生另一种数学证明。

**同起点两版对照。** v1先Verus后直接清导入，没有先运行本轮Lynette；两者最终源码修复同类，只是诊断证据多少不同。 见[另一版CP7](../v1/REPORT.md#cp7)。

**语义审计结论。** 与v1最终改动相同，额外诊断步骤有真实目的。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The proof body now verifies in Verus; do not add further proof steps. The remaining issue is compatibility/cleanup: this checkpoint has an extra top-level vstd::seq_lib import that is absent from input.rs, and Verus reports it as unused. Since the task requires both Verus and Lynette checks, first restore the import surface to match input.rs while keeping the verified proof body unchanged. Then run Verus again to confirm no warning or error, and run Lynette. The fact that a cleaned version with the same proof body later passed both checks supports this cleanup direction, but this checkpoint itself has only been checked by Verus; if Lynette reports an issue with the extra import, that failure would be specific to this state. Do not add assumptions or new lemmas.

</details>

[起点源码](../checkpoints/CP07.rs) · [hint原文件](CP07/hint.json) · [全部修改与工具反馈](CP07/PROCESS.md) · [最终源码](CP07/final.rs) · [最终验证](CP07/result.json)

## 可用于训练的范围

本版最终双通过项可作为待格式整理的训练候选，必须携带题目规格、完整checkpoint起点和真实编辑／工具结果。失败中间态保留失败标签，不把未验证断言、错误API、actor自述或hint的诊断预测变成已证明事实。终点正确不表示每个中间尝试都正确；失败后的有效修复本身可有价值。AC v1 CP1、AC v2 CP3只作失败对照，不混入成功样本。

逐条核对了checkpoint hash、最终candidate与宿主验证hash、input未变化及skill一致性。源码差分中未发现新增assume/admit/external_body/unimplemented绕过标记；AC题目原有组件stub不算本轮新增。见[source_checks.json](source_checks.json)。这些检查与源码阅读不等于对任意工具行为的安全证明；本报告不把一次通过当作下游skill收益证据。

本题策略差异依赖核心引理、见证与证明分解判断，不用hash/F1代替语义审计。所有hint也并非“纯数学”：宏限定、implies、删除非法属性等含实现指导，但未给出可直接粘贴的完整最终proof。成功的hint采纳只能说明行为对应，不能证明提速因果或跨题稳定性。

## Hint生成成本

| CP | 输入token | 输出token |
|---|---:|---:|
| [CP1](#cp1) | 35,187 | 1,684 |
| [CP2](#cp2) | 35,109 | 2,441 |
| [CP3](#cp3) | 36,181 | 3,165 |
| [CP4](#cp4) | 35,561 | 4,578 |
| [CP5](#cp5) | 36,171 | 3,154 |
| [CP6](#cp6) | 35,319 | 3,069 |
| [CP7](#cp7) | 35,320 | 2,032 |

保留的自动证据原稿（未随本次发布的本地材料） · [结构化语义审计](semantic_audit.json)
