#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"
: "${VERUS_BIN:?set VERUS_BIN in .env}"
: "${LYNETTE_BIN:?set LYNETTE_BIN in .env}"
: "${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY in .env}"
"$REPO_ROOT/skillopt-verusage/scripts/bootstrap_skillopt.sh" >/dev/null

PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
CODEX_CLI_BIN="${CODEX_CLI_BIN:-$(command -v codex)}"
RUN_NAME="${SKILLOPT_RUN_NAME:-codex-pro-fixed80-e1-600s-20260817-1916}"
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18081}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"
STATE_PATH="$RUN_DIR/runtime_state.json"
START_PATH="$RUN_DIR/epoch2_resume_start.json"

test -d "$RUN_DIR"
test -f "$RUN_DIR/models.json"
test -f "$RUN_DIR/best_skill.md"
test -f "$RUN_DIR/cost_ledger.json"
test -f "$STATE_PATH"
test -f "$RUN_DIR/slow_update/epoch_01/slow_result.json"

jq -e '
  .last_completed_step == 1 and
  .current_score == 0.7 and
  .best_score == 0.7 and
  .best_step == 1
' "$STATE_PATH" >/dev/null

if [ -e "$RUN_DIR/steps/step_0002" ] || [ -e "$START_PATH" ]; then
  echo "epoch 2 has already started; refusing a duplicate launch" >&2
  exit 1
fi
if curl -fsS --max-time 2 "http://127.0.0.1:$BRIDGE_PORT/health" >/dev/null 2>&1; then
  echo "bridge port $BRIDGE_PORT is already serving" >&2
  exit 1
fi

if [ "${SKILLOPT_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "epoch 2 resume preflight passed"
  exit 0
fi

cp -n "$RUN_DIR/summary.json" "$RUN_DIR/summary_epoch1.json"
cp -n "$RUN_DIR/config.json" "$RUN_DIR/config_epoch1.json"
cp -n "$RUN_DIR/cost_ledger.json" "$RUN_DIR/cost_ledger_epoch1.json"
mv "$RUN_DIR/formal_epoch_validation.json" \
  "$RUN_DIR/formal_epoch_validation_epoch1.json"
cp -n "$RUN_DIR/bridge_manifest.json" "$RUN_DIR/bridge_manifest_epoch1.json"

jq -n \
  --arg started_at "$(date -u -Is)" \
  --arg run_name "$RUN_NAME" \
  --argjson starting_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_requests "$(jq '.target.requests' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_prompt "$(jq '.target.prompt_tokens' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_completion "$(jq '.target.completion_tokens' "$RUN_DIR/cost_ledger.json")" \
  '{
    schema_version: "1",
    continuation: "epoch_2",
    started_at: $started_at,
    run_name: $run_name,
    starting_actor: {
      estimated_cost_usd: $starting_cost,
      requests: $starting_requests,
      prompt_tokens: $starting_prompt,
      completion_tokens: $starting_completion
    }
  }' >"$START_PATH"

export CODEX_CLI_BIN
export VERUS_BIN LYNETTE_BIN VERUS_SKILL_RUN_ROOT
export DEEPSEEK_API_KEY
export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export SKILLOPT_VERUSAGE_OUT_ROOT="$RUN_DIR"
export SKILLOPT_VERUSAGE_SPLIT_DIR="$SPLIT_DIR"
export SKILLOPT_CODEX_BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
export SKILLOPT_CODEX_BRIDGE_LEDGER="$RUN_DIR/bridge_calls.jsonl"
export SKILLOPT_CODEX_BRIDGE_MANIFEST="$RUN_DIR/bridge_manifest_epoch2.json"

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  --native-responses \
  --model deepseek-v4-pro \
  --port "$BRIDGE_PORT" \
  --request-timeout-seconds 540 \
  --expected-upstream-model deepseek-v4-pro \
  --ledger-path "$SKILLOPT_CODEX_BRIDGE_LEDGER" \
  --manifest-path "$SKILLOPT_CODEX_BRIDGE_MANIFEST" \
  --model-catalog-path "$RUN_DIR/models.json" \
  >"$RUN_DIR/bridge_epoch2.log" 2>&1 &
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
curl -fsS "$SKILLOPT_CODEX_BRIDGE_URL/health" \
  | jq -e '.model == "deepseek-v4-pro" and .active_requests == 0' >/dev/null

# The bridge child inherited the real key. Actor and optimizer subprocesses do not.
unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENAI_API_KEY OPENROUTER_API_KEY
export SKILLOPT_CODEX_BRIDGE_TOKEN=local-bridge-only

"$PYTHON_BIN" -m skillopt_verusage.train \
  --config "$REPO_ROOT/skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e2_resume_600s.yaml" \
  2>&1 | tee -a "$RUN_DIR/train.log"

jq -e '.last_completed_step == 2' "$STATE_PATH" >/dev/null

result_count() {
  find "$1/predictions" -mindepth 1 -maxdepth 1 -type d \
    -exec test -f '{}/result.json' \; -print | wc -l
}

TRAIN_COUNT="$(result_count "$RUN_DIR/steps/step_0002/rollout")"
GATE_COUNT="$(result_count "$RUN_DIR/steps/step_0002/selection_eval")"
if [ "$TRAIN_COUNT" -ne 40 ] || [ "$GATE_COUNT" -ne 20 ]; then
  echo "epoch 2 core schedule incomplete: train=$TRAIN_COUNT gate=$GATE_COUNT" >&2
  exit 1
fi

jq -n \
  --arg completed_at "$(date -u -Is)" \
  --argjson last_step "$(jq '.last_completed_step' "$STATE_PATH")" \
  --argjson best_score "$(jq '.best_score' "$STATE_PATH")" \
  --argjson train_count "$TRAIN_COUNT" \
  --argjson gate_count "$GATE_COUNT" \
  --argjson total_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_cost "$(jq '.starting_actor.estimated_cost_usd' "$START_PATH")" \
  '{
    schema_version: "1",
    continuation: "epoch_2",
    completed_at: $completed_at,
    last_completed_step: $last_step,
    best_score: $best_score,
    actor_task_counts: {
      train: $train_count,
      candidate_selection: $gate_count
    },
    total_actor_cost_usd: $total_cost,
    epoch2_incremental_actor_cost_usd: ($total_cost - $starting_cost)
  }' >"$RUN_DIR/epoch2_resume_complete.json"
