# Autoresearch Tool Practical Shortlist

Survey date: 2026-10-10 (Pacific). Status: documentation-based shortlist; no installation, execution benchmark, paid call, or new subproject creation.

## Scope and evidence limits

User wants current, popular, practical autoresearch tools before starting a subproject. Interpret autoresearch as autonomous hypothesis/code/experiment/evaluation iteration; separate this from web-report generation. Domain and budget are not selected. Verus-specific recommendations below are conditional, not a decision to reuse the existing project.

Primary GitHub pages were opened during the survey. Approximate displayed stars are popularity signals, not growth rates, quality scores, or independently reproduced capabilities. Search/commit pages may be cached; avoid treating the newest visible commit as a verified live head. No comparative performance or dollar-cost claim is established.

## Shortlist

| Tool | Approximate displayed stars | Documented purpose | Practical assessment |
|---|---:|---|---|
| Karpathy autoresearch | 97.6k | Single-GPU nanochat training; modify code, train for five minutes, evaluate, keep/discard | Strong minimal reference loop. Original needs NVIDIA GPU and has been tested on H100. Generic Verus usage requires replacing its training/evaluation contract. |
| ARIS | 17.2k | Markdown skills covering ideas, experiments, cross-model review, writing, and persistent research knowledge | First integration candidate for an existing research repository. README records a 2026-10-07 Lean formalization addition; Lean support is not Verus support. |
| uditgoenka/autoresearch | 6.5k | General measurable-goal iteration with verify/guard, bounded iterations, evaluation and regression helpers | Good small pilot candidate when a stable evaluator exists. Core supports Claude Code/OpenCode/Codex; hook guardrails are documented as Claude-only. |
| ShinkaEvolve | 1.4k | Program evolution, candidate archive, parallel local/Slurm evaluation, custom evaluators | Especially relevant when code has an executable verifier. Requires task-specific correctness checks and score design. |
| EvoScientist | 5.0k | Research agent with planning/coding/analysis/writing, persistent memory, skills, scheduling, WebUI | Strong candidate for a separate general research assistant. README records v0.3.6 on 2026-10-09. Memory/skill distillation resembles the existing research theme, but no Verus efficacy is established. |
| AutoResearchClaw | 14.6k | 23-stage idea-to-paper pipeline with experiment execution and human intervention modes | Useful to inspect end-to-end research orchestration; broader integration surface than a minimal experiment loop. |
| Microsoft RD-Agent | 14.9k | Data-driven model/feature R&D, including data-science competition workflows | More relevant for ML/data-science work than formal verification. README requires Linux and Docker for most scenarios. |

## Primary sources

- https://github.com/karpathy/autoresearch
- https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep
- https://github.com/uditgoenka/autoresearch
- https://github.com/SakanaAI/ShinkaEvolve
- https://github.com/EvoScientist/EvoScientist
- https://github.com/aiming-lab/AutoResearchClaw
- https://github.com/microsoft/RD-Agent

AI-Scientist-v2 was also inspected as an established tree-search scientific-discovery reference: https://github.com/SakanaAI/AI-Scientist-v2 (approximately 7.3k displayed stars). It is not the first integration recommendation for a small existing-repository pilot.

## Next anchor

Choose intended domain before attaching/importing a tool. For continuing Verus, inspect ARIS as the workflow layer and compare a lightweight metric loop against ShinkaEvolve for verifier-backed search. For a new broad research-assistant project, inspect EvoScientist first and compare ARIS. This is a shortlist, not an installation or research-performance decision.

For a Verus pilot, keep the external evaluator and task/specification contracts fixed; report budgeted dual-pass solved rate first, then tokens/time/cost and timeout rates. Search only development tasks; reserve unseen evaluation for final comparison. Existing repository instructions mention optional ARIS links, but .agents/skills is absent in this checkout, so an actual installation was not verified. Dedicated scout artifact/memory/bash_exec tools are unavailable; native shell was used for local context and repository-required closeout.

Raw-data safety: only compact memory files and the generated memory index/registry were written. Raw/sealed datasets, historical runs, existing implementation and experiment inputs were unchanged. Pre-existing working-tree edits were preserved.
