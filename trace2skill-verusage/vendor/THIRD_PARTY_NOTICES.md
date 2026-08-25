# Third-party notices

## Trace2Skill

The runtime under `trace2skill_verus/` contains source derived from
[Qwen-Applications/Trace2Skill](https://github.com/Qwen-Applications/Trace2Skill)
at upstream commit `3d0b52a140f002a512930252b613c49048f7d5ac`. The
upstream project identifies this work as Apache-2.0. A copy of the Apache
License 2.0 is provided in `LICENSE`.

The integrated snapshot was migrated through
`Verus-Skill-Learning@92a1e8ab55d79b0831f251bbd9b9e61e1562bc9e` and
modified for the Verus Trace2Skill producer. Modifications include:

- adapting construction prompts from spreadsheet tasks to Verus proof repair;
- relocating the generation-only model clients into the vendored runtime;
- excluding the deprecated ReAct task harness, semantic reducer/router, and
  legacy evaluation bridges;
- selecting the native global MAP/REDUCE pipeline and the repository-local
  skill validator;
- preserving literal JSON examples while rendering named prompt placeholders;
- restricting LLM-authored file edits to `SKILL.md` and
  `references/*.md`, with resolved-path containment checks.

The following vendored Python files differ from the upstream commit and carry
a file-level modification notice:

- `trace2skill_verus/skill_evolver/__init__.py`
- `trace2skill_verus/skill_evolver/model_clients.py` (derived from
  upstream `src/react_agent/models.py`)
- `trace2skill_verus/skill_evolver/parallel_evolving_agent.py`
- `trace2skill_verus/skill_evolver/parallel_success_evolving_agent.py`
- `trace2skill_verus/skill_evolver/run_parallel_combined_skill_evolution.py`
- `trace2skill_verus/skill_evolver/run_parallel_skill_evolution.py`
- `trace2skill_verus/skill_evolver/skill_evolving_agent.py`

The following modified plain-text prompt files are listed here rather than
having notice text inserted into the model input, so the reviewed historical
prompt bytes remain unchanged:

- `trace2skill_verus/skill_evolver/prompts/parallel_evolving_agent/translation_system_prompt.txt`
- `trace2skill_verus/skill_evolver/prompts/parallel_evolving_agent/verification_system_prompt.txt`
- `trace2skill_verus/skill_evolver/prompts/skill_evolving_agent/system_prompt_base.txt`

This vendor-scoped notice and license apply to the Trace2Skill-derived material
only; they do not assert an Apache-2.0 license for the repository as a whole.
