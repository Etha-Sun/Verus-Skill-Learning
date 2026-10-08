"""Complete-input admission for history-free, text-only Responses requests.

Offline tokenizer counts are estimates of hosted framing, not provider usage.
No tokenizer configuration means the prior conservative UTF-8 byte bound applies.
Invalid configured tokenizers never fall back to that bound.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


CONTEXT_WINDOW = 1048576


def _verified_json(path, expected_sha256):
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Configured context tokenizer SHA-256 mismatch")
    return content.decode("utf-8")


@lru_cache(maxsize=4)
def _load_tokenizer(path, expected_sha256):
    from tokenizers import Tokenizer

    # Static tokenizer JSON only; no AutoTokenizer or downloaded Python imports.
    tokenizer = Tokenizer.from_str(_verified_json(path, expected_sha256))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def context_admission(payload, *, tokenizer_path=None, expected_sha256=None):
    """Return a conservative receipt, or reject unsupported/oversized requests.

    Only one user message containing input_text parts is supported. Tool calls,
    images, files, prior responses and message histories need separate accounting.
    """
    allowed = {"model", "instructions", "input", "reasoning", "max_output_tokens", "text", "stream"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError("Unsupported text-only context request fields")
    if payload.get("model") != "deepseek-v4-pro" or not isinstance(payload.get("instructions"), str):
        raise ValueError("Text-only context requires Pro and string instructions")
    output = payload.get("max_output_tokens")
    if not isinstance(output, int) or isinstance(output, bool) or output <= 0:
        raise ValueError("Text-only context requires a positive integer output cap")
    messages = payload.get("input")
    if not isinstance(messages, list) or len(messages) != 1:
        raise ValueError("Text-only context does not support message history")
    message = messages[0]
    if (not isinstance(message, dict) or set(message) - {"type", "role", "content"}
            or message.get("role") != "user" or message.get("type", "message") != "message"):
        raise ValueError("Text-only context requires one user message")
    parts = message.get("content")
    if not isinstance(parts, list) or not parts:
        raise ValueError("Text-only context requires input_text content")
    if any(not isinstance(part, dict) or set(part) != {"type", "text"}
           or part["type"] != "input_text" or not isinstance(part["text"], str) for part in parts):
        raise ValueError("Text-only context does not support non-text content")
    serialized = json.dumps(payload, ensure_ascii=False)
    receipt = {"context_window": CONTEXT_WINDOW, "max_output_tokens": output,
               "serialized_payload_bytes": len(serialized.encode()),
               "request_sha256": hashlib.sha256(serialized.encode()).hexdigest()}
    if tokenizer_path is None and expected_sha256 is None:
        receipt.update({"method": "conservative_utf8_byte_bound", "safety_margin_tokens": 0,
                        "admission_total": receipt["serialized_payload_bytes"] + output})
    else:
        if tokenizer_path is None or not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("Context tokenizer requires both path and expected SHA-256")
        path = str(Path(tokenizer_path).resolve())
        # Recheck every call, including cache hits: changed files cannot bypass the hash gate.
        _verified_json(path, expected_sha256)
        tokenizer = _load_tokenizer(path, expected_sha256)
        user = "".join(part["text"] for part in parts)
        framed = ("<｜begin▁of▁sentence｜>" + payload["instructions"] + "<｜User｜>" + user
                  + "<｜Assistant｜><think>")
        text_tokens = len(tokenizer.encode(framed, add_special_tokens=False).ids)
        json_tokens = len(tokenizer.encode(serialized, add_special_tokens=False).ids)
        # For the calibrated one-part JSON-object request, outer HTTP escaping
        # is transport encoding, not model-visible text. Internal user JSON
        # escaping remains in `framed`. Other formats (especially schemas) and
        # multipart framing retain the conservative transport bound.
        framed_only = (len(parts) == 1 and payload.get('reasoning') == {'effort':'high'}
                       and payload.get('text') == {'format':{'type':'json_object'}}
                       and payload.get('stream') is False)
        bound = text_tokens if framed_only else max(text_tokens, json_tokens)
        margin = max(8192, (bound + 9) // 10)
        receipt.update({"method": "static_v4_tokenizer_with_margin", "tokenizer_path": path,
                        "tokenizer_sha256": expected_sha256, "framed_text_tokens": text_tokens,
                        "serialized_payload_tokens": json_tokens, "input_token_bound": bound,
                        "input_bound_basis": "framed_text" if framed_only else "max_framed_and_transport",
                        "safety_margin_tokens": margin, "admission_total": bound + margin + output})
    if receipt["admission_total"] > CONTEXT_WINDOW:
        raise ValueError("Complete request exceeds text-only context admission")
    return receipt
