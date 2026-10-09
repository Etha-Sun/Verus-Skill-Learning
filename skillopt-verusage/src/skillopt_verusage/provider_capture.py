"""Opt-in private capture of public native Responses payloads, not hidden thought."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re


def redact(value, secret):
    if isinstance(value, dict):
        return {key: '[REDACTED]' if key.lower() in {
            'authorization', 'api_key', 'apikey', 'password', 'access_token',
            'refresh_token', 'encrypted_content',
        } else redact(part, secret) for key, part in value.items()}
    if isinstance(value, list):
        return [redact(part, secret) for part in value]
    if isinstance(value, str):
        text = value.replace(secret, '[REDACTED]') if secret else value
        text = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', '[REDACTED]', text)
        return re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._-]+', 'Bearer [REDACTED]', text)
    return value


def capture_root(ledger):
    if ledger is None or not os.environ.get('VERUS_SKILL_RUN_ROOT'):
        raise ValueError('capture requires an external ledger and approved run root')
    parent = ledger.parent.resolve()
    approved = Path(os.environ['VERUS_SKILL_RUN_ROOT']).resolve()
    repo = Path(__file__).resolve().parents[3]
    if approved not in parent.parents or repo == parent or repo in parent.parents:
        raise ValueError('capture must be below the approved external run root')
    root = parent/'provider_capture'
    if root.is_symlink():
        raise ValueError('capture root must not be a symlink')
    return root


def private_write(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(data)


def start_capture(root, request_id, incoming, forwarded, secret):
    root.mkdir(mode=0o700, exist_ok=True)
    root.chmod(0o700)
    directory = root/request_id
    directory.mkdir(mode=0o700)
    request = {'incoming': redact(incoming, secret), 'forwarded': redact(forwarded, secret)}
    private_write(directory/'request.json', json.dumps(request, ensure_ascii=False).encode())
    return directory


def finish_capture(directory, body, content_type, request_id, task_id, secret):
    text = body.decode('utf-8')
    events = []
    if content_type == 'text/event-stream':
        lines = []
        for line in text.splitlines(keepends=True):
            if line.startswith('data:') and line[5:].strip() not in ('', '[DONE]'):
                event = json.loads(line[5:]); events.append(event)
                lines.append('data: '+json.dumps(redact(event, secret), ensure_ascii=False)+'\n')
            else:
                lines.append(redact(line, secret))
        saved = ''.join(lines).encode()
    else:
        event = json.loads(text); events.append(event)
        saved = json.dumps(redact(event, secret), ensure_ascii=False).encode()
    private_write(directory/'response.txt', saved)
    responses = [e.get('response', e) for e in events
                 if isinstance(e.get('response', e), dict)]
    final = next((e for e in reversed(responses) if e.get('status') == 'completed'), {})
    metadata = {'schema_version':'public-provider-capture-v1', 'complete':True, 'request_id':request_id,
                'task_id':task_id, 'content_type':content_type,
                'response_id':final.get('id'),
                'function_call_ids':[item.get('call_id') for item in final.get('output', [])
                                     if item.get('type') == 'function_call'],
                'upstream_response_sha256':hashlib.sha256(body).hexdigest(),
                'saved_response_sha256':hashlib.sha256(saved).hexdigest(),
                'request_sha256':hashlib.sha256((directory/'request.json').read_bytes()).hexdigest(),
                'wire_bytes_exact':False, 'redacted_and_json_normalized':True,
                'hidden_reasoning_reconstructed':False,
                'caveat':'Only public provider returns are retained; credentials and opaque '
                         'encrypted_content are omitted. CLI-to-provider mapping is not inferred.'}
    private_write(directory/'capture.json', json.dumps(metadata, ensure_ascii=False, indent=2).encode())
    return metadata
