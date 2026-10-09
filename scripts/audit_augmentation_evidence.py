"""Audit stored fork diversity and card support; no semantic/causal scoring."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from skillopt_verusage.fork_card_optimize import _require_run_child
from skillopt_verusage.guarded_deepseek import write_json


def audit(root, historical_summary):
    groups = []
    for name in ('augmented_smoke','augmented_remaining'):
        for path in sorted((root/'banks'/name/'predictions').glob('group_*/conversation.json')):
            group = json.loads(json.loads(path.read_text())[0]['content'])
            original = group['original']['complete_trace']
            traces = [original] + [f['complete_suffix'] for f in group['forks']]
            hashes = [t['final_source']['sha256'] for t in traces]
            groups.append({'source_task':group['source_task'],'packet_path':str(path),
                'packet_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'original_solved':bool(original['result']['proof_solved'] and original['result']['safety_passed']),
                'fork_solved':[bool(t['result']['proof_solved'] and t['result']['safety_passed']) for t in traces[1:]],
                'final_text_hashes':hashes,'distinct_final_texts':len(set(hashes)),
                'checkpoint_kinds':{f['checkpoint']['checkpoint_id']:f['checkpoint']['kind'] for f in group['forks']},
                'fallback_points':sum(bool(f['checkpoint'].get('fallback')) for f in group['forks']),
                'fork_texts_equal_original':sum(h==hashes[0] for h in hashes[1:])})
    if len(groups)!=38 or len({g['source_task'] for g in groups})!=38:
        raise ValueError('Expected exactly38 unique training groups')
    support = {}
    checkpoint_kinds = {g['source_task']:g['checkpoint_kinds'] for g in groups}
    for condition in ('original_only','augmented'):
        path = root/'banks'/condition/'provenance.json'
        bank = json.loads((path.parent/'cards.json').read_text())['cards']
        provenance = json.loads(path.read_text())
        if {c['id'] for c in bank} != set(provenance):
            raise ValueError('Card/provenance mismatch')
        cards = []
        for card in bank:
            records = provenance[card['id']]
            sources = sorted({s for r in records for s in r['source_tasks']})
            refs = {ref for r in records for ref in r['evidence_refs']}
            kinds = sorted({'original' if ':original/' in ref else 'fork' for ref in refs})
            referenced_points = {tuple(ref.split('/',1)[0].split(':')[1:]) for ref in refs
                                 if ':original/' not in ref}
            point_kinds = sorted({checkpoint_kinds[task][cp] for task,cp in referenced_points})
            cards.append({'id':card['id'],'source_tasks':sources,'source_count':len(sources),
                          'reference_kinds':kinds,'referenced_checkpoint_kinds':point_kinds,
                          'reference_count':len(refs)})
        support[condition] = {'card_count':len(cards),
            'source_count_histogram':dict(Counter(c['source_count'] for c in cards)),
            'reference_kind_histogram':dict(Counter('+'.join(c['reference_kinds']) for c in cards)),
            'checkpoint_kind_combinations':dict(Counter('+'.join(c['referenced_checkpoint_kinds']) or 'no_fork_refs' for c in cards)),
            'cards':cards}
    historical = json.loads(historical_summary.read_text())
    return {'groups':groups,'training_totals':{'groups':len(groups),'forks':sum(len(g['fork_solved']) for g in groups),
        'originals_solved':sum(g['original_solved'] for g in groups),
        'forks_solved':sum(sum(g['fork_solved']) for g in groups),
        'fallback_points':sum(g['fallback_points'] for g in groups),
        'checkpoint_kind_histogram':dict(Counter(k for g in groups for k in g['checkpoint_kinds'].values())),
        'mixed_terminal_fork_groups':sum(len(set(g['fork_solved']))>1 for g in groups),
        'fork_texts_equal_original':sum(g['fork_texts_equal_original'] for g in groups),
        'distinct_final_texts_histogram':dict(Counter(g['distinct_final_texts'] for g in groups))},
        'card_support':support, 'historical_summary_path':str(historical_summary),
        'historical_summary_sha256':hashlib.sha256(historical_summary.read_bytes()).hexdigest(),
        'historical_conditions':historical['conditions'],
        'historical_paired':historical['primary_paired_augmented_minus_original_only'],
        'historical_joint_success':historical['joint_success_augmented_vs_original_only'],
        'limits':'Distinct final source text is not strategy diversity. Reference kinds do not prove correct '
                 'contrastive extraction. All-success terminal outcomes still permit intermediate failure evidence. '
                 'One card per source does not establish generalization. Historical comparison is source-matched, '
                 'not compute-matched; no new augmentation efficacy measurement here.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-root',type=Path,required=True)
    parser.add_argument('--historical-summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = audit(args.training_root,args.historical_summary)
    write_json(_require_run_child(args.output),result)
    print(json.dumps({'training':result['training_totals'],'support':{k:{key:value for key,value in v.items()
          if key!='cards'} for k,v in result['card_support'].items()}}))


if __name__=='__main__':
    main()
