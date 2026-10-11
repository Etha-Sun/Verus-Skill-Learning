# Literature And Autoresearch Tool Audit

Date: 2026-10-10 Pacific. Primary sources only for technical conclusions. Search scope: autoresearch system evaluations, long-context analysis, trajectory-to-skill learning, failure attribution, and verifier-grounded learning. No paper claim below has been reproduced locally.

## Tool evaluation evidence

ResearchClawBench evaluates 40 research tasks across 10 domains. Its paper's Table 5 reports Codex CLI/GPT-5.4 18.4, EvoScientist/GPT-5.4 15.5, and ARIS Codex/GPT-5.4 13.6 overall. This is a version-specific report, not an October ranking or a controlled Verus comparison. Its final-report rubric is not our verifier endpoint. The public project describes a dashboard using best scores per task/agent, so single-run, best-of-run and repeated-run numbers must not be mixed.
Source: https://arxiv.org/html/2606.07591v1 ; https://github.com/InternScience/ResearchClawBench

ARIS's technical report explicitly says its overnight four-round review/20-plus-experiment case is observational, not causal evidence for cross-family review. It also acknowledges missing controlled evaluation and potential reviewer-bias amplification. Reviewer scores should never select our research method without downstream verification.
Source: https://arxiv.org/html/2605.03042v1

Decision: select ARIS research-refine as a workflow tool because it fits the current methodological bottleneck and is locally available. Do not advertise it as the empirically strongest research agent. Retain existing SkillOpt and VeruSAGE execution/evaluation components. Karpathy's training loop is a useful pattern but not a method-discovery advantage demonstrated for this setting; moving to EvoScientist would add integration work without solving the evidential question.

## Callability audit

- No registered autoresearch / DeepScientist / Claude-review MCP tool exists in the current tool catalog. Skill names are instructions, not magically exposed remote services.
- A local external ARIS source directory exists. Its .git directory is unavailable in this view, so an upstream revision cannot be certified.
- Claude Code CLI 2.1.74 is installed; auth status reported loggedIn=true, oauth_token, firstParty. No credentials or identity were copied.
- Codex CLI 0.162.1 is installed; version inspection alone does not certify a second usable reviewer backend.
- The ARIS official Claude-review bridge command builder is importable. One tools-disabled, strict-empty-MCP, nonpersistent reviewer call was attempted with a USD1 ceiling and 180-second process timeout; completion is recorded separately in REVIEW_SUMMARY.md.
- Local optional .agents/skills links and .agent-context.local.md are absent. No installer or symlinked skill was modified.
- VERUS_SKILL_RUN_ROOT and VERUS_SKILL_DATA_ROOT are absent from this shell environment. Resolve them from approved machine-local configuration before launching any experiment; do not guess a writable legacy-run directory.

## Related-work map

| Reference | Mechanism actually described | Implication |
|---|---|---|
| Liu et al., Lost in the Middle, 2023 [1] | Position and length sensitivity in document QA/key-value retrieval | Motivation for a hypothesis, not proof about DeepSeek V4 Pro trace distillation. |
| Zhao et al., ExpeL, 2023/2024 [2] | Extract and recall natural-language experience without weight updates | Experience abstraction predates this proposal. |
| Ni et al., Trace2Skill, 2026 [3] | Parallel success/error analysts and hierarchical patch consolidation; agentic versus single-call analysis | Strong direct counterexample to the claim that existing systems only concatenate traces. |
| Ma et al., SkillOpt, 2026 [4] | Minibatch reflection, bounded text updates, validation gating | Existing local baseline; do not mislabel its staged optimization as a one-shot strawman. |
| Yang et al., PlugMem, 2026 [5] | Convert interactions into structured reusable knowledge and retrieve it | Knowledge-centric memory is prior work, not the novelty of structured cards. |
| SKILL-KD, 2026 [6] | Teacher/student contrasts, adaptive student reruns, trace-linked consolidation | Contrast plus rerun validation is already directly addressed. |
| DeFA, October 2026 [7] | Segment traces, recover dependency relations, identify decisive errors; connect diagnostics to skill evolution | Closest current competitor to graph/segment-based trace analysis. |
| Trace2Skill for EDA, 2026 [8] | Dense verifier feedback and skill evolution | Verifier-guided skill evolution also exists; independent paper sharing the Trace2Skill name. |

The remaining defensible question is narrower: does analysis anchored to actual Verus code/verifier transitions improve transferable applicability of rules, beyond ordinary hierarchical analysis and native SkillOpt, under matched extraction/deployment budgets? Treat this as an incremental testable route until closer intervention/replay systems are mapped and controlled evidence exists.

## References

[1] https://arxiv.org/abs/2307.03172
[2] https://arxiv.org/abs/2308.10144
[3] https://arxiv.org/html/2603.25158v1
[4] https://arxiv.org/html/2605.23904v2
[5] https://arxiv.org/abs/2603.03296
[6] https://arxiv.org/html/2607.28048v1
[7] https://arxiv.org/html/2610.01256v1
[8] https://arxiv.org/html/2605.21810v1

Outside-family watchlist: AgenTracer, FAMAS, REFLECT, and CausalFlow are referenced by DeFA as replay/intervention-based attribution methods. They have not been fully read in this bounded pass; consequently replay is not claimed novel and publication novelty is unresolved. Code-generation follow-up candidate: EvalPlus, https://github.com/evalplus/evalplus . Its release/contamination/task-split and actor-access conditions must be fixed before any code-generation experiment.
