# Research Outline 中文版

## Executive Summary

Verusage traces 表明，最高价值路线不是再加一个 generic repair action。主要机会是 controller/data 改进：把现有成功和失败轨迹转成 compact proof-skeleton 与 loop-memory system。这应该能提高 hard project families 的能力，并减少 repeated full-context prompting 造成的 token 浪费。

## Codebase / Data Analysis

当前 workspace 是结果仓库，包含：

- 早期 `result-*` 目录：repair candidates、diffs、summaries、checkpoints 和部分 reasoning；
- 后期 `all_batch_results-*` 目录：per-call prompts/outputs、reasoning、repair logs 和 per-model batch summaries；
- `claude_sonnet_gpt5/`：跨模型 project results 和 script outputs。

没有修改原始数据。新 artifacts 只在这个 analysis 文件夹中。

## KPIs

- 20 分钟 cap 下的 verified rate。
- Total tokens 和 non-verified average tokens。
- Repeated same-action loops 数量。
- Skeleton retrieval hit rate。
- Repetition gate 的 false-stop rate。

## 五个可执行方向

1. **Trace skeleton cache**  
   从成功 traces 蒸馏 reusable proof plans。

2. **Repetition gate**  
   停止 repeated action/error loops，并强制换路线。

3. **Project-family context profiles**  
   为 `AC`、`NR`、`OS` 等分别压缩 prompt。

4. **Final-verification-aware local reward**  
   惩罚会制造 persistent downstream assertion failures 的 local fixes。

5. **Action router from trace features**  
   在 skeleton/error signatures 稳定后学习或手写 priors。

## 推荐下一步实验

在改 live repair agent 前，先实现一个 offline replay analysis：

1. 将所有 `verus-repair.log` 解析成 attempt records。
2. Normalize error signatures。
3. 模拟 thresholds 2、3、4 下的 repetition gates。
4. 从 verified traces 和 `fix-v*-success-*` 文件中提取 skeletons。
5. 在 heldout high-token failures 上评估 retrieval hit rate。

如果 offline replay 结果好，再在 high-token `AC/NR/OS` failures 上跑小规模 online smoke。

