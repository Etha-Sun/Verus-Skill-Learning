#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/.env"

: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env}"

RUN_NAME="${SKILLOPT_RUN_NAME:-codex-pro-fixed80-e1-600s-20260817-1916}"
RUN_DIR="$VERUS_SKILL_RUN_ROOT/skillopt-verusage/$RUN_NAME"
RUN_SESSION="skillopt-pro-fixed80-e2-20260818"
COST_SESSION="skillopt-pro-fixed80-e2-cost-20260818"
RUN_SCRIPT="$SCRIPT_DIR/run_codex_pro_sol_fixed80_e2_resume_600s.sh"

if tmux has-session -t "$RUN_SESSION" 2>/dev/null; then
  echo "run session already exists: $RUN_SESSION" >&2
  exit 1
fi
if tmux has-session -t "$COST_SESSION" 2>/dev/null; then
  echo "cost session already exists: $COST_SESSION" >&2
  exit 1
fi

SKILLOPT_PREFLIGHT_ONLY=1 "$RUN_SCRIPT"

tmux new-session -d -s "$RUN_SESSION" \
  "cd '$REPO_ROOT' && exec '$RUN_SCRIPT'"
tmux new-session -d -s "$COST_SESSION" \
  "cd '$REPO_ROOT' && exec '$SCRIPT_DIR/monitor_codex_cost.sh' '$RUN_DIR' '$RUN_SESSION'"

tmux has-session -t "$RUN_SESSION"
tmux has-session -t "$COST_SESSION"
echo "launched $RUN_SESSION with monitor $COST_SESSION"
