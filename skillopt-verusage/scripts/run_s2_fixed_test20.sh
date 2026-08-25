#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 || "$#" -gt 3 ]]; then
  echo "usage: $0 {gpt|deepseek|glm|qwen} {blank|s1|s2|trace2skill} [skill-file-or-dir]" >&2
  exit 2
fi

CONDITION="$1"
SKILL_VARIANT="${2:-s2}"
EXTERNAL_SKILL_PATH="${3:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"
: "${VERUS_BIN:?set VERUS_BIN in .env}"
: "${LYNETTE_BIN:?set LYNETTE_BIN in .env}"
"$REPO_ROOT/skillopt-verusage/scripts/bootstrap_skillopt.sh" >/dev/null

PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
CODEX_CLI_BIN="${CODEX_CLI_BIN:-$(command -v codex)}"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"
SKILL_LABEL="$SKILL_VARIANT"
SKILL_INPUT_FLAGS=()
case "$SKILL_VARIANT" in
  blank)
    SKILL_FILE="$REPO_ROOT/skillopt-verusage/skills/blank.md"
    EXPECTED_SKILL_SHA256="01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"
    SKILL_INPUT_FLAGS=(--skill-file "$SKILL_FILE")
    ;;
  s1)
    SKILL_FILE="${SKILLOPT_S1_SKILL_FILE:-$VERUS_SKILL_RUN_ROOT/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/steps/step_0001/candidate_skill.md}"
    EXPECTED_SKILL_SHA256="fb4584310c22fcd030b7a2def19ccbf4777046e15d3ca136a55c477c7a8065ab"
    SKILL_INPUT_FLAGS=(--skill-file "$SKILL_FILE")
    ;;
  s2)
    SKILL_FILE="${SKILLOPT_S2_SKILL_FILE:-$VERUS_SKILL_RUN_ROOT/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/best_skill.md}"
    EXPECTED_SKILL_SHA256="1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e"
    SKILL_INPUT_FLAGS=(--skill-file "$SKILL_FILE")
    ;;
  trace2skill)
    if [[ -z "$EXTERNAL_SKILL_PATH" ]]; then
      echo "trace2skill requires a SKILL.md file or skill bundle directory" >&2
      exit 2
    fi
    SKILL_LABEL="${SKILLOPT_EXTERNAL_SKILL_LABEL:-trace2skill}"
    if ! [[ "$SKILL_LABEL" =~ ^[A-Za-z0-9._-]+$ ]]; then
      echo "SKILLOPT_EXTERNAL_SKILL_LABEL contains unsafe characters" >&2
      exit 2
    fi
    if [[ "$SKILL_LABEL" == "blank" ]]; then
      echo "SKILLOPT_EXTERNAL_SKILL_LABEL must not disable skill injection" >&2
      exit 2
    fi
    EXPECTED_SKILL_SHA256="$(
      PYTHONPATH="$REPO_ROOT/skillopt-verusage/src" \
        "$PYTHON_BIN" -m skillopt_verusage.skill_artifact "$EXTERNAL_SKILL_PATH"
    )"
    if [[ -d "$EXTERNAL_SKILL_PATH" ]]; then
      SKILL_INPUT_FLAGS=(--skill-dir "$EXTERNAL_SKILL_PATH")
    elif [[ -f "$EXTERNAL_SKILL_PATH" ]]; then
      SKILL_INPUT_FLAGS=(--skill-file "$EXTERNAL_SKILL_PATH")
    else
      echo "trace2skill artifact does not exist: $EXTERNAL_SKILL_PATH" >&2
      exit 2
    fi
    ;;
  *)
    echo "unknown skill variant: $SKILL_VARIANT" >&2
    exit 2
    ;;
esac
if [[ "$SKILL_VARIANT" != "trace2skill" && -n "$EXTERNAL_SKILL_PATH" ]]; then
  echo "the third argument is only valid for trace2skill" >&2
  exit 2
fi
: "${SKILLOPT_MODEL_CATALOG_PATH:?set SKILLOPT_MODEL_CATALOG_PATH in .env}"
BASE_CATALOG="$SKILLOPT_MODEL_CATALOG_PATH"
if [[ -n "${SKILLOPT_ACTOR_PROFILE:-}" ]]; then
  ACTOR_PROFILE="$SKILLOPT_ACTOR_PROFILE"
elif [[ "$CONDITION" == "glm" || "$CONDITION" == "qwen" ]]; then
  ACTOR_PROFILE="cross_provider_20260819"
else
  ACTOR_PROFILE="project"
fi
if [[ "$ACTOR_PROFILE" != "project" && "$ACTOR_PROFILE" != "cross_provider_20260819" ]]; then
  echo "unknown actor profile: $ACTOR_PROFILE" >&2
  exit 2
fi
EVAL_VERUS_BIN="${SKILLOPT_EVAL_VERUS_BIN:-$VERUS_BIN}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_NAME="${SKILLOPT_TEST_RUN_NAME:-fixed-test20-${CONDITION}-${SKILL_LABEL}-${STAMP}}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18083}"
BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
if [[ -n "${SKILLOPT_TEST_WORKERS:-}" ]]; then
  WORKERS="$SKILLOPT_TEST_WORKERS"
elif [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
  WORKERS=1
elif [[ "$CONDITION" == "glm" || "$CONDITION" == "qwen" ]]; then
  if [[ "$CONDITION" == "qwen" ]]; then
    WORKERS=4
  else
    WORKERS=2
  fi
else
  WORKERS=4
fi
if ! [[ "$WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "SKILLOPT_TEST_WORKERS must be a positive integer" >&2
  exit 2
fi
ITEM_FLAGS=()
CHECK_ONLY_FLAGS=()
if [[ "${SKILLOPT_CHECK_ONLY:-0}" == "1" ]]; then
  CHECK_ONLY_FLAGS=(--check-only)
fi
if [[ -n "${SKILLOPT_TEST_ITEM_IDS:-}" ]]; then
  IFS=',' read -r -a ITEM_IDS <<<"$SKILLOPT_TEST_ITEM_IDS"
  for ITEM_ID in "${ITEM_IDS[@]}"; do
    ITEM_FLAGS+=(--item-id "$ITEM_ID")
  done
fi

export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export VERUS_SKILL_RUN_ROOT VERUS_BIN LYNETTE_BIN

if [[ "$CONDITION" == "gpt" ]]; then
  GPT_CONTEXT_WINDOW=262144
  if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
    GPT_CONTEXT_WINDOW=1048576
  fi
  unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
  unset OPENAI_API_KEY OPENROUTER_API_KEY ZAI_API_KEY QWEN_LOCAL_API_KEY
  exec "$PYTHON_BIN" -m skillopt_verusage.test_eval \
    --run-dir "$RUN_DIR" \
    --split-dir "$SPLIT_DIR" \
    "${SKILL_INPUT_FLAGS[@]}" \
    --skill-label "$SKILL_LABEL" \
    --expected-skill-sha256 "$EXPECTED_SKILL_SHA256" \
    --codex-bin "$CODEX_CLI_BIN" \
    --verus-bin "$EVAL_VERUS_BIN" \
    --lynette-bin "$LYNETTE_BIN" \
    --transport direct \
    --model gpt-5.6-sol \
    --reasoning-effort max \
    --workers "$WORKERS" \
    --timeout-seconds 600 \
    --model-context-window "$GPT_CONTEXT_WINDOW" \
    --actor-contract-profile "$ACTOR_PROFILE" \
    --codex-provider-id openai \
    "${CHECK_ONLY_FLAGS[@]}" \
    "${ITEM_FLAGS[@]}"
fi

MODEL=""
DISPLAY_NAME=""
UPSTREAM_BASE_URL=""
API_KEY_ENV=""
CHAT_PROFILE=""
PRICING_PROFILE=""
CONTEXT_WINDOW=262144
NATIVE_FLAG=()
RATE_LIMIT_FLAGS=()
ALLOWED_TOOL_FLAGS=()
MAX_OUTPUT_TOKENS=65536
RETRY_OUTPUT_TOKENS=65536
REQUEST_TIMEOUT_SECONDS=540
REASONING_EFFORT=max
CODEX_PROVIDER_ID="${CONDITION}_bridge"

if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
  MAX_OUTPUT_TOKENS=8192
  RETRY_OUTPUT_TOKENS=131072
  REQUEST_TIMEOUT_SECONDS=1800
  if [[ "$CONDITION" != "qwen" ]]; then
    CONTEXT_WINDOW=1048576
  fi
fi

case "$CONDITION" in
  deepseek)
    : "${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY in .env}"
    MODEL="deepseek-v4-pro"
    DISPLAY_NAME="DeepSeek V4 Pro"
    UPSTREAM_BASE_URL="https://api.deepseek.com"
    API_KEY_ENV="DEEPSEEK_API_KEY"
    CHAT_PROFILE="deepseek"
    PRICING_PROFILE="deepseek-current"
    NATIVE_FLAG=(--native-responses)
    if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
      REASONING_EFFORT=high
    fi
    ;;
  glm)
    : "${ZAI_API_KEY:?set ZAI_API_KEY in .env}"
    MODEL="glm-5.3"
    DISPLAY_NAME="GLM-5.3"
    UPSTREAM_BASE_URL="${ZAI_BASE_URL:-https://api.z.ai/api/paas/v4}"
    API_KEY_ENV="ZAI_API_KEY"
    CHAT_PROFILE="glm"
    PRICING_PROFILE="zai-glm-5.3-20260819"
    CONTEXT_WINDOW=1048576
    CODEX_PROVIDER_ID="glm"
    RATE_LIMIT_FLAGS=(
      --rate-limit-retries 12
      --rate-limit-backoff-seconds 1
      --rate-limit-max-backoff-seconds 30
    )
    if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
      ALLOWED_TOOL_FLAGS=(--allowed-tool exec_command --allowed-tool write_stdin)
    fi
    ;;
  qwen)
    MODEL="${QWEN_LOCAL_MODEL:-qwen38-27b-bf16}"
    DISPLAY_NAME="Qwen3.8-27B BF16"
    UPSTREAM_BASE_URL="${QWEN_VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
    API_KEY_ENV="QWEN_LOCAL_API_KEY"
    export QWEN_LOCAL_API_KEY="${QWEN_LOCAL_API_KEY:-local-qwen-only}"
    CHAT_PROFILE="qwen38"
    PRICING_PROFILE="local-zero"
    REASONING_EFFORT=xhigh
    CODEX_PROVIDER_ID="qwen_local"
    if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]; then
      ALLOWED_TOOL_FLAGS=(--allowed-tool exec_command --allowed-tool write_stdin)
    fi
    curl -fsS \
      -H "Authorization: Bearer $QWEN_LOCAL_API_KEY" \
      "${UPSTREAM_BASE_URL%/v1}/v1/models" >/dev/null
    ;;
  *)
    echo "unknown condition: $CONDITION" >&2
    exit 2
    ;;
esac

export "$API_KEY_ENV"

ACTOR_ISOLATION_FLAGS=()
if [[ "${SKILLOPT_ACTOR_ISOLATION:-1}" == "1" ]]; then
  ACTOR_SCRATCH_ROOT="${VERUS_SKILL_SCRATCH_ROOT:-$(dirname "$REPO_ROOT")}"
  ACTOR_VERUS_ROOT="${SKILLOPT_ACTOR_VERUS_ROOT:-$(dirname "$(dirname "$EVAL_VERUS_BIN")")}"
  if [[ -n "${SKILLOPT_ACTOR_RUST_ROOT:-}" ]]; then
    ACTOR_RUST_ROOT="$SKILLOPT_ACTOR_RUST_ROOT"
  elif [[ -n "${CARGO_HOME:-}" && -d "$(dirname "$CARGO_HOME")/rustup" ]]; then
    ACTOR_RUST_ROOT="$(dirname "$CARGO_HOME")"
  else
    ACTOR_RUST_ROOT="$(rustc --print sysroot)"
  fi
  ACTOR_ISOLATION_FLAGS=(
    --actor-isolation-scratch-root "$ACTOR_SCRATCH_ROOT"
    --actor-isolation-verus-root "$ACTOR_VERUS_ROOT"
    --actor-isolation-rust-root "$ACTOR_RUST_ROOT"
    --actor-isolation-forbidden-path "$REPO_ROOT"
    --actor-isolation-forbidden-path "$SPLIT_DIR"
  )
elif [[ "${SKILLOPT_ACTOR_ISOLATION}" != "0" ]]; then
  echo "SKILLOPT_ACTOR_ISOLATION must be 0 or 1" >&2
  exit 2
fi

mkdir "$RUN_DIR"
"$PYTHON_BIN" "$SCRIPT_DIR/prepare_codex_model_catalog.py" \
  --input "$BASE_CATALOG" \
  --output "$RUN_DIR/models.json" \
  --slug "$MODEL" \
  --display-name "$DISPLAY_NAME" \
  --context-window "$CONTEXT_WINDOW" \
  --default-reasoning-level "$REASONING_EFFORT"

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  "${NATIVE_FLAG[@]}" \
  "${RATE_LIMIT_FLAGS[@]}" \
  "${ALLOWED_TOOL_FLAGS[@]}" \
  --model "$MODEL" \
  --port "$BRIDGE_PORT" \
  --upstream-base-url "$UPSTREAM_BASE_URL" \
  --api-key-env "$API_KEY_ENV" \
  --chat-profile "$CHAT_PROFILE" \
  --pricing-profile "$PRICING_PROFILE" \
  --max-output-tokens "$MAX_OUTPUT_TOKENS" \
  --retry-output-tokens "$RETRY_OUTPUT_TOKENS" \
  --request-timeout-seconds "$REQUEST_TIMEOUT_SECONDS" \
  --expected-upstream-model "$MODEL" \
  --ledger-path "$RUN_DIR/bridge_calls.jsonl" \
  --manifest-path "$RUN_DIR/bridge_manifest.json" \
  --model-catalog-path "$RUN_DIR/models.json" \
  >"$RUN_DIR/bridge.log" 2>&1 &
BRIDGE_PID=$!

cleanup() {
  kill "$BRIDGE_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$BRIDGE_URL/health" >/dev/null; then
    break
  fi
  if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    echo "bridge exited before readiness" >&2
    exit 1
  fi
  sleep 1
done
curl -fsS "$BRIDGE_URL/health" >/dev/null

unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENAI_API_KEY OPENROUTER_API_KEY ZAI_API_KEY QWEN_LOCAL_API_KEY
export SKILLOPT_CODEX_BRIDGE_TOKEN=local-bridge-only

"$PYTHON_BIN" -m skillopt_verusage.test_eval \
  --run-dir "$RUN_DIR" \
  --split-dir "$SPLIT_DIR" \
  "${SKILL_INPUT_FLAGS[@]}" \
  --skill-label "$SKILL_LABEL" \
  --expected-skill-sha256 "$EXPECTED_SKILL_SHA256" \
  --codex-bin "$CODEX_CLI_BIN" \
  --verus-bin "$EVAL_VERUS_BIN" \
  --lynette-bin "$LYNETTE_BIN" \
  --transport bridge \
  --bridge-url "$BRIDGE_URL" \
  --bridge-ledger "$RUN_DIR/bridge_calls.jsonl" \
  --bridge-manifest "$RUN_DIR/bridge_manifest.json" \
  --model "$MODEL" \
  --reasoning-effort "$REASONING_EFFORT" \
  --workers "$WORKERS" \
  --timeout-seconds 600 \
  --model-context-window "$CONTEXT_WINDOW" \
  --actor-contract-profile "$ACTOR_PROFILE" \
  --codex-provider-id "$CODEX_PROVIDER_ID" \
  "${ACTOR_ISOLATION_FLAGS[@]}" \
  "${CHECK_ONLY_FLAGS[@]}" \
  "${ITEM_FLAGS[@]}" \
  2>&1 | tee "$RUN_DIR/test.log"
