#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"
: "${VERUS_BIN:?set VERUS_BIN in .env}"
: "${LYNETTE_BIN:?set LYNETTE_BIN in .env}"
: "${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY in .env}"

PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
CODEX_CLI_BIN="${CODEX_CLI_BIN:-$(command -v codex)}"
export PATH="$(dirname "$CODEX_CLI_BIN"):$PATH"
RUN_NAME="${SKILLOPT_RUN_NAME:-codex-pro-fixed80-e1-600s-20260817-1916}"
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18082}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"
STATE_PATH="$RUN_DIR/runtime_state.json"
RETRY_DIR="$RUN_DIR/slow_update/epoch_02/retry_pointer_top3"
E3_CONFIG="$REPO_ROOT/skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e3_resume_600s.yaml"
E4_CONFIG="$REPO_ROOT/skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e4_resume_600s.yaml"

test -d "$RUN_DIR"
test -d "$SPLIT_DIR"
test -f "$RUN_DIR/models.json"
test -f "$STATE_PATH"
test -f "$RETRY_DIR/slow_result.json"
jq -e '.last_completed_step >= 2 and .last_completed_step <= 4' "$STATE_PATH" >/dev/null
jq -e '.status == "success" and (.result.slow_update_content | length) > 0' \
  "$RETRY_DIR/slow_result.json" >/dev/null

export CODEX_CLI_BIN
export VERUS_BIN LYNETTE_BIN VERUS_SKILL_RUN_ROOT
export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export SKILLOPT_VERUSAGE_OUT_ROOT="$RUN_DIR"
export SKILLOPT_VERUSAGE_SPLIT_DIR="$SPLIT_DIR"
export SKILLOPT_CODEX_BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
export SKILLOPT_CODEX_BRIDGE_LEDGER="$RUN_DIR/bridge_calls.jsonl"
export SKILLOPT_CODEX_BRIDGE_MANIFEST="$RUN_DIR/bridge_manifest_epoch3e4.json"

"$PYTHON_BIN" -m skillopt_verusage.train --config "$E3_CONFIG" --check-only >/dev/null
"$PYTHON_BIN" -m skillopt_verusage.train --config "$E4_CONFIG" --check-only >/dev/null

if [ "${SKILLOPT_PREFLIGHT_ONLY:-0}" = "1" ]; then
  if curl -fsS --max-time 2 "$SKILLOPT_CODEX_BRIDGE_URL/health" >/dev/null 2>&1; then
    echo "bridge port $BRIDGE_PORT is already serving" >&2
    exit 1
  fi
  echo "epoch 2 slow gate plus epoch 3/4 continuation preflight passed"
  exit 0
fi

if curl -fsS --max-time 2 "$SKILLOPT_CODEX_BRIDGE_URL/health" >/dev/null 2>&1; then
  echo "bridge port $BRIDGE_PORT is already serving" >&2
  exit 1
fi

"$PYTHON_BIN" -m skillopt_verusage.cost_ledger --run-root "$RUN_DIR" >/dev/null
jq -n \
  --arg started_at "$(date -u -Is)" \
  --arg run_name "$RUN_NAME" \
  --argjson starting_step "$(jq '.last_completed_step' "$STATE_PATH")" \
  --argjson starting_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_actor_errors "$(jq '.target.error_requests' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_actor_unmetered "$(jq '.target.unmetered_requests' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_optimizer_failed "$(jq '.optimizer.failed_attempts' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_optimizer_unknown "$(jq '.optimizer.unknown_usage_attempts' "$RUN_DIR/cost_ledger.json")" \
  '{
    schema_version: "1",
    continuation: "slow_retry_gate_then_epochs_3_and_4",
    started_at: $started_at,
    run_name: $run_name,
    starting_step: $starting_step,
    starting_actor_cost_usd: $starting_cost,
    historical_accounting_baseline: {
      actor_error_requests: $starting_actor_errors,
      actor_unmetered_requests: $starting_actor_unmetered,
      optimizer_failed_attempts: $starting_optimizer_failed,
      optimizer_unknown_usage_attempts: $starting_optimizer_unknown
    }
  }' >"$RUN_DIR/epoch3e4_continuation_start.json"

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  --native-responses \
  --model deepseek-v4-pro \
  --port "$BRIDGE_PORT" \
  --request-timeout-seconds 540 \
  --expected-upstream-model deepseek-v4-pro \
  --ledger-path "$SKILLOPT_CODEX_BRIDGE_LEDGER" \
  --manifest-path "$SKILLOPT_CODEX_BRIDGE_MANIFEST" \
  --model-catalog-path "$RUN_DIR/models.json" \
  >"$RUN_DIR/bridge_epoch3e4.log" 2>&1 &
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

# Only the bridge retains the provider key. Codex actor and optimizer children
# use the local bridge token or local Codex quota respectively.
unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENAI_API_KEY OPENROUTER_API_KEY
export SKILLOPT_CODEX_BRIDGE_TOKEN=local-bridge-only

"$PYTHON_BIN" -m skillopt_verusage.slow_retry_gate \
  --run-dir "$RUN_DIR" \
  --config "$E3_CONFIG" \
  2>&1 | tee -a "$RUN_DIR/train.log"
jq -e '.status == "complete" and .selection_n == 20' \
  "$RETRY_DIR/gate_result.json" >/dev/null

result_count() {
  local phase_dir="$1"
  if [ ! -d "$phase_dir/predictions" ]; then
    echo 0
    return
  fi
  find "$phase_dir/predictions" -mindepth 1 -maxdepth 1 -type d \
    -exec test -f '{}/result.json' \; -print | wc -l
}

validate_epoch() {
  local epoch="$1"
  local step
  step="$(printf '%04d' "$epoch")"
  local epoch_label
  epoch_label="$(printf '%02d' "$epoch")"
  local train_count gate_count slow_prev_count slow_curr_count slow_gate_count slow_action
  train_count="$(result_count "$RUN_DIR/steps/step_$step/rollout")"
  gate_count="$(result_count "$RUN_DIR/steps/step_$step/selection_eval")"
  slow_prev_count="$(result_count "$RUN_DIR/slow_update/epoch_$epoch_label/rollout_prev")"
  slow_curr_count="$(result_count "$RUN_DIR/slow_update/epoch_$epoch_label/rollout_curr")"
  slow_gate_count="$(result_count "$RUN_DIR/slow_update/epoch_$epoch_label/selection_eval")"
  test "$train_count" -eq 40
  test "$gate_count" -eq 20
  test "$slow_prev_count" -eq 20
  test "$slow_curr_count" -eq 20
  test "$slow_gate_count" -eq 20
  jq -e --argjson epoch "$epoch" '.last_completed_step >= $epoch' "$STATE_PATH" >/dev/null
  jq -e '(.slow_update_content | type) == "string" and (.slow_update_content | length) > 0' \
    "$RUN_DIR/slow_update/epoch_$epoch_label/slow_result.json" >/dev/null
  slow_action="$(jq -r '.action' "$RUN_DIR/slow_update/epoch_$epoch_label/slow_result.json")"
  case "$slow_action" in
    accept|accept_new_best|reject) ;;
    *) echo "invalid epoch $epoch slow gate action: $slow_action" >&2; return 1 ;;
  esac
  "$PYTHON_BIN" -m skillopt_verusage.cost_ledger --run-root "$RUN_DIR" >/dev/null
  jq -e --slurpfile start "$RUN_DIR/epoch3e4_continuation_start.json" '
    .target.error_requests == $start[0].historical_accounting_baseline.actor_error_requests and
    .target.unmetered_requests == $start[0].historical_accounting_baseline.actor_unmetered_requests and
    .optimizer.failed_attempts == $start[0].historical_accounting_baseline.optimizer_failed_attempts and
    .optimizer.unknown_usage_attempts == $start[0].historical_accounting_baseline.optimizer_unknown_usage_attempts
  ' "$RUN_DIR/cost_ledger.json" >/dev/null
  jq -n \
    --argjson epoch "$epoch" \
    --arg validated_at "$(date -u -Is)" \
    --arg slow_action "$slow_action" \
    --argjson train "$train_count" \
    --argjson gate "$gate_count" \
    --argjson slow_prev "$slow_prev_count" \
    --argjson slow_curr "$slow_curr_count" \
    --argjson slow_gate "$slow_gate_count" \
    --argjson total_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
    '{
      schema_version: "1",
      status: "pass",
      epoch: $epoch,
      validated_at: $validated_at,
      actor_task_counts: {
        train: $train,
        gate: $gate,
        slow_prev: $slow_prev,
        slow_curr: $slow_curr,
        slow_gate: $slow_gate
      },
      slow_action: $slow_action,
      total_actor_cost_usd: $total_cost
    }' >"$RUN_DIR/epoch${epoch}_continuation_validation.json"
}

"$PYTHON_BIN" -m skillopt_verusage.train --config "$E3_CONFIG" \
  2>&1 | tee -a "$RUN_DIR/train.log"
validate_epoch 3

"$PYTHON_BIN" -m skillopt_verusage.train --config "$E4_CONFIG" \
  2>&1 | tee -a "$RUN_DIR/train.log"
validate_epoch 4

jq -n \
  --arg completed_at "$(date -u -Is)" \
  --argjson last_step "$(jq '.last_completed_step' "$STATE_PATH")" \
  --argjson best_score "$(jq '.best_score' "$STATE_PATH")" \
  --argjson total_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_cost "$(jq '.starting_actor_cost_usd' "$RUN_DIR/epoch3e4_continuation_start.json")" \
  '{
    schema_version: "1",
    status: "complete",
    completed_at: $completed_at,
    last_completed_step: $last_step,
    best_selection_hard: $best_score,
    total_actor_cost_usd: $total_cost,
    continuation_actor_cost_usd: ($total_cost - $starting_cost)
  }' >"$RUN_DIR/epoch3e4_continuation_complete.json"
