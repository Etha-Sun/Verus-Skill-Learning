# Cross-Provider Verus Evaluation Setup and API Bridge Contract

## Technical summary

This document records the complete evaluation contract used for DeepSeek V4 Pro, GPT-5.6 Sol Max, GLM-5.3, and local Qwen3.8-27B FP8. Its primary purpose is to diagnose why another GLM-5.3 run may have lower proof success and much larger token usage.

Machine-local paths from the reference run are represented with portable
placeholders: `${REFERENCE_REPO_ROOT}`, `${REFERENCE_RUN_ROOT}`,
`${REFERENCE_VERUS_BIN}`, `${REFERENCE_LYNETTE_BIN}`, and provider-specific
`${REFERENCE_*_ENV_FILE}` variables.

The most consequential implementation difference is the API transport:

| Response model | Codex-facing API | Upstream API | Bridge behavior |
|---|---|---|---|
| DeepSeek V4 Pro | Responses | Responses | Native body and SSE response pass-through; only the model ID is frozen |
| GPT-5.6 Sol Max | Responses | Responses | Native body and SSE response pass-through; only the model ID is frozen |
| GLM-5.3 | Responses | Chat Completions | Responses request is translated to Chat messages and tools; Chat output is rebuilt as Responses SSE |
| Qwen3.8-27B FP8 | Responses | Chat Completions through local vLLM | Same translation family as GLM, with Qwen-specific thinking and reasoning-history fields |

Therefore, a nominally identical “GLM-5.3 + Codex” experiment can behave differently if its bridge does not preserve assistant reasoning, tool-call IDs, tool results, cache usage, or Responses event structure exactly. The completed GLM no-skill run used the frozen bridge implementation SHA-256:

    18dced3a21caf87b643a88f06493aa6da6f4f937573849aa51143c0769d7ada3

Its GLM no-skill bridge configuration SHA-256 was:

    2b8d2b2ca70372a5ef80f44abba67315737fe2e35b5cef56a915763bca1cc629

The source currently present at the recorded bridge path has the same implementation hash. These two hashes should be the first bridge-level comparison against another run.

## Frozen evaluation scope

### Dataset

The paired comparison used the frozen test split:

    ${REFERENCE_REPO_ROOT}/fixed-claude-stratified-80-seed20260814/test/items.json

| Identity | Recorded value |
|---|---|
| Number of test tasks | 20 |
| Split file SHA-256 | 81194e9cc30b737898c9eb545ad9934490eff2118616194bd9c051600c2d0c42 |
| Ordered task projection SHA-256 | f863a48142310e3382246851662f5e23efc98420973f5348ac5b6f31e709fd64 |
| Project composition | AL: 7, AC: 6, IR: 7 |
| Scheduling | Serial, task 1 through task 20 |
| Repetitions | One run per model and condition |
| Actor timeout | 600 seconds per task |
| Final verification timeout | 120 seconds |
| Conditions | no-skill; with-native-official-baseline |

DeepSeek additionally ran the frozen 20-task validation split. GPT, GLM, and Qwen ran only the test split in this baseline comparison.

Tasks 9 and 19 were reported as failed for every response model because of known fixture defects. This reporting convention must be kept constant when comparing aggregate success rates.

### Baseline skill

The with-skill condition used this unchanged skill tree:

    ${REFERENCE_RUN_ROOT}/cross-task-global-20260814/native_official_baseline_v1/skill/verus-proof-repair

| Identity | SHA-256 |
|---|---|
| Complete skill tree | fc2c51a283212ffe365fcd9bc91fedca1c6a46d43a51c4310facd7f76f41b74b |
| Root SKILL.md | 40de0d04f2f4e2b05a0d8187439251f2e381b2f4675c2ef44247519acf9452bd |

For each with-skill task, the runner copied a frozen snapshot to:

    skill/verus-proof-repair/

Codex was required to read the root SKILL.md first and load references only when routed there. For no-skill, no skill directory was present and the experiment manifest recorded “skill: null”.

## End-to-end architecture

The common execution path was:

    frozen task source
      -> isolated task workspace
      -> Codex CLI 0.147.0
      -> task-scoped loopback Responses endpoint
      -> provider-specific bridge mode
      -> response model
      -> Codex tool call
      -> audited shell
      -> Verus and/or Lynette feedback
      -> next model turn
      -> final independent Verus + Lynette verification

The model never received the provider API key. Codex saw a placeholder credential for the loopback bridge. The real key existed only in the bridge process.

The actor ran inside private user, mount, PID, temporary, and network namespaces. The task workspace was writable; Verus, Rust, and Lynette were mounted read-only. The broader scratch tree and host home were hidden. Network access was limited to the task-scoped loopback relay.

## Exact Codex version and invocation contract

| Setting | Value |
|---|---|
| Codex CLI | codex-cli 0.147.0 |
| Codex binary | /home/xinyueh/.codex/packages/standalone/releases/0.147.0-x86_64-unknown-linux-musl/bin/codex |
| Codex binary SHA-256 | cb0a15567e9a60a5820d54b0f6ae86d504dc3805c1eab21a47f70e3eb7b73a40 |
| Approval policy | never |
| User configuration | ignored |
| Session persistence | ephemeral |
| Output mode | JSON events |
| Git repository check | skipped |
| Codex sandbox flag | danger-full-access inside the stronger outer namespace |
| Provider request retries | 4 |
| Provider stream retries | 4 |
| Normal maximum output | 8,192 tokens |
| Expanded bridge retry | 131,072 tokens, only after Chat finish_reason=length |
| Upstream HTTP timeout | 1,800 seconds |
| Temperature | not explicitly set by the runner |
| Top-p | not explicitly set by the runner |
| Per-task decoding seed | not set by the actor runner |

The effective Codex command had this shape:

~~~bash
/home/xinyueh/.codex/packages/standalone/releases/0.147.0-x86_64-unknown-linux-musl/bin/codex \
  -a never \
  exec \
  --ignore-user-config \
  --ephemeral \
  --json \
  --skip-git-repo-check \
  -C TASK_WORKSPACE \
  -s danger-full-access \
  -m MODEL_ID \
  -c 'model_provider="PROFILE_NAME"' \
  -c 'model_providers.PROFILE_NAME.base_url="http://127.0.0.1:PORT/tasks/test--TASK_KEY/v1"' \
  -c 'model_providers.PROFILE_NAME.env_key="PROVIDER_API_KEY_NAME"' \
  -c 'model_providers.PROFILE_NAME.wire_api="responses"' \
  -c 'model_providers.PROFILE_NAME.request_max_retries=4' \
  -c 'model_providers.PROFILE_NAME.stream_max_retries=4' \
  -c 'model_reasoning_effort="PROVIDER_EFFORT"' \
  -c 'model_context_window=PROVIDER_CONTEXT' \
  -c 'model_max_output_tokens=8192' \
  'Repair the Verus proof in candidate.rs. ...'
~~~

The task workspace always began with:

    AGENTS.md
    TASK.md
    input.rs
    candidate.rs

The with-skill condition additionally contained the frozen skill directory. TASK.md contained exactly:

    Repair candidate.rs.

The full rule text below was written to AGENTS.md and was also passed as the final Codex CLI prompt. This duplication was identical across all four providers. Codex’s built-in internal instructions are part of the pinned Codex binary rather than a separate experiment-owned prompt file; reproducibility of that layer is therefore represented by the Codex version and binary hash.

## Exact no-skill prompt

~~~text
Repair the Verus proof in candidate.rs.

Rules:
- This is the no-skill control; no proof-repair skill is supplied.
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with ${REFERENCE_VERUS_BIN} candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both ${REFERENCE_VERUS_BIN} candidate.rs and
  ${REFERENCE_LYNETTE_BIN} compare -t input.rs candidate.rs to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
~~~

The final phrase “supplied immutable skill” remained in the common rule template, but the explicit first rule, missing skill directory, and manifest “skill: null” made this the no-skill control.

## Exact with-baseline-skill prompt

~~~text
Repair the Verus proof in candidate.rs.

Rules:
- Read skill/verus-proof-repair/SKILL.md first and follow it. Consult a file below skill/verus-proof-repair/references/ only when the root skill explicitly routes you there.
- input.rs is immutable and candidate.rs is the only file you may edit.
- Do not use assume, admit, newly introduced external_body, axioms, or
  unimplemented trusted helpers. Do not weaken or remove requires, ensures,
  recommends, signatures, executable code, or intended specifications.
- Diagnose with ${REFERENCE_VERUS_BIN} candidate.rs and iterate on the smallest proof-only edit.
- Before finishing, require both ${REFERENCE_VERUS_BIN} candidate.rs and
  ${REFERENCE_LYNETTE_BIN} compare -t input.rs candidate.rs to exit successfully.
- Do not search for trajectories, verified solutions, sibling task outputs, or
  validation/test metadata. Work only from this task, local Verus/vstd
  documentation, verifier diagnostics, and the supplied immutable skill.
- Finish only after both checks pass. Otherwise leave the best candidate.rs and
  state the precise blocker.
~~~

## Provider profiles

| Field | DeepSeek | GPT | GLM | Local Qwen |
|---|---|---|---|---|
| Runner provider name | deepseek | openai | glm | qwen_local |
| Model sent upstream | deepseek-v4-pro | gpt-5.6-sol | glm-5.3 | qwen38-27b-fp8 |
| Codex reasoning effort | high | max | max | xhigh |
| Codex context window | 1,048,576 | 1,048,576 | 1,048,576 | 262,144 |
| Upstream base URL | https://api.deepseek.com | https://api.openai.com/v1 | https://api.z.ai/api/paas/v4 | http://127.0.0.1:8000/v1 |
| Upstream path | /responses | /responses | /chat/completions | /chat/completions |
| Native Responses | yes | yes | no | no |
| Chat reasoning effort | not used | not used | max | omitted |
| Chat thinking field | not used | not used | thinking={type: enabled} | omitted |
| Chat template kwargs | not used | not used | none | enable_thinking=true, preserve_thinking=true |
| Reasoning-history field | provider-native | provider-native | reasoning_content | reasoning |
| Upstream streaming | provider-native Responses body | provider-native Responses body | false | false |
| Chat tools allowed by bridge | not filtered by bridge | not filtered by bridge | exec_command, write_stdin | exec_command, write_stdin |
| Paid budget guard | yes | yes | yes | no |
| Test no-skill loopback port | 4318 | 4331 | 4335 | 4333 |
| Test with-skill loopback port | 4320 | 4332 | 4336 | 4334 |

The OpenAI profile additionally mounted the co-versioned codex-code-mode-host. The other three profiles did not.

## Environment-file formats

Credentials are intentionally omitted. The environment files should contain only the relevant provider profile. A complete reproducible template is:

### DeepSeek

~~~dotenv
DEEPSEEK_API_KEY=FILL_THIS
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
~~~

The completed experiment loaded:

    ${REFERENCE_DEEPSEEK_ENV_FILE}

### GPT

~~~dotenv
OPENAI_API_KEY=FILL_THIS
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5.6-sol
~~~

The completed experiment loaded:

    ${REFERENCE_GPT_ENV_FILE}

Only OPENAI_API_KEY was explicitly present in that file; the runner supplied the recorded default base URL and model.

### GLM

~~~dotenv
GLM_API_KEY=FILL_THIS
GLM_BASE_URL=https://api.z.ai/api/paas/v4
GLM_MODEL=glm-5.3
~~~

The completed experiment loaded:

    ${REFERENCE_GLM_ENV_FILE}

### Qwen local

~~~dotenv
QWEN_LOCAL_API_KEY=EMPTY
QWEN_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
QWEN_LOCAL_MODEL=qwen38-27b-fp8
~~~

The value EMPTY is only a local vLLM placeholder, not a paid-provider credential.

## Wire format: DeepSeek and GPT native Responses

Codex posts a Responses request to the task-scoped loopback endpoint:

    POST http://127.0.0.1:PORT/tasks/test--TASK_KEY/v1/responses

For DeepSeek and GPT, the bridge copies the request body, replaces only the model field with the frozen model ID, and posts it to the provider’s /responses endpoint:

~~~json
{
  "model": "deepseek-v4-pro or gpt-5.6-sol",
  "instructions": "Codex-generated instruction block",
  "input": [
    {"role": "user", "content": "..."},
    {"type": "function_call", "call_id": "...", "name": "...", "arguments": "..."},
    {"type": "function_call_output", "call_id": "...", "output": "..."}
  ],
  "tools": ["provider receives the original Codex Responses tool definitions"],
  "max_output_tokens": 8192
}
~~~

All additional Codex Responses fields are passed through rather than reconstructed. The upstream response body and content type are returned to Codex unchanged. The bridge separately parses the terminal Responses usage event for accounting but does not rewrite the native response.

This is why the DeepSeek and GPT bridges are less likely to change agent semantics: they isolate credentials, budget, and task routing without converting conversation or tool history.

## Wire format: GLM Responses-to-Chat translation

Codex still sees a Responses endpoint. The GLM bridge converts that payload to this Chat Completions shape:

~~~json
{
  "model": "glm-5.3",
  "messages": [
    {
      "role": "system",
      "content": "Responses instructions plus developer/system contents"
    },
    {
      "role": "user",
      "content": "task prompt or prior user content"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "CALL_ID",
          "type": "function",
          "function": {
            "name": "exec_command",
            "arguments": "{\"cmd\":\"...\"}"
          }
        }
      ],
      "reasoning_content": "preserved reasoning associated with CALL_ID"
    },
    {
      "role": "tool",
      "tool_call_id": "CALL_ID",
      "content": "tool stdout/stderr returned to Codex"
    }
  ],
  "stream": false,
  "max_tokens": 8192,
  "reasoning_effort": "max",
  "thinking": {"type": "enabled"},
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "exec_command or write_stdin",
        "description": "...",
        "parameters": {}
      }
    }
  ],
  "tool_choice": "auto",
  "parallel_tool_calls": true
}
~~~

Exact translation rules:

1. Responses instructions and developer/system messages are concatenated into one Chat system message.
2. Responses user/assistant messages become Chat messages.
3. Consecutive Responses function_call items become one assistant message containing tool_calls.
4. Responses function_call_output becomes a Chat tool message with the same call ID.
5. Responses reasoning, computer_call, and computer_call_output items are not copied as ordinary text.
6. Only exec_command and write_stdin function tools are sent upstream.
7. No temperature, top-p, or seed field is added.
8. Upstream streaming is disabled.
9. If finish_reason is length, the bridge retries the same request with max_tokens=131072.
10. Both the truncated attempt and the retry are included in token and cost totals.

### GLM reasoning continuity

When GLM returns a tool call, the bridge reads:

    choices[0].message.reasoning_content

It also accepts message.reasoning as a fallback. The reasoning text is stored by tool-call ID. On the next request, it is inserted into the historical assistant tool-call message under reasoning_content.

This is a critical compatibility behavior. A bridge that drops reasoning_content, attaches it to the wrong tool call, changes call IDs, or serializes the tool result as a user message rather than a tool message is not equivalent to this experiment. Such a bridge can make GLM lose its chain of reasoning between verifier iterations or cause provider-side validation errors.

### Chat response reconstructed for Codex

The bridge converts the first Chat choice into synthetic Responses SSE events:

- message.content becomes response.output_text events;
- message.tool_calls become response function_call events;
- the final Chat usage object becomes the Responses usage object;
- prompt cache hits become input_tokens_details.cached_tokens;
- completion reasoning tokens are copied only if the provider reports completion_tokens_details.reasoning_tokens;
- the response terminates with response.completed and data: [DONE].

The raw GLM reasoning text is retained for subsequent tool-call history but is not emitted to Codex as ordinary assistant text. Therefore, reasoning-token figures can differ between bridges even when the model generated similar reasoning: the summary depends on the provider’s usage fields, not on counting the reasoning_content string locally.

## Wire format: local Qwen3.8-27B FP8

Qwen used the same Responses-to-Chat bridge family, but its upstream request deliberately differed from GLM:

~~~json
{
  "model": "qwen38-27b-fp8",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": ["..."],
      "reasoning": "preserved Qwen reasoning"
    },
    {
      "role": "tool",
      "tool_call_id": "CALL_ID",
      "content": "..."
    }
  ],
  "stream": false,
  "max_tokens": 8192,
  "chat_template_kwargs": {
    "enable_thinking": true,
    "preserve_thinking": true
  },
  "tools": ["exec_command", "write_stdin"],
  "tool_choice": "auto",
  "parallel_tool_calls": true
}
~~~

Qwen differences from GLM:

- no upstream reasoning_effort field was sent because the pinned vLLM request schema rejected the literal xhigh;
- no thinking={type: enabled} field was sent;
- the official chat-template defaults selected xhigh;
- chat_template_kwargs explicitly enabled and preserved thinking;
- historical reasoning was written to the assistant field reasoning rather than reasoning_content;
- the endpoint was a local vLLM server, so no paid budget guard was needed.

The local service used:

| Setting | Value |
|---|---|
| Checkpoint | Qwen/Qwen3.8-27B-FP8 |
| Pinned revision | 017b9c7af6b5689d5dd426a76e0bc077eb5ca20a |
| Served name | qwen38-27b-fp8 |
| vLLM | 0.19.1 |
| Transformers overlay | 5.8.0 |
| PyTorch | 2.10.0+cu128 |
| GPUs | 4 × NVIDIA L40S |
| Tensor parallel size | 4 |
| Model context | 262,144 |
| Weight precision | official FP8 checkpoint |
| KV cache | FP8 |
| Reasoning parser | qwen3 |
| Tool parser | qwen3_coder |
| Maximum concurrent sequences | 4 |
| GPU memory utilization | 0.90 |
| vLLM seed | 0 |
| MTP speculative decoding | disabled |

This Qwen result is specifically an FP8-weight and FP8-KV-cache result. It is not a BF16 Qwen3.8-27B result.

## Tool access and verifier loop

For GLM and Qwen, the bridge exposed exactly two Codex function tools to the upstream Chat API:

- exec_command: start a shell command;
- write_stdin: continue or interact with a running shell session.

Verus, Lynette, and vstd inspection were not separate API tool names. The model accessed them through the audited shell:

~~~bash
${REFERENCE_VERUS_BIN} candidate.rs
${REFERENCE_LYNETTE_BIN} compare -t input.rs candidate.rs
~~~

The agent was expected to inspect verifier diagnostics, edit candidate.rs, rerun checks, and continue until both passed or the 600-second actor limit expired.

Attempts to inspect verified answers, trajectories, sibling tasks, or held-out metadata were blocked. A blocked attempt was returned to the model as an ineffective tool operation and recorded as an audit observation; it did not automatically fail the task.

## Final scoring contract

| Component | Recorded value |
|---|---|
| Policy | proof-outcome-v3 |
| Verus binary | ${REFERENCE_VERUS_BIN} |
| Verus version | 0.2025.07.12.0b6f3cb |
| Verus SHA-256 | c3afe80bbaabc45527a18e490fc124dea9cd79afe8861f698a7cf33c7123178d |
| Lynette binary | ${REFERENCE_LYNETTE_BIN} |
| Lynette version | 0.0.0 |
| Lynette SHA-256 | bcdd8e1b1fc407bfd415814f2791af91f1ac30c2af9ee0085ae97b4fd38deb11 |

Success required all of the following:

1. candidate.rs passed Verus;
2. Lynette accepted the change against immutable input.rs;
3. input.rs and the original source remained unchanged;
4. no unsafe bypass or specification-weakening edit was introduced.

Ordinary failures were timeout or final_verification_failed. A provider interruption exhausted across retries left the batch incomplete and resumable rather than converting the task into a proof failure.

The benchmark repository specifies Verus commit ddc66116, but these completed runs used 0b6f3cb. Any comparison using ddc66116 is a different verifier condition.

## How the four experiments were launched

The top-level drivers ran preflight first and then execution. These commands are templates with credentials kept in the referenced environment files.

### DeepSeek V4 Pro

This driver runs validation and test, no-skill and with-skill:

~~~bash
python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_deepseek_v4_pro.py \
  --preflight \
  --env-file ${REFERENCE_DEEPSEEK_ENV_FILE} \
  --approval-limit-usd 20

python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_deepseek_v4_pro.py \
  --execute \
  --env-file ${REFERENCE_DEEPSEEK_ENV_FILE} \
  --approval-limit-usd 20
~~~

### GPT-5.6 Sol Max

This driver runs only the test split. The completed v3 run used a USD 40 guard:

~~~bash
python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_gpt_5_6_sol_max.py \
  --preflight \
  --env-file ${REFERENCE_GPT_ENV_FILE} \
  --approval-limit-usd 40

python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_gpt_5_6_sol_max.py \
  --execute \
  --env-file ${REFERENCE_GPT_ENV_FILE} \
  --approval-limit-usd 40
~~~

### GLM-5.3

This driver runs only the test split. The no-skill arm completed under the original USD 20 guard. Later increases to USD 25 and USD 30 were used to finish/resume the with-skill arm and did not change completed no-skill tasks.

~~~bash
python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_glm_5_3.py \
  --preflight \
  --env-file ${REFERENCE_GLM_ENV_FILE} \
  --approval-limit-usd 20

python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_glm_5_3.py \
  --execute \
  --env-file ${REFERENCE_GLM_ENV_FILE} \
  --approval-limit-usd 20
~~~

### Local Qwen3.8-27B FP8

The local vLLM service had to be healthy before preflight and execution:

~~~bash
python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/manage_qwen3_8_service.py --status

python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_qwen3_8_27b_fp8.py \
  --preflight \
  --env-file ${REFERENCE_RUN_ROOT}/baseline-test-20260819/qwen/local.env

python3 ${REFERENCE_REPO_ROOT}/baseline-test-20260819/code/run_qwen3_8_27b_fp8.py \
  --execute \
  --env-file ${REFERENCE_RUN_ROOT}/baseline-test-20260819/qwen/local.env
~~~

Use --resume only with an incomplete output generated by the same frozen contract. Never point a replication at a completed output directory.

## Why GLM token totals can look unusually large

The recorded no-skill usage was:

| Model | Solved | Requests | Requests/task | Cumulative input | Input/request | Output | Cache-hit share |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek V4 Pro | 13/20 | 525 | 26.25 | 21,633,556 | 41,207 | 365,158 | 97.77% |
| GPT-5.6 Sol Max | 18/20 | 385 | 19.25 | 14,159,638 | 36,778 | 144,831 | 95.27% |
| GLM-5.3 | 16/20 | 624 | 31.20 | 25,369,274 | 40,656 | 224,505 | 97.10% |
| Qwen3.8-27B FP8 | 5/20 | 424 | 21.20 | 9,085,953 | 21,429 | 350,142 | not reported |

The GLM total is cumulative across 624 iterative requests. Each tool round resends the growing conversation, so the same prefix can be counted repeatedly. It is not 25.4 million unique context tokens. Of GLM’s 25.37 million reported input tokens, 24.63 million were reported as cache hits.

The harness also reports primary_uncached_tokens as:

    cache-miss input + cache-write input + output

For GLM no-skill this value was 960,883, much smaller than cumulative input. When comparing token consumption, both teams must compare the same fields:

- total cumulative input tokens;
- cache-hit input tokens;
- cache-miss input tokens;
- cache-write input tokens;
- output tokens;
- reasoning tokens;
- request count;
- number of length-triggered expanded retries.

Provider token schemas are not perfectly comparable. In particular, the translated bridge records reasoning_tokens only when the Chat provider supplies completion_tokens_details.reasoning_tokens. Missing reasoning-token reporting does not prove that no reasoning occurred.

## Most likely bridge differences behind poor GLM performance

These are diagnostic hypotheses, not confirmed causes until the other bridge is inspected.

1. Reasoning continuity is missing. The other bridge may omit assistant reasoning_content when replaying tool-call history. This can make GLM restart its reasoning after every Verus command.
2. Tool history is malformed. Tool results must use role=tool and the exact tool_call_id. Converting them to user messages, regenerating IDs, or separating parallel calls incorrectly changes the conversation.
3. Responses instructions are dropped or duplicated. This bridge merges the Responses instructions and all developer/system contents into one system message exactly once per translated request.
4. The upstream thinking controls differ. Our GLM request sends both reasoning_effort=max and thinking={type: enabled}.
5. The output budget differs. Our first request allows 8,192 tokens and retries at 131,072 only on finish_reason=length.
6. Streaming differs. Our GLM upstream call is non-streaming; only the reconstructed Codex-facing response is SSE.
7. Tool schemas differ. Our Chat bridge exposes only exec_command and write_stdin and preserves their JSON schemas.
8. Cache accounting differs. Total prompt tokens can look much larger if cache-hit tokens are not separated, even when billed/uncached usage is modest.
9. The agent loop differs. This is Codex CLI 0.147.0 with iterative shell feedback, not a direct one-shot GLM Chat Completions request.
10. The verifier differs. The completed run used Verus 0b6f3cb; a teammate using ddc66116 is not running the same condition.
11. The model alias may drift. The provider exposed glm-5.3 as an alias, not an immutable weights revision.
12. Stochasticity remains. No per-task seed or temperature was set, and there was only one run per condition.

## Exact comparison checklist for the teammate

Ask the teammate to provide these items with credentials and raw proof answers removed:

1. Codex version and binary SHA-256.
2. Exact AGENTS.md and CLI prompt.
3. Exact 20 ordered task IDs or the two split hashes.
4. Verus and Lynette versions and hashes.
5. Provider base URL and model alias.
6. One sanitized Codex Responses request.
7. The translated GLM Chat request after at least one tool call.
8. The corresponding GLM response fields: content, tool_calls, reasoning_content/reasoning, finish_reason, and usage.
9. The synthetic Responses SSE events returned to Codex.
10. Bridge implementation and configuration hashes.
11. Per-task request counts and token breakdown by cache hit/miss/write/output/reasoning.
12. Timeout, retry, max_tokens, thinking, and reasoning-effort settings.

For our completed GLM no-skill arm, the most useful comparison files are:

    ${REFERENCE_RUN_ROOT}/baseline-test-20260819/glm-5.3/no-skill/test/experiment_manifest.json
    ${REFERENCE_RUN_ROOT}/baseline-test-20260819/glm-5.3/no-skill/test/bridge_manifest.json
    ${REFERENCE_RUN_ROOT}/baseline-test-20260819/glm-5.3/no-skill/test/summary.json
    ${REFERENCE_RUN_ROOT}/baseline-test-20260819/glm-5.3/no-skill/test/bridge_calls.jsonl

The bridge implementation used by GLM is:

    ${REFERENCE_REPO_ROOT}/trace2skill_verusage_baseline_test/code/verus_agent/codex_harness/upstream_skillopt/codex_deepseek_bridge.py

The actor runner is:

    ${REFERENCE_REPO_ROOT}/trace2skill_verusage_cross_task_global_skills_20260814/code/run_actor_matrix.py

A separate task-level GLM report is available at:

    ${REFERENCE_RUN_ROOT}/baseline-test-20260819/GLM53_NO_SKILL_EVALUATION_SETUP.md

## Frozen GLM identities

| Artifact | GLM no-skill SHA-256 or identity |
|---|---|
| Actor contract | 628ef5a8170229724ff42004dd396d5d7dc1d12ed3b4c4c979884d449e6edeb0 |
| Actor runner | 86ab7f957c0565166d566628c0c29a6843f9d12ec33c174aaf088ae882d0887c |
| Isolation runner | d2f7d64e936b294e4c4916ac9b39a6040f831efe6529f2aafa1a62aab8bd3015 |
| Bridge implementation | 18dced3a21caf87b643a88f06493aa6da6f4f937573849aa51143c0769d7ada3 |
| Bridge configuration | 2b8d2b2ca70372a5ef80f44abba67315737fe2e35b5cef56a915763bca1cc629 |
| Codex binary | cb0a15567e9a60a5820d54b0f6ae86d504dc3805c1eab21a47f70e3eb7b73a40 |
| Verus binary | c3afe80bbaabc45527a18e490fc124dea9cd79afe8861f698a7cf33c7123178d |
| Lynette binary | bcdd8e1b1fc407bfd415814f2791af91f1ac30c2af9ee0085ae97b4fd38deb11 |

## Limitations

- One run per condition does not estimate run-to-run variance.
- Provider aliases are not immutable model snapshot IDs.
- The completed provider runs were executed at different times, and their recorded bridge source hashes are not all identical because the shared bridge evolved. The GLM diagnosis must use the GLM-specific hashes above.
- DeepSeek/GPT native Responses token fields and GLM/Qwen translated Chat usage fields are not guaranteed to have identical semantics.
- Qwen was FP8 in both weights and KV cache and should not be generalized to BF16 Qwen3.8-27B.
- Tasks 9 and 19 remain fixture-defect failures under the chosen reporting policy.
- The old Verus revision is a material reproduction caveat.

## Recommended next step

Before rerunning either team’s full 20-task GLM arm, perform one matched task smoke using the same source task and capture a sanitized request/response sequence across two tool turns. Diff these four objects:

1. the initial Codex Responses request;
2. the translated first GLM Chat request;
3. the translated second GLM Chat request containing assistant reasoning_content and the tool result;
4. the synthetic Responses SSE returned to Codex.

If those objects match, compare Verus version, provider alias timing, request count, and stochastic variation. If they do not match, fix the bridge difference before interpreting the success-rate gap as a model-performance result.
