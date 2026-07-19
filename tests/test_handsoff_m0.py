import json
import tempfile
import unittest
from pathlib import Path

from verus_self_evolve.handsoff_m0 import (
    apply_leakage_quarantine,
    build_inventory,
    normalize_task_id,
    parse_copilot_usage,
    run_leakage_audit,
)


class HandsOffM0Test(unittest.TestCase):
    def test_usage_parser_handles_abbreviated_counts(self):
        usage = parse_copilot_usage(
            "Total usage est:       3 Premium requests\n"
            "Total duration (API):  10m 35.285s\n"
            "Total duration (wall): 11m 9.909s\n"
            "Usage by model:\n"
            "    claude-opus-4.5      4.4m input, 53.5k output, 4.3m cache read "
            "(Est. 3 Premium requests)\n"
        )
        self.assertTrue(usage["available"])
        self.assertEqual(usage["totals"]["input_tokens"], 4_400_000)
        self.assertEqual(usage["totals"]["output_tokens"], 53_500)
        self.assertEqual(usage["totals"]["cache_read_tokens"], 4_300_000)
        self.assertEqual(usage["totals"]["uncached_total_tokens"], 153_500)
        self.assertAlmostEqual(usage["wall_seconds"], 669.909)

    def test_usage_parser_handles_current_copilot_footer(self):
        usage = parse_copilot_usage(
            "Changes   +0 -0\n"
            "Duration  29s\n"
            "Tokens    ↑ 15.6k • ↓ 882 • 900 (cached)\n"
        )
        self.assertTrue(usage["available"])
        self.assertEqual(usage["totals"]["input_tokens"], 15_600)
        self.assertEqual(usage["totals"]["output_tokens"], 882)
        self.assertEqual(usage["totals"]["cache_read_tokens"], 900)
        self.assertEqual(usage["totals"]["uncached_total_tokens"], 15_582)
        self.assertEqual(usage["wall_seconds"], 29)

    def test_task_normalization_removes_project_prefix(self):
        self.assertEqual(normalize_task_id("MA__foo__bar_verified"), "foo_bar")

    def test_inventory_never_reads_sealed_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "corpus"
            out = Path(tmp) / "out"
            train = root / "verified-ironkv" / "results-opus45"
            sealed = root / "verified-memory-allocator" / "results-opus45"
            train.mkdir(parents=True)
            sealed.mkdir(parents=True)
            (train / "train_task.log").write_text(
                "    claude-opus-4.5 1k input, 20 output, 900 cache read\n"
            )
            (train / "train_task.rs").write_text("fn train_task() {}\n")
            (sealed / "secret_task.log").write_text("SECRET SEALED CONTENT\n")
            (sealed / "secret_task.rs").write_text("fn secret_task() {}\n")
            summary = build_inventory(root, out)
            rows = [
                json.loads(line)
                for line in (out / "corpus_manifest.jsonl").read_text().splitlines()
            ]
            by_task = {row["task_id"]: row for row in rows}
            self.assertTrue(by_task["train_task"]["content_scanned"])
            self.assertFalse(by_task["secret_task"]["content_scanned"])
            self.assertIsNone(by_task["secret_task"]["log_sha256"])
            self.assertIsNone(
                by_task["secret_task"]["source"]["normalized_code_sha256"]
            )
            self.assertEqual(summary["sealed_content_scanned"], 0)

    def test_inventory_refuses_output_inside_raw_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "corpus"
            root.mkdir()
            with self.assertRaises(ValueError):
                build_inventory(root, root / "derived")

    def test_audit_ignores_answer_and_detects_clean_project_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "corpus"
            out = Path(tmp) / "out"
            audit = Path(tmp) / "audit"
            train = root / "verified-ironkv" / "results-opus45"
            train.mkdir(parents=True)
            (train / "train_unique.log").write_text("")
            (train / "train_unique.rs").write_text(
                "fn train_unique() { assert(true); }\n"
            )
            build_inventory(root, out)
            eval_path = Path(tmp) / "eval.jsonl"
            eval_item = {
                "prompt_messages": [
                    {"role": "user", "content": "Task without embedded code"}
                ],
                "answer": "SECRET FINAL ANSWER",
                "meta": {"project": "MA", "task_id": "MA__heldout"},
            }
            eval_path.write_text(json.dumps(eval_item) + "\n")
            report = run_leakage_audit(
                out / "corpus_manifest.jsonl",
                eval_path,
                audit,
                near_threshold=0.90,
            )
            split = json.loads((audit / "split_manifest.json").read_text())
            self.assertEqual(report["verdict"], "PASS")
            self.assertFalse(split["evaluation_answers_accessed"])
            self.assertNotIn(
                "SECRET FINAL ANSWER",
                (audit / "split_manifest.json").read_text(),
            )

    def test_quarantine_removes_all_traces_for_overlapping_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.jsonl"
            rows = [
                {
                    "trace_id": f"trace-{index}",
                    "split": "train",
                    "normalized_task_id": "overlap",
                    "source": {"normalized_code_sha256": "source-hash"},
                }
                for index in range(2)
            ]
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
            leakage = Path(tmp) / "leakage.json"
            leakage.write_text(
                json.dumps(
                    {
                        "verdict": "REVIEW",
                        "exact_name_pairs": [
                            {"normalized_task_id": "overlap"}
                        ],
                        "near_pairs": [],
                    }
                )
            )
            out = Path(tmp) / "out"
            result = apply_leakage_quarantine(manifest, leakage, out)
            effective = [
                json.loads(line)
                for line in (out / "effective_corpus_manifest.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertEqual(result["quarantined_trace_count"], 2)
            self.assertEqual({row["split"] for row in effective}, {"quarantine"})


if __name__ == "__main__":
    unittest.main()
