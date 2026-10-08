import importlib.util
import json
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location('export_codex_transcript',
    Path(__file__).resolve().parents[1]/'scripts/export_codex_transcript.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    episode = tmp_path/'episode'
    (episode/'snapshots').mkdir(parents=True)
    (episode/'prompt.txt').write_text('Exact initial prompt.\n')
    (episode/'run_manifest.json').write_text(json.dumps({'bridge':{'task_key':'demo'}}))
    (episode/'validation.json').write_text(json.dumps({'verus':{'passed':True}}))
    (episode/'snapshots/initial.rs').write_text('initial code\n')
    (episode/'snapshots/edited.rs').write_text('edited code\n')
    (episode/'snapshots/edit.diff').write_text('-initial code\n+edited code\n')
    events = [{'type':'item.completed','item':{'id':'item_0','type':'command_execution',
        'command':'read file','aggregated_output':'a\n```nested\nfull feedback\n', 'exit_code':1,'status':'failed'}},
        {'type':'item.completed','item':{'id':'item_1','type':'file_change','changes':[{'kind':'update'}]}},
        {'type':'item.completed','item':{'id':'item_2','type':'agent_message','text':'Exact final output.'}}]
    (episode/'codex_events.raw.jsonl').write_text('\n'.join(map(json.dumps,events)))
    normalized = [{'actor':'host','data':{'boundary':'initial','snapshot':'snapshots/initial.rs'}},
        *({'actor':'codex','timestamp':f'time-{i}','data':{'raw_codex_event':event}} for i,event in enumerate(events)),
        {'actor':'host','data':{'boundary':'file_change:item_1', 'snapshot':'snapshots/edited.rs', 'diff':'snapshots/edit.diff'}}]
    (episode/'agent_events.jsonl').write_text('\n'.join(map(json.dumps,normalized)))
    ledger = tmp_path/'ledger.jsonl'
    ledger.write_text(json.dumps({'task_id':'demo','attempts':[{'usage':{'reasoning_tokens':10}}]})+'\n')
    return episode, ledger, events


def test_full_stitch_preserves_payloads_and_marks_unrecoverable_gaps(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    episode, ledger, events = fixture(tmp_path)
    packet = module.export_transcript(episode, ledger, tmp_path/'export')
    assert packet['raw_cli_events'] == events
    assert [step['raw_event'] for step in packet['steps']] == events
    assert packet['initial_user_prompt'] == 'Exact initial prompt.\n'
    assert packet['steps'][1]['edit_evidence']['candidate_after'] == 'edited code\n'
    assert packet['completeness']['visible_reasoning_items'] == 0
    assert packet['completeness']['full_provider_conversation_complete'] is False
    assert all(step['visible_reasoning'] is None for step in packet['steps'])
    markdown = (tmp_path/'export/full_trace.md').read_text()
    assert events[0]['item']['aggregated_output'] in markdown
    assert 'Exact final output.' in markdown
    assert 'original patch arguments' in markdown
    assert '````text\na\n```nested' in markdown
    assert json.loads((tmp_path/'export/full_trace.json').read_text()) == packet


def test_export_refuses_overwrite_and_outside_run_root(tmp_path, monkeypatch):
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path/'allowed'))
    episode, ledger, _ = fixture(tmp_path)
    with pytest.raises(ValueError):
        module.export_transcript(episode, ledger, tmp_path/'outside')
    monkeypatch.setenv('VERUS_SKILL_RUN_ROOT', str(tmp_path))
    module.export_transcript(episode, ledger, tmp_path/'export')
    with pytest.raises(FileExistsError):
        module.export_transcript(episode, ledger, tmp_path/'export')
