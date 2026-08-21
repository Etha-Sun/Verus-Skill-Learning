# S2 Skill 四模型固定测试 Tracker

时间：2026-08-19 17:08 CDT

| 项目 | 状态 | 证据/阻塞 |
|---|---|---|
| 固定 test-20 与 S2 hash 校验 | PASS | evaluator check-only 通过；20 个唯一 task |
| 统一 Codex test evaluator | PASS | `skillopt_verusage.test_eval` |
| DeepSeek native Responses 配置 | READY | exact model + 当前峰谷计费 |
| GPT-5.6 Sol direct Codex 配置 | READY | local quota，20 并发 |
| GLM-5.3 Chat bridge 配置 | READY_WITH_KEY_BLOCKER | 需 `ZAI_API_KEY` |
| Qwen3-8B 权重 | PASS | 官方 BF16，约 16 GiB |
| Qwen vLLM Python 环境 import | PASS | torch/transformers/vLLM 均可导入 |
| Qwen Responses→Chat 单元测试 | PASS | Qwen 参数、tool history、terminal、usage |
| Qwen Codex CLI 假上游 tool smoke | PASS | `exec_command(pwd)` 后返回 `READY` |
| Qwen tier-2 GPU witness | BLOCKED | 当前节点无可见 CUDA driver |
| Qwen 真实模型 tool smoke | BLOCKED | 等待 GPU |
| 四组 test-20 正式运行 | NOT_STARTED | 用户本轮仅要求先设置与估算 |

## 已生成入口

- `skillopt-verusage/scripts/run_s2_fixed_test20.sh`
- `skillopt-verusage/scripts/launch_qwen3_8b_vllm.sh`
- `skillopt-verusage/scripts/prepare_codex_model_catalog.py`
- `skillopt_verusage.test_eval`
- `.aris/compute/qwen3-8b-codex-test.json`

## Qwen 协议 smoke 输出

`${VERUS_SKILL_RUN_ROOT}/skillopt-verusage/qwen3-8b-codex-bridge-fake-preflight-20260819/`

该 smoke 使用 fake upstream，只证明 Codex CLI、Responses→Chat、工具调用回传和
终态记录可工作，不证明 Qwen3-8B 的 proof-repair 能力。

## 下一检查点

GPU 可见后，依次验证：

1. seeded CUDA witness；
2. vLLM `/v1/models` 精确返回 `qwen3-8b`；
3. 一次真实工具调用；
4. 一个真实 Verus test task；
5. 若无 V0_INVALID，再运行完整 Qwen test-20。

