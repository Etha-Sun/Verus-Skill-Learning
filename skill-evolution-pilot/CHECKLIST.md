# Implementation Checklist

Run ID: `skill-evolution-infra-v1`

## In progress

- [ ] Run the live OpenRouter preflight after runtime-secret injection.

## Next

- [ ] Run one OpenRouter preflight if the runtime credential is available.
- [ ] Implement the host-controlled Qwen repair loop.
- [ ] Implement the token ledger.

## Blocked

- [ ] Live OpenRouter preflight: `OPENROUTER_API_KEY` is not currently present
  in the process environment.
- [ ] Full token round: fourth task is not frozen.

## Validation

- [ ] zero fake-secret matches in artifacts;
- [ ] zero JSON parse errors for valid fixtures;
- [ ] malformed rows are preserved as explicit incomplete events;
- [ ] request and tool call pairing audits pass;
- [ ] missing usage fields remain null;
- [ ] immutable input and visibility manifests pass;
- [ ] real model identity matches the requested model;
- [ ] final Verus/Lynette results bind to the final candidate hash.

## Done

- [x] detailed experiment and information contracts written.
- [x] token-first run budget and stop rules frozen.
- [x] normalized-event and redaction layer implemented.
- [x] Codex raw-event normalization and visibility manifests implemented.
- [x] OpenRouter env-only completion adapter implemented and fake-tested.
- [x] 12 model-free tests pass.
- [x] failed Codex F3 smoke retained and diagnosed.
- [x] corrected Codex F3 smoke passed.
