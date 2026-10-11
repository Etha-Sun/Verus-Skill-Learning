"""Descriptive checkpoint routing report; does not infer advice adoption."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics


def summarize(summary):
    arms = {}
    for result in summary['rows']:
        arms.setdefault(result['condition'],[]).append(result)
    totals = {}
    for arm, rows in arms.items():
        valid = [r for r in rows if r['row']['provider_valid']]
        solved = [r for r in valid if r['row']['proof_solved']]
        usage_keys = ('prompt_tokens','completion_tokens','estimated_cost_usd',
                      'unmetered_requests','unknown_cost_requests')
        totals[arm] = {'attempts':len(rows),'valid':len(valid),'success':len(solved),
            'timeouts':sum(bool(r['row'].get('timed_out')) for r in valid),
            'actor_seconds':sum(r['row']['actor_wall_seconds'] for r in valid),
            'success_median_actor_seconds':statistics.median(
                r['row']['actor_wall_seconds'] for r in solved) if solved else None,
            'search_calls':sum(r['retrieval']['search_calls'] for r in valid),
            'read_calls':sum(r['retrieval']['read_calls'] for r in valid),
            'reviewed_card_body_hit_cases':sum(bool(r['reviewed_card_body_hits']) for r in valid),
            'all_attempt_usage':{k:sum(r['settled_usage'].get(k,0) for r in rows) for k in usage_keys},
            'success_only_usage':{k:sum(r['settled_usage'].get(k,0) for r in solved) for k in usage_keys}}
    # Compare efficiency on identical solved cases, not different solved subsets.
    by_case = {}
    for result in summary['rows']:
        by_case.setdefault(result['id'],{})[result['condition']] = result
    pairs = {}
    for arm in ('exposed','index','query'):
        matched = [rows for rows in by_case.values() if 'none' in rows and arm in rows
                   and all(rows[a]['row']['provider_valid'] and rows[a]['row']['proof_solved']
                           for a in ('none',arm))]
        pairs[arm] = {'joint_success_count':len(matched)}
        for label in ('none',arm):
            pairs[arm][label] = {
                'actor_seconds':sum(r[label]['row']['actor_wall_seconds'] for r in matched),
                **{k:sum(r[label]['settled_usage'].get(k,0) for r in matched)
                   for k in ('prompt_tokens','completion_tokens','estimated_cost_usd')}}
    return {'arms':totals,'joint_success_vs_none':pairs,
            'caveat':'Exposed cards are in SKILL.md, not counted as card_read body hits. '
                     'Queries/reads prove exposure only, not correct use or causality.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    args = parser.parse_args()
    from skillopt_verusage.fork_card_optimize import _require_run_child
    root = _require_run_child(args.root.resolve())
    summary = json.loads((root/'summary.json').read_text())
    totals = summarize(summary)
    (root/'statistics.json').write_text(json.dumps(totals,indent=2)+'\n')
    parts = ['# Checkpoint card routing diagnostic\n\n',summary['caveat']+'\n\n',
             f"Completed {summary['completed_episodes']}/{summary['expected_episodes']}; "
             f"failures {len(summary['failures'])}; drained {summary['bridge_drained']}; "
             f"frozen inputs unchanged {summary['frozen_inputs_unchanged']}.\n\n",
             '| Arm | Valid | Success | Timeout | Input tokens | Output tokens | Known USD |\n',
             '|---|---:|---:|---:|---:|---:|---:|\n']
    for arm, data in totals['arms'].items():
        u = data['all_attempt_usage']
        parts.append(f"| {arm} | {data['valid']}/{data['attempts']} | {data['success']} | "
                     f"{data['timeouts']} | {u['prompt_tokens']} | {u['completion_tokens']} | "
                     f"{u['estimated_cost_usd']:.6f} |\n")
    parts += ['\n'+totals['caveat']+'\n\n',
              'See statistics.json for success-only usage and same-case joint-success comparisons. '
              'Unmetered/unknown-cost requests must not be treated as zero cost.\n\n',
              '## Case-level exposure (manual application audit still required)\n\n']
    for result in sorted(summary['rows'],key=lambda r:(r['id'],r['condition'])):
        retrieval = result['retrieval']
        queries = [{'query':e['query'],'ids':[r['id'] for r in e.get('results',[])]}
                   for e in retrieval.get('events',[]) if e['operation']=='search']
        parts.append(f"- {result['id']} / {result['condition']}: solved="
                     f"{result['row']['proof_solved']}; read={retrieval.get('read_ids',[])}; "
                     f"reviewed-hit={result['reviewed_card_body_hits']}; queries={queries}.\n")
    parts.append('\nFull saved prompts, public provider payloads, commands, feedback and edits: '
                 'full_traces/. Missing private reasoning is not reconstructed.\n')
    (root/'REPORT.md').write_text(''.join(parts))
    print(json.dumps({'phase':'report_written','completed':summary['completed_episodes']}),flush=True)


if __name__ == '__main__':
    main()
