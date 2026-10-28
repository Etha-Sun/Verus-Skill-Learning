#!/usr/bin/env python3
"""Prepare index-only review bundles offline; deliberately has no launch mode."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

MARKER = b'## Card index\n'
ARMS = ('I0_old_index', 'I1_compact_index')
FROZEN = {
    'SKILL.md': '5d24245c9e718ac38c465ecaf89d5816839e28b72f1772618c6120f5e8829c8a',
    'cards.json': '213dc075e353f5c4a426c3d06c6c355045176b6d353667201b05736b2f4149d8',
    'card_read.py': '0d6b25e4b6e3506873492d96029cfd2a4bb55f7e71b180586b93ed4c4c76fd57',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parent, index, out = (p.resolve() for p in (args.parent, args.index, args.output))
    require(not out.exists(), 'Use a fresh output directory; never overwrite a run')
    require(out.parent == parent.parent, 'Output must be a sibling in the external run root')
    source = parent / 'bundles/R0_current'
    require(all(sha(source / f) == h for f, h in FROZEN.items()), 'Frozen R0 changed')
    old = (source / 'SKILL.md').read_bytes()
    require(old.count(MARKER) == 1, 'Expected one final card-index section')
    prefix, old_index = old.split(MARKER)
    old_index = MARKER + old_index
    new_index = index.read_bytes()
    require(new_index.startswith(MARKER), 'Index heading changed')
    bank = json.loads((source / 'cards.json').read_text())['cards']
    ids = [c['id'] for c in bank]
    require(re.findall(rb'^- (new-\d{3}):', new_index, re.M) ==
            [ident.encode() for ident in ids], 'Keep all ten IDs in original order')
    require(new_index.count(b'\n## ') == 0, 'Unexpected added section')
    prior_hashes = json.loads((parent / 'source-hashes.json').read_text())
    require(all(Path(p).is_file() and sha(p) == h for p, h in prior_hashes.items()),
            'Previously frozen dependency changed')
    from tokenizers import Tokenizer
    tokenizer_path = parent / 'runtime/tokenizer.json'
    tok = Tokenizer.from_file(str(tokenizer_path))

    def measure(payload):
        text = payload.decode()
        return {'bytes': len(payload), 'words_whitespace': len(text.split()),
                'tokens_local': len(tok.encode(text, add_special_tokens=False).ids)}

    lengths = {'old_index': measure(old_index), 'new_index': measure(new_index),
               'old_main': measure(old), 'new_main': measure(prefix + new_index)}
    require(lengths['new_index']['tokens_local'] < lengths['old_index']['tokens_local'],
            'Candidate index must be shorter')
    out.mkdir()
    for arm in ARMS:
        bundle = out / 'bundles' / arm
        shutil.copytree(source, bundle)
        if arm == ARMS[1]:
            (bundle / 'SKILL.md').write_bytes(prefix + new_index)
        require((bundle / 'SKILL.md').read_bytes().split(MARKER)[0] == prefix,
                'Executive or R0 usage changed')
        require(all(sha(bundle / f) == FROZEN[f] for f in ('cards.json', 'card_read.py')),
                'Body bank or reader changed')
        # Exercise the real frozen reader, not an imitation of its implementation.
        for card in bank:
            result = subprocess.run([sys.executable, 'card_read.py', card['id']],
                                    cwd=bundle, text=True, capture_output=True, check=True)
            payload = json.loads(result.stdout)
            require(payload['id'] == card['id'] and payload['content'] == card['content'],
                    'Reader payload mismatch')
    for name in ('EXECUTIVE.md', 'TASK.md'):
        shutil.copyfile(parent / name, out / name)
    (out / 'INDEX_OLD.md').write_bytes(old_index)
    (out / 'INDEX_NEW.md').write_bytes(new_index)
    (out / 'I0-I1.diff').write_text(''.join(difflib.unified_diff(
        old.decode().splitlines(True), (prefix + new_index).decode().splitlines(True),
        fromfile='I0_old_index/SKILL.md', tofile='I1_compact_index/SKILL.md')))
    shutil.copyfile(Path(__file__), out / 'prepare_index_ablation.py')
    (out / 'baseline-source-hashes.json').write_text(json.dumps(prior_hashes, indent=2) + '\n')
    report = {
        'status': 'offline_material_review_only', 'paid_calls': 0, 'launch_authorized': False,
        'parent': str(parent), 'source_index': str(index), 'source_index_sha256': sha(index),
        'only_actor_visible_change': 'final Card index section', 'arms': list(ARMS),
        'new_structured_representation': 'new_skeleton',
        'r0_prefix_sha256': hashlib.sha256(prefix).hexdigest(),
        'reader_payload_checks': 20, 'prior_frozen_hash_checks': len(prior_hashes),
        'tokenizer_sha256': sha(tokenizer_path), 'lengths': lengths,
        'length_caveat': 'Frozen local tokenizer, not provider-billed request tokens.',
        'known_shared_issue': 'R0 example card-001 retained unchanged; actual IDs are new-001 etc.',
        'not_yet_done': ['new runtime isolation preflight', 'launchable evaluation driver/contract',
                         'final schedule and budget review', 'API launch'],
        'artifact_hashes': {str(p.relative_to(out)): sha(p)
                           for p in sorted(out.rglob('*')) if p.is_file()},
    }
    (out / 'material-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'lengths': lengths,
                      'reader_payload_checks': 20, 'paid_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
