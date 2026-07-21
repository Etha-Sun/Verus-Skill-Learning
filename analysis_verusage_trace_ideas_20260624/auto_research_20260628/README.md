# Verusage 自动化科研小结（2026-06-28）

本目录是独立工作区，只包含这次基于 meeting 和本地 trace 的派生产物；原始数据没有被修改。

## 结论先行

这次 meeting 的核心约束是：不要把项目做成泛泛的 “formal verification for agent/harness”。真正可发表、可快速推进的路线应该把 fitness 明确落在 Verusage/Verus/Rust formal verification 任务上，即：

1. agent/harness 变化必须提升 Verusage 成功率、降低 token、降低无效迭代，或者提升 proof 迁移能力。
2. verification/specification 只能作为约束搜索空间、减少坏演化、解释 agent 行为的工具；不能先验作为主贡献。
3. 第一阶段要能出表格，不依赖昂贵 API：用已有 traces 做 offline replay、retrieval upper bound、prompt/token audit。

本地实验支持一个更具体的方向：

> **Verusage-specific trace-distilled proof skeleton memory + repetition gate + project-aware context compaction**

它不是泛化 harness 论文，而是从 Verusage trace 中挖出三类 dataset-specific 结构：

- 重复错误-动作循环：同一 `(Verus error, primary_action)` 在失败 trace 中高度重复，可作为低风险 early-stop / reroute 信号。
- 跨模型成功 skeleton：同一 task 上，一个模型失败而另一个模型成功的情况很多，说明成功轨迹可以作为 exact-task skeleton cache 的强上界。
- 项目族 prompt 膨胀：AC/NR/OS 是明显 token sink，适合做项目级 context compaction 和 lemma retrieval。

## 新文件

- `meeting_deep_read.md`：meeting 逐字稿的细读，按研究约束、否定方向、正向路线整理。
- `literature_scout.md`：和 meeting 相关的一手文献定位，以及为什么它们不能直接替代本项目。
- `experiment_report.md`：本地离线实验设计、结果和解释。
- `next_steps.md`：接下来可自动化推进的科研路线。
- `verus_tla_opportunity.md`：修正 Lean4Agent/AgentSpec 后，对 verus-tla 连接机会的专门判断。
- `self_evolving_and_verus_specificity.md`：self-evolving 代表工作方法表，以及当前架构缺少哪些深层 Verus-specific 决策信号。
- `scripts/local_experiments.py`：可复现实验脚本，只读原始 traces/results。
- `outputs/`：CSV/JSON 实验结果。
  - `skeleton_cache.jsonl`：1,691 条 verified trace 的 skeleton 雏形。
  - `reroute_prior_threshold8.csv`：threshold=8 触发时的跨模型成功轨迹 reroute prior。

## 复现实验

在仓库根目录运行：

```bash
PYTHONPATH=src python3 analysis_verusage_trace_ideas_20260624/auto_research_20260628/scripts/local_experiments.py \
  --root "${VERUS_SKILL_DATA_ROOT}" \
  --out-dir "${VERUS_SKILL_RUN_ROOT}/auto-research-20260628"
```

主数据口径：只使用 `all_batch_results-cyy-*/results-batch_*/`，不混入 sampled-unverified 额外批次。
