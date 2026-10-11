# Expanded Autoresearch Tool And Blog Review Including DeepScientist

Date: 2026-10-10. Status: bounded literature and availability audit complete; no performance reproduction or new experimental launch.

## Correction And Decision

The prior seven-agent ResearchClawBench list was not a census of autoresearch tools. Selecting ARIS as uniquely most useful was stronger than the evidence warrants. Retain it as an optional planning-checklist source. Expand the practical shortlist to DeepScientist (persistent research workflow), EvoScientist (research agent and memory), and ShinkaEvolve (measurable program search), with task-fit judgments provisional until a matched local smoke test. This changes the tool recommendation, not the user's frozen research objective or experimental approval state.

## Additional Official Repositories

Stars are rounded GitHub page snapshots, not API-precise or efficacy measures.

| Project | Stars | Documented focus / fit judgment | Official source |
|---|---:|---|---|
| DeepScientist | 3.4k | Persistent research state, findings memory, baseline/experiment/analysis workflow; investigate first for long-lived project organization | https://github.com/ResearAI/DeepScientist |
| Karpathy autoresearch | 97.6k | Fixed-budget single-GPU training experiment loop; useful pattern, needs a different evaluator for Verus | https://github.com/karpathy/autoresearch |
| Microsoft RD-Agent | 14.9k | Automated data/model R&D; adaptation to Verus not established | https://github.com/microsoft/RD-Agent |
| AutoResearchClaw | 14.6k | End-to-end research/paper pipeline; distinct from ymx10086/ResearchClaw | https://github.com/aiming-lab/AutoResearchClaw |
| Sakana AI Scientist | 14.7k | Computational research and paper pipeline; not direct evidence for trace distillation | https://github.com/SakanaAI/AI-Scientist |
| Sakana AI Scientist v2 | 7.3k | Agentic tree search for computational experiments and papers | https://github.com/SakanaAI/AI-Scientist-v2 |
| HKUDS AI-Researcher | 5.8k | Autonomous scientific innovation pipeline | https://github.com/HKUDS/AI-Researcher |
| ShinkaEvolve | 1.4k | Population-based program evolution with executable evaluation; useful if optimizing an extraction program | https://github.com/SakanaAI/ShinkaEvolve |

Official repository descriptions establish capabilities claimed by maintainers, not independent efficacy. The current DeepScientist README's comparison matrix is also vendor-authored, not an independent leaderboard.

## DeepScientist Evidence And Local Availability

Read the original arXiv v1: https://arxiv.org/html/2509.26603v1 . It reports a month-scale campaign using16 H800 GPUs, over20,000 GPU-hours, about5,000 ideas, about1,100 experimentally validated candidates, and21 innovations across three tasks. Human experts supervised outputs. These author-reported results do not establish cost-effectiveness or superiority for a small Verus pilot, and the old campaign is not equivalent to the current local v1.6.0 product.

Direct research relevance: the agent-failure-attribution experiment starts from All-at-Once on Who&When and proposes A2P (Abduction-Action-Prediction). Algorithm-generated attribution accuracy is reported16.67% to47.46%. This addresses locating failures, not proof that extracted experience improves held-out solving. Its proposed causal reasoning relies on hypothetical predictions; actual controlled replay must be distinguished from imagined fixes. It belongs on the methodological reading list before claiming attribution novelty.

The newer OpenReview paper exists but its forum/PDF requests encountered browser verification in this audit. Do not claim to have read the current accepted manuscript or its Micronano evaluation from search snippets alone.

Local read-only inspection resolved the installed ds executable to npm package @researai/deepscientist version1.6.0. The supplied skill catalog includes scout, baseline, idea, experiment, analysis-campaign, review and others. No DeepScientist/artifact/memory API is exposed in the current callable tool catalog. Thus CLI/package/skills availability is verified, while a healthy studio/daemon/model/evaluator integration is not. No daemon was started, no package installed/updated, and no model experiment launched.

## Blog Comparisons And Their Evidence Level

1. Ry Walker, Autoresearch Tools Compared: https://rywalker.com/research/autoresearch-tools . Updated September16,2026;19 tools spanning optimization, information research and science. Explicitly documentation/published-experience comparison, not hands-on testing of every tool or a common benchmark. Author discloses Tembo co-founder role. Useful taxonomy and operational questions, not a ranking. DeepScientist is not included by name in the accessible text.
2. Liqing/MindFlow, AutoResearch Project Landscape: https://liqing.io/mindflow/Topics/AutoResearch . June17,2026; eight projects with architecture/deployment discussion. Useful Chinese overview. Some unqualified descriptions (e.g. unique long-term evolution, preventing cheating) overstate what architecture alone proves. Do not treat it as controlled outcome evidence.
3. Evolutionary AI Survey, DeepScientist chapter: https://evo.si5.pl/chapters/deepscientist.html . Paper-derived critical analysis of memory, selection, resource cost and evaluation independence. It is not an independent reproduction; its statement about absent reproductions is dated April2026, not a verified October census. Its8.73/10 header is not a benchmark score. Its AutoResearchClaw chapter misdescribes Karpathy autoresearch as lacking execution, so the site requires source checking and should not be a factual authority.
4. AutoSci vs EvoScientist architecture comparison: https://zhichai.net/en/topic/177980718 . Implementation-oriented comparison of memory, runtime and deployment. No shared downstream experiment demonstrated in the accessible page; test-count and security descriptions were not independently reproduced.
5. Single-user AutoResearchClaw experience: https://medium.com/@LakshmiNarayana_U/one-prompt-one-agent-one-research-paper-on-hollywoods-ai-problem-da34a0f81a53 . March19,2026. Author describes trying the system through Bizclaw/Claude Code; only introductory content was accessible. Do not infer output quality, cost, or reproducibility from the preview.
6. SkillProof wrapper test: https://skillproof.dev/skills/researchclaw . Test dated July15, upstream recheck August10,2026. Reports a namespace collision in a third-party wrapper's pip command and config mismatch. It evaluates OthmanAdi/researchclaw-skill, not the entire AutoResearchClaw framework or ymx10086/ResearchClaw. Not locally reproduced; useful as a deployment-issue report only.

## More Substantive Empirical Comparisons / Firsthand Cases

AI CFD Scientist: https://arxiv.org/html/2605.06607v1 , Section5 and AppendicesD/I. Other authors compare their own CFD system against ARIS and DeepScientist on four tasks using GPT-5.5, with reported roughly matched LLM spending and artifact/manual assessment. Both general frameworks perform parts of execution but miss validation evidence. This is competitor-authored, domain-specific evidence, not a neutral general ranking or Verus result. The useful lesson is to retain domain validity gates and evaluator contracts.

Klarna Engineering: https://engineering.klarna.com/beyond-prompting-how-algorithmic-evolution-doubled-our-training-speed-8f874af3080d , March30,2026. Firsthand AlphaEvolve deployment with Google collaboration, almost6,000 candidates over three weeks. Reports49 to97 samples/s under deterministic constraints; an earlier143 samples/s path violated those constraints. Reports631 plateau evaluations. This is a concrete deployment case with lessons about constraints and stopping, not an independent comparison of all tools.

Emulated Autoresearch Bench: https://www.autoresearch-bench.com/ , September1,2026. Four-hour iterative optimization runs, public feedback and private scores on many tasks. Final scoring uses best private score reached; this is a lenient retrospective definition, not necessarily the deployed final artifact. It compares models/agents on optimization rather than DeepScientist versus ARIS end-to-end science. Keep distinct from ResearchClawBench and literature-search AutoResearchBench.

## Next Step And Safety

For this project, inspect DeepScientist's existing local workflow/evaluator compatibility before choosing a new platform; preserve frozen DeepSeek V4 Pro, splits, ledger and raw-data boundaries. Compare a small evidence packet and reproducible execution readiness rather than chasing reviewer scores or installing many systems. No tool is currently established as best for Verus trace analysis. Original plan remains a methodological proposal, not dispatch authorization.

All changes are compact research notes. Raw/sealed/legacy/frozen runs were not modified. No API credentials or personal absolute paths are copied here.
