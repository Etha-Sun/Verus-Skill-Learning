"""Local HTTP clients cannot turn a halted native bridge into another paid call."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection, IncompleteRead
from http.server import ThreadingHTTPServer
import hashlib
import json
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from skillopt_verusage import codex_deepseek_bridge as bridge


def completed_body(**overrides):
    return json.dumps({"status": "completed", "model": "deepseek-v4-pro",
                       "usage": {"input_tokens": 10, "output_tokens": 2}, **overrides}).encode()


class Response:
    headers = SimpleNamespace(get_content_type=lambda: "application/json")

    def __init__(self, body, error=None):
        self.body, self.error = body, error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        if self.error:
            raise self.error
        return self.body


@contextmanager
def server_for(config):
    server = ThreadingHTTPServer(("127.0.0.1", 0), bridge.make_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def post(server, payload):
    client = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        client.request("POST", "/tasks/actor--fixture/v1/responses", body=json.dumps(payload),
                       headers={"Content-Type": "application/json"})
        response = client.getresponse()
        return response.status, response.read()
    finally:
        client.close()


def config_for(tmp_path, **kwargs):
    return bridge.BridgeConfig(model="deepseek-v4-pro", upstream_base_url="https://example.invalid",
        api_key="fixture-secret-not-a-credential", ledger_path=tmp_path/"provider_calls.jsonl",
        max_output_tokens=32, retry_output_tokens=32, request_timeout_seconds=1,
        native_responses=True, pricing_profile="deepseek-current", **kwargs)


def ledger(config):
    return [json.loads(line) for line in config.ledger_path.read_text().splitlines()]


def test_identical_client_retry_is_denied_before_upstream_or_reserve(tmp_path, monkeypatch):
    # Even a partial body containing a completed terminal event must not validate.
    partial = completed_body()
    network = Mock(side_effect=[Response(b"", IncompleteRead(partial)), Response(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    guard = Mock()
    guard.reserve.return_value = "fixture-reservation"
    config = config_for(tmp_path, fail_closed_on_provider_error=True, budget_guard=guard)
    payload = {"input": [{"role": "user", "content": "fixture task"}]}
    with server_for(config) as server:
        first_status, first_body = post(server, payload)
        second_status, second_body = post(server, payload)
    assert first_status in (409, 502) and b"IncompleteRead" in first_body
    assert second_status == 409 and b"halted pending review" in second_body
    assert network.call_count == guard.reserve.call_count == 1
    guard.settle.assert_called_once_with("fixture-reservation", cost_usd=None, usage=None)
    rows = ledger(config)
    assert len(rows) == 1 and rows[0]["task_id"] == "actor--fixture"
    assert rows[0]["attempts"][0]["usage"] is None
    assert rows[0]["attempts"][0]["estimated_cost_usd"] is None
    assert "IncompleteRead" in config.halted_error
    directory = config.ledger_path.parent/rows[0]["failure_evidence_relative_path"]
    assert directory.parent.name == "provider_failure_evidence"
    assert (directory/"response.partial.raw").read_bytes() == partial
    request = (directory/"request.json").read_bytes()
    evidence = json.loads((directory/"error.json").read_text())
    assert evidence["request_sha256"] == hashlib.sha256(request).hexdigest()
    assert evidence["partial_body_sha256"] == hashlib.sha256(partial).hexdigest()
    assert evidence["partial_body_bytes"] == len(partial)
    assert evidence["partial_response_accepted"] is False
    assert json.loads(request) == {**payload, "model": "deepseek-v4-pro", "max_output_tokens": 32}
    assert config.api_key.encode() not in request
    assert not (directory/"validated.json").exists()
    assert not (directory/"response.raw").exists()


def test_two_valid_client_posts_remain_allowed_with_campaign_flag(tmp_path, monkeypatch):
    network = Mock(side_effect=[Response(completed_body()), Response(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    config = config_for(tmp_path, fail_closed_on_provider_error=True)
    with server_for(config) as server:
        assert post(server, {"input": []})[0] == 200
        assert post(server, {"input": []})[0] == 200
    assert network.call_count == 2 and config.halted_error is None
    assert len(ledger(config)) == 2
    assert all(row["attempts"][0]["estimated_cost_usd"] is not None for row in ledger(config))
    assert not (tmp_path/"provider_failure_evidence").exists()


def test_default_bridge_keeps_legacy_non_latching_behavior(tmp_path, monkeypatch):
    network = Mock(side_effect=[Response(b"", IncompleteRead(b"partial")), Response(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    config = config_for(tmp_path)
    assert config.fail_closed_on_provider_error is False
    with server_for(config) as server:
        assert post(server, {"input": []})[0] == 502
        assert post(server, {"input": []})[0] == 200
    assert network.call_count == 2 and config.halted_error is None
    rows = ledger(config)
    assert len(rows) == 2 and rows[0]["attempts"][0]["estimated_cost_usd"] is None
    assert "failure_evidence_relative_path" not in rows[0]


@pytest.mark.parametrize("bad_body", [b"not-json", completed_body(usage=None),
    completed_body(model="wrong-model"), completed_body(status="incomplete")])
def test_protocol_errors_also_stop_subsequent_client_posts(tmp_path, monkeypatch, bad_body):
    network = Mock(side_effect=[Response(bad_body), Response(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    config = config_for(tmp_path, fail_closed_on_provider_error=True)
    with server_for(config) as server:
        assert post(server, {"input": []})[0] in (409, 502)
        assert post(server, {"input": []})[0] == 409
    assert network.call_count == 1 and config.halted_error
    rows = ledger(config)
    assert len(rows) == 1 and rows[0]["attempts"][0]["error"]
    evidence = json.loads((tmp_path/rows[0]["failure_evidence_relative_path"]/"error.json").read_text())
    assert evidence["partial_response_accepted"] is False


def test_direct_native_call_is_halted_even_without_http_handler_or_ledger(tmp_path, monkeypatch):
    network = Mock(side_effect=[Response(b"", IncompleteRead(b"partial")), Response(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    config = config_for(tmp_path, fail_closed_on_provider_error=True)
    config.ledger_path = None
    with pytest.raises(IncompleteRead):
        bridge.forward_native_responses(config, {"input": []})
    with pytest.raises(RuntimeError, match="halted pending review"):
        bridge.forward_native_responses(config, {"input": []})
    assert network.call_count == 1


def test_inflight_request_may_finish_but_cannot_clear_the_halt(tmp_path, monkeypatch):
    first_started, second_started, finish_second = (threading.Event() for _ in range(3))
    class FirstResponse(Response):
        def read(self):
            first_started.set()
            assert second_started.wait(3)
            raise IncompleteRead(b"partial")
    class SecondResponse(Response):
        def read(self):
            second_started.set()
            assert finish_second.wait(3)
            return self.body
    network = Mock(side_effect=[FirstResponse(b""), SecondResponse(completed_body())])
    monkeypatch.setattr(bridge, "urlopen", network)
    config = config_for(tmp_path, fail_closed_on_provider_error=True)
    with server_for(config) as server, ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(post, server, {"input": []})
        assert first_started.wait(3)
        second = pool.submit(post, server, {"input": []})
        try:
            assert first.result(timeout=3)[0] in (409, 502)
            assert post(server, {"input": []})[0] == 409
            assert network.call_count == 2
        finally:
            finish_second.set()
        assert second.result(timeout=3)[0] == 200
        assert post(server, {"input": []})[0] == 409
    assert network.call_count == 2 and config.halted_error
    rows = ledger(config)
    assert len(rows) == 2
    assert sum(row["attempts"][0]["estimated_cost_usd"] is None for row in rows) == 1
