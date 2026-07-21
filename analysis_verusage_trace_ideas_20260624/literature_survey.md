# Compact Related-Work Grounding

This is a targeted search pass for an optimization brief, not a full paper survey.

## Reused/Local Coverage

The local traces already define the relevant system: Verus-based repair agents with verifier feedback and specialized action routing.

## Newly Checked External Work

1. Lattuada et al. 2023, "Verus: Verifying Rust Programs using Linear Ghost Types." arXiv:2303.05491. https://arxiv.org/abs/2303.05491
   - Establishes Verus as an SMT-based Rust verification system. Relevant because Verusage tasks are Verus proof/program repair tasks, not Lean-style tactic scripts.

2. Shinn et al. 2023, "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366. https://arxiv.org/abs/2303.11366
   - Supports the general idea of using verbal feedback memory for language agents. Verusage needs a more structured version: verifier/error/action memory rather than free-form reflection.

3. Xin et al. 2024, "DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search." arXiv:2408.08152. https://arxiv.org/abs/2408.08152
   - Shows proof-assistant feedback and search can improve theorem proving. Verusage differs because repair actions are code-level Verus edits, and token cost is dominated by repeated full-context repair prompts.

4. Ji et al. 2025, "Leanabell-Prover-V2: Verifier-integrated Reasoning for Formal Theorem Proving via Reinforcement Learning." arXiv:2507.08649. https://arxiv.org/abs/2507.08649
   - Relevant for verifier-integrated multi-turn reasoning. The transferable idea is optimizing over verifier interactions; the Verusage-specific gap is action-loop detection and proof-skeleton reuse from repair traces.

5. Tan 2026, "Automating Formal Verification with Reinforcement Learning and Recursive Inference." arXiv:2605.30914. https://arxiv.org/abs/2605.30914
   - Nearby because it discusses verifier-guided inference scaffolds for verified programs/proofs. The local trace evidence here points to a concrete scaffold improvement: project-specific proof-plan caches and repetition gates.

## Closest-Prior-Work Comparison

| prior mechanism | overlap | remaining Verusage gap |
|---|---|---|
| Reflexion-style memory | uses past feedback to guide future agent decisions | local traces need typed verifier signatures, not only text reflections |
| Proof-assistant feedback RL/MCTS | optimizes proof attempts with verifier signals | Verusage repair has action-specific loops and high input-token replay that need cost-aware routing |
| Verifier-guided recursive inference | decomposes and repairs proofs using verifier feedback | current Verusage data exposes exact project-family proof skeletons and negative loops that can be mined offline |

## Novelty / Value Boundary

The selected direction should not be claimed as broadly novel. Its value is **transfer-to-new-setting and infrastructure/platform value**:

- Verus/Rust repair tasks differ from Lean mathematical theorem proving.
- The local dataset has repeated project families (`AC`, `NR`, `OS`, etc.) with reusable lemma/action motifs.
- The traces contain both positive proof skeletons and negative loop signatures.
- The immediate win is measurable token reduction and success lift on heldout Verusage tasks.

## Unresolved Gaps

- I did not find a direct Verusage-specific paper in this targeted pass.
- A paper-ready claim would need a fuller search over Verus repair, LLM program repair with compiler feedback, and formal-verification benchmarks.

