# Trace2Skill Evaluation Handoff

This contract lets Trace2Skill and other skill-learning systems use the fixed
test-20 evaluator without moving their training or construction code into this
repository.

## Accepted artifact

Provide either:

1. one UTF-8 Markdown skill file; or
2. one skill bundle directory whose entrypoint is `SKILL.md`.

A bundle may contain files such as `references/` and `agents/`. Every entry must
be a regular file. Symlinks are rejected so the recorded tree hash and the files
visible to the actor cannot resolve to different content.

Executable bits are recorded and preserved for bundle scripts; write bits are
removed in each task workspace. Final scoring also requires every supplied
skill file and executable bit to remain unchanged after the actor exits.

The bundle hash uses the same `hash_skill_tree()` contract as Trace2Skill
candidate snapshots. The evaluator records the tree hash, entrypoint hash, file
inventory, total bytes, split hash, prompt hash, provider configuration, and
tool identities before execution.

## One-command evaluation

From the repository root:

```bash
skillopt-verusage/scripts/run_s2_fixed_test20.sh \
  {gpt|deepseek|glm|qwen} trace2skill /absolute/path/to/verus-proof-repair
```

For a single file, pass that file instead of the directory. To use a more
specific result label without changing the artifact:

```bash
SKILLOPT_EXTERNAL_SKILL_LABEL=trace2skill-semantic-v4 \
  skillopt-verusage/scripts/run_s2_fixed_test20.sh \
  glm trace2skill /absolute/path/to/verus-proof-repair
```

Run the normal model-free preflight first:

```bash
SKILLOPT_CHECK_ONLY=1 \
  skillopt-verusage/scripts/run_s2_fixed_test20.sh \
  glm trace2skill /absolute/path/to/verus-proof-repair
```

The existing `.env`, Verus release, split, provider, actor profile, timeout, and
output-root requirements remain authoritative. The handoff changes only the
skill artifact supplied to the evaluator.

## What the producer must deliver

- the final skill file or bundle directory;
- a stable human-readable label;
- the producer's own construction/provenance manifest when the result will be
  described as held-out or test-disjoint; otherwise it remains optional.

The producer does not need to adopt SkillOpt classes, the local candidate
controller, or this repository's training layout. Evaluation outputs retain the
exact artifact inventory and hash, so results can be joined back to an external
Trace2Skill provenance manifest by hash.

The tracked test-20 is a recurring fixed benchmark, not a sealed test. Without
producer evidence that construction excluded these tasks and without actor
filesystem isolation, report the run as diagnostic rather than leakage-safe or
held-out.

If a producer wants held-out promotion for every intermediate candidate, add a
separate controller adapter that calls the same evaluator. Do not put training
or materialization logic inside the evaluator.
