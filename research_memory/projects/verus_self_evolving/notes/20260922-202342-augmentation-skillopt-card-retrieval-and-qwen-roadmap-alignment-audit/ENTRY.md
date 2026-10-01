# Augmentation SkillOpt card retrieval and Qwen roadmap alignment audit

## Metadata

- project: `verus_self_evolving`
- kind: `notes`
- created_at: `2026-09-22T20:23:42`
- status: `complete` (repository audit only)

## Scope

核对用户第4–8项：obfuscation / hint augmentation、增强skill对比原SkillOpt、
基于增强轨迹提取skillcard、retrieval / hint机制、Qwen简单评测。
结论是方向对齐，尚未形成augmentation → skill → retrieval → Qwen的实验闭环。
本条是仓库审计，下列实验顺序是建议，不表示已执行或新实验已获授权。

检查研究记忆、计划、发布摘要及实际接入代码。本会话未配置外部run root，
外部运行状态依据已审阅仓库记录；未直接核验全部原始轨迹。保留工作区已有及
调研期间其他会话新增的实现／文档修改。

## Alignment and evidence

所有路径相对仓库根目录。

| 事项 | 已核实进度 | 缺口 |
|---|---|---|
| 4. 两种augmentation | Hint有IR/AC/AL三题19个checkpoint，v1/v2共38条续跑，各18/19双通过；fresh no-hint为19/19。另有完整F／精简F／无参考两题实验，共24条续跑。 | v1/v2是hint方法的两个版本。未找到明确命名的语义保持obfuscation实现／结果；若用户指精简F，需明确映射，pruning／参考可见性不自动等于混淆。 |
| 5. 对比增强skill与原SkillOpt | 已保留普通train-40第一阶段skill，已定义内容比较维度。 | 未找到已审阅的增强skill结果或三方法下游对照。三题与40题的文本比较只能用于定性诊断。 |
| 6. Augmented skillcard pipeline | 已有fork exporter、task-grouped Reflect driver、card prompt和native merge/rank；每题最多2条提议、全局最多4项编辑。 | 当前是三题diagnostic，尚无完整train-40公平对照或经gate接受的新card bank。 |
| 7. Retrieval / hint | 旧路径已有project过滤、关键词top-1、至少2个trigger匹配及abstention，含注入日志和selection gate代码。 | 查询使用全部messages，未限定最新验证状态；negative scope仅展示。当前Codex训练／固定test evaluator未接该动态retrieval，Markdown card与JSON bank也未打通。 |
| 8. Qwen简单eval | 固定test-20评测基础设施及旧SkillOpt／Trace2Skill结果已存在。 | 未核实新obfuscation／hint-derived skill／retrieval链路的Qwen结果。 |

关键证据：

- `docs/hint-augmentation-20260916/README.md`和`INFORMATION_VALUE_AUDIT.md`：
  38条续跑、hint版本、成功／失败／重复主题及信息价值边界。
- `docs/skillopt-fork-packets-20260918/NO_HINT_RESULTS_20260919.md`：19条fresh
  no-hint；存在Codex/Lynette版本漂移，19/19对18/19不构成稳定的hint效应结论。
- `docs/deepseekv4pro-augmentation-20260911/README.md`：两题三种参考条件；
  blank skill和隔离设置与后续hint实验不同，不能直接做净方法比较。
- `docs/skillopt-fork-packets-20260918/README.md`：证据包与diagnostic协议。
- `skillopt-verusage/src/skillopt_verusage/fork_card_optimize.py`：只接受hint-visible
  packet，输出`candidate_skill.md`，不是可直接使用的retrieval JSON bank。
- `skillopt-verusage/prompts/fork_cards/analyst.md`：Trigger / Action / Validate /
  Avoid when；支持及反驳分支在patch reasoning中记录。
- `skillopt-verusage/skills/baselines/README.md`：普通train-40第一阶段比较参考；
  augmentation仍用`skills/initial.md`作为seed，不能混同seed与learned baseline。
- `skillopt-verusage/src/skillopt_verusage/retrieval.py`、`skill_proxy.py`、
  `retrieval_gate.py`：旧runtime原型；support audit核对task标签，不能替代逐状态
  card动作replay。`schemas/retrieval_cards.schema.json`定义JSON bank接口。
- `skillopt-verusage/src/skillopt_verusage/train.py`：Codex adapter分支不传
  retrieval_cards_path，旧VeruSAGEAdapter分支才传。
- `skillopt-verusage/src/skillopt_verusage/test_eval.py`：当前固定skill文件／bundle入口。
- `research_memory/projects/verus_self_evolving/experiments/20260821-130358-skillopt-s1-s2-four-model-held-out-evaluation/ENTRY.md`：
  历史600秒Qwen blank/S1/S2为3/20、5/20、6/20。
- `research_memory/projects/verus_self_evolving/experiments/20260826-225014-qwen-test20-three-arm-heatmaps/ENTRY.md`：
  历史1200秒Qwen blank/S2/Trace2Skill为5/20、7/20、6/20。
  两组预算与条件不同，不混表，不当作新augmentation的效果。

## Latest trajectory availability correction

调研期间CURRENT与fork README同步了新进展：完整38条历史hint轨迹已在
`76f75dae6a0ad791e22aea5dab44ede0e820c3c0`找回并校验，六个真实archive适配
已通过。优先复用该archive，不再计划重跑hint。当前主机仍缺三条完整原始
train轨迹；需在Vegeta或转移原件后做真实prefix/suffix export与SkillOpt调用。
使用synthetic原始prefix元数据的集成测试只验证导出机制，不能替代真实训练证据。
本条没有独立重跑archive验证。

## Proposed sequence with verifiable milestones

1. **冻结方法定义与身份。** 确认obfuscation具体操作，记录train任务、checkpoint、
   seed skill、模型、工具链及预算。验收：两种方法分别对应可定位的代码与证据。
2. **先产出三题诊断card。** 复用已恢复hint与no-hint，补齐完整原始轨迹，执行
   task-grouped提取。验收：每张card的触发状态、实际动作、验证及反例可追溯；
   与普通train-40 skill对比新增／保留／删除内容，不从文本差异推出性能收益。
3. **完成第5项数据对照。** 固定原SkillOpt提取流程，在相同任务集合上比较原始、
   原始+obfuscation、原始+hint。控制seed、optimizer、proposal权重和skill预算，
   在selection-20选择、冻结后才报告test-20。生成成本单列；增加相近生成预算的
   fresh no-hint对照，区分干预内容与多采样收益。
4. **隔离第6项提取贡献。** 固定增强材料，对比原提取与task-grouped card提取。
   复用verifier、isolation、merge/rank和gate，优先改证据单元、batch及card输出。
   同题checkpoint总权重为1，同时控制不同minibatch导致的proposal权重差异；
   三题diagnostic不能直接混入37题普通提议后声称权重公平。
5. **接通第7项最小机制。** 将审核后的Markdown card转成机器可读bank并保存证据
   sidecar。复用project/keyword top-1+abstention；查询用任务规格、当前源码和
   最新有效Verus诊断，避免重复注入。接入当前Codex/Qwen路径，记录查询、命中、
   abstain、实际注入及后续行动。用同一bank比较固定注入与检索注入。
6. **第8项分dev smoke与固定评测。** 先在非test任务覆盖AC/AL/IR并核验工具调用；
   冻结Qwen revision/precision、harness、Verus/Lynette、时限与并发后跑test-20。
   先比较第5项三种skill，再比较同一bank的固定／检索注入。首轮单次是诊断，
   有信号后预先声明重复规则，报告paired gains/regressions与不确定性。

## Necessary additions

- **区分训练hint与运行hint。** Teacher可见train题原F及完整轨迹；评测时只能
  由冻结train bank与当前可观察状态提供hint，不能读取test F或未来反馈。
- **小消融。** 同一fork packet的hint-visible / hint-masked检查是否只是复制teacher；
  同一bank的固定／检索注入检查routing。随机卡／oracle只在dev诊断确有需要时追加。
- **有效样本与选择偏差。** 19个checkpoint仅来自3题；成功、重复及有信息失败分开。
  当前selector按Verus事件源码hash去重并排除最终源码，不等于按停滞／错误类型采样。
  先报告状态分布，再决定是否增加checkpoint选择规则。
- **主终点。** 预算内双验证solved、逐题得失、总input/output、wall time、timeout及
  安全性；区分最终proof正确与预算内完成。Teacher、augmentation、提取及retrieval
  成本分别记录。信息增益和新增策略数仅作次级诊断。
- **统一计划入口。** 根`PLAN.md`仍是7月R041；`skillopt-verusage/PLAN.md`是8月
  Trace2Skill迁移；refine-logs计划是8月跨模型评测；9月主线散在CURRENT与docs。
  建议增加4–8项当前里程碑索引并保留历史合同，本轮不改既有计划或R系列状态约束。

## Closeout

本轮仅检查仓库并写紧凑研究摘要；未运行模型、训练、评测或测试。未读取sealed
任务内容、未改raw数据／固定benchmark／历史run、未改已有实现。下一步建议是
明确obfuscation并完成三题card产出与证据审计，再扩展公平比较。
