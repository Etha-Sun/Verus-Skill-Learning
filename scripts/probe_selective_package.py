"""Zero-provider package/tool checks inside the real actor isolation environment."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess


def main():
    config = json.loads(Path('probe_config.json').read_text())
    for name in config['hidden']:
        try:
            Path(name).read_bytes()
        except OSError:
            pass
        else:
            raise AssertionError('Private file visible')
    library = Path(config['library']) / 'set.rs'
    assert library.read_bytes()
    try:
        library.open('r+b')
    except OSError:
        pass
    else:
        raise AssertionError('vstd writable')
    try:
        socket.create_connection(('1.1.1.1', 443), timeout=1)
    except OSError:
        pass
    else:
        raise AssertionError('External network reachable')
    Path('input.rs').write_text('use vstd::prelude::*;\nverus! { proof fn probe() { } }\nfn main() {}\n')
    Path('candidate.rs').write_text(Path('input.rs').read_text().replace(
        'proof fn probe() { }', 'proof fn probe() { assert(1int == 1int); }'))
    for command in ([config['verus'], 'candidate.rs'], [config['lynette'], 'compare', '-t', 'input.rs', 'candidate.rs']):
        result = subprocess.run(command, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stdout + result.stderr
    references = json.loads(Path('reference_manifest.json').read_text())
    checks = 0
    for family, entry in references.items():
        selections = [([], entry, 'index' if len(entry.get('rules', {})) > 1 else 'body')]
        if 'rules' in entry:
            selections.append((['--full'], entry['full'], 'body'))
            selections.extend((['--rules', rule], item, 'body') for rule, item in entry['rules'].items())
        for flags, expected, kind in selections:
            result = subprocess.run(['/usr/bin/python3', 'reference_read.py', family, *flags],
                                    capture_output=True, text=True, check=True, timeout=10)
            payload = json.loads(result.stdout)
            assert payload['content'].encode() == Path(expected['path']).read_bytes()
            assert payload['sha256'] == expected['sha256']
            assert hashlib.sha256(payload['content'].encode()).hexdigest() == payload['sha256']
            if payload['reference_retrieval'] == 2:
                assert payload['body_read'] == (kind == 'body')
                if kind == 'index':
                    assert not payload['source_card_ids'] and not payload['rule_ids']
            checks += 1
    invalid = subprocess.run(['/usr/bin/python3', 'reference_read.py', '../invalid'], capture_output=True, text=True)
    assert invalid.returncode != 0 and 'content' not in json.loads(invalid.stdout)
    print(json.dumps({'passed': True, 'families': len(references), 'reader_checks': checks,
                      'private_files_hidden': True, 'vstd_readonly': True, 'network_blocked': True,
                      'dual_validation': True, 'paid_calls': 0}))


if __name__ == '__main__':
    main()
