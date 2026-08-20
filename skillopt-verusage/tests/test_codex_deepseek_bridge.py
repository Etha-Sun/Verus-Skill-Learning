from __future__ import annotations

import json
import tempfile
import unittest
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from skillopt_verusage.codex_deepseek_bridge import (
    BridgeConfig,
    _compatible_upstream_model,
    _native_response_usage,
    _post_chat,
    forward_native_responses,
    forward_responses,
    responses_sse_events,
    translate_responses_request,
)


class CodexDeepSeekBridgeTests(unittest.TestCase):
    def test_chat_retries_rate_limit_and_records_backoff(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            @staticmethod
            def read():
                return b'{"model":"glm-5.3","choices":[],"usage":{}}'

        headers = Message()
        headers["Retry-After"] = "2"
        rate_limit = HTTPError(
            "https://example.invalid/chat/completions",
            429,
            "rate limited",
            headers,
            BytesIO(b'{"error":"rate limited"}'),
        )
        config = BridgeConfig(
            model="glm-5.3",
            upstream_base_url="https://example.invalid",
            api_key="secret",
            ledger_path=None,
            max_output_tokens=1,
            retry_output_tokens=1,
            request_timeout_seconds=10,
            rate_limit_retries=1,
            rate_limit_backoff_seconds=1,
            rate_limit_max_backoff_seconds=3,
        )
        with (
            patch(
                "skillopt_verusage.codex_deepseek_bridge.urlopen",
                side_effect=[rate_limit, Response()],
            ) as mocked_urlopen,
            patch(
                "skillopt_verusage.codex_deepseek_bridge.random.uniform",
                return_value=0.25,
            ),
            patch("skillopt_verusage.codex_deepseek_bridge.time.sleep") as sleep,
        ):
            candidate, metadata = _post_chat(config, {"messages": []})
        self.assertEqual(candidate["model"], "glm-5.3")
        self.assertEqual(metadata["rate_limit_retries"], 1)
        self.assertEqual(metadata["rate_limit_sleep_seconds"], 2.25)
        self.assertEqual(mocked_urlopen.call_count, 2)
        sleep.assert_called_once_with(2.25)

    def test_openai_style_cached_input_usage_is_preserved(self) -> None:
        events = responses_sse_events(
            {
                "model": "glm-5.3",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "READY"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "prompt_tokens_details": {"cached_tokens": 80},
                    "completion_tokens": 5,
                },
            },
            request_model="glm-5.3",
        )
        usage = events[-1]["response"]["usage"]
        self.assertEqual(usage["input_tokens_details"]["cached_tokens"], 80)

    def test_extracts_usage_without_rewriting_native_response_stream(self) -> None:
        body = (
            "event: response.completed\n"
            'data: {"type":"response.completed","response":'
            '{"status":"completed","model":"deepseek-v4-pro","usage":'
            '{"input_tokens":100,"input_tokens_details":{"cached_tokens":60},'
            '"output_tokens":25,"output_tokens_details":{"reasoning_tokens":20},'
            '"total_tokens":125}}}\n\n'
            "data: [DONE]\n\n"
        ).encode()
        usage, model, status = _native_response_usage(body)
        self.assertEqual(model, "deepseek-v4-pro")
        self.assertEqual(status, "completed")
        self.assertEqual(usage["prompt_cache_hit_tokens"], 60)
        self.assertEqual(usage["prompt_cache_miss_tokens"], 40)
        self.assertEqual(usage["completion_tokens"], 25)

    def test_upstream_model_check_uses_observed_exact_alias(self) -> None:
        self.assertTrue(
            _compatible_upstream_model("deepseek-v4-pro", "deepseek-v4-pro")
        )
        self.assertFalse(
            _compatible_upstream_model("deepseek-v4-pro", "deepseek-v4-pro-0813")
        )

    def test_native_responses_fail_closed_on_invalid_terminal_payloads(self) -> None:
        class Headers:
            @staticmethod
            def get_content_type():
                return "text/event-stream"

        class Response:
            headers = Headers()

            def __init__(self, body: bytes):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        cases = {
            "malformed": b"not-json-or-sse",
            "incomplete": (
                b'data: {"type":"response.incomplete","response":'
                b'{"status":"incomplete","model":"deepseek-v4-pro-0813",'
                b'"usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
            ),
            "missing_usage": (
                b'data: {"type":"response.completed","response":'
                b'{"status":"completed","model":"deepseek-v4-pro-0813"}}\n\n'
            ),
            "wrong_model": (
                b'data: {"type":"response.completed","response":'
                b'{"status":"completed","model":"another-model",'
                b'"usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
            ),
        }
        for label, body in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                ledger = Path(tmp) / "bridge.jsonl"
                config = BridgeConfig(
                    model="deepseek-v4-pro",
                    upstream_base_url="https://example.invalid",
                    api_key="secret",
                    ledger_path=ledger,
                    max_output_tokens=1,
                    retry_output_tokens=1,
                    request_timeout_seconds=1,
                    native_responses=True,
                )
                with patch(
                    "skillopt_verusage.codex_deepseek_bridge.urlopen",
                    return_value=Response(body),
                ):
                    with self.assertRaises(RuntimeError):
                        forward_native_responses(config, {"input": []}, task_id="t")
                row = json.loads(ledger.read_text(encoding="utf-8"))
                self.assertTrue(row["attempts"][0]["error"])

    def test_translates_codex_history_and_tools(self) -> None:
        payload = {
            "instructions": "system rules",
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "read it"}],
                },
                {
                    "type": "function_call",
                    "call_id": "call-1",
                    "name": "shell",
                    "arguments": '{"command":"pwd"}',
                },
                {
                    "type": "function_call_output",
                    "call_id": "call-1",
                    "output": "workspace",
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "name": "shell",
                    "description": "run command",
                    "parameters": {"type": "object"},
                }
            ],
        }
        translated, types = translate_responses_request(
            payload,
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            allowed_tool_names=frozenset({"shell"}),
        )
        self.assertEqual(translated["model"], "deepseek-v4-flash")
        self.assertEqual(translated["messages"][0]["role"], "system")
        self.assertEqual(translated["messages"][2]["tool_calls"][0]["id"], "call-1")
        self.assertEqual(translated["messages"][3]["role"], "tool")
        self.assertEqual(translated["tools"][0]["function"]["name"], "shell")
        self.assertEqual(types, {"shell": "function"})

    def test_filters_non_workspace_tools(self) -> None:
        translated, types = translate_responses_request(
            {
                "input": [],
                "tools": [
                    {"type": "function", "name": "exec_command", "parameters": {}},
                    {
                        "type": "function",
                        "name": "request_user_input",
                        "parameters": {},
                    },
                    {"type": "namespace", "name": "mcp__codex_apps__github"},
                ],
            },
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            allowed_tool_names=frozenset({"exec_command", "write_stdin"}),
        )
        self.assertEqual(
            [tool["function"]["name"] for tool in translated["tools"]],
            ["exec_command"],
        )
        self.assertEqual(types, {"exec_command": "function"})

    def test_translates_custom_apply_patch_tool_and_history(self) -> None:
        translated, types = translate_responses_request(
            {
                "input": [
                    {
                        "type": "custom_tool_call",
                        "call_id": "patch-1",
                        "name": "apply_patch",
                        "input": "*** Begin Patch\n*** End Patch",
                    },
                    {
                        "type": "custom_tool_call_output",
                        "call_id": "patch-1",
                        "output": "Success",
                    },
                ],
                "tools": [
                    {
                        "type": "custom",
                        "name": "apply_patch",
                        "description": "Apply a patch",
                    }
                ],
            },
            model="qwen3.8-27b",
            max_output_tokens=65536,
            allowed_tool_names=frozenset({"apply_patch"}),
            chat_profile="qwen38",
        )
        self.assertEqual(types, {"apply_patch": "custom"})
        tool = translated["tools"][0]["function"]
        self.assertEqual(tool["name"], "apply_patch")
        self.assertEqual(tool["parameters"]["required"], ["input"])
        call = translated["messages"][0]["tool_calls"][0]
        self.assertEqual(
            json.loads(call["function"]["arguments"])["input"],
            "*** Begin Patch\n*** End Patch",
        )
        self.assertEqual(translated["messages"][1]["role"], "tool")

    def test_qwen_profile_uses_qwen_sampling_without_deepseek_fields(self) -> None:
        translated, _ = translate_responses_request(
            {"input": []},
            model="qwen3-8b",
            max_output_tokens=32768,
            chat_profile="qwen3",
        )
        self.assertNotIn("thinking", translated)
        self.assertNotIn("reasoning_effort", translated)
        self.assertEqual(translated["temperature"], 0.6)
        self.assertEqual(translated["chat_template_kwargs"], {"enable_thinking": True})

    def test_qwen38_profile_uses_official_xhigh_sampling(self) -> None:
        translated, _ = translate_responses_request(
            {"input": []},
            model="qwen3.8-27b",
            max_output_tokens=65536,
            chat_profile="qwen38",
        )
        self.assertNotIn("thinking", translated)
        self.assertNotIn("reasoning_effort", translated)
        self.assertEqual(translated["temperature"], 1.0)
        self.assertEqual(translated["top_p"], 0.95)
        self.assertEqual(translated["top_k"], 20)
        self.assertEqual(
            translated["chat_template_kwargs"], {"reasoning_effort": "xhigh"}
        )

    def test_qwen38_merges_all_system_messages_at_the_front(self) -> None:
        translated, _ = translate_responses_request(
            {
                "instructions": "base rules",
                "input": [
                    {"type": "message", "role": "user", "content": "task"},
                    {"type": "message", "role": "developer", "content": "late rules"},
                    {"type": "message", "role": "user", "content": "continue"},
                ],
            },
            model="qwen3.8-27b",
            max_output_tokens=65536,
            chat_profile="qwen38",
        )
        self.assertEqual(
            [message["role"] for message in translated["messages"]],
            ["system", "user", "user"],
        )
        self.assertEqual(
            translated["messages"][0]["content"], "base rules\n\nlate rules"
        )

    def test_duplicate_retry_budget_preserves_upstream_error(self) -> None:
        config = BridgeConfig(
            model="qwen3.8-27b",
            upstream_base_url="http://127.0.0.1:8000/v1",
            api_key="local",
            ledger_path=None,
            max_output_tokens=65536,
            retry_output_tokens=65536,
            request_timeout_seconds=1,
            expected_upstream_model="qwen3.8-27b",
            chat_profile="qwen38",
            pricing_profile="local-zero",
        )
        with patch(
            "skillopt_verusage.codex_deepseek_bridge._post_chat",
            side_effect=RuntimeError("upstream HTTP 400: exact diagnostic"),
        ):
            with self.assertRaisesRegex(RuntimeError, "exact diagnostic"):
                forward_responses(config, {"input": []})

    def test_glm_profile_preserves_interleaved_thinking(self) -> None:
        translated, _ = translate_responses_request(
            {"input": []},
            model="glm-5.3",
            max_output_tokens=32768,
            chat_profile="glm",
        )
        self.assertEqual(
            translated["thinking"], {"type": "enabled", "clear_thinking": False}
        )
        self.assertEqual(translated["reasoning_effort"], "max")

    def test_translated_chat_records_valid_terminal_model_and_local_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "bridge.jsonl"
            config = BridgeConfig(
                model="qwen3-8b",
                upstream_base_url="http://127.0.0.1:8000/v1",
                api_key="local",
                ledger_path=ledger,
                max_output_tokens=32768,
                retry_output_tokens=131072,
                request_timeout_seconds=1,
                expected_upstream_model="qwen3-8b",
                chat_profile="qwen3",
                pricing_profile="local-zero",
                fake_reply="READY",
            )
            events, record = forward_responses(config, {"input": []}, task_id="t")
            self.assertEqual(events[-1]["type"], "response.completed")
            self.assertEqual(record["upstream_model"], "qwen3-8b")
            self.assertEqual(record["attempts"][0]["finish_reason"], "completed")
            self.assertEqual(record["attempts"][0]["upstream_finish_reason"], "stop")
            self.assertEqual(record["attempts"][0]["estimated_cost_usd"], 0.0)

    def test_restores_deepseek_reasoning_for_tool_history(self) -> None:
        translated, _ = translate_responses_request(
            {
                "input": [
                    {
                        "type": "function_call",
                        "call_id": "call-1",
                        "name": "exec_command",
                        "arguments": '{"cmd":"pwd"}',
                    },
                    {
                        "type": "function_call_output",
                        "call_id": "call-1",
                        "output": "workspace",
                    },
                ]
            },
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            reasoning_by_call={"call-1": "private continuity state"},
        )
        self.assertEqual(
            translated["messages"][0]["reasoning_content"],
            "private continuity state",
        )

    def test_emits_complete_text_response_stream(self) -> None:
        events = responses_sse_events(
            {
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "READY"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "prompt_cache_hit_tokens": 4,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                },
            },
            request_model="deepseek-v4-flash",
        )
        self.assertEqual(events[0]["type"], "response.created")
        self.assertEqual(events[-1]["type"], "response.completed")
        completed = events[-1]["response"]
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["output"][0]["content"][0]["text"], "READY")
        self.assertEqual(completed["usage"]["input_tokens_details"]["cached_tokens"], 4)

    def test_emits_function_call_response_stream(self) -> None:
        events = responses_sse_events(
            {
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-2",
                                    "type": "function",
                                    "function": {"name": "shell", "arguments": "{}"},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {},
            },
            request_model="deepseek-v4-flash",
        )
        done = [
            event for event in events if event["type"] == "response.output_item.done"
        ]
        self.assertEqual(done[0]["item"]["type"], "function_call")
        self.assertEqual(done[0]["item"]["call_id"], "call-2")

    def test_emits_custom_tool_call_response_stream(self) -> None:
        events = responses_sse_events(
            {
                "model": "qwen3.8-27b",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "patch-1",
                                    "type": "function",
                                    "function": {
                                        "name": "apply_patch",
                                        "arguments": json.dumps(
                                            {"input": "*** Begin Patch\n*** End Patch"}
                                        ),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
            request_model="qwen3.8-27b",
            tool_types={"apply_patch": "custom"},
        )
        completed = events[-1]["response"]
        call = completed["output"][0]
        self.assertEqual(call["type"], "custom_tool_call")
        self.assertEqual(call["name"], "apply_patch")
        self.assertEqual(call["input"], "*** Begin Patch\n*** End Patch")


if __name__ == "__main__":
    unittest.main()
