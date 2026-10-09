import importlib.util
import json
from pathlib import Path


def test_read_attempts_are_not_success_and_headers_not_obligations(tmp_path):
    path = Path(__file__).resolve().parents[1]/'scripts/audit_card_trace_use.py'
    spec = importlib.util.spec_from_file_location('card_trace_audit',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    items = [
        {'id':'index','command':'cat SKILL.md','aggregated_output':'- card-001: cue\n- card-078: cue'},
        {'id':'attempt','command':'python3 card_read.py card-999','aggregated_output':json.dumps(
            {'card_retrieval':1,'operation':'read','id':'card-999','error':'unknown card id'})},
        {'id':'direct','command':'python3 -c "read cards.json"','aggregated_output':''},
        {'id':'failure','command':'./tools/run_verus.sh candidate.rs',
         'aggregated_output':'error: assertion failed\nerror: assertion failed\nverification results:: 0 verified, 1 errors'}]
    (tmp_path/'codex_events.raw.jsonl').write_text('\n'.join(json.dumps(
        {'type':'item.completed','item':dict(item,type='command_execution',exit_code=1)}) for item in items))
    result = module.audit_episode(tmp_path)
    assert result['helper_read_calls']==0
    assert len(result['reader_invocations'])==1 and len(result['direct_bank_candidates'])==1
    assert result['index_endpoint_exposure']
    assert result['repeated_error_header_proxy']=={'error: assertion failed':2}
    assert result['first_visible_verus_pass_line'] is None
    assert result['body_read_phases']==[]


def test_read_phase_does_not_claim_dual_pass(tmp_path):
    path = Path(__file__).resolve().parents[1]/'scripts/audit_card_trace_use.py'
    spec = importlib.util.spec_from_file_location('card_trace_audit_stage',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    payload = json.dumps({'card_retrieval':1,'operation':'read','id':'card-001','content':'advice'})
    commands = [('python3 card_read.py card-001',payload),
        ('./tools/run_verus.sh candidate.rs','verification results:: 1 verified, 0 errors'),
        ('python3 card_read.py card-001',payload)]
    (tmp_path/'codex_events.raw.jsonl').write_text('\n'.join(json.dumps({'type':'item.completed',
        'item':{'id':str(i),'type':'command_execution','command':c,'aggregated_output':o,'exit_code':0}})
        for i,(c,o) in enumerate(commands)))
    result = module.audit_episode(tmp_path)
    assert [r['phase'] for r in result['body_read_phases']]==[
        'before_first_visible_verus_pass','after_first_visible_verus_pass']
    assert result['first_visible_verus_pass_line']==2
