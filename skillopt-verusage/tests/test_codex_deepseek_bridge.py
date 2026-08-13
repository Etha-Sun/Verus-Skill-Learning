from __future__ import annotations

import unittest

from skillopt_verusage.codex_deepseek_bridge import (
    responses_sse_events,
    translate_responses_request,
)


class CodexDeepSeekBridgeTests(unittest.TestCase):
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
                    {"type": "function", "name": "request_user_input", "parameters": {}},
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
        done = [event for event in events if event["type"] == "response.output_item.done"]
        self.assertEqual(done[0]["item"]["type"], "function_call")
        self.assertEqual(done[0]["item"]["call_id"], "call-2")


if __name__ == "__main__":
    unittest.main()
