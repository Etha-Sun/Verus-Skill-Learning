#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"
: "${VERUS_BIN:?set VERUS_BIN in .env}"
: "${LYNETTE_BIN:?set LYNETTE_BIN in .env}"
: "${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY in .env}"
: "${SKILLOPT_MODEL_CATALOG_PATH:?point to the reviewed Codex models.json}"
"$REPO_ROOT/skillopt-verusage/scripts/bootstrap_skillopt.sh" >/dev/null

PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
CODEX_CLI_BIN="${CODEX_CLI_BIN:-$(command -v codex)}"
RUN_NAME="${SKILLOPT_RUN_NAME:-codex-pro-fixed80-e1-600s-20260817}"
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18081}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"

mkdir "$RUN_DIR"
cp "$SKILLOPT_MODEL_CATALOG_PATH" "$RUN_DIR/models.json"

export CODEX_CLI_BIN
export VERUS_BIN LYNETTE_BIN VERUS_SKILL_RUN_ROOT
export DEEPSEEK_API_KEY
export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export SKILLOPT_VERUSAGE_OUT_ROOT="$RUN_DIR"
export SKILLOPT_VERUSAGE_SPLIT_DIR="$SPLIT_DIR"
export SKILLOPT_CODEX_BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
export SKILLOPT_CODEX_BRIDGE_LEDGER="$RUN_DIR/bridge_calls.jsonl"
export SKILLOPT_CODEX_BRIDGE_MANIFEST="$RUN_DIR/bridge_manifest.json"

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  --native-responses \
  --model deepseek-v4-pro \
  --port "$BRIDGE_PORT" \
  --request-timeout-seconds 540 \
  --expected-upstream-model deepseek-v4-pro \
  --ledger-path "$SKILLOPT_CODEX_BRIDGE_LEDGER" \
  --manifest-path "$SKILLOPT_CODEX_BRIDGE_MANIFEST" \
  --model-catalog-path "$RUN_DIR/models.json" \
  >"$RUN_DIR/bridge.log" 2>&1 &
BRIDGE_PID=$!

cleanup() {
  kill "$BRIDGE_PID" 2>/dev/null || true
  wait "$BRIDGE_PID" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$SKILLOPT_CODEX_BRIDGE_URL/health" >/dev/null; then
    break
  fi
  if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
    echo "bridge exited before readiness" >&2
    exit 1
  fi
  sleep 1
done
curl -fsS "$SKILLOPT_CODEX_BRIDGE_URL/health" >/dev/null

# The bridge child inherited the real key. Actor and optimizer subprocesses do not.
unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENAI_API_KEY OPENROUTER_API_KEY
export SKILLOPT_CODEX_BRIDGE_TOKEN=local-bridge-only

"$PYTHON_BIN" -m skillopt_verusage.train \
  --config "$REPO_ROOT/skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e1_600s.yaml" \
  2>&1 | tee "$RUN_DIR/train.log"
