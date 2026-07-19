import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verus_self_evolve.handsoff_harness import (
    build_copilot_command,
    build_prompt,
    configured_tool_path,
    run_harness,
    validate_paths,
    verus_succeeded,
)


class HandsOffHarnessTest(unittest.TestCase):
    def test_prompt_adds_only_delimited_payload(self):
        base = build_prompt()
        augmented = build_prompt("Prefer a local assertion.")
        self.assertTrue(augmented.startswith(base))
        self.assertIn("<provided_knowledge>", augmented)
        self.assertIn("Prefer a local assertion.", augmented)

    def test_prompt_and_tools_use_portable_configuration(self):
        prompt = build_prompt(
            verus_command="/tools/verus", lynette_command="/tools/lynette"
        )
        self.assertIn("/tools/verus candidate.rs", prompt)
        self.assertIn("/tools/lynette target-mode", prompt)
        with patch.dict(os.environ, {"VERUS_BIN": "/custom/verus"}):
            self.assertEqual(
                configured_tool_path("VERUS_BIN", "verus"), Path("/custom/verus")
            )

    def test_command_pins_noninteractive_scaffold(self):
        command = build_copilot_command(Path("/bin/copilot"), "model", "prompt")
        for flag in (
            "--allow-all-tools",
            "--no-ask-user",
            "--no-custom-instructions",
            "--disable-builtin-mcps",
        ):
            self.assertIn(flag, command)

    def test_sealed_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "verified-nrkernel" / "unverified" / "task.rs"
            source.parent.mkdir(parents=True)
            source.write_text("fn task() {}\n")
            with self.assertRaisesRegex(ValueError, "sealed source"):
                validate_paths(source, Path(tmp) / "out")

    def test_condition_payload_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.rs"
            source.write_text("fn task() {}\n")
            knowledge = Path(tmp) / "knowledge.txt"
            knowledge.write_text("knowledge\n")
            common = dict(
                source=source,
                model="model",
                copilot_bin=Path("/bin/true"),
                verus_bin=Path("/bin/true"),
                lynette_bin=Path("/bin/true"),
                dry_run=True,
            )
            with self.assertRaisesRegex(ValueError, "h0 must not"):
                run_harness(
                    out_dir=Path(tmp) / "h0",
                    condition="h0",
                    knowledge_file=knowledge,
                    **common,
                )
            with self.assertRaisesRegex(ValueError, "requires"):
                run_harness(
                    out_dir=Path(tmp) / "h1",
                    condition="h1",
                    **common,
                )

    def test_dry_run_is_reproducible_and_copies_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.rs"
            source.write_text("fn task() {}\n")
            out = Path(tmp) / "out"
            result = run_harness(
                source=source,
                out_dir=out,
                condition="h0",
                model="model",
                copilot_bin=Path("/bin/true"),
                verus_bin=Path("/bin/true"),
                lynette_bin=Path("/bin/true"),
                dry_run=True,
            )
            manifest = json.loads((out / "run_manifest.json").read_text())
            self.assertEqual(result["status"], "DRY_RUN")
            self.assertEqual(manifest["source_sha256"], manifest["input_copy_sha256"])
            self.assertEqual((out / "workspace" / "input.rs").read_text(), source.read_text())

    def test_verus_success_requires_zero_exit(self):
        self.assertTrue(verus_succeeded(0, "verification results:: 1 verified"))
        self.assertFalse(verus_succeeded(1, "error: aborting"))

    def test_live_fixture_resolves_relative_tool_and_output_paths(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=cwd) as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn main() {}\n")
            fake = root / "fake_copilot.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import shutil, sys\n"
                "if '--version' in sys.argv:\n"
                "    print('fixture')\n"
                "else:\n"
                "    shutil.copyfile('input.rs', 'candidate.rs')\n"
                "    print('fixture-model 1k input, 10 output, 900 cache read')\n"
            )
            fake.chmod(0o755)
            result = run_harness(
                source=source.relative_to(cwd),
                out_dir=(root / "out").relative_to(cwd),
                condition="h0",
                model="fixture",
                copilot_bin=fake.relative_to(cwd),
                verus_bin=Path("/bin/true"),
                lynette_bin=Path("/bin/true"),
                timeout_seconds=30,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["usage_available"])
            self.assertTrue(result["validation"]["verus"]["passed"])
            self.assertTrue(result["validation"]["lynette"]["passed"])

    def test_timeout_allows_copilot_usage_footer_to_flush(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory(dir=cwd) as tmp:
            root = Path(tmp)
            source = root / "source.rs"
            source.write_text("fn main() {}\n")
            fake = root / "fake_copilot.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import shutil, signal, sys, time\n"
                "if '--version' in sys.argv:\n"
                "    print('fixture')\n"
                "    raise SystemExit\n"
                "shutil.copyfile('input.rs', 'candidate.rs')\n"
                "def finish(signum, frame):\n"
                "    print('Duration  1s', flush=True)\n"
                "    print('Tokens    ↑ 1k • ↓ 10 • 0 (cached)', flush=True)\n"
                "    raise SystemExit(130)\n"
                "signal.signal(signal.SIGINT, finish)\n"
                "time.sleep(60)\n"
            )
            fake.chmod(0o755)
            result = run_harness(
                source=source.relative_to(cwd),
                out_dir=(root / "out").relative_to(cwd),
                condition="h0",
                model="fixture",
                copilot_bin=fake.relative_to(cwd),
                verus_bin=Path("/bin/true"),
                lynette_bin=Path("/bin/true"),
                timeout_seconds=1,
            )
            self.assertTrue(result["copilot"]["timed_out"])
            self.assertTrue(result["usage_available"])
            self.assertEqual(
                json.loads((root / "out" / "usage.json").read_text())["totals"]["input_tokens"],
                1_000,
            )


if __name__ == "__main__":
    unittest.main()
