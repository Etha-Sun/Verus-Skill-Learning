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
BRIDGE_PORT="${SKILLOPT_BRIDGE_PORT:-18084}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
SPLIT_DIR="$REPO_ROOT/fixed-claude-stratified-80-seed20260814"
REPAIR_DIR="$RUN_DIR/optimizer_repairs/epoch_03_missing_fail_000_pointer_top3"
STATE_PATH="$RUN_DIR/runtime_state.json"
E4_CONFIG="$REPO_ROOT/skillopt-verusage/configs/verusage_codex_pro_sol_fixed80_e4_resume_600s.yaml"
START_PATH="$RUN_DIR/epoch4_after_reflect_repair_start.json"

test -d "$RUN_DIR"
test -d "$SPLIT_DIR"
test -f "$RUN_DIR/models.json"
test -f "$STATE_PATH"
test -f "$REPAIR_DIR/gate_result.json"
jq -e '
  .last_completed_step == 3 and
  .current_score == 0.75 and
  .best_score == 0.75
' "$STATE_PATH" >/dev/null
jq -e '
  .status == "complete" and
  .candidate_solved == 14 and
  .current_solved == 15 and
  .canonical_checkpoint_updated == false and
  .accounting_complete == true
' "$REPAIR_DIR/gate_result.json" >/dev/null
test "$(sha256sum "$RUN_DIR/best_skill.md" | awk '{print $1}')" = \
  "1549611562e38c6dcb75d0b18bdf081434c431c5d7d6659a3411f8cbc540d96e"

export CODEX_CLI_BIN
export VERUS_BIN LYNETTE_BIN VERUS_SKILL_RUN_ROOT
export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"
export SKILLOPT_VERUSAGE_OUT_ROOT="$RUN_DIR"
export SKILLOPT_VERUSAGE_SPLIT_DIR="$SPLIT_DIR"
export SKILLOPT_CODEX_BRIDGE_URL="http://127.0.0.1:$BRIDGE_PORT"
export SKILLOPT_CODEX_BRIDGE_LEDGER="$RUN_DIR/bridge_calls.jsonl"
export SKILLOPT_CODEX_BRIDGE_MANIFEST="$RUN_DIR/bridge_manifest_epoch4_reflect_repair.json"

"$REPO_ROOT/skillopt-verusage/scripts/bootstrap_skillopt.sh" >/dev/null
"$PYTHON_BIN" -m skillopt_verusage.train --config "$E4_CONFIG" --check-only >/dev/null
"$PYTHON_BIN" -m pytest -q \
  "$REPO_ROOT/skillopt-verusage/tests/test_upstream_path_references.py" \
  >/dev/null

if curl -fsS --max-time 2 "$SKILLOPT_CODEX_BRIDGE_URL/health" >/dev/null 2>&1; then
  echo "bridge port $BRIDGE_PORT is already serving" >&2
  exit 1
fi

"$PYTHON_BIN" -m skillopt_verusage.cost_ledger --run-root "$RUN_DIR" >/dev/null
if [ -f "$START_PATH" ]; then
  jq -e '
    .schema_version == "1" and
    .continuation == "epoch_4_after_reflect_pointer_repair" and
    .starting_step == 3
  ' "$START_PATH" >/dev/null
else
  jq -n \
    --arg started_at "$(date -u -Is)" \
    --arg run_name "$RUN_NAME" \
    --arg repair_dir "$REPAIR_DIR" \
    --argjson starting_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
    --argjson starting_actor_errors "$(jq '.target.error_requests' "$RUN_DIR/cost_ledger.json")" \
    --argjson starting_actor_unmetered "$(jq '.target.unmetered_requests' "$RUN_DIR/cost_ledger.json")" \
    --argjson starting_optimizer_failed "$(jq '.optimizer.failed_attempts' "$RUN_DIR/cost_ledger.json")" \
    --argjson starting_optimizer_unknown "$(jq '.optimizer.unknown_usage_attempts' "$RUN_DIR/cost_ledger.json")" \
    '{
      schema_version: "1",
      continuation: "epoch_4_after_reflect_pointer_repair",
      started_at: $started_at,
      run_name: $run_name,
      repair_artifact: $repair_dir,
      starting_step: 3,
      starting_actor_cost_usd: $starting_cost,
      historical_accounting_baseline: {
        actor_error_requests: $starting_actor_errors,
        actor_unmetered_requests: $starting_actor_unmetered,
        optimizer_failed_attempts: $starting_optimizer_failed,
        optimizer_unknown_usage_attempts: $starting_optimizer_unknown
      }
    }' >"$START_PATH"
fi

"$PYTHON_BIN" -m skillopt_verusage.codex_deepseek_bridge \
  --native-responses \
  --model deepseek-v4-pro \
  --port "$BRIDGE_PORT" \
  --request-timeout-seconds 540 \
  --expected-upstream-model deepseek-v4-pro \
  --ledger-path "$SKILLOPT_CODEX_BRIDGE_LEDGER" \
  --manifest-path "$SKILLOPT_CODEX_BRIDGE_MANIFEST" \
  --model-catalog-path "$RUN_DIR/models.json" \
  >"$RUN_DIR/bridge_epoch4_reflect_repair.log" 2>&1 &
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

unset ANTHROPIC_API_KEY DEEPSEEK_API_KEY GEMINI_API_KEY GOOGLE_API_KEY
unset OPENAI_API_KEY OPENROUTER_API_KEY
export SKILLOPT_CODEX_BRIDGE_TOKEN=local-bridge-only

"$PYTHON_BIN" -m skillopt_verusage.train --config "$E4_CONFIG" \
  2>&1 | tee -a "$RUN_DIR/train.log"

result_count() {
  local phase_dir="$1"
  if [ ! -d "$phase_dir/predictions" ]; then
    echo 0
    return
  fi
  find "$phase_dir/predictions" -mindepth 1 -maxdepth 1 -type d \
    -exec test -f '{}/result.json' \; -print | wc -l
}

wait_for_bridge_idle() {
  for _ in $(seq 1 30); do
    if curl -fsS "$SKILLOPT_CODEX_BRIDGE_URL/health" \
      | jq -e '.active_requests == 0' >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "bridge did not become idle within 30 seconds" >&2
  return 1
}

TRAIN_COUNT="$(result_count "$RUN_DIR/steps/step_0004/rollout")"
GATE_COUNT="$(result_count "$RUN_DIR/steps/step_0004/selection_eval")"
SLOW_PREV_COUNT="$(result_count "$RUN_DIR/slow_update/epoch_04/rollout_prev")"
SLOW_CURR_COUNT="$(result_count "$RUN_DIR/slow_update/epoch_04/rollout_curr")"
SLOW_GATE_COUNT="$(result_count "$RUN_DIR/slow_update/epoch_04/selection_eval")"
test "$TRAIN_COUNT" -eq 40
test "$GATE_COUNT" -eq 20
test "$SLOW_PREV_COUNT" -eq 20
test "$SLOW_CURR_COUNT" -eq 20
test "$SLOW_GATE_COUNT" -eq 20
jq -e '.last_completed_step == 4' "$STATE_PATH" >/dev/null
jq -e '(.slow_update_content | type) == "string" and (.slow_update_content | length) > 0' \
  "$RUN_DIR/slow_update/epoch_04/slow_result.json" >/dev/null
SLOW_ACTION="$(jq -r '.action' "$RUN_DIR/slow_update/epoch_04/slow_result.json")"
case "$SLOW_ACTION" in
  accept|accept_new_best|reject) ;;
  *) echo "invalid epoch 4 slow gate action: $SLOW_ACTION" >&2; exit 1 ;;
esac
wait_for_bridge_idle

"$PYTHON_BIN" -m skillopt_verusage.cost_ledger --run-root "$RUN_DIR" >/dev/null
jq -e --slurpfile start "$START_PATH" '
  .target.error_requests == $start[0].historical_accounting_baseline.actor_error_requests and
  .target.unmetered_requests == $start[0].historical_accounting_baseline.actor_unmetered_requests and
  .optimizer.failed_attempts == $start[0].historical_accounting_baseline.optimizer_failed_attempts and
  .optimizer.unknown_usage_attempts == $start[0].historical_accounting_baseline.optimizer_unknown_usage_attempts
' "$RUN_DIR/cost_ledger.json" >/dev/null

jq -n \
  --arg validated_at "$(date -u -Is)" \
  --arg slow_action "$SLOW_ACTION" \
  --argjson train "$TRAIN_COUNT" \
  --argjson gate "$GATE_COUNT" \
  --argjson slow_prev "$SLOW_PREV_COUNT" \
  --argjson slow_curr "$SLOW_CURR_COUNT" \
  --argjson slow_gate "$SLOW_GATE_COUNT" \
  --argjson best_score "$(jq '.best_score' "$STATE_PATH")" \
  --argjson total_cost "$(jq '.target.estimated_cost_usd' "$RUN_DIR/cost_ledger.json")" \
  --argjson starting_cost "$(jq '.starting_actor_cost_usd' "$START_PATH")" \
  '{
    schema_version: "1",
    status: "complete",
    epoch: 4,
    validated_at: $validated_at,
    actor_task_counts: {
      total: ($train + $gate + $slow_prev + $slow_curr + $slow_gate),
      train: $train,
      gate: $gate,
      slow_prev: $slow_prev,
      slow_curr: $slow_curr,
      slow_gate: $slow_gate
    },
    slow_action: $slow_action,
    best_selection_hard: $best_score,
    total_actor_cost_usd: $total_cost,
    epoch4_actor_cost_usd: ($total_cost - $starting_cost)
  }' >"$RUN_DIR/epoch4_after_reflect_repair_complete.json"
