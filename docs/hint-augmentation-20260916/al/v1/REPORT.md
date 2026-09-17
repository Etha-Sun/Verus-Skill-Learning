# AL · Initial skill + Hint v1：逐checkpoint语义审计

**本版全部7条过程审计完成，待用户复核。** 审查保存的起点、hint正文、每次源码变化、实际工具反馈及最终宿主验证；本次没有重新调用模型或验证器。最终正确与中间每一步正确分开判断。

两版均7/7，主要保持“长度消去＋前缀逐点相等＋外延性”同一数学路线。v2 CP3/5直接成功，部分点仍有量词／导入返工。v1 CP1首个无依据的相等断言是错误尝试，须在训练整理中明确标失败。

## 先读懂原题与原F

目标为`s1 == s2 <==> s1 + suffix == s2 + suffix`。正向只需等式替换；逆向不能直接从拼接相等跳到前缀相等，原F补了两个桥梁：由拼接长度相等消去共同suffix长度，得到s1、s2等长；然后对前缀范围内的i，用拼接索引定律把两侧元素还原为s1[i]与s2[i]，最后用序列外延性。

CP1为空proof，CP2逆向缺事实，CP3使用不可解析的引理，CP4长度／索引桥接未补全，CP5改猜对象方法仍失败，CP6外延宏内缺逐点事实，CP7数学已通过。宏、局部broadcast和显式forall是表达该路线的不同方式，不应仅凭源码不同称作新数学策略。额外顶层导入可能不影响Verus证明，却影响本实验Lynette的结构比较。

## 图与版本对照

![同initial skill的两版hint对照](../v2/comparison_prefix_tokens.png)

两版actor输出合计：v1 **65,299**，v2 **54,141**（-17.1%）。包括失败续跑和结束说明，hint生成另计。上图为相对原F的Patch F1，即参考路径相似度；下图为同一观测的Verus状态。横轴包含原前缀归属token，但actor并未回放原前缀；彩色竖虚线仅标首次提取到的Verus通过，不等于Lynette／整个任务完成。

[本版单组图](hint_prefix_tokens.png) · [v1审计](REPORT.md) · [v2审计](../v2/REPORT.md) · [图表数据](../comparison.json)

## 数据和条件核对

来源为Yuechun固定train40中本题的step_0001 DeepSeek v4 Pro原轨迹。全部起点沿用冻结的Yuechun checkpoint提取逻辑；没有按结果另选checkpoint。原轨迹和本轮actor均通过工作区SKILL.md装备同一initial skill，SHA256为`96a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40`。本版每条实际读取全文的事件见下表；不是仅根据文件存在推断使用。

Actor获原题、完整checkpoint代码、fresh hint和skill；hint agent可看原完整轨迹与F。没有把原完整对话或F直接发给actor。38个hint全新生成，旧blank组保持不动。新旧同时变化了skill和hint样本，不能把actor差异单独归因于skill；本轮v1/v2也仅各一次采样，不支持稳定因果结论。

[原题规格与源码](../original_input.rs) · [原trace最终源码F](../original_final.rs) · [原轨迹](../ORIGINAL_CHANGES.md) · [Skill装备核对](../../SKILL_PARITY.md)

## 本版逐点结果

| CP | Actor输出token | 源码变化次数 | 读取skill事件 | 最终Verus＋Lynette |
|---|---:|---:|---|---|
| [CP1](#cp1) | 11,474 | 3 | 14 | 通过 |
| [CP2](#cp2) | 8,816 | 1 | 17 | 通过 |
| [CP3](#cp3) | 6,950 | 3 | 18 | 通过 |
| [CP4](#cp4) | 15,920 | 5 | 6 | 通过 |
| [CP5](#cp5) | 8,039 | 1 | 11 | 通过 |
| [CP6](#cp6) | 10,382 | 3 | 21 | 通过 |
| [CP7](#cp7) | 3,718 | 1 | 15 | 通过 |

事件编号使用本条agent_events.jsonl的event_index；源码变化取snapshot差分事件，工具编号取完成命令事件，可能与图中随后保存的verifier事件相差1，不是不同轨迹。源码变化次数不是提取后的checkpoint数。

同版本旧blank审计另见旧v1报告（未随本次发布的本地材料）。下面的逐点版本对照均指**本轮两个initial-skill组**，不混用旧blank结果。

## 逐checkpoint语义审计

<a id="cp1"></a>
### CP1：方向正确，但首个分支写出错误断言

**客观起点（原trace事件21）。** 空proof，需证明加同一suffix保持且反映序列相等。

**Hint作何判断。** 长度消去、合法前缀索引相等、外延性是正确逆向证明路线。

**实际编辑与验证顺序。** 32在s1!=s2分支无相应假设直接断言拼接相等及s1==s2；34失败。40改为在拼接相等假设下证明长度和逐点相等，但调用不存在的ext_equal方法；42 E0599。48删错误方法，50／55双通过。

**为什么这些修改有效，或仍然失败。** s1!=s2并不推出两者拼接相等，更不推出s1==s2。最初逆向分支缺少“拼接相等”的假设，直接写这些assert是错误尝试，不能称作提前列出若干正确事实。事件40改为在真正逆向前提下做长度消去和索引推理，逻辑才接回原目标。随后ext_equal是不存在的方法，删除它后已有事实足以由验证器闭合目标。

事件32的实际错误分支如下（保留原代码，不是建议写法）：

```rust
    } else {
        assert(s1 + suffix == s2 + suffix) by {
            // Backward direction is not yet established; keep this branch explicit
            // so the verifier reports the remaining subgoal.
        }
        assert(s1 == s2);
    }
```

这里else继承的是`s1 != s2`。注释把它称为暴露剩余子目标，但断言并非由该分支前提推出；事件34实际报错。事件40改成独立的`if s1 + suffix == s2 + suffix`后才回到正确逆向前提。这是源码与自述不一致的明确例子，训练时以代码／诊断为准。

**Hint究竟起了什么作用。** hint给出的逆向链本来正确，错误分支和猜API由actor生成，不是提示要求。提示至少在后续修复中被采用；但不能用最终通过为最早无依据断言背书。

**同起点两版对照。** v2没有该错误逆向分支，但仍先写错broadcast名称及量词前提形式。两版都需区分数学路线正确与具体实现正确。 见[另一版CP1](../v2/REPORT.md#cp1)。

**语义审计结论。** 最终逻辑成立，但事件32不能解释成合理的“分阶段证明”：它是错误中间尝试。可保留真实纠错轨迹，禁止把该失败断言抽成有效推理步骤。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Current failure is an unproved postcondition in an empty body. The target is an equivalence, so the next objective is to prove the two implications separately. For the forward direction, if s1 == s2, append the same suffix to both sides and close the concatenation equality by congruence. The backward direction is the real gap: from s1 + suffix == s2 + suffix, do not immediately assert s1 == s2; that fails. Instead derive equality stepwise. First use equality of the concatenations to obtain equal lengths, then reason from the length behavior of sequence append to conclude s1.len() == s2.len(). Then prove extensional equality of s1 and s2: for any index in s1's range, the corresponding concatenated indices are equal by assumption, and because the index is below s1.len(), those values reduce to s1[i] and s2[i]. Equal lengths plus pointwise equality should close sequence equality. Run Verus after establishing each direction to identify the remaining subgoal.

</details>

[起点源码](../checkpoints/CP01.rs) · [hint原文件](CP01/hint.json) · [全部修改与工具反馈](CP01/PROCESS.md) · [最终源码](CP01/final.rs) · [最终验证](CP01/result.json)

<a id="cp2"></a>
### CP2：一次补齐逆向事实

**客观起点（原trace事件28）。** 正向已可证明，逆向直接断言序列相等失败。

**Hint作何判断。** 准确要求先等长、再逐索引相等。

**实际编辑与验证顺序。** 66补长度／索引推理及proof局部broadcast use vstd::seq::group_seq_axioms；68／73双通过。

**为什么这些修改有效，或仍然失败。** 仅知道两个拼接序列相等时，必须先确保前缀长度相同，才能将同一i同时视作两边的合法前缀索引。补入长度等式完成这一步，再用拼接索引性质获得逐点相等，最后外延性才能收尾。局部broadcast激活相关库事实，没有改写目标规格。

**Hint究竟起了什么作用。** 长度和索引两项提示都得到明确代码对应，没有见到改规格或增加未经证明的假设。值得保留的是事实依赖链，而不只是“最后通过”这条标签。

**同起点两版对照。** v2也一次补全同类事实；两版没有实质数学策略差异。 见[另一版CP2](../v2/REPORT.md#cp2)。

**语义审计结论。** 清楚的缺失事实→补足→验证样本。局部broadcast不等于改变顶层导入；检索时间不应从成本中忽略。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is the backward direction of the biconditional: under the assumption that s1 + suffix == s2 + suffix, the direct assertion s1 == s2 is too strong for Verus to derive automatically. The next proof objective is to establish the two facts needed for sequence equality of s1 and s2: equal lengths and matching elements at every valid prefix index. From equality of the concatenated sequences, first derive equality of their lengths, then unwind the length relationship of sequence concatenation to conclude that s1.len() and s2.len() agree. After that, for an arbitrary index i in the prefix range, use the equality of the concatenations at i and the fact that indexing a concatenation before the boundary of the left operand selects the left operand's element. This gives pointwise equality on the prefixes, after which sequence extensionality should close the goal. Re-run Verus after this reasoning; the diagnostic should progress from the failed assertion to any remaining unfoldings before Lynette is checked.

</details>

[起点源码](../checkpoints/CP02.rs) · [hint原文件](CP02/hint.json) · [全部修改与工具反馈](CP02/PROCESS.md) · [最终源码](CP02/final.rs) · [最终验证](CP02/result.json)

<a id="cp3"></a>
### CP3：先去错调用，再补事实，再清导入

**客观起点（原trace事件36）。** lemma_seq_add_len/index解析失败，起点含导入。

**Hint作何判断。** 建议不用猜测API，以长度及索引基本事实完成。

**实际编辑与验证顺序。** 39只删不可用调用，41长度断言失败；47补长度展开，49 Verus；54 Lynette失败；60删导入，62／66双通过。

**为什么这些修改有效，或仍然失败。** 删除不可解析调用只消除了编译障碍，不会凭空产生原来希望那些调用提供的拼接事实。因此第一次删调用后长度断言仍失败是合理诊断，下一轮显式长度展开才补上实际证明缺口。最后删导入处理结构要求，与长度论证本身无关。

**Hint究竟起了什么作用。** actor接受了不用猜测API的方向，但第一次只做“去掉错误语句”，没有同时补其数学职责；之后才补全，提示落实延迟。hint没有让此点提前规避导入失败。

**同起点两版对照。** v2把去调用、补事实和删导入一次做完，本点是可观察到修复组织改善的配对案例。 见[另一版CP3](../v2/REPORT.md#cp3)。

**语义审计结论。** 数学建议有效但未一次落实，兼容未预防。API解析失败不能泛化成任何环境都没有同名引理。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The Verus diagnostic is a name-resolution failure: the proof calls two guessed vstd::seq_lib lemmas for concatenation length and indexing, but those names do not exist. Do not hunt for similarly named helpers. In the branch where s1 + suffix == s2 + suffix, prove the needed facts directly from sequence concatenation. First derive s1.len() == s2.len(): equality of the concatenated sequences gives equal lengths, and concatenation length is the sum of component lengths. Then prove pointwise prefix equality: for any valid index i < s1.len(), the equality of the concatenated sequences gives equal values at i, and concatenation indexing gives those values as s1[i] and s2[i]. Equal lengths plus pointwise equality support extensional equality s1 == s2. Remove the unresolved helper calls, re-run Verus, and use any remaining assertion failure to identify whether those concatenation facts need a more explicit proof or available library statement.

</details>

[起点源码](../checkpoints/CP03.rs) · [hint原文件](CP03/hint.json) · [全部修改与工具反馈](CP03/PROCESS.md) · [最终源码](CP03/final.rs) · [最终验证](CP03/result.json)

<a id="cp4"></a>
### CP4：数学路线保留，实现上多次返工

**客观起点（原trace事件48）。** 长度桥接与外延宏证明未完成，另有导入。

**Hint作何判断。** 长度／逐点目标正确；“不用宏”的倾向不是必要数学限制，宏在事实齐备时可用。

**实际编辑与验证顺序。**

| 编辑／检查事件 | 修改意图 | 实际反馈与解释 |
|---|---|---|
| 46／48 | 补长度与宏内索引，激活broadcast组 | 组名不可解析，数学主体尚未通过检查 |
| 54／56／61 | 用顶层导入解决组名 | Verus通过，但Lynette报差异；名称可见与结构允许是两回事 |
| 76／78／82 | 改限定组名并删新增导入 | Verus通过，Lynette仍失败；另一个原有seq_lib导入未删 |
| 107／109 | 删剩余导入，宏改显式forall | 引入==>前提上下文问题，索引证明失败 |
| 115／117／121 | 将该量词改为implies | 前提进入证明体，Verus与Lynette最终都通过 |

**为什么这些修改有效，或仍然失败。** 第一次证明构造本身沿用长度和索引路线，但未限定broadcast组导致名称失败。用顶层导入救活名称后，Verus通过却Lynette失败；移除一条导入仍失败，因为原seq_lib导入还在。随后改写宏为forall时又使用==>，前提没进入proof体，引出新的索引问题。最终implies修复的是该局部上下文，不是新增序列数学定理。

**Hint究竟起了什么作用。** hint数学目标可行，却没有约束住名称／导入的反复试错。它对宏的偏好不应被当成“宏路线不合法”的结论；本题宏和forall都能表达正确外延证明。

**同起点两版对照。** v2仍有==>和导入返工，但未经历v1新增导入再逐个删掉的长链；相同数学路线的实现效率有所不同。 见[另一版CP4](../v2/REPORT.md#cp4)。

**语义审计结论。** 不存在顺畅的一次修复；失败都有实际源码和反馈。最终长度＋逐点路线成立，错误API、导入和前提写法不能作为正知识。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The backward direction is failing because after assuming the concatenations are equal, Verus has not derived either length equality or pointwise prefix equality. The sequence-equality macro cannot close until those facts are available. Next objective: derive len(s1) == len(s2). Equality of the concatenated sequences gives equality of their lengths; express each concatenated length as a sum and cancel the common len(suffix). Then prove the prefixes agree pointwise: for an arbitrary valid index i of s1, compare the concatenated sequences at i and use the concatenation index property on each side to reduce this to s1[i] == s2[i]. Finally close with sequence extensionality rather than the macro. Check by rerunning Verus: the length assertion should pass, and the pointwise/extensionality step should establish the backward implication. If an index-unfolding assertion fails, expose that concatenation index fact before using it in the pointwise proof.

</details>

[起点源码](../checkpoints/CP04.rs) · [hint原文件](CP04/hint.json) · [全部修改与工具反馈](CP04/PROCESS.md) · [最终源码](CP04/final.rs) · [最终验证](CP04/result.json)

<a id="cp5"></a>
### CP5：数学与导入一次修好

**客观起点（原trace事件55）。** Seq对象方法调用不可用，长度／索引桥接待补。

**Hint作何判断。** 建议直接用拼接事实，并删除不再使用的导入。

**实际编辑与验证顺序。** 54删除错误方法和导入，补长度与索引事实；56／61双通过。

**为什么这些修改有效，或仍然失败。** 不可用对象方法原本想提供长度与索引事实。事件54用显式拼接等式替代这些调用，使逆向证明先确定前缀长度，再在合法索引上建立元素相同；一并去掉不再需要的导入避免提交结构差异。这里没有通过删掉证明责任来取得通过。

**Hint究竟起了什么作用。** 数学替代和兼容清理都与hint对应，之后直接双通过，是本版较清楚的采纳样例。仍只能说明本次行为对应，而非证明每次同提示都如此。

**同起点两版对照。** v2也是一次同类修复；两版差别不足以支持“新解法”，更适合作重复可行的修复模式。 见[另一版CP5](../v2/REPORT.md#cp5)。

**语义审计结论。** 本题直接采纳提示的清晰成功项，仍是原证明的同类数学路线。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The current failure is a method-resolution problem, not a missing proof obligation: the guessed Seq helpers for concatenation length/index do not exist in this vstd version. Replace that approach by using the built-in facts about Seq concatenation directly. The mathematical facts needed are that concatenation length is the sum of component lengths, and for an index below the prefix length, the concatenated value equals the prefix value at that index. In the backward direction, first derive equal lengths from the assumed equality of concatenated sequences, then decompose the lengths to conclude the prefixes have equal length. Then prove pointwise equality for each valid index by exposing the prefix-index simplification on both sides and matching them through the concatenation equality. Finally close with sequence extensionality. Remove the now-unnecessary seq_lib import if no library helpers remain. Re-run Verus: success should first eliminate the E0599 method errors, then verify the postcondition.

</details>

[起点源码](../checkpoints/CP05.rs) · [hint原文件](CP05/hint.json) · [全部修改与工具反馈](CP05/PROCESS.md) · [最终源码](CP05/final.rs) · [最终验证](CP05/result.json)

<a id="cp6"></a>
### CP6：证明补好后处理两层名称问题

**客观起点（原trace事件62）。** 外延宏内尚缺拼接索引事实，起点有导入。

**Hint作何判断。** 提示补逐点关系；没有使actor避免后续名称／导入问题。

**实际编辑与验证顺序。** 55补宏内索引证明但broadcast未限定，57解析失败；63限定broadcast，65 Verus；70 Lynette失败；76删导入并限定宏，78／82双通过。

**为什么这些修改有效，或仍然失败。** 序列相等宏不会自动知道拼接前缀索引定律：补宏内逐点事实才填上数学空缺。未限定broadcast与顶层导入是随后两个独立实现问题；前者修后Verus已过，后者只有Lynette暴露，最后限定宏保留相同论证。

**Hint究竟起了什么作用。** hint在数学层有可见作用，但没有避免actor使用错误名称，也没让它在第一次编辑时清理导入。不能把后续全部返工描述成有益证明展开。

**同起点两版对照。** v2无本轮v1的broadcast名称错误，但仍数学通过后才处理导入；二者并非兼容问题都被彻底解决。 见[另一版CP6](../v2/REPORT.md#cp6)。

**语义审计结论。** 核心数学修复有效，工具兼容延迟处理。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

Verus now fails only at the sequence-equality macro for s1 and s2. The length reasoning is no longer the problem, but the macro cannot derive pointwise equality from the concatenation equality by itself. Next objective: in the branch where s1 + suffix == s2 + suffix, prove that for every valid prefix index i, s1[i] == s2[i]. Use the assumed equality of the concatenated sequences at that same i, then unfold the meaning of concatenation indexing in the prefix range so that (s1 + suffix)[i] is s1[i] and (s2 + suffix)[i] is s2[i]. Once length equality and this pointwise prefix equality are available, close by sequence extensionality rather than relying only on the macro. Re-run Verus: a successful edit should eliminate the macro failure and report 1 verified, 0 errors, possibly with only an unused-import warning.

</details>

[起点源码](../checkpoints/CP06.rs) · [hint原文件](CP06/hint.json) · [全部修改与工具反馈](CP06/PROCESS.md) · [最终源码](CP06/final.rs) · [最终验证](CP06/result.json)

<a id="cp7"></a>
### CP7：删除多余导入

**客观起点（原trace事件69）。** 起点数学已通过，只剩可能的结构差异。

**Hint作何判断。** 建议清理unused导入后检查Lynette。

**实际编辑与验证顺序。** 19确认Verus，25删除导入，27／32双通过；本次未先复现Lynette失败。

**为什么这些修改有效，或仍然失败。** 本点已有长度、合法索引和外延性完整链，删导入不改变该链。actor先确认Verus，然后按提示改结构并通过Lynette；本次没有先测出Lynette失败，所以不能把原轨迹中的失败事件冒充本轮实际事件。

**Hint究竟起了什么作用。** hint作用是约束修复范围，避免对已经正确的数学继续动手。它可能节省无关重写，但没有无hint配对重复实验来量化该因果效应。

**同起点两版对照。** v2先实际运行Lynette确认差异再删导入；最终修复内容相同，诊断顺序不同。 见[另一版CP7](../v2/REPORT.md#cp7)。

**语义审计结论。** 只做兼容清理，不计作新的数学解法。

**最终检查边界。** 宿主Verus=通过，Lynette=通过；该结论对应链接中的最终candidate hash，不用中途通过替代终点检查。

<details><summary>本次实际发送的hint全文</summary>

The mathematical proof in this checkpoint is already accepted by Verus: the recorded run reports 1 verified, 0 errors. Do not add more sequence reasoning unless a later check exposes a new failure. The remaining issue is a warning for an unused `vstd::seq_lib` import. Remove that unused import since the current proof does not call any `seq_lib` helpers; then rerun Verus and confirm clean verification. Also run the Lynette comparison, because Verus success alone does not establish proof-only safety/spec preservation. If Lynette reports a mismatch, classify its diagnostic before changing the proof.

</details>

[起点源码](../checkpoints/CP07.rs) · [hint原文件](CP07/hint.json) · [全部修改与工具反馈](CP07/PROCESS.md) · [最终源码](CP07/final.rs) · [最终验证](CP07/result.json)

## 可用于训练的范围

本版最终双通过项可作为待格式整理的训练候选，必须携带题目规格、完整checkpoint起点和真实编辑／工具结果。失败中间态保留失败标签，不把未验证断言、错误API、actor自述或hint的诊断预测变成已证明事实。终点正确不表示每个中间尝试都正确；失败后的有效修复本身可有价值。AC v1 CP1、AC v2 CP3只作失败对照，不混入成功样本。

逐条核对了checkpoint hash、最终candidate与宿主验证hash、input未变化及skill一致性。源码差分中未发现新增assume/admit/external_body/unimplemented绕过标记；AC题目原有组件stub不算本轮新增。见[source_checks.json](source_checks.json)。这些检查与源码阅读不等于对任意工具行为的安全证明；本报告不把一次通过当作下游skill收益证据。

本题策略差异依赖核心引理、见证与证明分解判断，不用hash/F1代替语义审计。所有hint也并非“纯数学”：宏限定、implies、删除非法属性等含实现指导，但未给出可直接粘贴的完整最终proof。成功的hint采纳只能说明行为对应，不能证明提速因果或跨题稳定性。

## Hint生成成本

| CP | 输入token | 输出token |
|---|---:|---:|
| [CP1](#cp1) | 34,740 | 2,138 |
| [CP2](#cp2) | 34,662 | 1,754 |
| [CP3](#cp3) | 35,734 | 2,141 |
| [CP4](#cp4) | 35,114 | 2,190 |
| [CP5](#cp5) | 35,724 | 2,798 |
| [CP6](#cp6) | 34,872 | 1,771 |
| [CP7](#cp7) | 34,873 | 1,595 |

保留的自动证据原稿（未随本次发布的本地材料） · [结构化语义审计](semantic_audit.json)
