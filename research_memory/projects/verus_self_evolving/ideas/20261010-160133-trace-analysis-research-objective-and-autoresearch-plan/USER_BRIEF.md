# User Research Brief

Recorded: 2026-10-10 (Pacific). This is the user's original request, preserved verbatim.

找找有没有相关评价，我现在主要是方法上陷入瓶颈了，我们的科研目标是说，我们认为agent现在不断的产生大量的长trace，这些trace对提炼经验非常重要，但是常见的agent分析方法往往是将大量trace统一扔给agent，这样的设置对人类专家已经是一个考验，所以我们猜agent在这方面也不是很好，所以想开发一些方法提升agent分析trace的能力，能够在benchmark的这些问题中，榨取出更多可以泛化的经验，便于提升在同类问题上的能力，目前先考虑verusage这个场景，如果你的解决方法不是很泛化到普遍code generation，就只需要测试verusage上的表现，如果很泛化，就需要补充在code 生成任务上的表现，优先尝试优化verusage上的能力以及efficiency。我们目前需要测试已经划分的verusage的训练集，有40个train 20个validation以及很多test，主要是用deepseekv4pro来跑，批判性的审阅我们的描述，可能有些站不住脚的你需要用一些实例证据提醒我，但是总体是想要做这个方向。把我刚刚说的内容保存，然后你找找你可以调用的autoresearch工具，找一个最有用的，然后批准你的计划

## Normalized constraints

- Research target: improve agents' analysis of long execution traces so extracted experience improves performance on related unseen tasks.
- Initial domain: VeruSAGE / Verus proof repair.
- Priorities: task-solving capability and efficiency; offline analysis quality is an intermediate measure.
- Model: mainly DeepSeek V4 Pro; do not silently replace it with another actor.
- Requested data regime: existing train40 / validation20 and additional test tasks. Verify manifests and test provenance before using any test task.
- Scope: Verus-specific methods can remain VeruSAGE-only; methods making broad code-generation claims need a code-generation evaluation.
- Review: challenge weak premises with concrete evidence while preserving the overall research direction.
- Current deliverables: saved brief, tool evaluation/callability audit, one selected useful autoresearch workflow, critical review, concrete research plan.
- Approval wording is ambiguous: do not manufacture user approval or launch a paid campaign from this planning request. Prepare the complete reviewable plan first; obtain explicit launch scope/budget before paid execution.
