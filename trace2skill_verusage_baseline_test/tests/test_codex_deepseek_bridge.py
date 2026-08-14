from __future__ import annotations

import unittest

from verus_agent.codex_harness.upstream_skillopt.codex_deepseek_bridge import (
    _native_response_usage,
    responses_sse_events,
    translate_responses_request,
)


class CodexDeepSeekBridgeTests(unittest.TestCase):
    def test_extracts_native_responses_usage(self) -> None:
        body = (
            'event: response.completed\n'
            'data: {"type":"response.completed","response":'
            '{"status":"completed","model":"deepseek-v4-pro-0813","usage":'
            '{"input_tokens":100,"input_tokens_details":{"cached_tokens":60},'
            '"output_tokens":25,"output_tokens_details":{"reasoning_tokens":20},'
            '"total_tokens":125}}}\n\n'
            'data: [DONE]\n\n'
        ).encode()
        usage, model, status = _native_response_usage(body)
        self.assertEqual(model, "deepseek-v4-pro-0813")
        self.assertEqual(status, "completed")
        self.assertEqual(usage["prompt_cache_hit_tokens"], 60)
        self.assertEqual(usage["prompt_cache_miss_tokens"], 40)
        self.assertEqual(usage["completion_tokens"], 25)

    def test_translates_codex_tool_history(self) -> None:
        translated, types = translate_responses_request(
            {
                "instructions": "system rules",
                "input": [
                    {"type": "message", "role": "user", "content": [
                        {"type": "input_text", "text": "read it"}
                    ]},
                    {"type": "function_call", "call_id": "call-1",
                     "name": "exec_command", "arguments": '{"cmd":"pwd"}'},
                    {"type": "function_call_output", "call_id": "call-1",
                     "output": "workspace"},
                ],
                "tools": [{"type": "function", "name": "exec_command",
                           "description": "run command", "parameters": {"type": "object"}}],
            },
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            allowed_tool_names=frozenset({"exec_command"}),
        )
        self.assertEqual(translated["messages"][0]["role"], "system")
        self.assertEqual(translated["messages"][2]["tool_calls"][0]["id"], "call-1")
        self.assertEqual(translated["messages"][3]["role"], "tool")
        self.assertEqual(types, {"exec_command": "function"})

    def test_filters_non_workspace_tools(self) -> None:
        translated, types = translate_responses_request(
            {"input": [], "tools": [
                {"type": "function", "name": "exec_command", "parameters": {}},
                {"type": "function", "name": "request_user_input", "parameters": {}},
                {"type": "namespace", "name": "mcp__codex_apps__github"},
            ]},
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            allowed_tool_names=frozenset({"exec_command", "write_stdin"}),
        )
        self.assertEqual(
            [tool["function"]["name"] for tool in translated["tools"]],
            ["exec_command"],
        )
        self.assertEqual(types, {"exec_command": "function"})

    def test_restores_reasoning_for_tool_history(self) -> None:
        translated, _ = translate_responses_request(
            {"input": [
                {"type": "function_call", "call_id": "call-1",
                 "name": "exec_command", "arguments": '{"cmd":"pwd"}'},
                {"type": "function_call_output", "call_id": "call-1",
                 "output": "workspace"},
            ]},
            model="deepseek-v4-flash",
            max_output_tokens=32768,
            reasoning_by_call={"call-1": "private continuity state"},
        )
        self.assertEqual(
            translated["messages"][0]["reasoning_content"],
            "private continuity state",
        )

    def test_emits_text_and_function_call_response_streams(self) -> None:
        text_events = responses_sse_events(
            {"model": "deepseek-v4-flash", "choices": [{"message": {
                "role": "assistant", "content": "READY"}, "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 10, "prompt_cache_hit_tokens": 4,
                       "completion_tokens": 2, "total_tokens": 12}},
            request_model="deepseek-v4-flash",
        )
        self.assertEqual(text_events[-1]["type"], "response.completed")
        self.assertEqual(
            text_events[-1]["response"]["output"][0]["content"][0]["text"],
            "READY",
        )
        call_events = responses_sse_events(
            {"model": "deepseek-v4-flash", "choices": [{"message": {
                "role": "assistant", "content": None, "tool_calls": [{
                    "id": "call-2", "type": "function",
                    "function": {"name": "exec_command", "arguments": "{}"}
                }]}, "finish_reason": "tool_calls"}], "usage": {}},
            request_model="deepseek-v4-flash",
        )
        done = [event for event in call_events
                if event["type"] == "response.output_item.done"]
        self.assertEqual(done[0]["item"]["call_id"], "call-2")


if __name__ == "__main__":
    unittest.main()
