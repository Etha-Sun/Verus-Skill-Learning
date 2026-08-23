import math
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from verus_self_evolve.logprob_scorer import (
    TokenScore,
    _checkpoint_complete,
    _context_target_ids,
    _target_chunk_metrics,
    action_distribution_metrics,
    entropy_bits,
    information_density_bits,
    normalize_log_scores,
    score_target_hf_loaded,
    _resolve_prepared_prompt_format,
)


class FakeTokenizer:
    chat_template = "available"

    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def apply_chat_template(self, messages, tokenize, add_generation_prompt, **kwargs):
        self.last_messages = messages
        self.last_template_kwargs = kwargs
        if not tokenize:
            return "<chat>" + messages[0]["content"]
        return [900, 901] + [ord(char) for char in messages[0]["content"]]


class LogprobScorerTest(unittest.TestCase):
    def test_chat_boundary_keeps_target_separate(self):
        context_ids, target_ids = _context_target_ids(FakeTokenizer(), "context ", "A", "chat")
        self.assertEqual(context_ids, [900, 901] + [ord(char) for char in "context "])
        self.assertEqual(target_ids, [ord("A")])

    def test_chat_direct_omits_reasoning_prefix(self):
        context_ids, target_ids = _context_target_ids(FakeTokenizer(), "context", "A", "chat_direct")
        rendered = "".join(chr(token_id) for token_id in context_ids)
        self.assertIn("<|im_start|>assistant\n", rendered)
        self.assertNotIn("<think>", rendered)
        self.assertEqual(target_ids, [ord("A")])

    def test_chat_nonthinking_and_assistant_prefix(self):
        tokenizer = FakeTokenizer()
        context_ids, target_ids = _context_target_ids(
            tokenizer,
            "context",
            'postcondition_repair"}',
            "chat_nonthinking",
            assistant_prefix='{"action":"',
        )
        self.assertEqual(tokenizer.last_template_kwargs, {"enable_thinking": False})
        self.assertEqual(context_ids[-11:], [ord(char) for char in '{"action":"'])
        self.assertEqual(target_ids, [ord(char) for char in 'postcondition_repair"}'])

    def test_chat_template_batch_encoding_uses_input_ids(self):
        class BatchTokenizer(FakeTokenizer):
            def apply_chat_template(self, messages, tokenize, add_generation_prompt, **kwargs):
                return {"input_ids": [11, 12, 13], "attention_mask": [1, 1, 1]}

        context_ids, _ = _context_target_ids(BatchTokenizer(), "context", "A", "chat_nonthinking")
        self.assertEqual(context_ids, [11, 12, 13])

    def test_normalized_distribution_sums_to_one(self):
        probabilities = normalize_log_scores({"A": -1.0, "B": -2.0, "C": -3.0})
        self.assertAlmostEqual(sum(probabilities.values()), 1.0)
        self.assertGreater(probabilities["A"], probabilities["B"])

    def test_decision_pmi_and_entropy(self):
        metrics = action_distribution_metrics(
            {"A": math.log(0.5), "B": math.log(0.5)},
            {"A": math.log(0.8), "B": math.log(0.2)},
            "A",
        )
        self.assertAlmostEqual(metrics["decision_pmi_bits"], math.log2(0.8 / 0.5))
        self.assertGreater(metrics["entropy_reduction_bits"], 0.0)
        self.assertTrue(metrics["observed_action_top1_artifact"])
        self.assertAlmostEqual(metrics["baseline_candidate_raw_mass"], 1.0)
        self.assertAlmostEqual(metrics["artifact_candidate_raw_mass"], 1.0)
        self.assertAlmostEqual(entropy_bits({"A": 0.5, "B": 0.5}), 1.0)

    def test_empty_text_container_has_density_when_context_grows(self):
        baseline = len(FakeTokenizer().apply_chat_template(
            [{"role": "user", "content": "state"}], tokenize=True, add_generation_prompt=True
        ))
        artifact = len(FakeTokenizer().apply_chat_template(
            [{"role": "user", "content": "state\n\nAdditional artifact:\n"}],
            tokenize=True,
            add_generation_prompt=True,
        ))
        self.assertGreater(artifact - baseline, 0)
        self.assertIsNotNone(information_density_bits(-1.0, artifact - baseline))

    def test_scoring_requires_prepared_metadata(self):
        with self.assertRaises(ValueError):
            _resolve_prepared_prompt_format([{"prepared_intervention_token_count": 10}], None)
        with self.assertRaises(ValueError):
            _resolve_prepared_prompt_format([{"prepared_prompt_format": "chat_direct"}], None)
        self.assertEqual(
            _resolve_prepared_prompt_format([
                {"prepared_prompt_format": "chat_direct", "prepared_intervention_token_count": 10}
            ], None),
            "chat_direct",
        )

    def test_chunk_metrics_preserve_total_delta(self):
        baseline = [TokenScore(i, i, str(i), 0.5, -2.0) for i in range(5)]
        artifact = [TokenScore(i, i, str(i), 0.5, -1.0) for i in range(5)]
        chunks = _target_chunk_metrics(baseline, artifact, chunk_size=2)
        self.assertEqual([row["token_count"] for row in chunks], [2, 2, 1])
        self.assertAlmostEqual(sum(row["loglikelihood_delta_nats"] for row in chunks), 5.0)

    def test_checkpoint_requires_matching_fingerprint_and_token_table(self):
        with tempfile.TemporaryDirectory() as temporary:
            case_dir = Path(temporary)
            (case_dir / "token_scores.jsonl").write_text("{}\n", encoding="utf-8")
            (case_dir / "aggregate.json").write_text(
                json.dumps({"case_fingerprint": "expected"}), encoding="utf-8"
            )
            self.assertTrue(_checkpoint_complete(case_dir, "expected"))
            self.assertFalse(_checkpoint_complete(case_dir, "different"))

    def test_chunked_hf_scoring_preserves_cross_chunk_next_token_boundary(self):
        try:
            import torch
        except ImportError:
            self.skipTest("optional torch dependency is not installed")

        class Tokenizer:
            def encode(self, text, add_special_tokens=False):
                if not text:
                    return []
                return [1, 2] if text == "context" else [3, 4, 5, 6, 7]

            def decode(self, token_ids):
                return str(token_ids[0])

        class Model:
            def __init__(self):
                self.embedding = SimpleNamespace(weight=torch.zeros(1))
                self.logits_to_keep = []

            def get_input_embeddings(self):
                return self.embedding

            def __call__(self, input_ids, past_key_values, use_cache, logits_to_keep):
                self.logits_to_keep.append(logits_to_keep)
                kept = input_ids[0, -logits_to_keep:]
                logits = torch.full((1, len(kept), 10), -10.0)
                for index, token_id in enumerate(kept.tolist()):
                    logits[0, index, (token_id + 1) % 10] = 10.0
                return SimpleNamespace(logits=logits, past_key_values=object())

        model = Model()
        scores = score_target_hf_loaded(
            torch,
            Tokenizer(),
            model,
            "context",
            "target",
            prefill_chunk_size=1,
            score_chunk_size=2,
        )
        self.assertEqual([row.token_id for row in scores], [3, 4, 5, 6, 7])
        self.assertEqual([row.token_index for row in scores], [0, 1, 2, 3, 4])
        self.assertTrue(all(row.logprob > -0.001 for row in scores))
        self.assertEqual(model.logits_to_keep, [1, 1, 2, 2, 1])


if __name__ == "__main__":
    unittest.main()
