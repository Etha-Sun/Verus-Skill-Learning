# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | 解析 hands-on verified trace schema | parser only | smoke | parse rate, prefix count | MUST | DONE | 3 traces, 7 prefixes; `verus-self-evolve-scaffold/runs/ig_probe_sanity_20260704` |
| R002 | M1 | 提取 primary action target | target builder | smoke | action coverage | MUST | DONE | primary action coverage 1.000 |
| R003 | M1 | 提取 full-proof target | target builder | smoke | proof target length | MUST | DONE | full proof coverage 1.000; mean 83,546 chars |
| R004 | M1 | 提取 patch-span target | deterministic diff filter | smoke | non-empty patch rate, fallback rate | MUST | DONE | patch span non-empty 1.000; fallback 0.000 |
| R005 | M2 | QwQ-32B scorer feasibility | local scorer | smoke | token logprob availability | MUST | DONE | vLLM backend passed 1 action_primary case; `runs/ig_probe_sanity_20260704/qwq_vllm_smoke_action_reuse` |
| R006 | M3 | Action IG sanity | no/generic/trace/irrelevant artifacts | 3 traces | IG_sum, IG_avg, rank | MUST | DONE | raw prompt all negative; explicit action prompt gives positive mean IG but weak separation from irrelevant control |
| R007 | M3 | Full-proof IG sanity | same artifacts | 3-5 traces | IG_sum, IG_avg, chunk stats | MUST | TODO | 注意 length bias |
| R008 | M3 | Patch-span IG sanity | same artifacts | 3-5 traces | hunk IG, fallback rate | MUST | TODO | reviewer-auditable extraction |
| R009 | M4 | Action IG probe | same artifacts | 20-50 traces | positive IG rate, rank | MUST | TODO | peer-success target 作为后续 |
| R010 | M4 | Full-proof IG probe | same artifacts | 20-50 traces | normalized/chunked IG | MUST | TODO | 并列但风险更高 |
| R011 | M4 | Patch-span IG probe | same artifacts | 20-50 traces | hunk-level IG | MUST | TODO | 与 full proof 对照 |
| R012 | M5 | Peer-success action target | train-split action prior | dev prefixes | agreement, IG | NICE | TODO | 避免 eval leakage |
| R013 | M5 | Cloud scorer sensitivity | DeepSeek/OpenAI/Gemini if available | small subset | scorer agreement | NICE | TODO | 仅当 teacher forcing 可行 |
| R014 | M5 | Motif/TLA artifact pilot | motif skill | small subset | IG by motif | NICE | TODO | 第一版 deferred |
