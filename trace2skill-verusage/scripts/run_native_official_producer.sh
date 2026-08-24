#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 || "$#" -gt 3 ]]; then
  echo "usage: $0 {--check-only|--execute} [combined-records.json] [output-directory]" >&2
  exit 2
fi
mode="$1"
if [[ "$mode" != "--check-only" && "$mode" != "--execute" ]]; then
  echo "first argument must be --check-only or --execute" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
if [[ -f "$repo_root/.env" ]]; then
  set -a
  source "$repo_root/.env"
  set +a
fi
: "${VERUS_SKILL_RUN_ROOT:?set VERUS_SKILL_RUN_ROOT in .env or the environment}"

records="${2:-${TRACE2SKILL_RECORDS_PATH:-}}"
if [[ -z "$records" ]]; then
  echo "provide combined-records.json or set TRACE2SKILL_RECORDS_PATH" >&2
  exit 2
fi
stamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${3:-$VERUS_SKILL_RUN_ROOT/trace2skill-verusage/native-official-producer-$stamp}"
model="${TRACE2SKILL_MODEL:-deepseek-v4-pro}"
base_url="${TRACE2SKILL_BASE_URL:-${DEEPSEEK_BASE_URL:-}}"
api_key_env="${TRACE2SKILL_API_KEY_ENV:-DEEPSEEK_API_KEY}"

flags=()
if [[ "$mode" == "--check-only" ]]; then
  flags=(--check-only)
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo_root/trace2skill-verusage/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m trace2skill_verusage.producer \
  --records "$records" \
  --output-dir "$output_dir" \
  --run-root "$VERUS_SKILL_RUN_ROOT" \
  --runtime-root "$repo_root/trace2skill-verusage/vendor/trace2skill_verus" \
  --model "$model" \
  --base-url "$base_url" \
  --api-key-env "$api_key_env" \
  --expected-records-sha256 4151b9c4ca39ca98628f33bc0355a7f49d509e28a18258482d66f935733d8466 \
  "${flags[@]}"
