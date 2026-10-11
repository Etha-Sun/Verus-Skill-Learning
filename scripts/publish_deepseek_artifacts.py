"""Publish reviewed October trace/card evidence without changing source runs.

Archives contain sanitized, content-deduplicated text, not complete run folders.
The manifest records every selected source path, including exact duplicates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tarfile


REDACTED = '[REDACTED]'
SENSITIVE = re.compile(
    r'^(authorization|api[-_]?key|x-api-key|password|access_token|refresh_token|'
    r'credential|secret|encrypted_content)$', re.I)
TOKEN = re.compile(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|'
                   r'github_pat_[A-Za-z0-9_]{20,})\b')
BEARER = re.compile(r'(?i)\bBearer\s+(?!\[REDACTED\])[A-Za-z0-9._~+/=-]+')
HOME_PATH = re.compile(r'/(?:home|Users)/[^/\s"\x27\\<>]+')
SCRATCH_PATH = re.compile(r'/zp_vegeta/[^\s"\x27\\<>]*')
KEY_VALUE = re.compile(
    r'(?i)(["\x27]?(?:authorization|api[_-]?key|password|access_token|refresh_token|encrypted_content|credential|secret)'
    r'["\x27]?\s*[:=]\s*)(["\x27])([^"\x27\n]*)(\2)')
SKIP_DIRS = {'workspace', 'toolchain', '__pycache__', '.git', '.codex',
             'val_inputs', 'inputs', 'config',
             'controller-config', 'sealed', 'node_modules', '.venv'}
TRACE_NAMES = {'codex_events.raw.jsonl', 'agent_events.jsonl', 'conversation.json',
               'trajectory.json', 'trajectory.jsonl', 'trace.json', 'trace.jsonl',
               'full_trace.json', 'full_trace.md', 'prompt.txt', 'target_user_prompt.txt',
               'last_message.txt', 'result.json', 'validation.json', 'run_manifest.json',
               'fidelity_audit.json', 'continuation_contract.json', 'visibility_manifest.json'}
CARD_NAMES = {'cards.json', 'SKILL.md', 'card_read.py', 'card_query.py', 'revision.json'}
LOG_NAMES = {'codex_stderr.log', 'run.log', 'bridge.log', 'campaign.log', 'resume.log'}
EVIDENCE_TREES = {'snapshots', 'provider_capture', 'calls', 'hints',
                  'checkpoint_preparation', 'banks', 'artifacts', 'provider_failure_evidence'}
TEXT_SUFFIXES = {'.json', '.jsonl', '.md', '.txt', '.raw', '.rs', '.diff', '.patch', '.py', '.log'}
PART_BYTES = 40 * 1024 * 1024


def selected(relative):
    if any(p in SKIP_DIRS or 'sealed' in p.lower() for p in relative.parts):
        return False
    return (relative.name in TRACE_NAMES | CARD_NAMES | LOG_NAMES
            or (relative.suffix in TEXT_SUFFIXES and any(p in EVIDENCE_TREES for p in relative.parts))
            or relative.name in {'provider_calls.jsonl', 'bridge_calls.jsonl',
                                 'selected_episode_ledger.jsonl', 'summary.json',
                                 'validation_summary.json', 'validation_rows.json',
                                 'executive_summary.json', 'single_executive_summary.json',
                                 'full_executive_summary.json', 'full_validation_summary.json',
                                 'guidance_summary.json', 'cost_summary.json', 'statistics.json'})


def known_secrets(repo):
    values = [v for k, v in os.environ.items() if SENSITIVE.search(k) or
              re.search(r'(?:API_KEY|ACCESS_TOKEN|SECRET|PASSWORD)$', k, re.I)]
    envfile = repo / '.env'
    if envfile.is_file():
        for line in envfile.read_text().splitlines():
            match = re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line.strip())
            if match and re.search(r'(?:API_KEY|ACCESS_TOKEN|SECRET|PASSWORD)$', match[1], re.I):
                values.append(match[2].strip().strip('"\x27'))
    return sorted({v for v in values if len(v) >= 8 and not v.startswith('${')}, key=len, reverse=True)


def sanitize(data, suffix, roots, secrets=()):
    counts = Counter()

    def clean_text(text):
        for secret in secrets:
            if secret in text:
                counts['known_secret'] += text.count(secret)
                text = text.replace(secret, REDACTED)
        for pattern, replacement, key in ((TOKEN, REDACTED, 'token'),
                                          (BEARER, 'Bearer '+REDACTED, 'bearer')):
            text, n = pattern.subn(replacement, text)
            counts[key] += n
        text, n = KEY_VALUE.subn(lambda m: m[1]+m[2]+REDACTED+m[4], text)
        counts['credential_assignment'] += n
        for source, alias in roots:
            counts['path'] += text.count(source)
            text = text.replace(source, alias)
        text, n = HOME_PATH.subn('<HOME>', text)
        counts['path'] += n
        text, n = SCRATCH_PATH.subn('<SCRATCH_PATH>', text)
        counts['path'] += n
        if '-----BEGIN ' in text and 'PRIVATE KEY-----' in text:
            raise ValueError('Private key material: refusing publication')
        return text

    def clean(value):
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                key = clean_text(k)
                if SENSITIVE.fullmatch(k):
                    result[key] = REDACTED
                    counts['sensitive_field'] += 1
                else:
                    result[key] = clean(v)
            return result
        if isinstance(value, list):
            return [clean(v) for v in value]
        return clean_text(value) if isinstance(value, str) else value

    text = data.decode('utf-8')
    if suffix in {'.json', '.raw'}:
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            text = clean_text(text)
        else:
            text = json.dumps(clean(value), ensure_ascii=False, separators=(',', ':'))+'\n'
    elif suffix == '.jsonl':
        lines = []
        for line in text.splitlines():
            if not line.strip():
                lines.append(line)
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                lines.append(clean_text(line))
            else:
                lines.append(json.dumps(clean(value), ensure_ascii=False, separators=(',', ':')))
        text = '\n'.join(lines)+'\n'
    else:
        text = clean_text(text)
    if TOKEN.search(text) or BEARER.search(text) or HOME_PATH.search(text) or SCRATCH_PATH.search(text):
        raise ValueError('Residual sensitive text: refusing publication')
    if any(secret in text for secret in secrets):
        raise ValueError('Residual known secret: refusing publication')
    return text.encode(), dict(+counts)


def files_in(run):
    for parent, dirs, names in os.walk(run, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and 'sealed' not in d.lower()
                         and not (Path(parent)/d).is_symlink())
        for name in sorted(names):
            path = Path(parent)/name
            if not path.is_symlink() and path.is_file() and selected(path.relative_to(run)):
                yield path


def publish(run_root, repo, destination):
    if destination.exists():
        raise ValueError('Publication destination already exists')
    destination.mkdir(parents=True)
    roots = sorted([(str(repo.resolve()), '<REPO>'),
                    (str(run_root.resolve()), '<RUN_ROOT>/skillopt-verusage'),
                    (str(run_root.parent.resolve()), '<RUN_ROOT>'),
                    (str(run_root.parent.parent/'verusys-result'), '<DATA_ROOT>'),
                    (str(run_root.parent.parent), '<SCRATCH>'),
                    (str(Path.home()), '<HOME>')], key=lambda p: len(p[0]), reverse=True)
    secrets = known_secrets(repo)
    seen = {}
    runs = []
    totals = Counter()
    with (destination/'files.jsonl').open('x') as manifest:
        for run in sorted(run_root.iterdir()):
            if not run.is_dir() or run.is_symlink() or not re.search(r'202610\d\d', run.name):
                continue
            stats = Counter()
            archive_path = destination/(run.name+'.tar.gz')
            with archive_path.open('xb') as output, gzip.GzipFile(fileobj=output, mode='wb', mtime=0, compresslevel=6) as compressed:
                with tarfile.open(fileobj=compressed, mode='w|') as archive:
                    for path in files_in(run):
                        relative = path.relative_to(run_root).as_posix()
                        if not relative.isascii():
                            raise ValueError('Non-ASCII publication path: '+relative)
                        before = path.stat()
                        raw = path.read_bytes()
                        after = path.stat()
                        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                            raise ValueError('Source changed during read: '+relative)
                        digest = hashlib.sha256(raw).hexdigest()
                        record = {'path':relative, 'source_sha256':digest, 'source_bytes':len(raw)}
                        stats['source_files'] += 1
                        stats['source_bytes'] += len(raw)
                        if digest in seen:
                            record.update(seen[digest])
                            stats['duplicate_files'] += 1
                        else:
                            data, redactions = sanitize(raw, path.suffix, roots, secrets)
                            info = tarfile.TarInfo(relative)
                            info.size = len(data)
                            info.mode = 0o644
                            archive.addfile(info, io.BytesIO(data))
                            record.update({'archive_run':run.name, 'member':relative,
                                           'published_sha256':hashlib.sha256(data).hexdigest(),
                                           'published_bytes':len(data), 'redactions':redactions})
                            seen[digest] = {k:v for k,v in record.items() if k not in
                                            {'path','source_sha256','source_bytes'}}
                            stats['unique_files'] += 1
                            stats['published_bytes'] += len(data)
                            if path.name == 'cards.json':
                                target = destination/'cards'/relative
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(json.dumps(json.loads(data), ensure_ascii=False, indent=2).encode()+b'\n')
                                stats['readable_card_banks'] += 1
                        manifest.write(json.dumps(record, sort_keys=True)+'\n')
            parts = []
            if archive_path.stat().st_size > PART_BYTES:
                with archive_path.open('rb') as source:
                    number = 0
                    while chunk := source.read(PART_BYTES):
                        part = archive_path.with_name(archive_path.name+f'.part{number:03d}')
                        part.write_bytes(chunk)
                        parts.append(part)
                        number += 1
                archive_path.unlink()  # Only the just-created publication archive.
            else:
                parts = [archive_path]
            archives = [{'path':p.name,'bytes':p.stat().st_size,
                         'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in parts]
            runs.append({'run':run.name, **stats, 'archives':archives})
            totals.update(stats)
            print(json.dumps({'run':run.name, **stats,
                              'compressed_bytes':sum(p['bytes'] for p in archives)}), flush=True)
    summary = {'schema_version':'reviewed-deepseek-artifacts-v1', 'source_root_alias':'VERUS_SKILL_RUN_ROOT/skillopt-verusage',
               'scope':'All selected October 2026 trace/card files, including interrupted runs and exact duplicate references.',
               'sanitization':'Credentials, opaque encrypted content and machine-local paths redacted; JSON normalized. No missing reasoning reconstructed.',
               'excluded':'Full workspaces/toolchains/config/auth/raw datasets/sealed data/meeting transcripts and unrelated older projects.',
               'source_runs_unchanged':True, 'totals':dict(totals), 'runs':runs}
    (destination/'manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    return complete_cards(run_root, repo, destination)


def complete_cards(run_root, repo, destination):
    """Supplement unusual card layouts and trace failure diagnostics."""
    summary = json.loads((destination/'manifest.json').read_text())
    rows = list(manifest_records(destination))
    recorded = {r['path'] for r in rows}
    seen = {r['source_sha256']:r for r in rows}
    roots = sorted([(str(repo.resolve()), '<REPO>'),
                    (str(run_root.parent.resolve()), '<RUN_ROOT>'),
                    (str(run_root.parent.parent/'verusys-result'), '<DATA_ROOT>'),
                    (str(run_root.parent.parent), '<SCRATCH>'),
                    (str(Path.home()), '<HOME>')], key=lambda p:len(p[0]), reverse=True)
    secrets = known_secrets(repo)
    totals = Counter(summary['totals'])
    added = 0
    added_cards = 0
    manifest_path = destination/'files.jsonl'
    opener = open
    if not manifest_path.exists():
        manifest_path = destination/'files.jsonl.gz'
        opener = gzip.open
    with opener(manifest_path, 'at') as manifest:
        for run in sorted(run_root.iterdir()):
            if not run.is_dir() or run.is_symlink() or not re.search(r'202610\d\d', run.name):
                continue
            for path in files_in(run):
                relative = path.relative_to(run_root).as_posix()
                wanted = path.name in CARD_NAMES | LOG_NAMES or 'provider_failure_evidence' in path.parts
                if not wanted or relative in recorded:
                    continue
                if not relative.isascii():
                    raise ValueError('Non-ASCII card asset path')
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                row = {'path':relative,'source_sha256':digest,'source_bytes':len(raw)}
                if digest in seen:
                    row.update({k:v for k,v in seen[digest].items()
                                if k not in {'path','source_sha256','source_bytes'}})
                    totals['duplicate_files'] += 1
                else:
                    data, redactions = sanitize(raw, path.suffix, roots, secrets)
                    if path.name == 'cards.json':
                        data = json.dumps(json.loads(data), ensure_ascii=False, indent=2).encode()+b'\n'
                        totals['readable_card_banks'] += 1
                    direct = ('cards/' if path.name in CARD_NAMES else 'trace_support/')+relative
                    target = destination/direct
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    if target.stat().st_size > PART_BYTES:
                        raise ValueError('Supplemental file exceeds publication volume limit')
                    row.update({'direct_path':direct,'member':relative,
                                'published_sha256':hashlib.sha256(data).hexdigest(),
                                'published_bytes':len(data),'redactions':redactions})
                    totals['unique_files'] += 1
                    totals['published_bytes'] += len(data)
                manifest.write(json.dumps(row, sort_keys=True)+'\n')
                seen[digest] = row
                recorded.add(relative)
                totals['source_files'] += 1
                totals['source_bytes'] += len(raw)
                added += 1
                added_cards += int(path.name in CARD_NAMES)
    summary['totals'] = dict(totals)
    summary['supplemental_paths'] = summary.get('supplemental_paths', 0)+added
    summary['supplemental_card_asset_paths'] = summary.get('supplemental_card_asset_paths', 0)+added_cards
    if manifest_path.suffix != '.gz':
        packed = destination/'files.jsonl.gz'
        with manifest_path.open('rb') as source, packed.open('xb') as target:
            with gzip.GzipFile(fileobj=target, mode='wb', mtime=0, compresslevel=6) as compressed:
                shutil.copyfileobj(source, compressed)
        manifest_path.unlink()  # Only the just-created publication manifest.
        manifest_path = packed
    summary['file_manifest'] = {'path':manifest_path.name, 'bytes':manifest_path.stat().st_size,
                               'sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    principals = []
    for label, relative, expected in (
        ('original63', 'train38-hindsight-native-20261007-aQfE7o/artifacts/original_only/cards.json', 63),
        ('augmented78', 'train38-hindsight-native-20261007-aQfE7o/artifacts/augmented/cards.json', 78),
        ('repaired78', 'card-repair-validation-20261008-3gtA3H/revised78/cards.json', 78),
    ):
        source = run_root/relative
        if not source.is_file():
            continue
        data, _ = sanitize(source.read_bytes(), '.json', roots, secrets)
        bank = json.loads(data)
        if len(bank['cards']) != expected or relative not in recorded:
            raise ValueError('Principal card bank coverage mismatch')
        target = destination/'cards'/(label+'.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(bank, ensure_ascii=False, indent=2)+'\n')
        principals.append({'label':label,'path':target.relative_to(destination).as_posix(),
                           'source_path':relative,'cards':expected,
                           'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    summary['principal_banks'] = principals
    (destination/'manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def manifest_records(publication):
    path = publication/'files.jsonl'
    opener = open
    if not path.exists():
        path = publication/'files.jsonl.gz'
        opener = gzip.open
    with opener(path, 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def audit(publication, repo):
    """Independently hash every stored member and check all logical references."""
    summary = json.loads((publication/'manifest.json').read_text())
    rows = list(manifest_records(publication))
    if len({r['path'] for r in rows}) != len(rows):
        raise ValueError('Duplicate manifest paths')
    expected = {r['member']:r['published_sha256'] for r in rows if 'direct_path' not in r}
    actual = {}
    secrets = [v.encode() for v in known_secrets(repo)]
    bad_paths = re.compile(rb'/(?:home|Users)/[^/\s"\x27\\<>]+|/zp_vegeta/')
    bad_tokens = re.compile(TOKEN.pattern.encode())
    bad_bearer = re.compile(BEARER.pattern.encode())

    def check(data):
        if bad_paths.search(data) or bad_tokens.search(data) or bad_bearer.search(data):
            raise ValueError('Sensitive content in publication')
        if any(secret in data for secret in secrets):
            raise ValueError('Known credential in publication')

    for run in summary['runs']:
        parts = []
        for part in run['archives']:
            data = (publication/part['path']).read_bytes()
            if len(data) != part['bytes'] or hashlib.sha256(data).hexdigest() != part['sha256']:
                raise ValueError('Archive checksum mismatch')
            if len(data) > PART_BYTES:
                raise ValueError('Archive volume exceeds publication limit')
            parts.append(data)
        with tarfile.open(fileobj=io.BytesIO(b''.join(parts)), mode='r:gz') as archive:
            for member in archive:
                if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                    raise ValueError('Unsafe archive member')
                data = archive.extractfile(member).read()
                check(data)
                actual[member.name] = hashlib.sha256(data).hexdigest()
        print(json.dumps({'audited_run':run['run'], 'stored_members_so_far':len(actual)}), flush=True)
    if actual != expected:
        raise ValueError('Archive/member coverage mismatch')
    for row in rows:
        if 'direct_path' in row:
            data = (publication/row['direct_path']).read_bytes()
            check(data)
            if hashlib.sha256(data).hexdigest() != row['published_sha256']:
                raise ValueError('Direct card asset checksum mismatch')
        elif actual[row['member']] != row['published_sha256']:
            raise ValueError('Alias checksum mismatch')
    for path in (publication/'cards').rglob('*'):
        if path.is_file():
            check(path.read_bytes())
    for bank in summary['principal_banks']:
        data = (publication/bank['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != bank['sha256'] or len(json.loads(data)['cards']) != bank['cards']:
            raise ValueError('Principal bank mismatch')
    receipt = {'schema_version':'publication-content-audit-v1', 'logical_files':len(rows),
               'stored_archive_members':len(actual), 'source_runs':len(summary['runs']),
               'all_member_hashes_verified':True, 'all_aliases_resolvable':True,
               'credential_and_personal_path_scan_passed':True,
               'maximum_archive_volume_bytes':PART_BYTES}
    (publication/'audit.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def restore(publication, output):
    if output.exists():
        raise ValueError('Restore destination must not exist')
    output.mkdir(parents=True)
    summary = json.loads((publication/'manifest.json').read_text())
    file_manifest = summary.get('file_manifest')
    if file_manifest and hashlib.sha256((publication/file_manifest['path']).read_bytes()).hexdigest() != file_manifest['sha256']:
        raise ValueError('File manifest checksum mismatch')
    for run in summary['runs']:
        with io.BytesIO() as combined:
            for part in run['archives']:
                data = (publication/part['path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != part['sha256']:
                    raise ValueError('Archive checksum mismatch: '+part['path'])
                combined.write(data)
            combined.seek(0)
            with tarfile.open(fileobj=combined, mode='r:gz') as archive:
                archive.extractall(output, filter='data')
    for record in manifest_records(publication):
        target = output/record['path']
        source_root = publication if 'direct_path' in record else output
        source = source_root/record.get('direct_path', record['member'])
        if output.resolve() not in target.resolve().parents or source_root.resolve() not in source.resolve().parents:
            raise ValueError('Unsafe manifest path')
        if hashlib.sha256(source.read_bytes()).hexdigest() != record['published_sha256']:
            raise ValueError('Published file checksum mismatch')
        if target != source:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('publish')
    export.add_argument('--run-root', type=Path, required=True)
    export.add_argument('--repo', type=Path, default=Path.cwd())
    export.add_argument('--output', type=Path, required=True)
    unpack = sub.add_parser('restore')
    unpack.add_argument('publication', type=Path)
    unpack.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('audit')
    verify.add_argument('publication', type=Path)
    verify.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.command == 'publish':
        publish(args.run_root, args.repo, args.output)
    elif args.command == 'restore':
        restore(args.publication, args.output)
    else:
        audit(args.publication, args.repo)


if __name__ == '__main__':
    main()
