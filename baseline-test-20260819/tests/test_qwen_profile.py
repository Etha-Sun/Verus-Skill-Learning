from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


service = load(
    "manage_qwen3_8_service_test",
    ROOT / "baseline-test-20260819" / "code" / "manage_qwen3_8_service.py",
)
driver = load(
    "run_qwen3_8_27b_fp8_test",
    ROOT / "baseline-test-20260819" / "code" / "run_qwen3_8_27b_fp8.py",
)
gpt_driver = load(
    "run_gpt_5_6_sol_max_test",
    ROOT / "baseline-test-20260819" / "code" / "run_gpt_5_6_sol_max.py",
)

glm_driver = load(
    "run_glm_5_3_test",
    ROOT / "baseline-test-20260819" / "code" / "run_glm_5_3.py",
)

class QwenProfileTests(unittest.TestCase):
    def test_service_command_freezes_local_qwen_contract(self) -> None:
        command = service.service_command()
        joined = "\n".join(command)
        self.assertIn("Qwen3.8-27B-FP8", joined)
        self.assertIn("qwen38-27b-fp8", joined)
        self.assertIn("--tensor-parallel-size\n4", joined)
        self.assertIn("--max-model-len\n262144", joined)
        self.assertIn("--kv-cache-dtype\nfp8", joined)
        self.assertIn("--structured-outputs-config.reasoning_parser\nqwen3", joined)
        self.assertIn("--tool-call-parser\nqwen3_coder", joined)
        self.assertNotIn("deepseek", joined.lower())
        self.assertNotIn("api.openai.com", joined.lower())

    def test_service_environment_strips_host_credentials(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "secret",
                "OPENAI_API_KEY": "secret",
                "VSCODE_CLI_REQUIRE_TOKEN": "secret",
                "PATH": "/usr/bin",
            },
            clear=True,
        ):
            env = service.overlay_env()
        self.assertNotIn("DEEPSEEK_API_KEY", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("VSCODE_CLI_REQUIRE_TOKEN", env)
        self.assertEqual("0,1,2,3", env["CUDA_VISIBLE_DEVICES"])
        self.assertEqual("1", env["HF_HUB_OFFLINE"])

    def test_gpt_driver_propagates_prior_spend_into_shared_budget(self) -> None:
        args = SimpleNamespace(
            skill_dir=Path("/skill"),
            run_root=Path("/run"),
            output_root=Path("/run/gpt"),
            scratch_root=Path("/scratch"),
            env_file=Path("/gpt.env"),
            codex_bin=Path("/codex"),
            verus_bin=Path("/verus"),
            rust_root=Path("/rust"),
            lynette_bin=Path("/lynette"),
            approval_limit_usd=20.0,
            prior_spend_usd=0.577884,
        )
        command = gpt_driver.actor_command(
            args,
            condition="no-skill",
            split="test",
            output=Path("/output"),
            preflight=False,
            resume=False,
        )
        joined = "\n".join(command)
        self.assertIn("--provider\nopenai", joined)
        self.assertIn("--prior-spend-usd\n0.577884", joined)
        self.assertIn("--approval-limit-usd\n20.0", joined)

    def test_glm_driver_uses_isolated_paid_profile(self) -> None:
        args = SimpleNamespace(
            skill_dir=Path("/skill"),
            run_root=Path("/run"),
            output_root=Path("/run/glm"),
            scratch_root=Path("/scratch"),
            env_file=Path("/glm.env"),
            codex_bin=Path("/codex"),
            verus_bin=Path("/verus"),
            rust_root=Path("/rust"),
            lynette_bin=Path("/lynette"),
            approval_limit_usd=20.0,
            prior_spend_usd=0.0,
        )
        command = glm_driver.actor_command(
            args,
            condition="no-skill",
            split="test",
            output=Path("/output"),
            preflight=False,
            resume=False,
        )
        joined = "\n".join(command)
        self.assertIn("--provider\nglm", joined)
        self.assertIn("--timeout-seconds\n600", joined)
        self.assertIn("--proxy-port\n4335", joined)
        self.assertIn("--budget-state-path", command)
        self.assertIn("--approval-limit-usd\n20.0", joined)

    def test_experiment_driver_selects_qwen_without_paid_budget(self) -> None:
        args = SimpleNamespace(
            skill_dir=Path("/skill"),
            run_root=Path("/run"),
            scratch_root=Path("/scratch"),
            env_file=Path("/local.env"),
            codex_bin=Path("/codex"),
            verus_bin=Path("/verus"),
            rust_root=Path("/rust"),
            lynette_bin=Path("/lynette"),
        )
        command = driver.actor_command(
            args,
            condition="no-skill",
            split="test",
            output=Path("/output"),
            preflight=False,
            resume=False,
        )
        joined = "\n".join(command)
        self.assertIn("--provider\nqwen_local", joined)
        self.assertIn("--timeout-seconds\n600", joined)
        self.assertIn("--proxy-port\n4333", joined)
        self.assertNotIn("--budget-state-path", command)
        self.assertNotIn("--approval-limit-usd", command)


if __name__ == "__main__":
    unittest.main()
