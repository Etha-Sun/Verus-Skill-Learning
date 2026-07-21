# Selected Idea: Verusage Trace-Distilled Skeleton Cache With Repetition Gate

## Idea ID

`verusage_trace_skeleton_gate_20260624`

## Selected Route

Build a Verusage-specific repair controller layer that:

1. distills successful local traces into compact proof skeletons;
2. retrieves skeletons by normalized verifier state and project-family features;
3. blocks repeated same-action loops when local evidence says the loop is low value;
4. routes the next prompt to either skeleton-guided code generation, diagnosis-only planning, or early stop.

## Why Now

The current workspace contains enough trace data to mine both positive and negative patterns: 2,996 repair logs, 65k reasoning files, 104k prompt files, and cross-model runs over the same 849-task benchmark.

## Core Hypothesis

On Verusage, high-cost failures are often caused by missing compact transfer of proof structure and repeated low-value actions, not by absence of any successful proof route. A trace-distilled skeleton cache plus repetition gate should reduce token use on failed tasks and improve success on project families such as `AC`, `NR`, and `OS`.

## Mechanism Sketch

### Skeleton Record

Each successful or locally useful trace is compressed into:

- project family: `AC`, `NR`, `OS`, etc.
- target name and normalized file/function family;
- verifier error sequence;
- action sequence;
- accepted/rejected local outcomes;
- helper lemmas/functions actually used;
- proof-shape tags such as `exists-witness`, `leads_to_trans`, `seqsetmap`, `bitvector-bound`, `postcondition-split`;
- compact final patch diff summary;
- anti-patterns observed before success.

### Retrieval Key

Use a structured key rather than raw token similarity:

`project + normalized target name + error type + nearby lemma names + spec-shape + prior failed actions`.

### Repetition Gate

Normalize the current error signature and track:

- same target error after same action;
- candidate rejected for same reason;
- accepted local repair followed by persistent `AssertFail`;
- repeated action count per state.

After a threshold, the controller stops the repeated action and forces one of:

- retrieve skeleton and ask for code using named lemmas/witnesses;
- ask for diagnosis-only proof plan;
- switch action family;
- terminate if expected value is low.

## Code-Level Landing Surface

Likely components in the repair system:

- trace parser over `verus-repair.log`, `reasoning/*.txt`, `fix-v*-success-*`, and result CSVs;
- skeleton index builder;
- controller hook before action selection;
- prompt template that accepts a compact skeleton and forbids repeating rejected attempts;
- offline replay evaluator.

## Minimal Validation

### Offline First

1. Build skeletons from successful traces.
2. Simulate repetition gates over existing logs.
3. Report:
   - token calls saved by thresholds 2/3/4;
   - successful runs that would be falsely stopped;
   - top-k skeleton retrieval hit rate for heldout traces;
   - overlap between retrieved skeleton actions and actual successful actions.

### Small Online Smoke

Run 20-50 heldout high-token tasks from `AC`, `NR`, and `OS`.

Compare:

- verified rate;
- total tokens;
- average non-verified tokens;
- attempts to first accepted globally useful patch;
- number of repeated-action loops.

## Success Criteria

Minimum useful result:

- reduce non-verified average tokens by at least 30% without lowering verified rate.

Strong result:

- reduce non-verified average tokens by at least 50% and recover additional verified tasks in `AC/NR/OS`.

## Abandonment Condition

Abandon or downgrade if:

- offline replay shows many successful runs require repeated same-action attempts beyond the proposed gate;
- skeleton top-k retrieval rarely matches useful successful actions;
- online smoke reduces tokens only by early-stopping tasks that could otherwise verify;
- benefits appear only from exact-task patch memorization under a leakage-free split.

## Anti-Win Condition

The route is not a win if it only reduces token usage by giving up earlier while verified rate falls, or if it relies on retrieving exact final patches for evaluation tasks.

## Strongest Alternative Hypothesis

The real bottleneck may be prompt slicing rather than proof-plan memory. If smaller project-family contexts alone solve the problem, skeleton indexing may be unnecessary complexity.

## References

1. Andrea Lattuada et al. "Verus: Verifying Rust Programs using Linear Ghost Types." arXiv:2303.05491. https://arxiv.org/abs/2303.05491
2. Noah Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366. https://arxiv.org/abs/2303.11366
3. Huajian Xin et al. "DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search." arXiv:2408.08152. https://arxiv.org/abs/2408.08152
4. Xingguang Ji et al. "Leanabell-Prover-V2: Verifier-integrated Reasoning for Formal Theorem Proving via Reinforcement Learning." arXiv:2507.08649. https://arxiv.org/abs/2507.08649
5. Max Tan. "Automating Formal Verification with Reinforcement Learning and Recursive Inference." arXiv:2605.30914. https://arxiv.org/abs/2605.30914

