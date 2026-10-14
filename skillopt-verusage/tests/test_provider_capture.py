import hashlib
from io import BytesIO
from email.message import Message
import json
from pathlib import Path
import stat
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from skillopt_verusage.codex_deepseek_bridge import BridgeConfig, forward_native_responses


def config(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    directory = tmp_path/'run'; directory.mkdir()
    return BridgeConfig(model='deepseek-v4-pro', upstream_base_url='https://example.invalid',
        api_key='fixture-secret', ledger_path=directory/'ledger.jsonl', max_output_tokens=16,
        retry_output_tokens=16, request_timeout_seconds=1, native_responses=True,
        capture_public_payloads=True)


def response():
    event = {'type':'response.completed', 'response':{'id':'response-1', 'status':'completed',
        'model':'deepseek-v4-pro', 'usage':{'input_tokens':10,'output_tokens':2},
        'output':[{'type':'reasoning','summary':[{'text':'Actual public summary.'}],
                   'encrypted_content':'opaque-secret'},
                  {'type':'function_call','call_id':'call-1','name':'apply_patch',
                   'arguments':'Actual patch args.'}]}}
    body = ('data: '+json.dumps(event)+'\n\n').encode()
    value = BytesIO(body); value.headers = Message()
    value.headers['Content-Type'] = 'text/event-stream'
    return value, body


def test_capture_public_payloads_without_headers_secrets_or_opaque_reasoning(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch)
    value, body = response()
    monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', lambda *a,**k:value)
    payload = {'input':[{'text':'fixture-secret Bearer abcdefghijk'},
                        {'api_key':'other-secret'}], 'tools':[], 'model':'actor-request'}
    returned, _, record = forward_native_responses(cfg, payload, task_id='episode-1')
    assert returned == body
    capture = record['public_capture']
    assert capture['request_id'] == record['request_id']
    assert capture['response_id'] == 'response-1'
    assert capture['function_call_ids'] == ['call-1']
    assert capture['upstream_response_sha256'] == hashlib.sha256(body).hexdigest()
    directory = cfg.ledger_path.parent/capture['relative_path']
    saved = ''.join(p.read_text() for p in directory.iterdir())
    assert 'fixture-secret' not in saved and 'other-secret' not in saved and 'opaque-secret' not in saved
    assert 'Actual public summary.' in saved and 'Actual patch args.' in saved
    assert 'authorization' not in saved.lower()
    request = json.loads((directory/'request.json').read_text())
    assert request['forwarded']['model'] == 'deepseek-v4-pro'
    assert request['forwarded']['max_output_tokens'] == 16
    assert payload['model'] == 'actor-request'
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in directory.iterdir())


def test_default_does_not_capture(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch); cfg.capture_public_payloads = False
    value, _ = response()
    monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', lambda *a,**k:value)
    _, _, record = forward_native_responses(cfg, {'input':[]})
    assert 'public_capture' not in record
    assert not (cfg.ledger_path.parent/'provider_capture').exists()


def test_capture_rejects_outside_run_root_before_dispatch(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch)
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path/'allowed'))
    upstream = Mock(); monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', upstream)
    with pytest.raises(ValueError): forward_native_responses(cfg, {'input':[]})
    upstream.assert_not_called()


def test_capture_storage_failure_halts_without_charging_unsent_request(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch)
    monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.start_capture',
                        Mock(side_effect=OSError('Storage unavailable')))
    upstream = Mock(); monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', upstream)
    with pytest.raises(OSError): forward_native_responses(cfg, {'input':[]})
    with pytest.raises(RuntimeError, match='halted'): forward_native_responses(cfg, {'input':[]})
    upstream.assert_not_called()
    record = json.loads(cfg.ledger_path.read_text())
    assert record['upstream_dispatched'] is False
    assert record['attempts'][0]['estimated_cost_usd'] == 0


def test_http_failure_does_not_echo_credential_to_actor_or_ledger(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch)
    error = HTTPError('https://example.invalid', 500, 'failed', {}, BytesIO(b'fixture-secret'))
    monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', Mock(side_effect=error))
    with pytest.raises(RuntimeError) as caught:
        forward_native_responses(cfg, {'input':[]})
    assert 'fixture-secret' not in str(caught.value)
    assert 'fixture-secret' not in cfg.ledger_path.read_text()
    assert cfg.halted_error and 'fixture-secret' not in cfg.halted_error


def test_incomplete_terminal_body_is_saved_but_not_accepted(tmp_path, monkeypatch):
    cfg = config(tmp_path, monkeypatch)
    event = {'type': 'response.incomplete', 'response': {'status': 'incomplete',
        'model': 'deepseek-v4-pro', 'usage': {'input_tokens': 10, 'output_tokens': 16},
        'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': 'partial proposal fixture-secret'}]}]}}
    body = ('data: ' + json.dumps(event) + '\n\n').encode()
    value = BytesIO(body)
    value.headers = Message()
    value.headers['Content-Type'] = 'text/event-stream'
    monkeypatch.setattr('skillopt_verusage.codex_deepseek_bridge.urlopen', lambda *args, **kwargs: value)
    with pytest.raises(RuntimeError, match='incomplete'):
        forward_native_responses(cfg, {'input': []}, task_id='incomplete-fixture')
    record = json.loads(cfg.ledger_path.read_text())
    capture = record['public_capture']
    assert capture['complete'] is True
    saved = (cfg.ledger_path.parent/capture['relative_path']/'response.txt').read_text()
    assert 'partial proposal' in saved and 'fixture-secret' not in saved
    assert record['attempts'][0]['finish_reason'] == 'incomplete'
    assert record['attempts'][0]['usage']['completion_tokens'] == 16
