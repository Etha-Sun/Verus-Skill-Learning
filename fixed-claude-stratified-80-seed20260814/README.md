# Fixed Claude-stratified VeruSAGE split

This frozen split contains 40 training, 20 selection (`val`), and 20 test tasks. Each split is 25% historical Claude `FAILED`/`TIMEOUT` and 75% historical Claude `VERIFIED`, with matched AC/AL/IR quotas and a joint LoC/runtime/token difficulty proxy. Previously used SkillOpt-100 and R040 tasks were excluded. No verified reference proof is included.

The `source_path` fields in `train/items.json`, `val/items.json`, and `test/items.json` are relative to the repository root.
