#!/usr/bin/env bash
set -euo pipefail

: "${QWEN_VLLM_PYTHON:?set QWEN_VLLM_PYTHON to the vLLM environment Python}"
: "${QWEN38_27B_MODEL_PATH:?set QWEN38_27B_MODEL_PATH to the local Qwen3.8-27B checkpoint}"

export CUDA_VISIBLE_DEVICES="${QWEN_CUDA_VISIBLE_DEVICES:-0,1,2,3}"
export VLLM_NO_USAGE_STATS=1
QWEN_LOCAL_API_KEY="${QWEN_LOCAL_API_KEY:-local-qwen-only}"

exec "$QWEN_VLLM_PYTHON" -m vllm.entrypoints.cli.main serve \
  "$QWEN38_27B_MODEL_PATH" \
  --served-model-name "${QWEN_LOCAL_MODEL:-qwen38-27b-bf16}" \
  --host 127.0.0.1 \
  --port "${QWEN_VLLM_PORT:-8000}" \
  --dtype bfloat16 \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 262144 \
  --kv-cache-dtype auto \
  --max-num-seqs 4 \
  --seed 0 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --structured-outputs-config.reasoning_parser qwen3 \
  --default-chat-template-kwargs '{"enable_thinking":true,"preserve_thinking":true}' \
  --enable-force-include-usage \
  --api-key "$QWEN_LOCAL_API_KEY"
