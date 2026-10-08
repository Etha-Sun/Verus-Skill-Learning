"""Outer transport escaping is not another layer of model-visible input text."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from skillopt_verusage.text_context import CONTEXT_WINDOW, context_admission


def payload():
    return {"model": "deepseek-v4-pro", "instructions": "preserve complete evidence",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "evidence"}]}],
            "reasoning": {"effort": "high"}, "text": {"format": {"type": "json_object"}},
            "stream": False, "max_output_tokens": 16384}


def counter(tmp_path, monkeypatch, framed=100, transport=200):
    path = tmp_path / "tokenizer.json"; path.write_text("{}")
    seen = []

    def encode(text, **kwargs):
        seen.append((text, kwargs))
        return SimpleNamespace(ids=range(transport if text.startswith("{") else framed))

    monkeypatch.setattr("skillopt_verusage.text_context._load_tokenizer",
                        lambda *args: SimpleNamespace(encode=encode))
    return {"tokenizer_path": path, "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, seen


def test_internal_json_escaping_is_preserved_exactly_and_wire_hash_is_unchanged(tmp_path, monkeypatch):
    value = payload()
    internal = {"proof": 'quoted "term"\nnext line\\literal\\n你好',
                "snapshot": json.dumps({"body": "assertion text\nwith quotes: \"x\""})}
    user = json.dumps(internal, ensure_ascii=False)
    value["input"][0]["content"][0]["text"] = user
    value["instructions"] = 'system "quotes"\nwith\\slashes'
    before = copy.deepcopy(value)
    wire = json.dumps(value, ensure_ascii=False).encode()
    config, seen = counter(tmp_path, monkeypatch, framed=300, transport=1100000)
    receipt = context_admission(value, **config)
    expected = ("<｜begin▁of▁sentence｜>" + value["instructions"] + "<｜User｜>" + user
                + "<｜Assistant｜><think>")
    assert seen[0] == (expected, {"add_special_tokens": False})
    assert seen[1] == (wire.decode(), {"add_special_tokens": False})
    assert user in seen[0][0]
    assert "\\n" in user and "\\\\" in user
    assert json.loads(user) == internal
    assert value == before
    assert json.dumps(value, ensure_ascii=False).encode() == wire
    assert receipt["request_sha256"] == hashlib.sha256(wire).hexdigest()
    assert receipt["serialized_payload_bytes"] == len(wire)
    assert receipt["serialized_payload_tokens"] == 1100000
    assert receipt["input_token_bound"] == 300
    assert receipt["input_bound_basis"] == "framed_text"
    assert receipt["admission_total"] == 300 + 8192 + 16384


def test_exact_context_boundary_passes_and_one_more_model_token_fails(tmp_path, monkeypatch):
    config, _ = counter(tmp_path, monkeypatch, framed=938356, transport=1100000)
    receipt = context_admission(payload(), **config)
    assert receipt["safety_margin_tokens"] == 93836
    assert receipt["max_output_tokens"] == 16384
    assert receipt["admission_total"] == CONTEXT_WINDOW
    config, _ = counter(tmp_path, monkeypatch, framed=938357, transport=1100000)
    with pytest.raises(ValueError, match="context admission"):
        context_admission(payload(), **config)


@pytest.mark.parametrize("framed,margin", [(0, 8192), (81920, 8192), (81921, 8193), (834976, 83498)])
def test_minimum_margin_and_ten_percent_ceiling_are_unchanged(tmp_path, monkeypatch, framed, margin):
    config, _ = counter(tmp_path, monkeypatch, framed=framed, transport=1100000)
    receipt = context_admission(payload(), **config)
    assert receipt["safety_margin_tokens"] == margin
    assert receipt["admission_total"] == framed + margin + 16384


@pytest.mark.parametrize("kind", ["schema", "schema_extra", "multipart", "max_effort", "stream",
                                   "missing_stream", "missing_reasoning", "format_extra"])
def test_uncalibrated_contracts_keep_max_transport_bound(tmp_path, monkeypatch, kind):
    value = payload()
    if kind == "schema": value["text"] = {"format": {"type": "json_schema", "schema": {"type": "object"}}}
    elif kind == "schema_extra": value["text"]["format"]["schema"] = {"description": "large schema"}
    elif kind == "multipart": value["input"][0]["content"].append({"type": "input_text", "text": "second part"})
    elif kind == "max_effort": value["reasoning"] = {"effort": "max"}
    elif kind == "stream": value["stream"] = True
    elif kind == "missing_stream": value.pop("stream")
    elif kind == "missing_reasoning": value.pop("reasoning")
    else: value["text"]["verbosity"] = "high"
    config, _ = counter(tmp_path, monkeypatch, framed=100, transport=90001)
    receipt = context_admission(value, **config)
    assert receipt["input_bound_basis"] == "max_framed_and_transport"
    assert receipt["input_token_bound"] == 90001
    assert receipt["safety_margin_tokens"] == 9001
    assert receipt["admission_total"] == 90001 + 9001 + 16384
    config, _ = counter(tmp_path, monkeypatch, framed=100, transport=938357)
    with pytest.raises(ValueError, match="context admission"):
        context_admission(value, **config)


def test_uncalibrated_max_still_preserves_a_larger_model_text_count(tmp_path, monkeypatch):
    value = payload(); value["stream"] = True
    config, _ = counter(tmp_path, monkeypatch, framed=90001, transport=100)
    receipt = context_admission(value, **config)
    assert receipt["input_token_bound"] == 90001


def test_no_tokenizer_still_uses_transport_utf8_byte_bound(monkeypatch):
    monkeypatch.setattr("skillopt_verusage.text_context._load_tokenizer",
                        lambda *args: pytest.fail("Unconfigured path must not load a tokenizer"))
    value = payload(); value["input"][0]["content"][0]["text"] = '"\\\n你好' * 100
    wire = json.dumps(value, ensure_ascii=False).encode()
    receipt = context_admission(value)
    assert receipt["method"] == "conservative_utf8_byte_bound"
    assert receipt["admission_total"] == len(wire) + 16384
    assert receipt["request_sha256"] == hashlib.sha256(wire).hexdigest()
    value["instructions"] = "x" * CONTEXT_WINDOW
    with pytest.raises(ValueError, match="context admission"):
        context_admission(value)


def test_configured_hash_mismatch_cannot_fall_back_to_any_smaller_bound(tmp_path, monkeypatch):
    config, _ = counter(tmp_path, monkeypatch, framed=1, transport=2)
    config["expected_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        context_admission(payload(), **config)
