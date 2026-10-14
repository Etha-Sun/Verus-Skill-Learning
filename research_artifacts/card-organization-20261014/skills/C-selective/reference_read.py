"""Read a family index, selected immutable rules, or an explicit full reference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def read_checked(root, entry):
    relative = Path(entry['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] != 'references':
        raise ValueError('unsafe reference path')
    path = root / relative
    if any(part.is_symlink() for part in [path, *path.parents] if part != root.parent):
        raise ValueError('symlink in reference path')
    if root / 'references' not in path.resolve().parents:
        raise ValueError('reference escapes library')
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != entry['sha256'] or len(body) != entry['bytes']:
        raise ValueError('reference integrity mismatch')
    return body.decode('utf-8')


def retrieve(root, family_id, rule_ids=None, full=False):
    manifest = json.loads((root / 'reference_manifest.json').read_text())
    family = manifest.get(family_id)
    if family is None:
        raise ValueError('unknown reference id')
    if full and rule_ids:
        raise ValueError('choose rules or full reference, not both')
    available = family['rules']
    selected = list(rule_ids or [])
    if len(selected) != len(set(selected)) or any(rule not in available for rule in selected):
        raise ValueError('unknown or repeated rule id')
    if full or len(available) == 1:
        content = read_checked(root, family['full'])
        selected = list(available)
        operation = 'read_full' if full else 'read_single'
    elif selected:
        scope, links = family['shared_scope'], family['shared_links']
        bodies = []
        for rule in selected:
            body = read_checked(root, available[rule])
            if not body.startswith(scope) or not body.endswith(links):
                raise ValueError('shared rule context mismatch')
            end = len(body) - len(links) if links else len(body)
            bodies.append(body[len(scope):end])
        content = scope + ''.join(bodies) + links
        operation = 'read_rules'
    else:
        content = read_checked(root, family)
        operation = 'index'
    body = content.encode('utf-8')
    return {
        'reference_retrieval': 2, 'operation': operation, 'id': family_id,
        'rule_ids': selected, 'body_read': operation != 'index',
        'source_card_ids': sorted({card for rule in selected for card in available[rule]['source_card_ids']}),
        'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'content': content,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('family_id')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--rules', nargs='+')
    selection.add_argument('--full', action='store_true')
    args = parser.parse_args()
    try:
        result = retrieve(Path(__file__).resolve().parent, args.family_id, args.rules, args.full)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'reference_retrieval': 2, 'error': str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
