# Research Contract: Verifier-Grounded Skill Information Gain

## Selected Idea

- **Description**: 从 VeruSAGE hands-on repair trajectory 的稳定状态中生成或检索 skill/rationale，并衡量它对下一步 action、proof patch 和完整 verified proof 的条件信息增益。用 verifier 结果做最终系统验证，用 information gain 做离线 skill promotion signal。
- **Source**: Kexin 2026-07-04 meeting、InfoGain-RAG、PlugMem，以及本地 VeruSAGE traces。
- **Selection rationale**: 不依赖 RL 或小模型训练，保留 LLM 自由探索；利用私有 trajectory 数据和 Verus verifier，同时显式优化 skill utility 与 token cost。

## Core Claims

1. 只看 trajectory prefix 生成的相关 artifact，应比长度和格式匹配的 shuffled/wrong controls 更稳定地提高 repair target likelihood。
2. artifact 的价值不仅是总 information gain，还包括每个注入 token 提供的 decision information density。
3. Action、patch 和 full-proof IG 是互补探索指标；最终价值必须由 held-out verifier solved rate 与 live token cost 验证。

## Method Summary

将 verified hands-on traces 切分在 verifier feedback 后、下一次 repair 前。每个 state 只能向 artifact generator 暴露当前代码、错误和历史，不能暴露未来 trajectory 或 final proof。对 baseline state 和 state+artifact 使用同一 scorer，计算 action、deterministic proof patch、完整 final proof 的 log-likelihood difference。

Action 使用 canonical candidate set 上的归一化分布，报告 correct-action PMI、entropy change 和排名。Patch/full proof 使用 teacher forcing；超长 proof 的 chunked/anchored score必须标为近似。所有结果保存 token-level evidence、artifact token cost、split 和 source path。

## Experiment Design

- **Datasets**: 第一阶段 3 条 verified hands-on traces / 7 states；通过 measurement gate 后扩大到 20-50 traces。按 normalized task id 分组，禁止跨模型同题泄漏。
- **Controls**: empty-container、generic skill、state-conditioned rationale、shuffled rationale、wrong-error rationale、length-matched neutral Verus text、weak irrelevant control。
- **Metrics**: action/patch/full-proof IG；action PMI bits；positive rate；paired win rate；entropy change；artifact information density；held-out solved rate、tokens、attempts、repetition。
- **Compute budget**: official Qwen3.6-27B dense，local 4 GPUs / vLLM TP=4。Action、patch、full-proof 三个 target 在六 states 上都必须运行；不再因 action gate 失败停止 proof targets。

## Baselines

| Method | Dataset | Metric | Score | Source |
|---|---|---|---|---|
| no artifact | 3-trace sanity | conditional target score | pending corrected run | local baseline |
| weak irrelevant text | 旧 3-trace sanity | action IG | 0.6295 nats, invalid/confounded | R006b |

## Current Results

| Method | Dataset | Metric | Score | Notes |
|---|---|---|---|---|
| old trace rationale | 3 traces / 7 states | mean action IG | 1.0817 nats | invalid for claims: token boundary and prompt confounds |

## Key Decisions

- 不把 successful trajectory 中 observed action 称为唯一 optimal action，使用 `demonstrator action`。
- 不复制 PlugMem 的 binary/F1-as-probability 实现；有 direct logprobs 时使用 normalized action scoring。
- Full-proof IG 使用整个 final verified `.rs`，带进度条、checkpoint 和 resume；不因成本或 action 结果提前删除。
- 三指标六-state pilot 全部完成后，matched-control separation 仍作为 20-50 trace 和 live self-evolving loop 的 gate。

## Status

- [x] Idea selected
- [x] Baseline pipeline feasibility established
- [ ] Corrected scorer implemented
- [ ] Corrected 3-trace results
- [ ] Representative dataset results
- [ ] Full dataset results
- [ ] Ablation studies
- [ ] Paper draft
