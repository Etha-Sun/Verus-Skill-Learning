#!/usr/bin/env bash
set -euo pipefail

: "${QWEN_VLLM_PYTHON:?set QWEN_VLLM_PYTHON to the vLLM environment Python}"
: "${QWEN38_27B_MODEL_PATH:?set QWEN38_27B_MODEL_PATH to the local Qwen3.8-27B checkpoint}"

export CUDA_VISIBLE_DEVICES="${QWEN_CUDA_VISIBLE_DEVICES:-0,1,2,3}"
export VLLM_NO_USAGE_STATS=1
QWEN_LOCAL_API_KEY="${QWEN_LOCAL_API_KEY:-local-qwen-only}"

exec "$QWEN_VLLM_PYTHON" -m vllm.entrypoints.openai.api_server \
  --model "$QWEN38_27B_MODEL_PATH" \
  --served-model-name qwen3.8-27b \
  --host 127.0.0.1 \
  --port "${QWEN_VLLM_PORT:-8000}" \
  --dtype bfloat16 \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 262144 \
  --max-num-seqs 4 \
  --language-model-only \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3 \
  --api-key "$QWEN_LOCAL_API_KEY"
