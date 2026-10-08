import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from skillopt_verusage.text_context import CONTEXT_WINDOW, _load_tokenizer, context_admission


def payload():
    return {"model": "deepseek-v4-pro", "instructions": "system",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
            "reasoning": {"effort": "high"}, "max_output_tokens": 16384,
            "text": {"format": {"type": "json_object"}}, "stream": False}


class ContextTests(unittest.TestCase):
    def test_no_tokenizer_matches_old_guard_without_claiming_real_tokens(self):
        value = payload()
        value["input"][0]["content"][0]["text"] = "你好"
        receipt = context_admission(value)
        size = len(json.dumps(value, ensure_ascii=False).encode())
        self.assertEqual(receipt["method"], "conservative_utf8_byte_bound")
        self.assertEqual(receipt["admission_total"], size + 16384)
        self.assertNotIn("serialized_payload_tokens", receipt)

    def test_fallback_preserves_full_input_and_rejects_oversize(self):
        value = payload()
        value["instructions"] = "x" * CONTEXT_WINDOW
        with self.assertRaisesRegex(ValueError, "context admission"):
            context_admission(value)

    def test_unsupported_formats_fail_closed_before_loading(self):
        variants = []
        for key, content in [("tools", []), ("previous_response_id", "prior"), ("conversation", "prior")]:
            value = payload(); value[key] = content; variants.append(value)
        value = payload(); value["input"].append(copy.deepcopy(value["input"][0])); variants.append(value)
        value = payload(); value["input"][0]["role"] = "assistant"; variants.append(value)
        for kind in ["input_image", "input_file", "function_call", "output_text"]:
            value = payload(); value["input"][0]["content"][0]["type"] = kind; variants.append(value)
        value = payload(); value["input"][0]["content"] = "bare string"; variants.append(value)
        value = payload(); value["input"][0]["content"] = []; variants.append(value)
        with patch("skillopt_verusage.text_context._load_tokenizer") as loader:
            for value in variants:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    context_admission(value)
            loader.assert_not_called()

    def test_bad_caps_or_partial_configuration_do_not_fall_back(self):
        for cap in [0, -1, True, 1.5, None]:
            value = payload(); value["max_output_tokens"] = cap
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                context_admission(value)
        for kwargs in [{"tokenizer_path": "missing"}, {"expected_sha256": "a" * 64},
                       {"tokenizer_path": "missing", "expected_sha256": "not-a-hash"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                context_admission(payload(), **kwargs)

    def test_hash_mismatch_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"; file.write_text("{}")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                context_admission(payload(), tokenizer_path=file, expected_sha256="0" * 64)

    def test_missing_or_invalid_configured_json_never_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"
            with self.assertRaises(FileNotFoundError):
                context_admission(payload(), tokenizer_path=file, expected_sha256="0" * 64)
            if importlib.util.find_spec("tokenizers"):
                file.write_text("{}")
                sha = hashlib.sha256(file.read_bytes()).hexdigest()
                with self.assertRaises(Exception):
                    context_admission(payload(), tokenizer_path=file, expected_sha256=sha)

    def test_model_text_bound_rounds_margin_up_without_outer_http_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"; file.write_text("{}")
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            fake = SimpleNamespace(encode=lambda text, **kw: SimpleNamespace(ids=range(120001 if text.startswith("{") else 90001)))
            with patch("skillopt_verusage.text_context._load_tokenizer", return_value=fake):
                receipt = context_admission(payload(), tokenizer_path=file, expected_sha256=sha)
            self.assertEqual(receipt["input_token_bound"], 90001)
            self.assertEqual(receipt["safety_margin_tokens"], 9001)
            self.assertEqual(receipt["admission_total"], 90001 + 9001 + 16384)
            self.assertEqual(receipt['serialized_payload_tokens'],120001)
            self.assertEqual(receipt['input_bound_basis'],'framed_text')

    def test_outer_encoding_does_not_reject_a_complete_supported_request(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'tokenizer.json'; file.write_text('{}')
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            fake = SimpleNamespace(encode=lambda text, **kw: SimpleNamespace(ids=range(1034323 if text.startswith('{') else 834976)))
            with patch('skillopt_verusage.text_context._load_tokenizer',return_value=fake):
                receipt = context_admission(payload(),tokenizer_path=file,expected_sha256=sha)
            self.assertEqual(receipt['admission_total'],934858)
            self.assertEqual(receipt['safety_margin_tokens'],83498)
            self.assertLess(receipt['admission_total'],CONTEXT_WINDOW)

    def test_uncalibrated_formats_and_multipart_keep_transport_bound(self):
        variants = []
        value = payload(); value['text'] = {'format':{'type':'json_schema','schema':{'type':'object'}}}; variants.append(value)
        value = payload(); value['reasoning'] = {'effort':'max'}; variants.append(value)
        value = payload(); value['stream'] = True; variants.append(value)
        value = payload(); value['input'][0]['content'].append({'type':'input_text','text':'second'}); variants.append(value)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'tokenizer.json'; file.write_text('{}')
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            fake = SimpleNamespace(encode=lambda text, **kw: SimpleNamespace(ids=range(120001 if text.startswith('{') else 90001)))
            with patch('skillopt_verusage.text_context._load_tokenizer',return_value=fake):
                for value in variants:
                    with self.subTest(value=value):
                        receipt = context_admission(value,tokenizer_path=file,expected_sha256=sha)
                        self.assertEqual(receipt['input_token_bound'],120001)
                        self.assertEqual(receipt['input_bound_basis'],'max_framed_and_transport')

    def test_token_admission_rejects_output_plus_margin_not_just_input(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"; file.write_text("{}")
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            fake = SimpleNamespace(encode=lambda *args, **kw: SimpleNamespace(ids=range(950000)))
            with patch("skillopt_verusage.text_context._load_tokenizer", return_value=fake):
                with self.assertRaisesRegex(ValueError, "context admission"):
                    context_admission(payload(), tokenizer_path=file, expected_sha256=sha)

    def test_configured_tokenizer_does_not_apply_the_old_byte_gate(self):
        value = payload(); value["instructions"] = "x" * (CONTEXT_WINDOW + 10)
        seen = []

        def encode(text, **kwargs):
            seen.append(text)
            return SimpleNamespace(ids=range(100))

        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"; file.write_text("{}")
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            with patch("skillopt_verusage.text_context._load_tokenizer", return_value=SimpleNamespace(encode=encode)):
                receipt = context_admission(value, tokenizer_path=file, expected_sha256=sha)
        self.assertGreater(receipt["serialized_payload_bytes"], CONTEXT_WINDOW)
        self.assertEqual(receipt["admission_total"], 100 + 8192 + 16384)
        self.assertIn(value["instructions"], seen[0])
        self.assertEqual(json.loads(seen[1]), value)

    @unittest.skipUnless(importlib.util.find_spec("tokenizers"), "optional tokenizers library unavailable")
    def test_configured_truncation_and_padding_are_disabled_for_full_count(self):
        from tokenizers import Tokenizer, models, pre_tokenizers

        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"
            tokenizer = Tokenizer(models.WordLevel({"[UNK]": 0, "hello": 1}, unk_token="[UNK]"))
            tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
            tokenizer.enable_truncation(max_length=2)
            tokenizer.save(str(file))
            self.assertEqual(len(Tokenizer.from_file(str(file)).encode("hello " * 50).ids), 2)
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            _load_tokenizer.cache_clear()
            value = payload(); value["instructions"] = "hello " * 50
            receipt = context_admission(value, tokenizer_path=file, expected_sha256=sha)
            self.assertGreater(receipt["framed_text_tokens"], 50)
            self.assertGreater(receipt["serialized_payload_tokens"], 50)
            tokenizer.enable_padding(length=200, pad_id=0, pad_token="[UNK]")
            tokenizer.save(str(file))
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            padded = context_admission(value, tokenizer_path=file, expected_sha256=sha)
            self.assertEqual(padded["framed_text_tokens"], receipt["framed_text_tokens"])
            self.assertEqual(padded["serialized_payload_tokens"], receipt["serialized_payload_tokens"])
            _load_tokenizer.cache_clear()

    @unittest.skipUnless(importlib.util.find_spec("tokenizers"), "optional tokenizers library unavailable")
    def test_small_actual_static_json_tokenizer_and_cache_hash_recheck(self):
        from tokenizers import Tokenizer, models, pre_tokenizers

        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "tokenizer.json"
            tokenizer = Tokenizer(models.WordLevel({"[UNK]": 0, "hello": 1, "system": 2}, unk_token="[UNK]"))
            tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
            tokenizer.save(str(file))
            sha = hashlib.sha256(file.read_bytes()).hexdigest()
            _load_tokenizer.cache_clear()
            with patch("tokenizers.Tokenizer.from_str", wraps=Tokenizer.from_str) as loader:
                first = context_admission(payload(), tokenizer_path=file, expected_sha256=sha)
                second = context_admission(payload(), tokenizer_path=file, expected_sha256=sha)
                self.assertEqual(first, second)
                self.assertEqual(loader.call_count, 1)
                self.assertEqual(first["safety_margin_tokens"], 8192)
                self.assertEqual(first["method"], "static_v4_tokenizer_with_margin")
                file.write_text("{}")
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    context_admission(payload(), tokenizer_path=file, expected_sha256=sha)
            _load_tokenizer.cache_clear()


if __name__ == "__main__":
    unittest.main()
