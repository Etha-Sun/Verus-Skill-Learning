# Experiment Report

## Dataset

- traces: 2996
- verified: 1691
- nonverified: 1305
- effective_total_tokens: 1524386760

Project counts:

```json
{
  "AC": 240,
  "AL": 356,
  "IR": 424,
  "MA": 292,
  "NO": 112,
  "NR": 704,
  "OS": 564,
  "ST": 228,
  "VE": 76
}
```

## Candidate Rules

- mined rules: 800

## Policy Ablation

The ablation table uses trace-level union over the selected top rules, so
a trace covered by multiple rules is counted once.

| policy_level | rules | selected_top_k | union_covered_failed | union_saved_failed_tokens | false_stop_rate | peer_diff_rate | best_rule |
|---|---:|---:|---:|---:|---:|---:|---|
| generic | 72 | 20 | 1038 | 800760044 | 0.112951 | 0.748705 | generic__4__all__any__AssertFail__USELEMMA |
| motif | 532 | 20 | 227 | 309382084 | 0.005322 | 0.777778 | motif__4__AC__sequence_set_map__AssertFail__USELEMMA |
| project | 196 | 20 | 539 | 548995746 | 0.03903 | 0.748252 | project__4__AC__any__AssertFail__USELEMMA |

## Top Rules

| rule_id | level | covered_failed | saved_failed_tokens | false_stop_rate | peer_action_diff_rate | prefer_actions |
|---|---|---:|---:|---:|---:|---|
| generic__4__all__any__AssertFail__USELEMMA | generic | 164 | 208741771 | 0.010645 | 0.736842 | CASE_ANALYSIS NONLINEAR_ARITHMETIC |
| generic__4__all__any__AssertFail__CASE_ANALYSIS | generic | 242 | 202898394 | 0.024246 | 0.75 | INSTANTIATE_FORALL USELEMMA |
| generic__6__all__any__AssertFail__USELEMMA | generic | 146 | 160928841 | 0.005914 | 0.740741 | ADD_TRIGGER_ASSERT NONLINEAR_ARITHMETIC |
| motif__4__AC__sequence_set_map__AssertFail__USELEMMA | motif | 70 | 146080563 | 0.000591 | 0.833333 | POSTCONDITION_REPAIR precondition_repair |
| project__4__AC__any__AssertFail__USELEMMA | project | 70 | 146080563 | 0.000591 | 0.833333 | POSTCONDITION_REPAIR precondition_repair |
| generic__4__all__any__PostCondFail__postcondition_repair | generic | 183 | 140759988 | 0.021289 | 0.807018 | USELEMMA ADD_TRIGGER_ASSERT |
| generic__6__all__any__AssertFail__CASE_ANALYSIS | generic | 241 | 140389770 | 0.010645 | 0.747253 | USELEMMA INSTANTIATE_FORALL |
| motif__4__AC__temporal__AssertFail__USELEMMA | motif | 61 | 126562607 | 0.000591 | 0.75 | POSTCONDITION_REPAIR CASE_ANALYSIS |
| generic__8__all__any__AssertFail__USELEMMA | generic | 121 | 117758449 | 0.002957 | 0.736842 | NONLINEAR_ARITHMETIC precondition_repair |
| motif__6__AC__sequence_set_map__AssertFail__USELEMMA | motif | 64 | 116544601 | 0.000591 | 0.75 | precondition_repair ADD_TRIGGER_ASSERT |

## Claim Update

This run supports the scaffold-level claim that Verus repair traces contain
enough structure to mine decision rules with measurable failed-token coverage
and peer-success reroute support. These are offline replay metrics, not yet
a live repair success improvement.

## Next Action

Run a small live rerun on the highest-token traces matched by the best
project-aware or motif-aware rules, comparing baseline action selection
against rule-guided reroute.
