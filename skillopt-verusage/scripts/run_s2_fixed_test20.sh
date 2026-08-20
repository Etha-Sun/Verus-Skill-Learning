#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 || "$#" -gt 2 ]]; then
  echo "usage: $0 {gpt|deepseek|glm|qwen} {blank|s2}" >&2
  exit 2
fi

CONDITION="$1"
SKILL_VARIANT="${2:-s2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"
: "${VERUS_BIN:?set VERUS_BIN in .env}"
: "${LYNETTE_BIN:?set LYNETTE_BIN in .env}"

PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
CODEX_CLI_BIN="${CODEX_CLI_BIN:-$(command -v codex)}"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"
case "$SKILL_VARIANT" in
  blank)
    SKILL_FILE="$REPO_ROOT/skillopt-verusage/skills/blank.md"
    EXPECTED_SKILL_SHA256="01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"
    ;;
  s2)
    SKILL_FILE="${SKILLOPT_S2_SKILL_FILE:-$VERUS_SKILL_RUN_ROOT/skillopt-verusage/codex-pro-fixed80-e1-600s-20260817-1916/best_skill.md}"
    EXPECTED_SKILL_SHA256="1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e"
    ;;
  *)
    echo "unknown skill variant: $SKILL_VARIANT" >&2
    exit 2
    ;;
esac
: "${SKILLOPT_MODEL_CATALOG_PATH:?set SKILLOPT_MODEL_CATALOG_PATH in .env}"
BASE_CATALOG="$SKILLOPT_MODEL_CATALOG_PATH"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_NAME="${SKILLOPT_TEST_RUN_NAME:-fixed-test20-${CONDITION}-${SKILL_VARIANT}-${STAMP}}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18083}"
BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
WORKERS="${SKILLOPT_TEST_WORKERS:-4}"
if ! [[ "$WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "SKILLOPT_TEST_WORKERS must be a positive integer" >&2
  exit 2
fi

export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export VERUS_SKILL_RUN_ROOT VERUS_BIN LYNETTE_BIN

if [[ "$CONDITION" == "gpt" ]]; then
  unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
  unset OPENAI_API_KEY OPENROUTER_API_KEY ZAI_API_KEY QWEN_LOCAL_API_KEY
  exec "$PYTHON_BIN" -m skillopt_verusage.test_eval \
    --run-dir "$RUN_DIR" \
    --split-dir "$SPLIT_DIR" \
    --skill-file "$SKILL_FILE" \
    --skill-label "$SKILL_VARIANT" \
    --expected-skill-sha256 "$EXPECTED_SKILL_SHA256" \
    --codex-bin "$CODEX_CLI_BIN" \
    --verus-bin "$VERUS_BIN" \
    --lynette-bin "$LYNETTE_BIN" \
    --transport direct \
    --model gpt-5.6-sol \
    --reasoning-effort max \
    --workers "$WORKERS" \
    --timeout-seconds 600 \
    --model-context-window 262144
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
MAX_OUTPUT_TOKENS=65536
RETRY_OUTPUT_TOKENS=65536

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
    ;;
  glm)
    : "${ZAI_API_KEY:?set ZAI_API_KEY in .env}"
    MODEL="glm-5.3"
    DISPLAY_NAME="GLM-5.3"
    UPSTREAM_BASE_URL="${ZAI_BASE_URL:-https://api.z.ai/api/paas/v4}"
    API_KEY_ENV="ZAI_API_KEY"
    CHAT_PROFILE="glm"
    PRICING_PROFILE="zai-glm-5.3-20260819"
    RATE_LIMIT_FLAGS=(
      --rate-limit-retries 12
      --rate-limit-backoff-seconds 1
      --rate-limit-max-backoff-seconds 30
    )
    ;;
  qwen)
    MODEL="qwen3.8-27b"
    DISPLAY_NAME="Qwen3.8-27B"
    UPSTREAM_BASE_URL="${QWEN_VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
    API_KEY_ENV="QWEN_LOCAL_API_KEY"
    export QWEN_LOCAL_API_KEY="${QWEN_LOCAL_API_KEY:-local-qwen-only}"
    CHAT_PROFILE="qwen38"
    PRICING_PROFILE="local-zero"
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

mkdir "$RUN_DIR"
"$PYTHON_BIN" "$SCRIPT_DIR/prepare_codex_model_catalog.py" \
  --input "$BASE_CATALOG" \
  --output "$RUN_DIR/models.json" \
  --slug "$MODEL" \
  --display-name "$DISPLAY_NAME" \
  --context-window "$CONTEXT_WINDOW" \
  --default-reasoning-level max

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  "${NATIVE_FLAG[@]}" \
  "${RATE_LIMIT_FLAGS[@]}" \
  --model "$MODEL" \
  --port "$BRIDGE_PORT" \
  --upstream-base-url "$UPSTREAM_BASE_URL" \
  --api-key-env "$API_KEY_ENV" \
  --chat-profile "$CHAT_PROFILE" \
  --pricing-profile "$PRICING_PROFILE" \
  --max-output-tokens "$MAX_OUTPUT_TOKENS" \
  --retry-output-tokens "$RETRY_OUTPUT_TOKENS" \
  --request-timeout-seconds 540 \
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
  --skill-file "$SKILL_FILE" \
  --skill-label "$SKILL_VARIANT" \
  --expected-skill-sha256 "$EXPECTED_SKILL_SHA256" \
  --codex-bin "$CODEX_CLI_BIN" \
  --verus-bin "$VERUS_BIN" \
  --lynette-bin "$LYNETTE_BIN" \
  --transport bridge \
  --bridge-url "$BRIDGE_URL" \
  --bridge-ledger "$RUN_DIR/bridge_calls.jsonl" \
  --bridge-manifest "$RUN_DIR/bridge_manifest.json" \
  --model "$MODEL" \
  --reasoning-effort max \
  --workers "$WORKERS" \
  --timeout-seconds 600 \
  --model-context-window "$CONTEXT_WINDOW" \
  2>&1 | tee "$RUN_DIR/test.log"
