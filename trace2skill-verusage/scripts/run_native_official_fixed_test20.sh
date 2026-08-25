#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 {gpt|deepseek|glm|qwen}" >&2
  exit 2
fi

provider="$1"
case "$provider" in
  gpt|deepseek|glm|qwen) ;;
  *)
    echo "unsupported provider: $provider" >&2
    exit 2
    ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
skill_dir="$repo_root/trace2skill-verusage/baselines/native-official-20260819/skill/verus-proof-repair"

exec bash "$repo_root/skillopt-verusage/scripts/run_s2_fixed_test20.sh" \
  "$provider" trace2skill "$skill_dir"
