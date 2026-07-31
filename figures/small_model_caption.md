# Small-Model Evolution Figures

`small_model_skill_heatmap` shows every audited Qwen3.6-27B
task-condition outcome from H0 and R1-R3. Each cell reports verifier-safe
PASS/FAIL, provider-reported tokens, and API requests. The aligned bars show
the total provider-token change relative to H0 only when all four runs satisfy
the F3 logging contract; runner errors are hatched and excluded from aggregate
comparison.

`small_model_round_summary` selects the complete condition with the highest
solve count in each round and breaks ties using fewer provider tokens. All
selected conditions solve the same 2/4 tasks. Their total provider-token counts
are 312,656 (H0), 327,572 (R1), 321,998 (R2), and 322,195 (R3). These are
single-run pilot contrasts, so the figures do not establish stable skill
benefit.
