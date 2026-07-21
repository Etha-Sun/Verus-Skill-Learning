# Research Memory System

This directory is the canonical memory filesystem for research work in this
workspace. It stores plans, literature notes, decisions, experiments, and
result manifests without mixing derived artifacts into raw data directories.

## Rules

1. Never write derived artifacts into raw data directories such as
   `all_batch_results-cyy-*`.
2. Every non-trivial research turn should create or update one entry under
   `projects/<project_id>/<kind>/`.
3. Every entry should include `ENTRY.md` and `metadata.json`.
4. Large generated outputs should live in the owning experiment repository or
   run directory; memory entries should link to them instead of duplicating
   them.
5. If an entry depends on raw data, record the data path and read-only contract
   in `metadata.json`.
6. If a result affects the research direction, record a decision entry.

## Layout

```text
research_memory/
├── BOOTSTRAP.md                # first file to read after context loss
├── CURRENT.md                  # current active state and next action
├── INDEX.md                    # regenerated global index
├── inbox/YYYY-MM-DD.md         # quick untriaged conversational notes
├── projects/<project_id>/
│   ├── PROJECT.md              # durable project summary
│   ├── literature/             # paper/source scouting entries
│   ├── ideas/                  # candidate directions and selected ideas
│   ├── experiments/            # experiment contracts/results
│   ├── decisions/              # go/no-go/route decisions
│   ├── meetings/               # meeting notes and extracted constraints
│   └── runs/                   # pointers to external run directories
├── templates/                  # entry templates
├── scripts/mem.py              # helper CLI
└── registry/                   # machine-generated registries
```

## Common Commands

Create a new entry:

```bash
python3 research_memory/scripts/mem.py new \
  --project verus_self_evolving \
  --kind experiments \
  --title "rule replay scoring v1"
```

Rebuild the global index:

```bash
python3 research_memory/scripts/mem.py index
```

Append a lightweight daily note:

```bash
python3 research_memory/scripts/mem.py log \
  --project verus_self_evolving \
  --text "short idea or context note"
```

## Current Projects

- `verus_self_evolving`: Verusage / Verus proof-repair self-evolving scaffold.
