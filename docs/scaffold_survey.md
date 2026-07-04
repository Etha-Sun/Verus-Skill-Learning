# Self-Evolving Scaffold Survey

This note records the design patterns used to shape this repository.

## Common Patterns

| Family | Representative Work | Evolves | Feedback | Reusable State | Takeaway for Verus |
|---|---|---|---|---|---|
| verbal memory | Reflexion | reflection text | task feedback | episodic memory | Verus reflections must cite verifier deltas, not just natural language |
| skill library | Voyager | executable skills | environment success/error | skill library | verified proof traces can become proof skills |
| prompt evolution | Promptbreeder | task prompts and mutation prompts | validation fitness | prompt population | evolve rule prompts, not only repair prompts |
| scaffold self-improvement | STOP | improver/scaffold code | downstream utility | scaffold versions | too broad for first pass; keep repair controller bounded |
| graph/workflow search | GPTSwarm, AFlow | agent graph/workflow code | benchmark execution | candidate graph archive | useful if the graph is Verus error/action routed |
| agent/code archive | ADAS | whole agent code | validation performance | agent archive | strong but too unconstrained for our resource budget |
| evolutionary program search | AlphaEvolve | code/program candidates | automatic evaluator | scored program database | Verus is naturally machine-gradeable; use evaluator as rule filter |
| compression/rule mining | TACO | context compression rules | task success and token cost | structured rules | closest fit for Verus-specific token reduction |
| formal workflow | Lean4Agent | workflow/trajectory formal artifacts | formal checks and benchmark score | verified workflow updates | tells us generic workflow formalization is occupied |
| runtime enforcement | AgentSpec | trigger/predicate/enforcement rules | safety/reliability checks | rule DSL | adapt DSL shape to verifier-grounded repair decision rules |

## Design Choice

The scaffold does not let an LLM freely rewrite the entire harness. It first
mines bounded artifacts:

- proof skills,
- successful skeletons,
- structured repair-decision rules,
- context/reroute policies.

Each artifact must survive offline replay before entering a live repair loop.

## Sources

- Reflexion: https://arxiv.org/abs/2303.11366
- Voyager: https://arxiv.org/abs/2305.16291
- Promptbreeder: https://arxiv.org/abs/2309.16797
- STOP: https://arxiv.org/abs/2310.02304
- GPTSwarm: https://arxiv.org/abs/2402.16823
- ADAS: https://arxiv.org/abs/2408.08435
- AFlow: https://arxiv.org/abs/2410.10762
- AlphaEvolve white paper: https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf
- TACO: https://arxiv.org/abs/2604.19572
- Lean4Agent: https://arxiv.org/abs/2606.06523
- AgentSpec: https://arxiv.org/abs/2503.18666

