# Trace grounded task scope and diagnostic first repair

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-10-09T17:44:35`
- dataset/split: existing validation20 development traces; no sealed-test access.
- baseline: frozen repaired78 versus optional guidance comparison, control16/20,
  guided13/20 (4losses,1gain); parent summary hash b35746a4...391559.
- variant: clarify shared task prompt's existing-trust boundary and syntax-first
  rule; add opt-in diagnostic-first-v1 Executive, preserve initial.md and bank.
- metrics: unit/regression tests; local before/after Verus and Lynette results;
  source hashes; per-case diagnostics. Not a new solved-rate endpoint.
- leakage controls: all probes offline and derived from explicitly seen validation;
  no task IDs/proofs in deployed prompt; frozen evidence never edited.
- stop condition: inspect all4losses and positive counterexamples, test definite
  repairs locally, record remaining prompt-efficacy uncertainty; no paid run.

## Plan and checklist

1. [x] Reconcile all20 pairs and inspect4losses/1gain/5reading cases; verify raw
   code and public reasoning against previous analysis, not self-report alone.
2. [x] Confirm trust-scope misunderstanding appears in both a failure and a
   success; verify missing assertion parentheses in first failed snapshot.
3. [x] Add regression tests, fix task wording and add versioned Executive.
   Preserve historical initial.md, all78bodies/index/reader and optional retrieval.
4. [x] Probe four concrete solver mechanisms and retain negative/partial results.
5. [x] Run relevant regressions, inspect diff, update CURRENT and memory index.

Execution is local CPU/Verus only, pinned0.2025.09.12.bb1f342; four paired code
probes, each solver30s timeout. New external root:
VERUS_SKILL_RUN_ROOT/skillopt-verusage/trace-grounded-repair-20261009-VyNDlm/.
No GPU or paid model work. Main experiment remains complete/frozen. Available
shell/hash fallback is used because bash_exec/artifact.science interfaces are
not exposed; no evidence-graph or main-run registration claimed.

Hypothesis: preserving supplied trusted background and prioritizing reported
syntax errors removes avoidable search detours. Local probes test whether the
diagnosed code mechanisms are real, NOT whether a prompt makes a model obey.
That behavioral alternative remains inconclusive without fresh paired inference.

## Commands

```bash
PYTHONPATH=src:skillopt-verusage/src:skill-evolution-pilot/src:skillopt-verusage/SkillOpt \
  python -m pytest -q tests/test_diagnostic_first_skill.py \
  skill-evolution-pilot/tests/test_codex_runner.py \
  tests/test_retrieval_guidance_validation.py \
  tests/test_card_revision_validation_driver.py skillopt-verusage/tests/test_card_bank.py
```

## Outputs

- run directory: external root above; probes.json and per-case before/after dirs.
- probe command: scripts/probe_guidance_failure_cases.py --parent FROZEN_GUIDANCE_ROOT
  --output NEW_EXTERNAL_ROOT (approved VERUS_SKILL_RUN_ROOT).
- implementation: codex_runner.build_prompt; skills/diagnostic-first-v1.md.
- baseline initial.md SHA25696a557582ff423d159aa97698d3ea1eb55bd07af59cbfd3a518d86326a40df40.

## Results

First focused suite51passed. Initial red-test pass reproduced missing rules/new
file; a manually mistyped baseline hash in the new test was corrected from the
actual immutable initial.md bytes, not treated as a product defect.

Full selected regression suite828unique tests:819passed in the restricted run;
9failed solely because local AF_INET socket creation was denied. With appropriate
permission, the mocked HTTP subset10passed (9previous failures plus1overlapping
pass). No product assertion failure remained; do not sum rerun counts as new
tests. Final7focused skill/probe tests also pass. git diff --check clean.
An initial broad test command used a nonexistent audit-test filename and ran
zero tests; corrected command used only actual collected files.

Broad command: same PYTHONPATH, vrl Python -m pytest -q
skill-evolution-pilot/tests skillopt-verusage/tests
tests/test_diagnostic_first_skill.py tests/test_guidance_failure_probes.py
tests/test_retrieval_guidance_validation.py tests/test_card_revision_validation_driver.py
tests/test_full_validation20.py tests/test_codex_transcript_export.py
tests/test_card_trace_use_audit.py.
Permission-adjusted local mock-only rerun: test_native_transport_halt.py and
test_augmentation_campaign.py::GuardTests::test_campaign_bridge_matches_actor_routed_url.

## Detailed paired case study and solver challenges

Parent failure-analysis/REPORT.md and paired_analysis.json hold all20paired
outcomes, raw CLI hashes/line/item anchors and public request IDs. All4guided
losses read no card body; no direct-bank command is observed. This turn does not
reinterpret body-read counts as adoption or treat a model explanation as proof.

1. **3ce00a38: wrong task scope.** Control87.6s, guided600.5s. Guided public
   reasoning explicitly interprets existing external-body declarations as
   forbidden, removes2attributes, tries to prove three obligations instead of
   the one target, and searches for nonexistent asserts. Case62ff0a3c independently
   repeats unnecessary reproof but still passes (guided175.9s versus82.6s), so
   scope misunderstanding is not inferred solely from a timeout. Local probe
   scope_existing_lemmas preserves2given declarations and adds only the short
   supplied-lemma chain to the original empty target: Verus0verified/1error ->
   1verified/0errors, Lynette passes. This demonstrates an available simpler
   proof, not that model solve time would become the0.433s verifier runtime.
2. **9b9f6cce: wrong diagnostic layer.** Control157.3s, guided600.5s. First
   edited snapshot000028 has plain assertions missing required parentheses.
   The model explores reserved temporal-keyword hypotheses until~467s. Local
   syntax_parentheses_only mechanically wraps only ordinary assertion conditions:
   parsing error disappears and Lynette passes, but two semantic assertions
   remain unproved. The repair removes a real syntax detour, not the whole proof.
3. **a23a4969: exact instantiation plus absent assumptions.** Control298.5s,
   guided600.6s. Control reads006/029/070, rejects absent helper assumptions and
   finally instantiates exact spec.implies(...).satisfied_by(ex). Guided does not
   retrieve; first patch~309s, adds unproved generic entailment helpers, finally
   proposes reading at cutoff. Local entailment_exact_term_only fills just
   lemma_entails_unfold using the exact returned implication term. That helper's
   failure disappears (3verified/2error groups ->4verified/1error group), but the
   main theorem still calls two premise-dependent lemmas without making their
   antecedents available. Do not say generic helpers are inherently bad: the
   local probe proves one once its contract is correctly instantiated. The
   actionable rule is validate each bridge and its premises, rather than expand
   abstractions without feedback.
4. **aded7990: mathematically equivalent is not trigger-equivalent.** Control
   410.5s, guided600.6s. Guided attempts unsuccessful negative-trigger and
   contrapositive routes. To challenge the control's own explanation, local
   trigger_term_ablation starts from the verified control proof and replaces
   exactly one lambda-application assertion with its beta-reduced equivalent.
   This fails (2verified/1error); restoring the exact term passes (3verified/
   0errors). Both Lynette checks pass. This is stronger evidence of the matching
   bottleneck than relying only on public reasoning. It is an offline ablation
   of an observed solution, not a fresh model solve or hint experiment.

All8derived candidate hashes,16tool checks, frozen input/wrapper/source hashes
checked exact; no solver timeouts. All4after candidates pass Lynette. Two probes
fully verify, two intentionally remain partial. Those limitations are retained
in probes.json and per-case stdout/stderr/change.diff, not hidden as successes.

## Retrieval and latency interpretation

The one gainb9e5384 also reads no body: control56command items/no patch/timeout;
guided10patches/12verifier commands/pass539.8s. This is a positive counterpart to
the four losses: useful edit/feedback cycles matter, not just shorter prompts.
Among12both-pass pairs, guided body readers include9ee(+110.3s),62ff(+93.2s)
and599(-31.6s). In599, model correctly rejects three cards lacking local premises.
Therefore neither "all card reading harms" nor "reading more is improvement"
fits the observed pairs. Read-frequency comparisons are confounded by difficulty
and the reason for retrieval; no forced card insertion is justified yet.

Across the4losses, reasoning37382->120905tokens; clipped provider-active time
902.02->2345.54s. Fully completed requests within actor windows have completion/
request-time proxy57.02control versus59.00guided tokens/s (77vs110requests,
51437vs135492completion tokens; guided4late requests excluded). This is NOT
decode throughput and not a causal latency test; server/prefill/transport included.
It offers no evidence that gross API slowdown caused the losses. Actual public
reasoning, edits and diagnostic detours support excess ineffective deliberation.
Reader payload timings are rounded and do not measure downstream thinking cost.

## Implemented and deferred decisions

- Implemented shared project task prompt: prohibit INTRODUCING bypasses, preserve
  supplied trusted declarations and permit contract-based calls; prioritize the
  smallest parse/type/mode/scope correction, with generic assert syntax example.
- Added explicit opt-in diagnostic-first-v1.md: task scope, available-lemma
  chains, exact quantified terms, explicit antecedents, small edit/verify loops
  and permitted-source-only API inspection. No task-specific answer, ID, interface
  or proof code from validation is inserted into the deployed skill.
- Original initial.md remains byte-identical. New Executive1899UTF8bytes,
  SHA25699584a8a601e3f60952a157e92f948d7979f7d30137c298901b52e0aad13cd93.
  It is not automatically selected by historical campaigns; use it as an explicit
  seed in a future newly frozen contract. Shared task clarification applies to
  future project-profile runs. Cross-provider historical prompt is untouched.
- All78card bodies, index descriptions, reader, retrieval guidance switch,
  checkpoint selector, model parameters and evaluation metric untouched.
- Deferred automatic stall triggers, forced reads, top-k, card rewrites and full
  paid evaluation: current evidence does not isolate their benefit. This is a
  prompt/skill repair plus offline analysis tooling, not a new runtime controller.
|---|---:|---:|---:|

## Interpretation

Computed local evidence supports scope and diagnostic/exact-term bottlenecks;
prompt tests establish intended wording and immutable-card compatibility. Model
adherence and solved-rate improvement remain INCONCLUSIVE because no new model
run occurred. Existing single stochastic validation comparison cannot attribute
particular trajectories causally to guidance or a card. Evidence is development
only, not held-out confirmation; raw/sealed/legacy/frozen outputs unchanged.

## Next Action

Retain the minimal scope/syntax repair and opt-in Executive for a fresh bounded
paired development comparison. Same corrected task prompt in both arms, same
bank/index/reader/model/600s; separately test the Executive seed before adding a
retrieval controller. No paid run queued. Old frozen evaluation hashes/review
receipts cannot authorize a changed implementation as if unchanged. CURRENT and
index updated. No commits, raw-data modifications or hidden reasoning claims.
