#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 RUN_DIR TMUX_SESSION" >&2
  exit 2
fi

RUN_DIR="$1"
RUN_SESSION="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${SKILLOPT_PYTHON_BIN:-python3}"
LOG_PATH="$RUN_DIR/live_cost_monitor.log"

export PYTHONPATH="$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/skill-evolution-pilot/src"

sample() {
  date -u -Is
  "$PYTHON_BIN" -m skillopt_verusage.cost_ledger --run-root "$RUN_DIR" \
    | jq -c '{
        status,
        model,
        target: {
          tasks: .target.task_ledgers,
          requests: .target.requests,
          metered: .target.metered_requests,
          errors: .target.error_requests,
          cost_usd: .target.estimated_cost_usd,
          bands: .target.price_band_requests,
          prompt: .target.prompt_tokens,
          cache_hit: .target.prompt_cache_hit_tokens,
          cache_miss: .target.prompt_cache_miss_tokens,
          completion: .target.completion_tokens
        },
        optimizer: {
          calls: .optimizer.calls,
          cost_usd: .optimizer.actual_metered_cost_usd
        }
      }'
}

while tmux has-session -t "$RUN_SESSION" 2>/dev/null; do
  sample >>"$LOG_PATH" 2>&1
  sleep 60
done
sample >>"$LOG_PATH" 2>&1
