"""Reconcile command-visible retrieval/exposure without inferring causal use."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from skillopt_verusage.card_bank import audit_retrieval
from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def audit_episode(episode):
    raw = episode/'codex_events.raw.jsonl'
    audit = audit_retrieval(raw)
    observations = []
    first_verus_pass_line = None
    body_read_phases = []
    for number,line in enumerate(raw.read_text().splitlines(),1):
        event = json.loads(line); item = event.get('item',{})
        if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        command = item.get('command',''); output = str(item.get('aggregated_output',''))
        verus_pass = bool(re.search(r'run_verus\.sh\s+candidate\.rs',command) and
                          re.search(r'verification results::\s*\d+ verified,\s*0 errors',output))
        for output_line in output.splitlines():
            try:
                payload = json.loads(output_line)
            except ValueError:
                continue
            if isinstance(payload,dict) and payload.get('card_retrieval')==1 and 'content' in payload:
                phase = ('after_first_visible_verus_pass' if first_verus_pass_line is not None else
                         'same_command_as_verus_pass_order_unknown' if verus_pass else 'before_first_visible_verus_pass')
                body_read_phases.append({'id':payload.get('id'),'line':number,'phase':phase})
        if verus_pass and first_verus_pass_line is None:
            first_verus_pass_line = number
        observations.append({'line':number,'item_id':item.get('id'),'command':command,
            'exit_code':item.get('exit_code'),
            'index_endpoints_visible':'- card-001:' in output and '- card-078:' in output,
            'reader_invocation_candidate':bool(re.search(r'\bcard_(?:read|search)\.py\b',command)),
            'direct_bank_candidate':'cards.json' in command,
            'verification_summaries':re.findall(r'verification results::[^\n]+',output),
            'error_headers':re.findall(r'^error[^\n]*',output,re.M),
            'missing_antecedent_warning':'does not currently assume the antecedent' in output})
    failures = Counter(header for e in observations for header in e['error_headers'])
    return {'episode':str(episode),'raw_event_path':str(raw),
        'helper_read_calls':audit['read_calls'],'helper_read_ids':audit.get('read_ids',[]),
        'index_endpoint_exposure':any(e['index_endpoints_visible'] for e in observations),
        'reader_invocations':[e for e in observations if e['reader_invocation_candidate']],
        'direct_bank_candidates':[e for e in observations if e['direct_bank_candidate']],
        'completed_commands':len(observations),
        'first_visible_verus_pass_line':first_verus_pass_line,'body_read_phases':body_read_phases,
        'repeated_error_header_proxy':{k:v for k,v in failures.items() if v>1},
        'observations':observations,
        'limits':'Visible command/output audit only. Index endpoints do not prove every intervening line '
                 'was attended to. Repeated headers can refer to different obligations. '
                 'Read phases refer to observed verifier-pass text, not current candidate validity '
                 'or dual validation. No automatic semantic adoption or causal utility classification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    rows = []
    for e in json.loads(args.summary.read_text())['rows']:
        rows.append({'condition':e['condition'],'id':e['row']['id'],
            'dual_pass':bool(e['row']['proof_solved'] and e['row']['safety_passed']),
            **audit_episode(Path(e['episode']))})
    totals = {}
    for condition in sorted({e['condition'] for e in rows}):
        selected = [e for e in rows if e['condition']==condition]
        totals[condition] = {'n':len(selected),
            'body_read_episodes':sum(bool(e['helper_read_calls']) for e in selected),
            'body_read_calls':sum(e['helper_read_calls'] for e in selected),
            'index_endpoint_episodes':sum(e['index_endpoint_exposure'] for e in selected),
            'reader_command_candidates':sum(len(e['reader_invocations']) for e in selected),
            'direct_bank_candidates':sum(len(e['direct_bank_candidates']) for e in selected),
            'completed_commands':sum(e['completed_commands'] for e in selected)}
    write_json(_require_run_child(args.output),{'rows':rows,'totals':totals})
    print(json.dumps(totals))


if __name__=='__main__':
    main()
