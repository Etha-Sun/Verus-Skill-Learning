"""Validate and render offline card organization without changing source cards."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


FIELDS = ('Trigger', 'Action', 'Why', 'Validate', 'Avoid when')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(rows, key):
    require(isinstance(rows, list), f'{key}: expected list')
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str), f'Missing {key}')
        require(row[key] not in result, f'Duplicate {key}: {row[key]}')
        result[row[key]] = row
    return result


def strings(value, label, nonempty=False):
    require(isinstance(value, list), f'{label}: expected array')
    require(not nonempty or bool(value), f'{label}: empty')
    require(all(isinstance(item, str) and item.strip() for item in value), f'{label}: invalid text')
    return value


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label}: missing text')
    return value


def ids(value, allowed, label, nonempty=True):
    strings(value, label, nonempty)
    require(len(value) == len(set(value)) and set(value) <= set(allowed), f'{label}: invalid IDs')
    return set(value)


def source_field(content, field):
    parts = re.split(r'\*\*(Trigger|Action|Why|Validate|Avoid when):\*\*', content)
    fields = {parts[index]: parts[index + 1] for index in range(1, len(parts) - 1, 2)}
    return fields.get(field, '')


def router_packet(bank_path, recipe_path):
    bank = json.loads(Path(bank_path).read_text())
    cards = unique(bank['cards'], 'id')
    require(set(cards) == {f'card-{number:03}' for number in range(1, 79)}, 'Expected frozen repaired78 IDs')
    descriptions = json.loads(Path(recipe_path).read_text())['index_descriptions']
    require(set(descriptions) == set(cards), 'Description coverage differs')
    for card in cards.values():
        require(set(card) == {'id', 'content'}, 'Private source metadata in public card bank')
        for field in FIELDS:
            require(bool(source_field(card['content'], field).strip()), f'{card["id"]}: missing {field}')
    return {'schema_version': 'card-router-input-v2', 'bank_sha256': sha(bank_path),
            'expected_card_ids': sorted(cards), 'cards': [
                {**cards[ident], 'content_sha256': hashlib.sha256(cards[ident]['content'].encode()).hexdigest(),
                 'index_description': descriptions[ident]} for ident in sorted(cards)]}


def validate_router(proposal, packet):
    require(proposal.get('schema_version') == 'card-cluster-proposal-v2', 'Router schema')
    require(proposal.get('input_bank_sha256') == packet['bank_sha256'], 'Router bank hash')
    require(proposal.get('status') in {'candidate', 'needs_review'}, 'Router blocked')
    require(proposal.get('blocking_errors') == [], 'Router blocking errors')
    cards = unique(packet['cards'], 'id')
    features = unique(proposal['card_features'], 'card_id')
    assignments = unique(proposal['assignments'], 'card_id')
    families = unique(proposal['families'], 'family_id')
    require(set(features) == set(assignments) == set(cards), 'Router card coverage differs')
    require(bool(families), 'No families')
    for ident, family in families.items():
        require(SLUG.fullmatch(ident) is not None, 'Unsafe family ID')
        text(family.get('title'), 'family title')
        strings(family.get('include_when'), 'include_when', True)
        strings(family.get('exclude_when'), 'exclude_when')
        for neighbor in family['distinguish_from']:
            require(neighbor['family_id'] in families and neighbor['family_id'] != ident, 'Bad neighboring family')
            text(neighbor.get('distinction'), 'distinction')
    reached = set()
    case_count = 0
    for ident, feature in features.items():
        cases = unique(feature['cases'], 'case_id')
        require(bool(cases), 'Empty cases')
        case_count += len(cases)
        for case in cases.values():
            strings(case.get('entry_states'), 'entry_states', True)
            for field in ('proof_object', 'goal_shape', 'observable_signal', 'required_premises',
                          'repair_action', 'avoid_when', 'version_scope'):
                require(field in case and (case[field] is None or isinstance(case[field], str)), f'Missing case {field}')
            require(bool(case.get('source_anchors')), 'Case has no source anchors')
            for anchor in case['source_anchors']:
                excerpt = text(anchor.get('excerpt'), 'anchor excerpt')
                require(anchor['field'] in FIELDS, 'Unknown anchor field')
                require(excerpt in source_field(cards[ident]['content'], anchor['field']), f'{ident}: anchor not in source field')
        assignment = assignments[ident]
        primary = assignment['primary_family']
        require(primary in families, 'Missing primary family')
        reached.add(primary)
        covered = ids(assignment['primary_case_ids'], cases, 'primary_case_ids')
        for link in assignment['cross_links']:
            require(link['family_id'] in families and link['family_id'] != primary, 'Invalid cross-link')
            covered |= ids(link['case_ids'], cases, 'cross-link cases')
            text(link.get('when'), 'cross-link condition')
            reached.add(link['family_id'])
        require(covered == set(cases), f'{ident}: uncovered cases')
        text(assignment.get('rationale'), 'assignment rationale')
        require(type(assignment.get('needs_review')) is bool, 'Missing review flag')
    require(reached == set(families), 'Unreachable family')
    for relation in proposal['relations']:
        require(len(ids(relation['card_ids'], cards, 'relation cards')) >= 2, 'Relation requires two cards')
        require(relation['relation'] in {'duplicate_candidate', 'complementary', 'conditional_alternative',
                                        'unresolved_conflict'}, 'Unknown relation')
        text(relation.get('boundary'), 'relation boundary')
    for item in proposal['review_items']:
        ids(item['card_ids'], cards, 'review cards', False)
        ids(item['family_ids'], families, 'review families', False)
        text(item.get('issue'), 'review issue')
        text(item.get('required_check'), 'required check')
    flagged = {ident for ident, assignment in assignments.items() if assignment['needs_review']}
    reviewed = {ident for item in proposal['review_items'] for ident in item['card_ids']}
    require(flagged <= reviewed, 'Flagged assignment missing review item')
    require(not (flagged or proposal['review_items']) or proposal['status'] == 'needs_review', 'Unresolved review marked candidate')
    return {'cards': len(cards), 'cases': case_count, 'families': len(families),
            'status': proposal['status'], 'review_items': len(proposal['review_items'])}


def reduction_packets(proposal, packet):
    validate_router(proposal, packet)
    features = unique(proposal['card_features'], 'card_id')
    cards = unique(packet['cards'], 'id')
    packets = {}
    for family in proposal['families']:
        family_id = family['family_id']
        members = sorted(assignment['card_id'] for assignment in proposal['assignments']
                         if assignment['primary_family'] == family_id)
        if not members:
            continue
        packets[family_id] = {'schema_version': 'card-family-input-v2', 'bank_sha256': packet['bank_sha256'],
            'family': family, 'expected_card_ids': members, 'cards': [cards[ident] for ident in members],
            'card_cases': [features[ident] for ident in members],
            'relations': [relation for relation in proposal['relations'] if set(relation['card_ids']) <= set(members)],
            'neighbor_routes': [neighbor for neighbor in proposal['families'] if neighbor['family_id'] != family_id]}
    return packets


def validate_reduction(proposal, packet):
    require(proposal.get('schema_version') == 'card-family-reduction-v2', 'Reduction schema')
    require(proposal.get('input_bank_sha256') == packet['bank_sha256'], 'Reduction bank hash')
    require(proposal.get('family_id') == packet['family']['family_id'], 'Reduction family ID')
    require(proposal.get('status') in {'candidate', 'needs_review'}, 'Reduction blocked')
    require(proposal.get('blocking_errors') == [], 'Reduction blocking errors')
    cards = unique(packet['cards'], 'id')
    rules = unique(proposal['rules'], 'rule_id')
    coverage = unique(proposal['coverage'], 'card_id')
    require(set(coverage) == set(cards) and bool(rules), 'Reduction coverage differs')
    for ident, rule in rules.items():
        require(SLUG.fullmatch(ident) is not None, 'Unsafe rule ID')
        text(rule.get('title'), 'rule title')
        sources = ids(rule['source_card_ids'], cards, 'rule sources')
        text(rule.get('merge_rationale'), 'merge rationale')
        if rule['kind'] == 'verbatim':
            require(len(sources) == 1 and rule['clauses'] == [], 'Invalid verbatim rule')
        else:
            require(rule['kind'] == 'merged' and len(sources) >= 2, 'Invalid merged rule')
            clauses = unique(rule['clauses'], 'clause_id')
            require(set(FIELDS) <= {clause['field'] for clause in clauses.values()}, 'Missing original fields')
            supported = set()
            for clause in clauses.values():
                require(clause['field'] in {*FIELDS, 'Premises', 'Version scope'}, 'Invalid clause field')
                supported |= ids(clause['supporting_card_ids'], sources, 'clause sources')
                text(clause.get('text'), 'clause text')
            require(supported == sources, 'Rule lists unused source')
    for ident, item in coverage.items():
        references = ids(item['rule_ids'], rules, 'coverage rules')
        actual = {rule_id for rule_id, rule in rules.items() if ident in rule['source_card_ids']}
        require(references == actual, 'Coverage not reciprocal with rule sources')
        require(item['disposition'] in {'retained_verbatim', 'merged', 'split_across_rules'}, 'Invalid disposition')
        if item['disposition'] == 'retained_verbatim':
            require(len(references) == 1 and rules[next(iter(references))]['kind'] == 'verbatim', 'False verbatim disposition')
        if item['disposition'] == 'merged':
            require(len(references) == 1 and rules[next(iter(references))]['kind'] == 'merged', 'False merged disposition')
        if item['disposition'] == 'split_across_rules':
            require(len(references) >= 2, 'False split disposition')
        strings(item['preserved_distinctions'], 'preserved distinctions')
    expected = {(feature['card_id'], case['case_id']) for feature in packet['card_cases'] for case in feature['cases']}
    actual = set()
    for item in proposal['case_rule_map']:
        pair = (item['card_id'], item['case_id'])
        require(pair in expected and pair not in actual, 'Missing or duplicate case map')
        actual.add(pair)
        for ident in ids(item['rule_ids'], rules, 'case rules'):
            require(item['card_id'] in rules[ident]['source_card_ids'], 'Case maps to unrelated rule')
    require(actual == expected, 'Incomplete case map')
    neighbors = {neighbor['family_id'] for neighbor in packet['neighbor_routes']}
    for link in proposal['cross_links']:
        require(link['family_id'] in neighbors, 'Unknown reduced cross-link')
        text(link.get('distinction'), 'reduced distinction')
    for item in proposal['review_items']:
        ids(item['card_ids'], cards, 'review cards', False)
        ids(item['rule_ids'], rules, 'review rules', False)
        text(item.get('issue'), 'review issue')
        text(item.get('required_check'), 'review check')
    require(not proposal['review_items'] or proposal['status'] == 'needs_review', 'Review issues marked candidate')
    return {'family_id': proposal['family_id'], 'source_cards': len(cards), 'rules': len(rules),
            'merged': sum(rule['kind'] == 'merged' for rule in rules.values()), 'status': proposal['status']}


READER = '''import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
manifest = json.loads((root / "reference_manifest.json").read_text())
ident = sys.argv[1] if len(sys.argv) == 2 else ""
entry = manifest.get(ident)
if entry is None:
    print(json.dumps({"reference_retrieval": 1, "error": "unknown reference id", "id": ident}))
    raise SystemExit(2)
path = root / entry["path"]
resolved = path.resolve()
if path.is_symlink() or root / "references" not in resolved.parents:
    raise SystemExit("unsafe reference path")
body = path.read_bytes()
if hashlib.sha256(body).hexdigest() != entry["sha256"]:
    raise SystemExit("reference hash mismatch")
print(json.dumps({"reference_retrieval": 1, "operation": "read", "id": ident,
                  "source_card_ids": entry["source_card_ids"], "bytes": len(body),
                  "sha256": entry["sha256"], "content": body.decode()}, ensure_ascii=False))
'''


def render_bundle(router, packet, reductions, template_path, seed_path, destination):
    validate_router(router, packet)
    packets = reduction_packets(router, packet)
    require(set(reductions) == set(packets), 'Missing family reductions')
    for ident in packets:
        validate_reduction(reductions[ident], packets[ident])
    cards = unique(packet['cards'], 'id')
    families = unique(router['families'], 'family_id')
    assignments = unique(router['assignments'], 'card_id')
    case_rules = {(item['card_id'], item['case_id']): (ident, item['rule_ids'])
                  for ident, reduction in reductions.items() for item in reduction['case_rule_map']}
    pages, exposures = {}, {}
    for ident, family in sorted(families.items()):
        lines = [f'# {family["title"]}', '', '## Scope', '',
                 *[f'- Consult when: {condition}' for condition in family['include_when']],
                 *[f'- Not for: {condition}' for condition in family['exclude_when']], '']
        rules = reductions.get(ident, {}).get('rules', [])
        lines += ['## Rules' if rules else '## Navigation only', '']
        for rule in rules:
            lines.append(f'- [{rule["title"]}](#{rule["rule_id"]})')
        exposed = set()
        for rule in rules:
            exposed.update(rule['source_card_ids'])
            lines += ['', f'<a id="{rule["rule_id"]}"></a>', f'## {rule["title"]}', '',
                      'Source cards: ' + ', '.join(rule['source_card_ids']), '']
            if rule['kind'] == 'verbatim':
                lines.append(cards[rule['source_card_ids'][0]]['content'])
            else:
                for field in ('Trigger', 'Premises', 'Action', 'Why', 'Validate', 'Avoid when', 'Version scope'):
                    selected = [clause['text'] for clause in rule['clauses'] if clause['field'] == field]
                    if selected:
                        lines += [f'**{field}:**', *['- ' + value for value in selected], '']
        links = []
        for card_id, assignment in assignments.items():
            for link in assignment['cross_links']:
                if link['family_id'] == ident:
                    for case_id in link['case_ids']:
                        owner, rule_ids = case_rules[(card_id, case_id)]
                        for rule_id in rule_ids:
                            links.append(f'- When {link["when"]}: [{owner}/{rule_id}]({owner}.md#{rule_id})')
        if links:
            lines += ['', '## Conditional links', '', *sorted(set(links))]
        for link in family['distinguish_from']:
            lines += ['', f'- Distinguish from [{link["family_id"]}]({link["family_id"]}.md): {link["distinction"]}']
        for link in reductions.get(ident, {}).get('cross_links', []):
            lines += ['', f'- Related [{link["family_id"]}]({link["family_id"]}.md): {link["distinction"]}']
        pages[ident] = '\n'.join(lines).rstrip() + '\n'
        exposures[ident] = sorted(exposed)
    index = []
    for ident, family in sorted(families.items()):
        index += [f'### {ident} — [{family["title"]}](references/{ident}.md)', '',
                  *[f'- Consult when: {condition}' for condition in family['include_when']],
                  *[f'- Not for: {condition}' for condition in family['exclude_when']]]
        for neighbor in family['distinguish_from']:
            index.append(f'- Distinguish from [{neighbor["family_id"]}](references/{neighbor["family_id"]}.md): {neighbor["distinction"]}')
        index.append('')
    skill = Path(template_path).read_text().replace('{{FIRST_REFERENCE_ID}}', sorted(families)[0]).replace(
        '{{REFERENCE_INDEX}}', '\n'.join(index).rstrip())
    require(skill.encode().startswith(Path(seed_path).read_bytes()), 'Executive prefix changed')
    require('{{' not in skill, 'Unresolved template variables')
    for ident, body in pages.items():
        for target in re.findall(r'\]\(([^)]+)\)', body):
            if '.md' in target:
                name, _, anchor = target.partition('#')
                require(name.endswith('.md') and name[:-3] in pages, 'Broken reference link')
                require(not anchor or f'id="{anchor}"' in pages[name[:-3]], 'Broken rule anchor')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'references').mkdir()
    manifest = {}
    for ident, body in pages.items():
        path = destination / 'references' / f'{ident}.md'
        path.write_text(body)
        manifest[ident] = {'path': f'references/{ident}.md', 'sha256': sha(path),
                           'source_card_ids': exposures[ident], 'bytes': len(body.encode())}
    (destination / 'SKILL.md').write_text(skill)
    (destination / 'reference_read.py').write_text(READER)
    (destination / 'reference_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {'references': len(pages), 'cards': len(cards), 'skill_bytes': len(skill.encode()),
            'rules': sum(len(value['rules']) for value in reductions.values()),
            'review_required': True, 'evaluation_authorized': False,
            'files': {str(path.relative_to(destination)): sha(path) for path in sorted(destination.rglob('*')) if path.is_file()}}
