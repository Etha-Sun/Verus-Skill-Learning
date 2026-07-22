import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from verus_self_evolve.handsoff_rationale import (
    _knowledge_text,
    _stable_case,
    freeze_prompts,
    freeze_qualitative_cases,
    qualitative_label,
    prepare_distillation_pack,
    select_qualitative_candidates,
)
from verus_self_evolve.handsoff_m0 import sha256_file


class HandsOffRationaleTest(unittest.TestCase):
    @staticmethod
    def _task(index: int) -> dict:
        return {
            "calibration_id": f"cal-{index:02d}",
            "selection_rank": index + 1,
            "directory_group": "verified-anvil" if index < 15 else "verified-ironkv",
            "source_size_bin": ("small", "medium", "large")[index % 3],
            "canonical_source_sha256": f"{index:064x}",
            "base_prompt_sha256": "b" * 64,
            "expected_model_config_sha256": "c" * 64,
            "expected_model_alias": "qwen35-27b",
            "expected_model_path": "/models/qwen",
            "expected_timeout_seconds": 1200,
            "expected_tool_sha256": {
                "copilot": "d" * 64,
                "verus": "e" * 64,
                "lynette": "f" * 64,
            },
            "max_model_len": 32768,
            "source_precheck": {
                "diagnostics": {
                    "summary_found": True,
                    "verified_count": 0,
                    "error_count": 1,
                }
            },
        }

    @staticmethod
    def _write_run(path: Path, task: dict, label: str) -> None:
        path.mkdir(parents=True)
        passed = label == "pass"
        (path / "run_manifest.json").write_text(
            json.dumps(
                {
                    "condition": "h0",
                    "source_sha256": task["canonical_source_sha256"],
                    "base_prompt_sha256": task["base_prompt_sha256"],
                    "prompt_sha256": task["base_prompt_sha256"],
                    "model": task["expected_model_alias"],
                    "provider": {
                        "model_path": task["expected_model_path"],
                        "model_config_sha256": task["expected_model_config_sha256"],
                        "max_model_len": 32768,
                    },
                    "timeout_seconds": 1200,
                    "tool_sha256": task["expected_tool_sha256"],
                }
            )
        )
        (path / "result.json").write_text(
            json.dumps(
                {
                    "status": "PASS" if passed else "FAIL",
                    "copilot": {"timed_out": False},
                    "validation": {
                        "candidate_present": True,
                        "verus": {
                            "checked": True,
                            "passed": passed,
                            "timed_out": False,
                        },
                        "lynette": {
                            "checked": True,
                            "passed": True,
                            "timed_out": False,
                        },
                    },
                }
            )
        )
        (path / "copilot.log").write_text("")
        if label == "closest_failure":
            failure = "error: postcondition not satisfied\n"
        elif label == "stalled":
            failure = "error[E0425]: cannot find value `x`\n"
        else:
            failure = ""
        errors = 0 if passed else 1
        (path / "verus.log").write_text(
            failure + f"verification results:: 1 verified, {errors} errors\n"
        )

    def test_closest_failure_requires_localized_single_proof_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = self._task(0)
            closest = root / "closest"
            stalled = root / "stalled"
            self._write_run(closest, task, "closest_failure")
            self._write_run(stalled, task, "stalled")
            self.assertEqual(
                qualitative_label(task, closest, 1)["qualitative_label"],
                "closest_failure",
            )
            self.assertEqual(
                qualitative_label(task, stalled, 1)["qualitative_label"], "stalled"
            )

    def test_stability_contract(self):
        self.assertTrue(_stable_case(["pass", "pass", "stalled"], "pass"))
        self.assertTrue(
            _stable_case(
                ["closest_failure", "closest_failure", "stalled"],
                "closest_failure",
            )
        )
        self.assertFalse(
            _stable_case(["closest_failure", "pass", "closest_failure"], "closest_failure")
        )

    def test_distiller_tags_are_removed_from_frozen_payload(self):
        response = {
            "choices": [{"message": {"content": "<knowledge>check Verus</knowledge>"}}]
        }
        self.assertEqual(_knowledge_text(response), "check Verus\n")

    def test_distillation_pack_rejects_sealed_directory_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selection = root / "selection.jsonl"
            row = {
                "directory_group": "verified-nrkernel",
                "relative_log_path": "verified-nrkernel/results/secret.log",
            }
            selection.write_text("".join(json.dumps(row) + "\n" for _ in range(30)))
            with self.assertRaisesRegex(ValueError, "forbidden distillation directory"):
                prepare_distillation_pack(selection, root / "corpus", root / "out")
            self.assertFalse((root / "out").exists())

    def test_selection_freezes_three_candidates_per_case_and_18_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = [self._task(index) for index in range(30)]
            tasks_path = root / "tasks.jsonl"
            tasks_path.write_text("".join(json.dumps(row) + "\n" for row in tasks))
            runs = root / "runs"
            cases = ("pass", "closest_failure", "stalled")
            labels = [cases[index % 3] for index in range(30)]
            for task, label in zip(tasks, labels):
                self._write_run(
                    runs / task["calibration_id"] / "rep_1" / "h0", task, label
                )
            summary = select_qualitative_candidates(
                tasks_path, runs, root / "out", per_case=3
            )
            self.assertEqual(summary["candidate_counts"], {
                "closest_failure": 3,
                "pass": 3,
                "stalled": 3,
            })
            self.assertEqual(summary["job_count"], 18)
            self.assertFalse(summary["h1_h2_outcomes_read"])
            selected = [
                json.loads(line)
                for line in (root / "out" / "r040c_qualitative_candidates.jsonl")
                .read_text()
                .splitlines()
            ]
            for case in ("pass", "closest_failure", "stalled"):
                directories = {
                    row["directory_group"]
                    for row in selected
                    if row["candidate_case"] == case
                }
                self.assertEqual(directories, {"verified-anvil", "verified-ironkv"})

    def test_freeze_cases_requires_and_freezes_three_per_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = ("pass", "closest_failure", "stalled")
            candidates = []
            runs = root / "runs"
            for index in range(9):
                task = self._task(index)
                task["candidate_case"] = cases[index // 3]
                candidates.append(task)
                for repetition in (1, 2, 3):
                    self._write_run(
                        runs
                        / task["calibration_id"]
                        / f"rep_{repetition}"
                        / "h0",
                        task,
                        task["candidate_case"],
                    )
            candidate_path = root / "r040c_qualitative_candidates.jsonl"
            candidate_path.write_text(
                "".join(json.dumps(row) + "\n" for row in candidates)
            )
            (root / "r040c_summary.json").write_text(
                json.dumps(
                    {
                        "status": "FROZEN",
                        "candidate_sha256": sha256_file(candidate_path),
                    }
                )
            )
            summary = freeze_qualitative_cases(
                candidate_path, runs, root / "frozen"
            )
            self.assertEqual(summary["status"], "DONE")
            frozen = json.loads(
                (root / "frozen" / "r040d_frozen_cases.json").read_text()
            )
            self.assertEqual(len(frozen["cases"]), 3)

    def test_prompt_freeze_enforces_transitive_provenance_and_bypass_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tokenizer = root / "tokenizer"
            tokenizer.mkdir()
            (tokenizer / "tokenizer_config.json").write_text("{}")
            (tokenizer / "config.json").write_text("{}")
            selection = root / "selection.jsonl"
            selection.write_text(json.dumps({"task_id": "trace_task_name"}) + "\n")
            calibration = root / "calibration.jsonl"
            calibration.write_text(json.dumps({"calibration_id": "calibration_a"}) + "\n")
            pack = root / "pack.jsonl"
            pack.write_text("{}\n")
            h1_raw = root / "h1_raw.txt"
            h1_raw.write_text("generic raw\n")
            h2_raw = root / "h2_raw.txt"
            h2_raw.write_text("trace raw\n")
            h1 = root / "h1.txt"
            h1.write_text("generic reviewed\n")
            h2 = root / "h2.txt"
            h2.write_text("Never introduce external_body, assume, or admit.\n")
            pack_summary = root / "pack_summary.json"
            pack_summary.write_text(
                json.dumps(
                    {
                        "selection_sha256": sha256_file(selection),
                        "pack_sha256": sha256_file(pack),
                    }
                )
            )
            h1_summary = root / "h1_summary.json"
            h1_summary.write_text(
                json.dumps(
                    {
                        "prompt_sha256": sha256_file(h1_raw),
                        "trace_evidence_read": False,
                    }
                )
            )
            h2_summary = root / "h2_summary.json"
            h2_summary.write_text(
                json.dumps(
                    {
                        "pack_sha256": sha256_file(pack),
                        "prompt_sha256": sha256_file(h2_raw),
                    }
                )
            )
            review = root / "review.json"

            def write_review():
                review.write_text(
                    json.dumps(
                        {
                            "h1_raw_sha256": sha256_file(h1_raw),
                            "h1_reviewed_sha256": sha256_file(h1),
                            "h2_raw_sha256": sha256_file(h2_raw),
                            "h2_reviewed_sha256": sha256_file(h2),
                            "safety_verdict": "PASS",
                            "reviewer_type": "ai_agent",
                            "agent_edit_minutes": 1,
                            "human_edit_minutes": 0,
                        }
                    )
                )

            write_review()
            arguments = (
                h1,
                h2,
                tokenizer,
                calibration,
                selection,
                root / "frozen",
                pack,
                pack_summary,
                h1_summary,
                h2_summary,
                review,
            )
            with mock.patch(
                "verus_self_evolve.handsoff_rationale._token_counter",
                return_value=lambda text: 100,
            ):
                manifest = freeze_prompts(*arguments)
                self.assertTrue(all(manifest["provenance_chain"].values()))

                pack_summary.write_text(
                    json.dumps(
                        {
                            "selection_sha256": "0" * 64,
                            "pack_sha256": sha256_file(pack),
                        }
                    )
                )
                with self.assertRaisesRegex(ValueError, "provenance chain"):
                    freeze_prompts(*arguments[:5], root / "bad-provenance", *arguments[6:])

                pack_summary.write_text(
                    json.dumps(
                        {
                            "selection_sha256": sha256_file(selection),
                            "pack_sha256": sha256_file(pack),
                        }
                    )
                )
                h2.write_text("Use external_body sparingly when a proof is hard.\n")
                write_review()
                with self.assertRaisesRegex(ValueError, "permissive proof-bypass"):
                    freeze_prompts(*arguments[:5], root / "bad-safety", *arguments[6:])


if __name__ == "__main__":
    unittest.main()
