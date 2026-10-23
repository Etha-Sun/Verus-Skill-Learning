"""Render reviewed per-card pseudocode routes offline; no model or actor calls.

The routes are Codex-authored, source-mapped transformations, not learned here.
Ported from the renderer used to prepare the October 21 pseudocode variants.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def render(source_dir, routes_path, output):
    ROOT = output
    ROOT.mkdir(parents=True, exist_ok=False)
    routes = {}
    for part in routes_path.read_text().split('@@ ')[1:]:
        key, text = part.split('\n', 1)
        assert key not in routes
        routes[key] = text.strip('\n').splitlines()
    sources = {p.stem: p for p in source_dir.glob('*.json')}
    assert set(routes) == set(sources) and len(routes) == 20
    (ROOT / 'cards').mkdir(exist_ok=True)
    banks = {}
    summary = []
    for key, path in sorted(sources.items()):
        source = json.loads(path.read_text())
        clauses = {c['id']: c for c in source['clauses']}
        mapping = {sid: [] for sid in clauses}
        lines = ['# ' + source['title'], '', '## Applicability', '']
        for c in source['clauses']:
            if c['role'] == 'Trigger':
                lines.append(c['text'])
                mapping[c['id']].append({'line': len(lines), 'kind': 'verbatim'})
        lines += ['', '## Proof skeleton', '',
                  'Schematic proof layout, NOT executable Verus. Angle-bracketed slots are',
                  'unresolved obligations or current-context inspections, never trusted helpers.',
                  'A branch marked `under` uses only a justified premise in that branch.', '', '```text']
        route_start = len(lines) + 1
        referenced = set()
        for row in routes[key]:
            ids, content = row.split('|', 1)
            ids = ids.split(',')
            assert ids and all(sid in clauses for sid in ids), (key, ids)
            assert content.strip() and '\t' not in content
            indent = len(content) - len(content.lstrip())
            assert indent % 4 == 0
            lines.append(content)
            for sid in ids:
                referenced.add(sid)
                mapping[sid].append({'line': len(lines), 'kind': 'pseudocode'})
        route_end = len(lines)
        lines += ['```', '']
        for role, heading in [('Why', 'Rationale and evidence limits'), ('Validate', 'Validation'), ('Avoid when', 'Rejection limits')]:
            lines += ['## ' + heading, '']
            for c in source['clauses']:
                if c['role'] == role:
                    lines += [c['text'], '']
                    mapping[c['id']].append({'line': len(lines) - 1, 'kind': 'verbatim'})
        action_ids = {c['id'] for c in source['clauses'] if c['role'] == 'Action'}
        assert action_ids <= referenced, (key, 'unmapped actions', action_ids - referenced)
        assert all(mapping.values()), (key, 'unmapped source')
        # Every route line is source-mapped; no mapping identifiers are rendered to actor.
        body = '\n'.join(lines).rstrip() + '\n'
        assert not re.search(r'\b[OS]\d+\b', body), (key, 'private/noisy IDs leaked')
        route_body = '\n'.join(lines[route_start - 1:route_end])
        assert route_body.startswith('when ') and '<' in route_body and '>' in route_body
        assert any(line.startswith('        ') for line in route_body.splitlines())
        # Exact ancillary clauses retain stronger old claims and weaker new evidence as written.
        for c in source['clauses']:
            if c['role'] != 'Action':
                assert c['text'] in body
        out = ROOT / 'cards' / (key + '--pseudocode.md')
        out.write_text(body)
        record = {'source_card_id': source['id'], 'source_file': path.name, 'source_sha256': digest(path),
                  'actor_file': str(out.relative_to(ROOT)), 'actor_sha256': digest(out),
                  'pseudocode_lines': [route_start, route_end],
                  'source_mapping': [{'source_clause_id': sid, 'source_role': clauses[sid]['role'],
                                      'source_text': clauses[sid]['text'], 'output_locations': locations}
                                     for sid, locations in mapping.items()],
                  'mechanical_checks': {'all_source_clauses_mapped': True, 'all_action_clauses_in_pseudocode': True,
                                        'all_pseudocode_lines_source_mapped': True, 'ancillary_clauses_verbatim': True,
                                        'no_actor_mapping_ids': True},
                  'semantic_review': 'Codex source-to-route review; not independent and not a proof replay'}
        write_json(ROOT / 'review' / (key + '.json'), record)
        family = key.split('--')[0]
        banks.setdefault(family, []).append({'id': source['id'], 'content': body})
        summary.append({'name': key, 'clauses': len(clauses), 'action_clauses': len(action_ids),
                        'pseudocode_lines': route_end - route_start + 1, 'actor_sha256': digest(out)})
    for family, cards in banks.items():
        write_json(ROOT / 'banks' / (family + '_pseudocode.json'),
                   {'schema_version': 'stage-card-bank-v1', 'cards': cards})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--routes', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.sources, args.routes, args.output)))


if __name__ == '__main__':
    main()
