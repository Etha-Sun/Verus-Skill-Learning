"""Storage failures halt dispatch even when failure evidence cannot be persisted."""
from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
from http.client import IncompleteRead
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from skillopt_verusage import guarded_deepseek as guarded


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(guarded, "context_admission", lambda *a, **k: {"admitted": True})
    monkeypatch.setattr(guarded.shutil, "disk_usage", lambda p: SimpleNamespace(free=2 << 30))
    return guarded.GuardedDeepSeek(root=tmp_path / "calls", api_key="fixture", guards=[],
                                   ledger=tmp_path / "ledger.jsonl")


def completed():
    body = json.dumps({"output": [{"type": "message", "content": [
        {"type": "output_text", "text": "{}"}]}]}).encode()
    usage = {"prompt_tokens": 10, "completion_tokens": 5}
    return body, None, {"attempts": [{"usage": usage}]}


def call(client, name="one"):
    return client.call(system="Synthetic system", user="Synthetic task", name=name)


@pytest.mark.parametrize("free,accepted", [(0, False), ((1 << 30) - 1, False),
                                            (1 << 30, True), ((1 << 30) + 1, True)])
def test_fixed_storage_reserve_boundary(tmp_path, monkeypatch, free, accepted):
    monkeypatch.setattr(guarded.shutil, "disk_usage", lambda p: SimpleNamespace(free=free))
    assert guarded.STORAGE_RESERVE_BYTES == 1 << 30
    if accepted:
        guarded.check_storage(tmp_path)
        assert not list(tmp_path.iterdir())
    else:
        with pytest.raises(OSError) as caught:
            guarded.check_storage(tmp_path)
        assert caught.value.errno == errno.ENOSPC


@pytest.mark.parametrize("probe", ["open", "fsync"])
def test_writable_probe_is_required_before_dispatch(client, monkeypatch, probe):
    error = PermissionError(errno.EACCES, "Storage is not writable")
    target = guarded.tempfile if probe == "open" else guarded.os
    monkeypatch.setattr(target, "TemporaryFile" if probe == "open" else "fsync",
                        Mock(side_effect=error))
    upstream = Mock(side_effect=AssertionError("No API call allowed"))
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(PermissionError) as caught:
        call(client)
    assert caught.value is error and client.errors
    upstream.assert_not_called()
    evidence = json.loads(next(client.root.glob("one/*/error.json")).read_text())
    assert evidence["upstream_dispatched"] is False
    assert not list(client.root.glob("one/*/started.json"))


def test_headroom_failure_latches_before_any_provider_or_started_record(client, monkeypatch):
    monkeypatch.setattr(guarded.shutil, "disk_usage", lambda p: SimpleNamespace(free=1024))
    upstream = Mock(side_effect=AssertionError("No API call allowed"))
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(OSError) as caught:
        call(client)
    assert caught.value.errno == errno.ENOSPC and client.errors
    with pytest.raises(RuntimeError, match="Prior client failure"):
        call(client, "two")
    upstream.assert_not_called()
    assert not list(client.root.glob("*/**/started.json"))


@pytest.mark.parametrize("filename", ["request.json", "context_admission.json", "started.json"])
def test_initial_write_failure_latches_and_preserves_original_error(client, monkeypatch, filename):
    error = OSError(errno.ENOSPC, "Initial evidence exhausted storage")
    write = guarded.write_json
    def failing(path, value):
        if path.name == filename:
            raise error
        if path.name == "error.json":
            assert client.errors
            raise OSError(errno.EROFS, "Cannot persist exception evidence")
        return write(path, value)
    monkeypatch.setattr(guarded, "write_json", failing)
    upstream = Mock(side_effect=AssertionError("No API call allowed"))
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(OSError) as caught:
        call(client)
    assert caught.value is error and client.errors
    with pytest.raises(RuntimeError, match="Prior client failure"):
        call(client, "two")
    upstream.assert_not_called()


def test_initial_directory_failure_is_also_latched(client, monkeypatch):
    error = OSError(errno.ENOSPC, "Directory allocation failed")
    mkdir = Path.mkdir
    def failing(path, *a, **k):
        if client.root in path.parents:
            raise error
        return mkdir(path, *a, **k)
    monkeypatch.setattr(Path, "mkdir", failing)
    upstream = Mock(side_effect=AssertionError("No API call allowed"))
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(OSError) as caught:
        call(client)
    assert caught.value is error and client.errors
    upstream.assert_not_called()


def test_headroom_is_rechecked_after_waiting_for_dispatch_slot(client, monkeypatch):
    remaining = iter([2 << 30, 0])
    monkeypatch.setattr(guarded.shutil, "disk_usage", lambda p: SimpleNamespace(free=next(remaining)))
    upstream = Mock(side_effect=AssertionError("No API call allowed"))
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(OSError):
        call(client)
    assert client.errors and list(client.root.glob("one/*/started.json"))
    assert json.loads(next(client.root.glob("one/*/error.json")).read_text())["upstream_dispatched"] is False
    upstream.assert_not_called()


@pytest.mark.parametrize("filename", ["response.raw", "validated.json"])
def test_postdispatch_storage_failure_latches_before_failed_error_write(client, monkeypatch, filename):
    error = OSError(errno.ENOSPC, "Completed response cannot be persisted")
    write = guarded.write_json; write_bytes = Path.write_bytes
    def failing_json(path, value):
        if path.name == filename:
            raise error
        if path.name == "error.json":
            assert client.errors
            raise OSError(errno.EROFS, "Secondary evidence failure")
        return write(path, value)
    def failing_bytes(path, body):
        if path.name == filename:
            raise error
        return write_bytes(path, body)
    monkeypatch.setattr(guarded, "write_json", failing_json)
    monkeypatch.setattr(Path, "write_bytes", failing_bytes)
    upstream = Mock(return_value=completed())
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(OSError) as caught:
        call(client)
    assert caught.value is error and client.errors
    with pytest.raises(RuntimeError, match="Prior client failure"):
        call(client, "two")
    assert upstream.call_count == 1
    assert not list(client.root.glob("*/**/validated.json"))


def test_partial_body_and_error_write_failure_cannot_mask_transport_error(client, monkeypatch):
    error = IncompleteRead(b"Incomplete paid response")
    write = guarded.write_json; write_bytes = Path.write_bytes
    def failing_json(path, value):
        if path.name == "error.json":
            assert client.errors
            raise OSError(errno.ENOSPC, "Cannot persist error")
        return write(path, value)
    def failing_bytes(path, body):
        if path.name == "response.partial.raw":
            assert client.errors
            raise OSError(errno.ENOSPC, "Cannot persist partial body")
        return write_bytes(path, body)
    monkeypatch.setattr(guarded, "write_json", failing_json)
    monkeypatch.setattr(Path, "write_bytes", failing_bytes)
    upstream = Mock(side_effect=error)
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    with pytest.raises(IncompleteRead) as caught:
        call(client)
    assert caught.value is error and client.errors and upstream.call_count == 1


def test_queued_call_never_dispatches_after_response_and_error_storage_fail(client, monkeypatch):
    client.slots = threading.Semaphore(1)
    entered, queued, finish = (threading.Event() for _ in range(3))
    error = OSError(errno.ENOSPC, "No space for raw response")
    write = guarded.write_json; write_bytes = Path.write_bytes
    def upstream(*a, **k):
        entered.set()
        assert finish.wait(5)
        return completed()
    network = Mock(side_effect=upstream)
    def failing_json(path, value):
        if path.name == "error.json":
            assert client.errors
            raise OSError(errno.ENOSPC, "No space for error evidence")
        result = write(path, value)
        if path.name == "started.json" and path.parent.parent.name == "two":
            queued.set()
        return result
    def failing_bytes(path, body):
        if path.name == "response.raw":
            raise error
        return write_bytes(path, body)
    monkeypatch.setattr(guarded, "forward_native_responses", network)
    monkeypatch.setattr(guarded, "write_json", failing_json)
    monkeypatch.setattr(Path, "write_bytes", failing_bytes)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(call, client, "one")
        assert entered.wait(5)
        second = pool.submit(call, client, "two")
        try:
            assert queued.wait(5)
        finally:
            finish.set()
        with pytest.raises(OSError) as caught:
            first.result(timeout=5)
        assert caught.value is error
        with pytest.raises(RuntimeError, match="queued request cancelled"):
            second.result(timeout=5)
    assert client.errors and network.call_count == 1


def test_exact_cache_replay_remains_read_only_even_with_low_storage(client, monkeypatch):
    payload = client.payload(system="Synthetic system", user="Synthetic task")
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
    directory = client.root / "one" / digest
    guarded.write_json(directory / "validated.json", {"text": "{}", "usage": {"prompt_tokens": 10}})
    before = {p: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    monkeypatch.setattr(guarded.shutil, "disk_usage", Mock(side_effect=AssertionError("Replay has no new dispatch")))
    monkeypatch.setattr(guarded, "forward_native_responses", Mock(side_effect=AssertionError("No API call allowed")))
    assert call(client) == ("{}", {"prompt_tokens": 10})
    assert not client.errors and all(p.read_bytes() == body for p, body in before.items())


def test_successful_dispatch_still_preserves_raw_reply_and_known_cache(client, monkeypatch):
    upstream = Mock(return_value=completed())
    monkeypatch.setattr(guarded, "forward_native_responses", upstream)
    assert call(client) == ("{}", {"prompt_tokens": 10, "completion_tokens": 5})
    assert next(client.root.glob("one/*/response.raw")).read_bytes() == completed()[0]
    assert call(client) == ("{}", {"prompt_tokens": 10, "completion_tokens": 5})
    assert upstream.call_count == 1 and not client.errors
