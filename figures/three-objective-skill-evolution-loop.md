# Three-Objective Skill Evolution Loop

The diagram shows the proposed `n=4` pilot: one shared Codex H0 collection,
followed by three isolated objective-specific evolution workspaces. Each
meta-agent deliberately overfits one metric and sees only its own workspace.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#FFFFFF", "primaryTextColor": "#111827", "lineColor": "#374151", "fontFamily": "Arial, sans-serif"}}}%%
flowchart TB
    tasks["4个冻结任务<br/>3个已有对照题 + 1个待确认的Codex失败题"]
    h0["共享H0：Codex正常prompt<br/>每题1条高保真baseline，共4条trace"]
    tasks --> h0

    subgraph token_ws["Token-cost workspace"]
        direction TB
        token_copy["复制4条H0 traces"]
        token_meta["Token meta-agent<br/>1次Codex调用<br/>分析上一轮并提出3个skills"]
        token_skills["3个只优化token cost的skills"]
        token_runs["3 × 4 = 12条Codex agentic traces"]
        token_eval["记录完整usage、thinking、tool tokens、pass<br/>计算Expected Tokens to Success"]
        token_compare["比较平均最高/最低skill<br/>同时保留全部12条结果"]
        token_copy --> token_meta --> token_skills --> token_runs --> token_eval --> token_compare
        token_compare -. "下一轮反思与新skills" .-> token_meta
    end

    subgraph small_ws["Small-model-benefit workspace"]
        direction TB
        small_copy["复制4条H0 traces"]
        small_meta["Small-model meta-agent<br/>1次Codex调用<br/>分析上一轮并提出3个skills"]
        small_skills["3个只优化小模型表现的skills"]
        small_runs["3 × 4 = 12条小模型agentic trajectories<br/>API并行；若max_iters=10，则最多120次model turns"]
        small_eval["记录Verus/Lynette outcome、token和API turns"]
        small_compare["比较平均最好/最差skill<br/>同时保留全部12条结果"]
        small_copy --> small_meta --> small_skills --> small_runs --> small_eval --> small_compare
        small_compare -. "下一轮反思与新skills" .-> small_meta
    end

    subgraph ig_ws["Full-proof InfoGain workspace"]
        direction TB
        ig_copy["复制4条H0 traces"]
        ig_meta["InfoGain meta-agent<br/>1次Codex调用<br/>分析上一轮并提出3个skills"]
        ig_skills["3个只优化full-proof IG的skills"]
        ig_runs["3 × 4 = 12条Codex agentic traces<br/>先冻结pre summary，再探索，最后输出post summary"]
        ig_score["本地小模型exact teacher forcing<br/>首轮：4个cached H0 + 12 pre + 12 post = 28条评分序列<br/>后续轮：复用H0，只新增24条"]
        ig_compare["得到12组pre/post IG<br/>比较平均最好/最差并保留全部结果"]
        ig_copy --> ig_meta --> ig_skills --> ig_runs --> ig_score --> ig_compare
        ig_compare -. "下一轮反思与新skills" .-> ig_meta
    end

    h0 --> token_copy
    h0 --> small_copy
    h0 --> ig_copy

    token_compare --> totals
    small_compare --> totals
    ig_compare --> totals
    totals["调用账本<br/>首轮含H0：31条Codex traces + 12条小模型API trajectories + 28条本地评分序列<br/>稳态每轮：27条Codex traces + 12条小模型API trajectories + 24条本地评分序列<br/>最终额外3次Codex meta-agent调用用于冻结总结"]

    classDef input fill:#ECFDF5,stroke:#059669,stroke-width:2px,color:#111827;
    classDef token fill:#EFF6FF,stroke:#2563EB,stroke-width:2px,color:#111827;
    classDef small fill:#F5F3FF,stroke:#7C3AED,stroke-width:2px,color:#111827;
    classDef ig fill:#FFF7ED,stroke:#EA580C,stroke-width:2px,color:#111827;
    classDef output fill:#F9FAFB,stroke:#374151,stroke-width:2px,color:#111827;

    class tasks,h0 input;
    class token_copy,token_meta,token_skills,token_runs,token_eval,token_compare token;
    class small_copy,small_meta,small_skills,small_runs,small_eval,small_compare small;
    class ig_copy,ig_meta,ig_skills,ig_runs,ig_score,ig_compare ig;
    class totals output;
```
