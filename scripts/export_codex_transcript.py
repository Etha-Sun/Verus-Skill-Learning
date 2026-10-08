"""Stitch saved CLI events, exact host prompt and proof snapshots without inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from skillopt_verusage.fork_card_optimize import _require_run_child


def fence(text, language='text'):
    marker = '`' * max(3, 1 + max((len(m[0]) for m in re.finditer(r'`+', text)), default=0))
    return f'{marker}{language}\n{text}' + ('' if text.endswith('\n') else '\n') + marker + '\n'


def export_transcript(episode: Path, ledger: Path, output: Path):
    episode = episode.resolve()
    hashes = {}

    def read(path):
        data = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(data).hexdigest()
        return data.decode('utf-8')

    def snapshot_file(relative):
        path = (episode/relative).resolve()
        if episode not in path.parents:
            raise ValueError('Snapshot outside the episode')
        return path

    raw = [json.loads(line) for line in read(episode/'codex_events.raw.jsonl').splitlines() if line.strip()]
    normalized = [json.loads(line) for line in read(episode/'agent_events.jsonl').splitlines() if line.strip()]
    manifest = json.loads(read(episode/'run_manifest.json'))
    key = manifest['bridge']['task_key']
    calls = [json.loads(line) for line in read(ledger).splitlines() if line.strip()]
    calls = [call for call in calls if call.get('task_id') == key]
    prompt = read(episode/'prompt.txt')
    validation = json.loads(read(episode/'validation.json'))
    boundary_states = {row['data']['boundary']:row for row in normalized
                       if row.get('actor') == 'host' and 'snapshot' in row.get('data', {})}
    completed_times = {row['data']['raw_codex_event']['item']['id']:row['timestamp']
                       for row in normalized
                       if row.get('actor') == 'codex'
                       and row.get('data', {}).get('raw_codex_event', {}).get('type') == 'item.completed'}
    steps = []
    for event in raw:
        if event.get('type') != 'item.completed':
            continue
        item = event['item']
        step = {'sequence':len(steps)+1, 'timestamp':completed_times.get(item['id']),
                'raw_event':event, 'visible_reasoning':None}
        state = boundary_states.get(item['type']+':'+item['id'])
        if item['type'] == 'file_change':
            if state is None:
                raise ValueError('File-change event has no saved post-edit snapshot')
            data = state['data']
            step['edit_evidence'] = {**data,
                'diff_text':read(snapshot_file(data['diff'])),
                'candidate_after':read(snapshot_file(data['snapshot']))}
        elif item['type'] == 'reasoning':
            step['visible_reasoning'] = item.get('text') or item.get('content') or item.get('summary')
        steps.append(step)
    initial = boundary_states['initial']['data']
    initial_candidate = read(snapshot_file(initial['snapshot']))
    gaps = ['Exact upstream request payloads and successful raw Responses/SSE bodies were not saved.',
            'The host-authored initial user prompt is exact; CLI built-in system/tool instructions are not recorded here.',
            'Completed CLI items are execution steps, not a reconstructed mapping to provider API rounds.',
            'File-edit diffs are reconstructed from saved before/after states, not original patch-call arguments.']
    reasoning_items = sum(step['raw_event']['item']['type'] == 'reasoning' for step in steps)
    if not reasoning_items:
        gaps.append('No visible reasoning/thinking item was saved. Reasoning token usage does not recover its text.')
    packet = {'schema_version':'stitched-codex-transcript-v1', 'initial_user_prompt':prompt,
              'initial_candidate':initial_candidate, 'run_manifest':manifest,
              'steps':steps, 'raw_cli_events':raw, 'provider_calls':calls,
              'independent_validation':validation, 'source_sha256':hashes,
              'completeness':{'saved_cli_payloads_complete':True,
                              'full_provider_conversation_complete':False,
                              'visible_reasoning_items':reasoning_items,
                              'gaps':gaps}}
    parts = ['# Stitched saved trace (not a complete provider transcript)\n',
             '## Recording gaps\n', *('- '+gap+'\n' for gap in gaps),
             'No model call was made to export this file. Missing thinking is not invented.\n',
             '## Initial host-authored user prompt (exact saved text)\n', fence(prompt),
             '## Initial candidate (before the first model action)\n', fence(initial_candidate, 'rust')]
    for step in steps:
        item = step['raw_event']['item']
        parts += [f"## Step {step['sequence']:02d} / {item['id']} / {item['type']}\n",
                  f"Recorded completion time: {step['timestamp']}\n", '### Thinking\n']
        parts.append(fence(str(step['visible_reasoning'])) if step['visible_reasoning'] is not None
                     else 'Not recorded for this step; no inferred substitute.\n')
        if item['type'] == 'command_execution':
            parts += ['### Tool command (exact)\n', fence(item['command'], 'bash'),
                      '### Tool feedback (exact, including empty output)\n',
                      fence(item['aggregated_output']),
                      f"Exit code: {item['exit_code']}; status: {item.get('status')}\n"]
        elif item['type'] == 'file_change':
            edit = step['edit_evidence']
            parts += ['### Recorded file-change output\n', fence(json.dumps(item, ensure_ascii=False, indent=2), 'json'),
                      '### Snapshot-derived diff (not original patch arguments)\n', fence(edit['diff_text'], 'diff'),
                      '### Complete candidate after this edit\n', fence(edit['candidate_after'], 'rust')]
        elif item['type'] == 'agent_message':
            parts += ['### Model output (exact)\n', fence(item['text'])]
        else:
            parts += ['### Saved item\n', fence(json.dumps(item, ensure_ascii=False, indent=2), 'json')]
    parts += ['## Independent host validation (not a model output)\n', fence(json.dumps(validation, indent=2), 'json'),
              f'## Provider call ledger ({len(calls)} API calls; {len(steps)} CLI steps)\n',
              fence(json.dumps(calls, ensure_ascii=False, indent=2), 'json'),
              '## Runtime manifest\n', fence(json.dumps(manifest, ensure_ascii=False, indent=2), 'json'),
              '## Source hashes\n', fence(json.dumps(hashes, indent=2), 'json')]
    output = _require_run_child(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'full_trace.md').write_text('\n'.join(parts), encoding='utf-8')
    (output/'full_trace.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path,digest in hashes.items()):
        raise ValueError('Source changed during export')
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    packet = export_transcript(args.episode, args.ledger, args.output)
    print(json.dumps({'file':str(args.output/'full_trace.md'), 'steps':len(packet['steps']),
                      'provider_calls':len(packet['provider_calls']), 'completeness':packet['completeness']}))


if __name__ == '__main__':
    main()
