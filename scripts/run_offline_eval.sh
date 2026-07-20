#!/usr/bin/env bash
set -euo pipefail

: "${VERUS_SKILL_DATA_ROOT:?Set VERUS_SKILL_DATA_ROOT first}"
: "${VERUS_SKILL_RUN_ROOT:?Set VERUS_SKILL_RUN_ROOT first}"

PYTHONPATH=src python3 -m verus_self_evolve.cli run \
  --out "${VERUS_SKILL_RUN_ROOT}/offline-eval"
