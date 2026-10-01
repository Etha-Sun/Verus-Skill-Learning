# Augmentation Experiment Plan — Budget-Conscious Version

> Active execution proposal: [forty-task experiment and budget plan](augmentation-main-experiment-20261001.md).
> It specifies the first comparison, eligibility, cost assumptions, budget design
> and audited pipeline/runtime gaps. The September 29 matrix below is retained
> as a historical set of candidate ablations, not the current execution order.

> Status update from the October 1 meeting: prioritize a 40-source-task main
> comparison against SkillOpt under reasonably matched learning budgets; small
> engineering checks may precede it. The matrix below preserves the September 29
> candidate ablations, but N=10 efficacy and every ablation are no longer required
> before that main comparison. Budget scope and exact settings remain to be frozen.
> See the [reviewed meeting summary](../research_memory/projects/verus_self_evolving/meetings/20261001-144332-forty-task-augmentation-experiment-priorities-and-learning-budget-meeting/ENTRY.md).

## Counting and Format Conventions

- 首轮不安排 160 条轨迹的实验；先在 10 道题上比较方法，有信号后再扩到 40 道题。
- 核心增强实验统一为**每题保留 1 条 original，只新增 1 条轨迹**：10 题共 20 条，40 题共 80 条。表中同时标出新增数量，避免将已有轨迹计作新的生成开销。
- 10 题使用同一固定 40 题集合的子集。Original 条件优先复用已有轨迹。
- `Cards / Plain Skill` compares structured cards with free-form skill text, using the same delivery mechanism and length budget. Cards may also be stored in a single file.
- A slash denotes separate experimental conditions. Grouping/format ablations reuse the exact same traces; they require new extraction/evaluation, not new trajectory generation.

## Experiment Matrix

| ID | Training Data | Analysis Grouping | Skill Format | Main Comparison |
|---|---|---|---|---|
| A | Original 40 problems / 40 existing traces | Positive–Negative / Random | Cards / Plain Skill | **先做：**复用已有数据，比较分组和格式，建立标准基线 |
| B | Original 10 problems / 10 existing traces | Random | Cards | **先做：**少数据基线，复用 A 的同一子集 |
| C | Unguided resampling: 10 problems / 20 total traces (**10 new**) | Problem-grouped | Cards | **小规模：**同轨迹数的普通重采样对照 |
| D | Hint augmentation: 10 problems / 20 total traces (**10 new**), **stagnation/regression points** | Problem-grouped / Random | Cards / Plain Skill | **小规模：**对比 B、C；复用这批数据做分组和格式消融 |
| E | Hint augmentation: 10 problems / 20 total traces (**10 new**), **random points** | Problem-grouped | Cards | **小规模：**对比 D，验证定向选点的价值 |
| F | Obfs augmentation: 10 problems / 20 total traces (**10 new**) | Problem-grouped | Cards | **小规模：**对比 B、C、D，评估 obfs 路线 |
| G | Unguided resampling: 40 problems / 80 total traces (**40 new**) | Problem-grouped | Cards | **有信号后：**40 题规模的同轨迹数对照 |
| H | Hint augmentation: 40 problems / 80 total traces (**40 new**), **stagnation/regression points** | Problem-grouped | Cards | **有信号后：**对比 A、G，检验较多训练题下的增强收益 |
| I | Obfs augmentation: 40 problems / 80 total traces (**40 new**) | Problem-grouped | Cards | **有信号后：**对比 A、G、H，检验较多训练题下的 obfs 收益 |
| J | Selected augmentation method: 40 problems / 160 total traces (**120 new**) | Problem-grouped | Cards | **可选、后置：**只对已有收益的方法检查增加每题轨迹数是否仍有价值 |

## Execution Order and Reuse

1. A 先跑三个条件：`Positive–Negative + Plain Skill`、`Random + Plain Skill`、`Random + Cards`，分别隔离分组与格式作用，不展开完整组合。
2. 在同一 10 题子集上做 B–F。D 先跑 `Grouped + Cards`、`Random + Cards`、`Grouped + Plain Skill` 三个条件，全部复用 D 的同一批轨迹。
3. 如果 C–F 全部运行，需要新增 **40 条训练轨迹**。这不包含 teacher/obfs 生成、SkillOpt 提炼和 from-scratch 评测的调用开销；这些成本单独记录。
4. 有稳定收益后再做 G–I，并只扩展值得继续的路线。若生成协议和模型等设置保持不变，C、D、F 已有的 10 条新轨迹可分别复用，各路线只需补齐另外 30 题。
5. J 不属于首轮必跑项，不为每个分组/格式组合分别生成 160 条轨迹。它固定题目数、增加每题经历数；不替代 H/I 的题目覆盖扩展实验。

## Shared Evaluation Rules

- **所有最终评测均 from scratch**，使用相同评测题、模型和预算。
- 对比时选择格式、分组匹配的条件；同时控制分析调用数、提议数和最终 skill 预算。
- D 的分组/格式和 D–E 的选点消融先支持 10 题设置下的结论；A 的 Positive–Negative / Random 对照支持 40 题原始轨迹设置。更广泛结论需要后续相应复验。
- Obfs 必须与对照使用同一题目集合。若当前生成器覆盖不足，报告共同可处理子集，不将不同项目/题目构成直接比较。
- **同轨迹数比较学习收益；计算效率需要匹配并统计生成、提炼等完整成本。**
- Positive–Negative 与 Random “差异不大”需要预先定义容忍范围，不能仅凭结果不显著下结论。

本表是分阶段实验计划；没有因本次修订启动任何生成、提炼或评测运行。
