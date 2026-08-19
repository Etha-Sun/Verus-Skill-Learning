# Blank/S2 Skill Four-Model Evaluation Setup and Audit

## Run Contract

- project: `verus_self_evolving`
- created_at: `2026-08-19T17:08:48-05:00`
- updated_at: `2026-08-20T19:10:00-05:00`
- status: `glm_stable_pair_complete_qwen_gpu_blocked_verusage_verus_installed`
- planned conditions: GPT-5.6 Sol, DeepSeek V4 Pro, GLM-5.3, and local
  Qwen3.8-27B crossed with `blank` and accepted S2
- planned endpoint: 20 held-out tasks per condition; 160 task executions total
- shared actor: autonomous noninteractive Codex CLI, 20 remote workers, four
  local Qwen workers, 262,144
  context, max reasoning, 600 seconds, zero valid-timeout retries, at most two
  V0 retries, and independent Verus plus Lynette judgment
- leakage controls: no reference proof, prior trajectory, retrieval card, or
  network resource; held-out outcomes cannot edit or select a skill
- formal output root: `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/`

## Upstream Baseline Finding

Microsoft SkillOpt does not define one universal initial skill. Its released
benchmark configurations point to task-specific initial documents; SearchQA's
three-line placeholder is only the nearest neutral example. Both the first
release and current documentation explicitly support an empty Markdown skill,
and the base configuration defaults to an empty value.

The canonical no-strategy control is now
`skillopt-verusage/skills/blank.md`: one LF byte, empty after stripping, SHA-256
`01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b`.
The prior local `skills/initial.md` is an 838-byte custom Verus seed and is not
an upstream-original blank baseline. Accepted S2 remains 4,179 bytes with
SHA-256
`1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e`.

## Harness Meaning and Parity Audit

The old `hands-off` label meant only that `codex exec` ran without human turns.
It did not select the legacy VeruSAGE `RepairRunner`. The precise actor label is
now `autonomous noninteractive Codex CLI`, and the ambiguous term was removed
from the task prompt.

A same-family Type-A independent reviewer initially returned FAIL / NO-GO. It
found that the Chat translator dropped Codex's custom `apply_patch`, direct and
bridge V0 handling differed, GPT inherited unrelated credentials, and the
planned test hash was recorded but not enforced. The implementation now:

- translates `apply_patch` calls and their history through Chat;
- retains invalid rows consistently and excludes them from solved counts;
- allowlists the actor environment and ignores user config/rules;
- enforces the exact test-items hash before task loading;
- hash-locks both skill variants and records the common prompt hash;
- freezes all arms to four workers, 262,144 context, and 600 seconds.

Strict byte-level parity remains impossible across providers. GPT and DeepSeek
use native Responses paths; GLM/Qwen require provider-specific Chat message and
sampling treatment. Native arms also see Codex's complete built-in tool schema,
while Chat arms see the task-required edit/command subset. Future results must
be described as semantic-contract comparisons.

## Qwen Real Edit Smoke

Official `Qwen/Qwen3.8-27B` revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` was served on four L40S GPUs
with BF16 TP=4 and 262,144 context. A non-held-out training-case smoke used the
canonical blank skill and the formal task prompt.

It ended unsolved as a valid `V1_TRUNCATED` timeout at 600.63 seconds. This is
not a score. It nevertheless proves edit-tool compatibility: five real
`apply_patch` file changes, seven command calls, eight requests containing
custom-tool history, no shell edits, unchanged input, F3 fidelity, independent
Verus and Lynette execution, and 12/12 completed requests with exact
`qwen3.8-27b` identity. Usage was 137,856 prompt plus 24,649 completion tokens
and USD 0 API cost. The service was stopped and GPU memory released afterward.

## Known Dataset Limitation and Scoring Decision

The frozen test manifest hash is
`81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42`, but
two referenced IronKV sources are not scoreable under the joint Verus+Lynette
contract because they contain the stale `verus_builtin_macros` alias:

- `f24cf9cc9db98c56f792`;
- `826687f9c56eb8e65d5d`.

Keeping the alias fails before proof checking; changing it violates the
proof-only surface. Raw data was not modified. The 2026-08-20 experiment
decision retains the original test-20: both items remain unchanged in every
condition, receive no special retry, and their verifier outcomes count toward
the main solved/20 result. The launcher now accepts `ZAI_API_KEY` and
`ZAI_BASE_URL`, explicitly exports a sourced key to its bridge, and defaults to
the general `https://api.z.ai/api/paas/v4` endpoint. Current public Z.AI
documentation lists `glm-5.1`, not the frozen `glm-5.3` ID. A 2026-08-20 direct
smoke nevertheless confirmed exact `glm-5.3` availability for this account:
HTTP success, no API error, 20 prompt tokens, and 16 reasoning/completion
tokens. The 16-token diagnostic cap ended with `finish_reason=length` before
visible answer text. Estimated cost under the frozen benchmark rates is USD
0.0000984.

A real blank-skill Codex smoke subsequently solved training item
`3a77a3e4e72edf600e2a` in 171.08 seconds. Independent Verus and Lynette passed;
24/24 metered requests completed under exact `glm-5.3`; usage was 312,922
prompt tokens (294,720 cached) and 5,665 completion tokens; estimated cost was
USD 0.127036. Two transient provider 429 events were recovered before the
unique `turn.completed`, and the event audit was otherwise F3-clean. The
terminal gate now records but does not invalidate recovered reconnects; it
still requires a zero Codex exit, exactly one completion, no `turn.failed`, a
valid complete provider ledger, and F3. The immutable stored result says
`V0_INVALID` under the old rule, while replay through the corrected classifier
is `V2_TRACE`.

Remote-provider groups use 20 actor-task workers with blank then S2
sequentially inside each group. Local Qwen remains at four workers. Its launch
is temporarily blocked because another user's vLLM workers occupy all four
L40S GPUs; those processes were not modified.

## Measured Formal Results

Six of eight arms are complete. GPT blank/S2 scored 18/20 and 17/20;
DeepSeek V4 Pro scored 13/20 and 13/20; GLM-5.3 scored 5/20 and 7/20. Every
completed arm has 20/20 provider-valid final results. Paired S2 changes were
-1 for GPT (zero gains, one regression), 0 for DeepSeek (two gains, two
regressions), and +2 for GLM (four gains, two regressions). Historical
Claude-failed solves decreased from 3/5 to 2/5, 1/5 to 0/5, and 1/5 to 0/5,
respectively. The GLM gain is therefore confined to historically normal
items in this one-run comparison.

Complete bridge-ledger formal cost was USD 2.991826 for DeepSeek and USD
3.241613 for GLM. GPT used local quota. The six completed arms therefore cost
USD 6.233439 in metered API calls. Including GLM availability/edit smokes and
two rejected pre-backoff concurrency attempts brings measured paid campaign
spend to USD 7.449787. Complete GLM ledgers exceed retained-result summaries
by USD 0.174586 because they include replaced provider-invalid attempts.

The GLM bridge absorbed 739 HTTP-429 retries across both accepted formal arms.
It reached 20/20 provider-valid results, unlike the rejected raw-concurrency
attempt, but blank/S2 still had 16 and 12 timeouts. Thus 20 workers is robust
with backoff but exceeds effective account throughput and confounds solve rate
with rate-limit waiting. Qwen blank/S2 remain pending on GPU release.

These worker-20 GLM scores are now treated as throughput-confounded rather
than stable capability measurements. A four-item frozen-training calibration
used the same blank skill, Codex CLI Chat bridge, 262,144 context, max
reasoning, 600-second limit, and joint Verus+Lynette metric at two workers.
All four tasks completed once as V2 traces; 51/51 upstream calls were metered
and accepted with zero HTTP-429 retries, zero backoff, and USD 0.354103 total
cost. Three of four tasks solved. Blank and S2 test-20 reruns therefore started
sequentially at two workers; their scores must replace the worker-20 GLM rows
only after both runs and complete-ledger checks finish.

Both stable reruns completed at 12/20 with 20/20 valid results, yielding zero
aggregate S2 delta. Blank used 592 requests, 20,333,394 prompt tokens, 216,940
completion tokens, and USD 6.976968; S2 used 498 requests, 15,920,375 prompt
tokens, 173,588 completion tokens, and USD 5.565405. Both ledgers had zero
terminal upstream errors but retained recovered HTTP-429 backoff. The stable
pair cost USD 12.542373; measured paid campaign spend including earlier arms,
smokes/rejected attempts, and calibration is USD 20.346263.

After these runs finished, the official VeruSAGE Verus commit
`ddc66116aa7a844a9e19cc50922fe85c84b8b4a5` was built in the machine-local
side-by-side checkout recorded in `.agent-context.local.md`. The binary reports
`0.2025.09.11.ddc6611`; both disputed IronKV references verify, both
unverified inputs reach their intended proof obligations, and one prior solved
candidate passes the new Verus plus Lynette. The local `.env` now selects this
binary while retaining the July binary under `VERUS_BIN_LEGACY`. Existing run
manifests and scores remain tied to the old verifier.

The accepted DeepSeek evolution uplift is independently confirmed as 13/20
for the custom 838-byte S0 and 15/20 for retained S2 on the reused selection
set. It is not a held-out or repeated-seed effect. The evolution and current
test paths share DeepSeek V4 Pro, Codex CLI, max reasoning, a 600-second task
limit, and the joint Verus+Lynette score, but are not exact protocol clones:
the current test baseline is the one-byte blank skill, the task prompt differs
by a two-word cleanup, context is 262,144 rather than 1,048,576, and optional
Codex capabilities are explicitly disabled. No observed evolution or test
prompt exceeded 262,144 tokens, so the context difference was nonbinding.

## Screenshot Audit and Official-Verus Two-Task Rerun

Comparison with `WechatIMG221.jpg` confirms that the July verifier was one
real undercounting source but not the whole explanation for lower scores. A
fresh actor rerun of the two version-sensitive IronKV tasks under official
VeruSAGE commit `ddc66116aa7a844a9e19cc50922fe85c84b8b4a5` produced the same
outcome in GPT blank/S2, DeepSeek blank/S2, and GLM blank/S2:
`f24cf9cc9db98c56f792` solved and `826687f9c56eb8e65d5d` timed out at 600
seconds. All 12 results were valid. Replacing just these two outcomes raises
the interim corrected blank/S2 estimates to GPT 19/18, DeepSeek 14/14, and GLM
13/13. These are targeted corrections, not complete official-Verus test-20
reruns.

Fresh metered spend was USD 1.947193: USD 0.310558 for DeepSeek and USD
1.636636 for GLM; GPT used local quota. DeepSeek had no provider retry. GLM
blank/S2 accumulated 17/21 recovered HTTP 429s and 193/372 aggregate
thread-seconds of backoff even at two task workers. Therefore GLM 12/20 remains
throughput-confounded. The screenshot's `Native baseline` label, test hash,
prompt hash, verifier hash, timeout, and actual upstream sampling parameters
are unavailable, so its 16/20 GLM score cannot yet be treated as an exact
same-condition replication.

The test evaluator now supports a repeatable `--item-id` diagnostic filter
without changing the default frozen test-20 behavior. The launcher exposes it
through `SKILLOPT_TEST_ITEM_IDS`. All 75 SkillOpt-VeruSAGE tests and launcher
syntax pass.

## Planning Budget

For both skill conditions (40 tasks per actor), planning estimates are:

| actor | approximate total |
|---|---|
| GPT-5.6 Sol | 500–800 calls; 18–24M tokens; local quota |
| DeepSeek V4 Pro | 600–900 calls; 26–34M tokens; USD 2.8–4.0 off-peak or USD 5.6–8.0 peak |
| GLM-5.3 | 500–1,000 calls; 20–36M input plus 1–3M output; USD 12–30 |
| Qwen3.8-27B | 90–140 minutes wall or 6–9.4 L40S GPU-hours; USD 0 API |

These are planning estimates, not measured formal outcomes.

## Verification

- all 75 currently discovered SkillOpt-VeruSAGE tests and all 43
  skill-evolution-pilot tests pass;
- launcher syntax passes; blank and S2 check-only contracts match the same
  test, prompt, workers, context, and timeout, and record both known items;
- real Qwen `apply_patch` and verifier smoke passes for compatibility;
- frozen test hash matches the declared value, and its two invalid sources are
  now explicitly recorded as blockers;
- six formal held-out conditions completed; two Qwen conditions are pending;
- raw and sealed datasets were read only and not modified.

## Durable Artifacts

- baseline contract:
  `skillopt-verusage/refine-logs/BASELINE_PARITY_CONTRACT_20260819.md`
- plan: `skillopt-verusage/refine-logs/EXPERIMENT_PLAN.md`
- tracker: `skillopt-verusage/refine-logs/EXPERIMENT_TRACKER.md`
- independent audit: `skillopt-verusage/refine-logs/EXPERIMENT_AUDIT.md`
- blank skill: `skillopt-verusage/skills/blank.md`
- evaluator: `skillopt-verusage/src/skillopt_verusage/test_eval.py`
- launcher: `skillopt-verusage/scripts/run_s2_fixed_test20.sh`
- Qwen edit smoke:
  `${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/qwen38-blank-apply-patch-smoke3-20260819/`
- measured result report:
  `skillopt-verusage/refine-logs/FIXED_TEST20_RESULTS_20260820.md`
- image/setting audit:
  `skillopt-verusage/refine-logs/IMAGE_RESULT_SETTING_AUDIT_20260820.md`

## Next Action

Obtain the screenshot run's contract hashes before merging its numbers. For
GLM, use one task worker or a global request-rate limiter and calibrate until
recovered 429 waiting is negligible, then rerun both complete test-20 arms
under official Verus. Run Qwen only after an owned service is available and
its model revision, precision, and reasoning template are locked.
