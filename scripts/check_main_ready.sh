#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$REPO_ROOT/skillopt-verusage/scripts/bootstrap_skillopt.sh"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT/skill-evolution-pilot/src:$REPO_ROOT/skillopt-verusage/src:$REPO_ROOT/skillopt-verusage/SkillOpt:$REPO_ROOT/trace2skill-verusage/src:$REPO_ROOT/trace2skill-verusage/vendor/trace2skill_verus${PYTHONPATH:+:$PYTHONPATH}"

while IFS= read -r script; do
  bash -n "$script"
done < <(find "$REPO_ROOT/scripts" "$REPO_ROOT/skillopt-verusage/scripts" "$REPO_ROOT/trace2skill-verusage/scripts" -type f -name '*.sh' -print)

"$PYTHON_BIN" -m pytest -q \
  "$REPO_ROOT/tests" \
  "$REPO_ROOT/skill-evolution-pilot/tests" \
  "$REPO_ROOT/skillopt-verusage/tests"
