"""Read frozen current-line results; separate success, timeout, and paired usage."""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import re
import statistics
from pathlib import Path


FIELDS = ('prompt_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens',
          'completion_tokens', 'reasoning_tokens', 'estimated_cost_usd',
          'requests', 'unmetered_requests', 'error_requests', 'unknown_cost_requests')
SUMMARIES = {
    'repair': 'full-validation20-20261008-6kHSjI/full_validation_summary.json',
    'guidance': 'retrieval-mechanism-audit-20261009-i8ZabJ/guidance-validation/summary.json',
    'executive_pilot': 'executive-pilot-20261009-NYYmFA/summary.json',
    'executive_full': 'executive-single-20261010-I5C6Z6/single_executive_summary.json',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bucket(row):
    if not row['provider_valid']:
        return 'invalid'
    if row['proof_solved'] and row['safety_passed'] and row['within_budget']:
        assert not row['timed_out']
        return 'success'
    return 'timeout' if row['timed_out'] else 'normal_unsolved'


def distribution(values):
    if not values:
        return {'n': 0, 'sum': 0}
    ordered = sorted(values)
    def percentile(p):
        pos = (len(ordered) - 1) * p
        low = int(pos)
        high = min(low + 1, len(ordered) - 1)
        return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)
    return dict(n=len(values), sum=sum(values), mean=statistics.mean(values),
                median=statistics.median(values), p25=percentile(.25),
                p75=percentile(.75), p90=percentile(.9), min=min(values), max=max(values))


def metrics(rows):
    return {field: distribution([row[field] for row in rows])
            for field in (*FIELDS, 'total_tokens', 'actor_seconds')}


def joint_pairs(rows, old, new):
    pairs = collections.defaultdict(dict)
    for row in rows:
        if row['condition'] not in (old, new):
            continue
        key = (row['task_id'], row['repeat'])
        assert row['condition'] not in pairs[key], key
        pairs[key][row['condition']] = row
    assert all(set(pair) == {old, new} for pair in pairs.values())
    joint = [pair for pair in pairs.values()
             if all(row['outcome'] == 'success' for row in pair.values())]
    result = {'old': old, 'new': new, 'n': len(joint),
              'task_n': len({pair[old]['task_id'] for pair in joint}),
              'keys': [(pair[old]['task_id'], pair[old]['repeat']) for pair in joint]}
    result['metrics'] = {}
    for field in (*FIELDS, 'total_tokens', 'actor_seconds'):
        a = distribution([pair[old][field] for pair in joint])
        b = distribution([pair[new][field] for pair in joint])
        result['metrics'][field] = {'old': a, 'new': b,
            'sum_change_pct': 100 * (b['sum'] / a['sum'] - 1) if a['sum'] else None}
    return result


def timeout_evidence(path):
    """Extract candidates for manual audit, NOT automatic same-state certification."""
    events_path = path / 'agent_events.jsonl'
    raw_path = path / 'codex_events.raw.jsonl'
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    initial = dt.datetime.fromisoformat(events[0]['timestamp'])
    stamps = {}
    for event in events:
        raw = event.get('data', {}).get('raw_codex_event', {})
        if raw.get('type') == 'item.completed':
            stamps.setdefault(raw['item']['id'], event['timestamp'])
    checks = []
    for line_number, line in enumerate(raw_path.read_text().splitlines(), 1):
        raw = json.loads(line)
        item = raw.get('item', {})
        if raw.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        command, output = item.get('command', ''), item.get('aggregated_output', '')
        if not re.search(r'run_verus|run_lynette|\blynette\b|\bverus\b', command):
            continue
        verus_pass = bool(re.search(r'verification results:: [1-9][0-9]* verified, 0 errors', output))
        lynette_exit0 = 'run_lynette.sh' in command and item.get('exit_code') == 0
        if verus_pass or lynette_exit0:
            stamp = stamps.get(item['id'])
            checks.append({'line': line_number, 'item_id': item['id'], 'command': command,
                'output': output, 'exit_code': item.get('exit_code'),
                'verus_pass_signal': verus_pass, 'lynette_exit0_signal': lynette_exit0,
                'elapsed_from_first_event_s':
                    (dt.datetime.fromisoformat(stamp) - initial).total_seconds() if stamp else None})
    return {'raw_sha256': sha(raw_path), 'events_sha256': sha(events_path),
            'first_event_at': events[0]['timestamp'], 'candidate_checks': checks}


def analyze(root, output):
    assert not output.exists(), 'Use a new output directory; frozen results must not be overwritten'
    assert output.resolve().is_relative_to(root.resolve()), 'Keep generated outputs under the run root'
    sources, ledger_cache, rows, evidence = {}, {}, [], []
    def load(path):
        sources[str(path.relative_to(root))] = sha(path)
        return json.loads(path.read_text())
    def usage(path, key):
        if path not in ledger_cache:
            sources[str(path.relative_to(root))] = sha(path)
            grouped = collections.defaultdict(lambda: dict.fromkeys(FIELDS, 0))
            for line in path.read_text().splitlines():
                record = json.loads(line)
                total = grouped[record.get('task_id')]
                for attempt in record.get('attempts') or []:
                    total['requests'] += 1
                    total['error_requests'] += bool(attempt.get('error'))
                    u = attempt.get('usage')
                    if not isinstance(u, dict):
                        total['unmetered_requests'] += 1
                        continue
                    for field in FIELDS[:5]:
                        total[field] += int(u.get(field, 0) or 0)
                    cost = attempt.get('estimated_cost_usd')
                    if cost is None:
                        total['unknown_cost_requests'] += 1
                    else:
                        total['estimated_cost_usd'] += float(cost)
            ledger_cache[path] = grouped
        assert key in ledger_cache[path], (path, key)
        return ledger_cache[path][key].copy()
    def add(campaign, condition, row, path, u, repeat):
        assert u['requests'] > 0 and not any(u[k] for k in
            ('unmetered_requests', 'error_requests', 'unknown_cost_requests'))
        assert u['prompt_tokens'] == u['prompt_cache_hit_tokens'] + u['prompt_cache_miss_tokens']
        assert u['reasoning_tokens'] <= u['completion_tokens']
        entry = dict(campaign=campaign, condition=condition, task_id=row['id'], repeat=repeat,
            outcome=bucket(row), final_dual_pass=bool(row['proof_solved'] and row['safety_passed']),
            actor_seconds=row['actor_wall_seconds'], episode=str(path), **u)
        entry['total_tokens'] = u['prompt_tokens'] + u['completion_tokens']
        rows.append(entry)
        if entry['outcome'] == 'timeout':
            evidence.append(dict(campaign=campaign, condition=condition, task_id=row['id'],
                repeat=repeat, final_dual_pass=entry['final_dual_pass'], episode=str(path),
                **timeout_evidence(path)))

    main = root / 'evaluation-resume-20261007-ri57is'
    mapping = load(main / 'evaluation_episode_sources.json')
    for key, source in sorted(mapping.items()):
        result_path, ledger_path = Path(source['result_path']), Path(source['ledger_path'])
        assert sha(result_path) == source['result_sha256']
        assert sha(ledger_path) == source['ledger_sha256']
        row = load(result_path)
        prefix = key.split('--')[0]
        add('main', prefix.split('_', 2)[2], row, result_path.parent,
            usage(ledger_path, key), int(prefix.split('_')[1][1:]) - 1)
    main_summary = load(main / 'analysis/hindsight-summary/summary.json')
    for campaign, relative in SUMMARIES.items():
        for entry in load(root / relative)['rows']:
            path, row = Path(entry['episode']), entry['row']
            u = usage(path.parent.parent / 'provider_calls.jsonl', row['bridge_task_key'])
            for field in FIELDS:
                assert abs(u[field] - entry['settled_usage'][field]) < 1e-7, (campaign, field)
            match = re.search(r'--repeat-(\d+)$', row['bridge_task_key'])
            add(campaign, entry['condition'], row, path, u, int(match[1]) if match else 0)
    groups = {}
    for campaign, condition in sorted({(r['campaign'], r['condition']) for r in rows}):
        selected = [r for r in rows if (r['campaign'], r['condition']) == (campaign, condition)]
        counts = dict(collections.Counter(r['outcome'] for r in selected))
        groups[campaign + '/' + condition] = {'n': len(selected), 'counts': counts,
            'final_dual_pass_timeouts': sum(r['outcome'] == 'timeout' and r['final_dual_pass'] for r in selected),
            'all': metrics(selected),
            'success': metrics([r for r in selected if r['outcome'] == 'success']),
            'timeout': metrics([r for r in selected if r['outcome'] == 'timeout'])}
        if campaign == 'main':
            expected = main_summary['conditions'][condition]
            assert counts['success'] == expected['within_budget_solved']
            assert counts['timeout'] == expected['timeouts']
            for a, b in [('prompt_tokens', 'prompt_tokens'), ('completion_tokens', 'completion_tokens'),
                         ('estimated_cost_usd', 'estimated_actor_cost_usd'), ('actor_seconds', 'actor_wall_seconds')]:
                assert abs(groups[campaign + '/' + condition]['all'][a]['sum'] - expected['all_run_settled_ledger'][b]) < 1e-6
    pairs = {'main': joint_pairs([r for r in rows if r['campaign'] == 'main'], 'original_only', 'augmented')}
    for campaign in SUMMARIES:
        pairs[campaign] = joint_pairs([r for r in rows if r['campaign'] == campaign], 'old', 'revised')
    assert len(rows) == 304 and len(evidence) == 70
    output.mkdir(parents=True)
    result = {'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'analysis_script_sha256': sha(Path(__file__)), 'source_sha256': sources,
        'selected_n': len(rows), 'counts': dict(collections.Counter(r['outcome'] for r in rows)),
        'groups': groups, 'joint_success': pairs,
        'method': 'Settled ledger, exact task key. Reasoning is a subset of completion. Linear percentiles. No outcome reclassification. Pilot and repeated tasks are not independent.'}
    (output / 'statistics.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'timeout_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    with (output / 'episodes.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'output': str(output), 'counts': result['counts'], 'groups': {
        k: {'counts': v['counts'], 'success_input_mean': v['success']['prompt_tokens']['mean'],
            'success_input_median': v['success']['prompt_tokens']['median'],
            'success_output_mean': v['success']['completion_tokens']['mean'],
            'success_output_median': v['success']['completion_tokens']['median'],
            'timeout_cost': v['timeout']['estimated_cost_usd']['sum']} for k, v in groups.items()},
        'pairs': {k: {'n': p['n'], 'changes': {f: v['sum_change_pct'] for f, v in p['metrics'].items()}}
                  for k, p in pairs.items()}}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.run_root, args.output)
