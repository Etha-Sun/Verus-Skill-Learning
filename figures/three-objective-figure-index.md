# Three-Objective Figure Index

| Objective | Primary metric | Result figures | Current evidence status |
|---|---|---|---|
| Token cost | Expected primary uncached tokens to verifier-safe success (ETtS) | [`token_evolution_skill_heatmap.png`](token_evolution_skill_heatmap.png) ([PDF](token_evolution_skill_heatmap.pdf), [SVG](token_evolution_skill_heatmap.svg)); [`token_evolution_round_best.png`](token_evolution_round_best.png) ([PDF](token_evolution_round_best.pdf), [SVG](token_evolution_round_best.svg)) | H0 and all 18 R1-R6 skills are plotted on four tasks. These are single-run pilot contrasts. |
| Small-model benefit | Verifier-safe solve rate, with API turns and provider tokens as secondary costs | [`small_model_skill_heatmap.png`](small_model_skill_heatmap.png) ([PDF](small_model_skill_heatmap.pdf), [SVG](small_model_skill_heatmap.svg)); [`small_model_round_summary.png`](small_model_round_summary.png) ([PDF](small_model_round_summary.pdf), [SVG](small_model_round_summary.svg)) | H0 and all nine R1-R3 skills are shown over four tasks. Every complete condition solves the same 2/4 subset and uses more provider tokens than H0; three R2/R3 conditions have an F3-invalid runner-error cell and are excluded from aggregate comparison. |
| Full-proof InfoGain | Paired pre/post change in teacher-forced reference-proof log probability | [`infogain_pre_skill_heatmap.png`](infogain_pre_skill_heatmap.png) ([PDF](infogain_pre_skill_heatmap.pdf), [SVG](infogain_pre_skill_heatmap.svg)); [`infogain_skill_heatmap.png`](infogain_skill_heatmap.png) ([PDF](infogain_skill_heatmap.pdf), [SVG](infogain_skill_heatmap.svg)); [`infogain_round_summary.png`](infogain_round_summary.png) ([PDF](infogain_round_summary.pdf), [SVG](infogain_round_summary.svg)) | Scorer gate passed on all four tasks. R1 and R2 each have 12/12 exact pre/post scores and do not improve monotonically. R3 trajectories are complete, but its scoring attempt stopped after 10/12 partial pairs; partial scores are excluded and R3 remains pending. |

## Shared Workflow

- English source: [`three-objective-skill-evolution-loop.mmd`](three-objective-skill-evolution-loop.mmd)
- Markdown preview: [`three-objective-skill-evolution-loop.md`](three-objective-skill-evolution-loop.md)
- Rendered PNG: [`three-objective-skill-evolution-loop.png`](three-objective-skill-evolution-loop.png)

The workflow depicts three isolated single-objective evolution loops. The
first three task roles are shared; the fourth hard case is branch-specific.
