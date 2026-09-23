# SkillOpt fork-packet experiment

This branch adds the train-only evidence format for a three-task SkillOpt card
generation diagnostic. It does not contain raw trajectories or run outputs.

The matched no-hint arm completed on 2026-09-19. See
[NO_HINT_RESULTS_20260919.md](NO_HINT_RESULTS_20260919.md) for its reviewed
result and remaining trajectory-mount blocker.

## Conditions

Each selected checkpoint has four related observations:

1. the original trajectory prefix through the Verus event;
2. the original suffix from that event;
3. fresh v1 and v2 hint continuations;
4. a fresh matched no-hint continuation.

The fresh actors do not see the historical prefix. The exported manifest keeps
that boundary explicit. Teacher hint text is labeled as an intervention rather
than verifier evidence. All branches under one source problem have total task
weight one; checkpoint branches are correlated observations, not independent
training tasks.

The first optimizer view is hint-visible. Its goal is to generate candidate
cards with this required shape:

- observable trigger or proof stage;
- recommended action;
- verifier-grounded validation check;
- failure boundary or exclusion condition;
- supporting and contradicting branches.

It is a diagnostic. A downstream benefit claim requires the unchanged held-out
selection gate and a weighting-matched baseline.

## Fixed published-hint replay

When the reviewed compact publication is present but the historical v1/v2 raw
runs are unavailable, replay only the continuation actors. Do not regenerate
the interventions. Copy `published_hint_replay_config.example.json` to six
external configs (IR/AC/AL times v1/v2), fill the complete original run and
tool paths, and use distinct output roots and bridge ports. Point every config
at the same external budget state with a total approval limit of USD 5.

For each version root, first reconstruct and hash-check the selected original
checkpoints, then seed the exact reviewed repository hints, then make live
actor calls:

```bash
python3 skillopt-verusage/scripts/run_hint_augmentation.py \
  --config "$CONFIG" prepare
python3 skillopt-verusage/scripts/run_hint_augmentation.py \
  --config "$CONFIG" seed-published-hints --checkpoints 1
python3 skillopt-verusage/scripts/run_hint_augmentation.py \
  --config "$CONFIG" run-published-hints --checkpoints 1
```

Start with CP01 for both versions of IR, AC, and AL (six pilot continuations).
Inspect complete events, snapshots, isolation manifests, hashes, Verus and
Lynette results before scheduling the remaining checkpoints. The replay mode
rejects any hint-provider response, usage, or call-start artifact. The actor
cannot read the publication tree, original run, private hint directory,
credential file, or reference directory. A replayed run is a new continuation
sample and must not be described as recovery of the historical raw run.

## Matched no-hint run

Copy `no_hint_config.example.json` to an external directory below
`VERUS_SKILL_RUN_ROOT`, fill the placeholders, and use the same actor skill,
model, reasoning effort, 600 second budget, toolchain, and checkpoint source as
the corresponding hint arms. When the complete hint-arm run is mounted, set
`checkpoint_source_root` to that run. When only the reviewed publication is
available, set `checkpoint_publication_root` to the project directory under
`docs/hint-augmentation-20260916`; preparation verifies every selected source
hash against `selection_manifest.json` and records that run-manifest parity
could not be rechecked from the compact publication.

Preparation is offline. `run-no-hint` makes live actor calls.

```bash
python3 skillopt-verusage/scripts/run_hint_augmentation.py \
  --config "$NO_HINT_CONFIG" prepare-no-hint
python3 skillopt-verusage/scripts/run_hint_augmentation.py \
  --config "$NO_HINT_CONFIG" run-no-hint --checkpoints 1 2 3 4 5 6
```

Use checkpoints 1-6 for IR and AC, and 1-7 for AL. A fresh output root and an
independent bridge port are required for each task.

## Packet export

After all no-hint continuations finish, fill `fork_export_config.example.json`.
The exporter requires complete external original and continuation runs. It
refuses to reconstruct them from the compact publication under
`docs/hint-augmentation-20260916`.

```bash
python3 skillopt-verusage/scripts/export_skillopt_fork_packets.py \
  --config "$FORK_EXPORT_CONFIG"
```

The output is written only below `VERUS_SKILL_RUN_ROOT`. Each task directory
contains one complete original trace, exact event-index prefix/suffix views,
three complete fresh continuation traces per checkpoint, every recorded source
snapshot and diff referenced by those traces, hashes, visibility metadata,
and an optimizer-facing hint-visible index.

## Task-grouped SkillOpt diagnostic

The diagnostic driver creates exactly one failure-side Reflect item for each
source task. IR, AC, and AL therefore have equal task weight even though they
contain 6, 6, and 7 checkpoints. Each Reflect call may propose at most two
cards. SkillOpt then uses its native failure merge and global rank stages to
retain at most four edits.

The optimizer is GPT-5.6 Sol through the local Codex exec backend. Network and
web search are disabled. Run the optimizer output as a child of the packet root
so every referenced evidence file stays under one working tree:

```bash
export PYTHONPATH="$PWD/skillopt-verusage/src:$PWD/skillopt-verusage/SkillOpt:$PWD/skill-evolution-pilot/src"
python3 -m skillopt_verusage.fork_card_optimize \
  --packet-root "$FORK_PACKET_ROOT" \
  --out-dir "$FORK_PACKET_ROOT/skillopt-hint-visible" \
  --seed-skill skillopt-verusage/skills/initial.md \
  --model gpt-5.6-sol \
  --reasoning-effort high
```

The candidate remains diagnostic until it passes manual card review and the
unchanged fixed validation-20 selection gate. The driver does not mix these
three task patches with the 37 ordinary train trajectories.

## Offline checks

```bash
python3 -m unittest discover -s skillopt-verusage/tests \
  -p 'test_hint_augmentation.py' -v
python3 -m unittest discover -s skillopt-verusage/tests \
  -p 'test_fork_packets.py' -v
```
