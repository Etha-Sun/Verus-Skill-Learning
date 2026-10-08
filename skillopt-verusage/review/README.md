# Card discovery and offline review

`build_bundle(..., autonomous_retrieval=True)` keeps all card IDs visible in
source order and allows arbitrary-ID reads, without ranking or a fixed read
count. An absent heading or a heading equal to the Trigger is rendered once.
Existing card banks and full card bodies are not changed.

An optional `index_descriptions={"card-001": "...", ...}` keyword separates
routing text from full prerequisites. It must cover every card ID with a
nonempty single-line description. There is no hard truncation, automatic
description generation, or semantic approval from the builder. Validate a
description before deployment; its full Trigger and Avoid when still govern
application after the agent reads the card. Existing callers keep the entire
Trigger in the index. The completed experiment's frozen bundles stay unchanged.

## Prepare an analyst-only worksheet

The initial seven cases are synthetic development states for the frozen
augmented bank, not validation/test task inputs or a measured benchmark.
They contrast missing-antecedent repair, post-pass warning cleanup, and
fixed-width serialization connectors with near-misses. Applicability is
different from a mandatory read: the agent may solve by another valid route.

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt \
python3 -m skillopt_verusage.card_review \
  --bank "$AUGMENTED_BANK" --bundle "$AUGMENTED_BUNDLE" \
  --cases skillopt-verusage/review/card_routing_cases.json \
  --output "$VERUS_SKILL_RUN_ROOT/skillopt-verusage/card-review-fresh"
```

The fresh external output contains the complete index, each reviewed card's
body, source hashes, expected applicability and blank evidence fields. `--bundle`
binds the actual deployed index (including custom descriptions) and artifact
manifest, and checks that its bodies/IDs preserve the source bank. Without it,
the packet uses the default index renderer, not an observed deployment. To add
cases, keep unique case IDs and supply card ID, current state, applicability
(`applicable`, `inapplicable`, `optional`) and rationale. Bind them to the exact
bank SHA256; IDs from another bank are not interchangeable. The tool never
calls a model and does not automatically grade reasoning.

For actual agent runs, the actor receives the ordinary deployed bundle, never
this answer-key packet. Independently inspect complete trace and proof outputs:

1. Was the body actually read? Record the completed event, not just an ID mention.
2. Did the full Trigger hold and did an Avoid when clause rule it out?
3. Was the suggestion adopted, partly used, or explicitly declined? Cite events.
4. What proof edit followed? If none, mark it absent rather than infer use.
5. What did Verus and preservation checks actually report after the action?
6. Separate correct advice/application from any claim of causal benefit.

Keep missing evidence explicit. A post-success cleanup cannot explain earlier
proof success; no read does not automatically mean failure. Development cases
and validation diagnostics do not become sealed final evaluation data. New/old
live index comparisons require their own authorized, leakage-safe run.
