import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.handsoff_calibration import (
    _run_record,
    classify_task,
    freeze_tiers,
    parse_verus_diagnostics,
    prepare_screen,
    select_boundary_candidates,
    select_calibration_tasks,
)
from verus_self_evolve.handsoff_m0 import normalized_code_sha256, sha256_file


class HandsOffCalibrationTest(unittest.TestCase):
    def _row(
        self,
        root: Path,
        directory: str,
        task: str,
        source_text: str,
        verified_text: str,
        *,
        variant: str = "standard",
        canonical_text: str | None = None,
    ):
        result_name = "results" if variant == "standard" else f"results-{variant}"
        result_dir = root / directory / result_name
        result_dir.mkdir(parents=True, exist_ok=True)
        source = result_dir / f"{task}.rs"
        verified = result_dir / f"{task}_verified.rs"
        source.write_text(source_text)
        verified.write_text(verified_text)
        canonical = root / directory / "unverified" / f"{task}.rs"
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(canonical_text if canonical_text is not None else source_text)
        return {
            "trace_id": f"trace-{directory}-{task}-{variant}",
            "relative_log_path": f"{directory}/{result_name}/{task}.log",
            "directory_group": directory,
            "split": "train",
            "model": "model",
            "variant": variant,
            "task_id": task,
            "normalized_task_id": task,
            "source": {
                "path": str(source),
                "size_bytes": source.stat().st_size,
                "sha256": sha256_file(source),
                "normalized_code_sha256": normalized_code_sha256(source_text),
            },
            "verified": {
                "path": str(verified),
                "size_bytes": verified.stat().st_size,
                "sha256": sha256_file(verified),
                "normalized_code_sha256": normalized_code_sha256(verified_text),
            },
        }

    @staticmethod
    def _precheck(source: Path, calibration_id: str):
        assert source.parent.name == "unverified"
        assert calibration_id
        return {
            "checked": True,
            "passed": False,
            "timed_out": False,
            "diagnostics": {
                "summary_found": True,
                "verified_count": 1,
                "error_count": 3,
            },
        }

    @staticmethod
    def _paired_precheck(source: Path, verified: Path, calibration_id: str):
        assert source.parent.name == "unverified"
        assert verified.name.endswith("_verified.rs")
        assert calibration_id
        return {
            "verus": {"checked": True, "passed": True, "timed_out": False},
            "lynette": {"checked": True, "passed": True, "timed_out": False},
        }

    def _selection_fixture(self, root: Path):
        excluded = self._row(
            root,
            "verified-anvil",
            "excluded",
            "fn excluded_r040() { assert(false); }\n",
            "fn excluded_r040() { assert(true); }\n",
        )
        rows = []
        for directory in ("verified-anvil", "verified-ironkv"):
            for index in range(9):
                padding = " ".join(
                    f"unique_{directory}_{index}_{part}" for part in range(index * 4 + 1)
                )
                rows.append(
                    self._row(
                        root,
                        directory,
                        f"task_{directory}_{index}",
                        f"fn trace_variant_{index}() {{ assert(false); }} {padding}\n",
                        f"fn trace_variant_{index}() {{ assert(true); }} {padding}\n",
                        canonical_text=(
                            f"fn canonical_original_{directory.replace('-', '_')}_{index}() "
                            f"{{ assert(false); }} {padding}\n"
                        ),
                    )
                )
        return rows, [excluded]

    def test_verus_diagnostics_uses_last_summary(self):
        diagnostics = parse_verus_diagnostics(
            "verification results:: 1 verified, 2 errors\n"
            "verification results:: 3 verified, 1 errors\n"
        )
        self.assertEqual(diagnostics["verified_count"], 3)
        self.assertEqual(diagnostics["error_count"], 1)

    def test_selection_uses_canonical_original_and_is_balanced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            selected, audit = select_calibration_tasks(
                rows,
                excluded,
                root,
                self._precheck,
                self._paired_precheck,
                lambda text: len(text.split()),
                per_directory=3,
                near_threshold=0.99,
                max_model_len=10000,
                context_reserve=100,
            )
            self.assertEqual(len(selected), 6)
            self.assertEqual(
                {row["source_size_bin"] for row in selected},
                {"small", "medium", "large"},
            )
            self.assertEqual(
                {row["directory_group"] for row in selected},
                {"verified-anvil", "verified-ironkv"},
            )
            self.assertTrue(
                all("/unverified/" in f"/{row['canonical_source_path']}" for row in selected)
            )
            self.assertTrue(all(row["standard_trace_id"] for row in selected))
            self.assertEqual(audit["sealed_content_reads"], 0)

    def test_nonstandard_shorter_variant_is_not_selected_as_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            task = rows[0]["task_id"]
            rows.append(
                self._row(
                    root,
                    "verified-anvil",
                    task,
                    "fn tiny(){}\n",
                    "fn tiny_verified(){}\n",
                    variant="no_lemma",
                    canonical_text=(root / "verified-anvil" / "unverified" / f"{task}.rs").read_text(),
                )
            )
            selected, _ = select_calibration_tasks(
                rows, excluded, root, self._precheck, self._paired_precheck,
                lambda text: len(text.split()),
                per_directory=3, near_threshold=0.99, max_model_len=10000, context_reserve=100,
            )
            self.assertTrue(all(row["standard_trace_id"].endswith("-standard") for row in selected))

    def test_stale_manifest_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            rows[0]["verified"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "stale verified SHA"):
                select_calibration_tasks(
                    rows, excluded, root, self._precheck, self._paired_precheck, lambda text: 1,
                    per_directory=3,
                )

    def test_path_traversal_task_id_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            rows[0]["task_id"] = "../verified-nrkernel/secret"
            with self.assertRaisesRegex(ValueError, "unsafe task id"):
                select_calibration_tasks(
                    rows, excluded, root, self._precheck, self._paired_precheck, lambda text: 1,
                    per_directory=3,
                )

    def test_context_ineligible_candidates_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            with self.assertRaisesRegex(ValueError, "insufficient eligible tasks"):
                select_calibration_tasks(
                    rows, excluded, root, self._precheck, self._paired_precheck, lambda text: len(text),
                    per_directory=3, max_model_len=100, context_reserve=50,
                )

    def test_invalid_paired_verified_artifact_is_not_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows, excluded = self._selection_fixture(root)
            baseline, _ = select_calibration_tasks(
                rows, excluded, root, self._precheck, self._paired_precheck,
                lambda text: len(text.split()), per_directory=3,
                near_threshold=0.99, max_model_len=10000, context_reserve=100,
            )
            rejected_task = baseline[0]["task_id"]

            def paired(source: Path, verified: Path, calibration_id: str):
                result = self._paired_precheck(source, verified, calibration_id)
                if source.stem == rejected_task:
                    result["verus"]["passed"] = False
                return result

            selected, audit = select_calibration_tasks(
                rows, excluded, root, self._precheck, paired,
                lambda text: len(text.split()), per_directory=3,
                near_threshold=0.99, max_model_len=10000, context_reserve=100,
            )
            self.assertNotIn(rejected_task, {row["task_id"] for row in selected})
            self.assertEqual(
                audit["precheck_counts"]["paired_verified_verus_failure"], 1
            )

    def test_prepare_screen_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "tasks.jsonl"
            tasks.write_text(
                json.dumps(
                    {
                        "calibration_id": "a",
                        "selection_rank": 1,
                        "canonical_source_sha256": "a" * 64,
                        "base_prompt_sha256": "b" * 64,
                        "canonical_source_path": "verified-anvil/unverified/a.rs",
                    }
                )
                + "\n"
            )
            summary = prepare_screen(tasks, root / "out", repetitions=(1, 2, 3))
            self.assertEqual(summary["job_count"], 3)
            with self.assertRaisesRegex(ValueError, "must be empty"):
                prepare_screen(tasks, root / "out", repetitions=(1,))

    def _task(self):
        return {
            "calibration_id": "cal-a",
            "directory_group": "verified-anvil",
            "source_size_bin": "small",
            "canonical_source_sha256": "a" * 64,
            "base_prompt_sha256": "b" * 64,
            "max_model_len": 32768,
            "expected_model_config_sha256": "c" * 64,
            "expected_model_alias": "qwen35-27b",
            "expected_model_path": "/models/qwen",
            "expected_timeout_seconds": 1200,
            "expected_tool_sha256": {
                "copilot": "d" * 64,
                "verus": "e" * 64,
                "lynette": "f" * 64,
            },
            "source_precheck": {
                "diagnostics": {"summary_found": True, "verified_count": 1, "error_count": 3}
            },
        }

    def _write_run(
        self,
        path: Path,
        task: dict,
        *,
        status: str = "FAIL",
        verus_passed: bool = False,
        lynette_passed: bool = True,
        candidate_errors: int = 3,
        candidate_verified: int = 1,
        timed_out: bool = False,
    ):
        path.mkdir(parents=True)
        (path / "run_manifest.json").write_text(
            json.dumps(
                {
                    "condition": "h0",
                    "source_sha256": task["canonical_source_sha256"],
                    "base_prompt_sha256": task["base_prompt_sha256"],
                    "prompt_sha256": task["base_prompt_sha256"],
                    "model": "qwen35-27b",
                    "provider": {
                        "model_path": "/models/qwen",
                        "model_config_sha256": task["expected_model_config_sha256"],
                        "max_model_len": 32768,
                    },
                    "timeout_seconds": task["expected_timeout_seconds"],
                    "tool_sha256": task["expected_tool_sha256"],
                }
            )
        )
        (path / "result.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "copilot": {"timed_out": timed_out},
                    "validation": {
                        "candidate_present": True,
                        "verus": {"checked": True, "passed": verus_passed, "timed_out": False},
                        "lynette": {"checked": True, "passed": lynette_passed, "timed_out": False},
                    },
                }
            )
        )
        (path / "copilot.log").write_text("")
        (path / "verus.log").write_text(
            f"verification results:: {candidate_verified} verified, {candidate_errors} errors\n"
        )

    def test_lynette_failure_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task()
            path = Path(tmp) / "run"
            self._write_run(path, task, status="PASS", verus_passed=True, lynette_passed=False)
            self.assertEqual(_run_record(task, path, 1)["outcome"], "unsafe")

    def test_wrong_condition_is_rejected_as_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task()
            path = Path(tmp) / "run"
            self._write_run(path, task)
            manifest_path = path / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["condition"] = "h2"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "non-H0"):
                _run_record(task, path, 1)

    def test_verified_count_increase_alone_is_stalled(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task()
            path = Path(tmp) / "run"
            self._write_run(path, task, candidate_errors=3, candidate_verified=99)
            self.assertEqual(_run_record(task, path, 1)["outcome"], "stalled")

    def test_error_count_decrease_is_near_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = self._task()
            path = Path(tmp) / "run"
            self._write_run(path, task, candidate_errors=2)
            self.assertEqual(_run_record(task, path, 1)["outcome"], "near_miss")

    def test_classification_requires_three_consistent_identities(self):
        base = {
            "result_available": True,
            "outcome": "pass",
            "source_sha256": "a",
            "base_prompt_sha256": "b",
            "model": "m",
            "model_path": "p",
            "model_config_sha256": "c",
            "max_model_len": 32768,
        }
        self.assertEqual(classify_task([base, base]), "incomplete")
        self.assertEqual(classify_task([base, base, {**base, "model": "other"}]), "identity_mismatch")
        self.assertEqual(classify_task([base, base, {**base, "outcome": "stalled"}]), "pass")

    def test_partial_boundary_without_done_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = self._task()
            task.update({"task_id": "a", "selection_rank": 1})
            boundary = root / "boundary.jsonl"
            boundary.write_text(json.dumps(task) + "\n")
            with self.assertRaisesRegex(ValueError, "boundary DONE summary"):
                freeze_tiers(boundary, root / "runs", root / "out")
            self.assertFalse((root / "out" / "r040d_frozen_tiers.json").exists())

    def test_incomplete_initial_screen_writes_no_boundary_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "tasks.jsonl"
            rows = []
            for index in range(30):
                row = self._task()
                row.update(
                    {
                        "calibration_id": f"cal-{index}",
                        "directory_group": "verified-anvil" if index < 15 else "verified-ironkv",
                        "source_size_bin": ("small", "medium", "large")[index % 3],
                    }
                )
                rows.append(row)
            tasks.write_text("".join(json.dumps(row) + "\n" for row in rows))
            summary = select_boundary_candidates(tasks, root / "runs", root / "out")
            self.assertEqual(summary["status"], "INCOMPLETE")
            self.assertFalse((root / "out" / "r040c_boundary_candidates.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
