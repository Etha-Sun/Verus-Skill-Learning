"""Qualified proof dependencies from Verus's own VIR, not source name guessing."""
from __future__ import annotations

from collections import Counter
import re

from .proof_progress import function_body, proof_line_coverage
from .trajectory_progress import normalize_code_lines


def compiler_functions(vir: str, source: str, source_path: str) -> dict[str, dict]:
    """Read local function headers, source spans and resolved function references.

    The input is the version-bound `--log vir` output. Generated functions with
    no matching source declaration are not proof-body measurement components.
    """
    starts = list(re.finditer(r'^\(@ "', vir, re.MULTILINE))
    functions = {}
    declarations = []
    counts = Counter()
    for line_number, line in enumerate(source.splitlines(), 1):
        for match in re.finditer(r'\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\b', line.split('//', 1)[0]):
            name = match.group(1)
            declarations.append((line_number, name, counts[name]))
            counts[name] += 1
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(vir)
        text = vir[start.start():end]
        header = re.match(r'\(@ "([^"\n]+)"\s+\(Function\s+:name \(Fun :path "([^"]+)"\)', text)
        if not header:
            continue
        span, path = header.groups()
        location = re.match(r'(.+):(\d+):\d+: (\d+):\d+ \(#\d+\)', span)
        if not location or location.group(1) != source_path:
            continue
        first_line, last_line = int(location.group(2)), int(location.group(3))
        crate, key = path.split('!', 1)
        name = key.rstrip('.').split('.')[-1]
        matching = [(line, occurrence) for line, leaf, occurrence in declarations
                    if leaf == name and first_line <= line <= last_line]
        mode = re.search(r':owning_module "[^"]+"\s+:mode (Proof|Spec|Exec)\b', text)
        if len(matching) != 1 or not mode:
            continue
        dependencies = sorted({ref.split('!', 1)[1] for ref in
                               re.findall(r'\(Fun :path "([^"]+)"\)', text)
                               if ref.startswith(crate + '!') and ref != path})
        functions[key] = {"key": key, "name": name, "occurrence": matching[0][1],
                          "declaration_line": matching[0][0], "mode": mode.group(1),
                          "has_body": not bool(re.search(r':body None :extra_dependencies', text)),
                          "dependencies": dependencies}
    return functions


def proof_scope(final_functions: dict, baseline_functions: dict, final_source: str,
                baseline_source: str, name: str, occurrence: int) -> dict:
    roots = [row for row in final_functions.values()
             if row['name'] == name and row['occurrence'] == occurrence]
    if len(roots) != 1:
        raise ValueError('Target has no unique compiler-qualified source mapping')
    root = roots[0]
    reachable, pending = set(), [root['key']]
    while pending:
        key = pending.pop()
        if key in reachable:
            continue
        reachable.add(key)
        pending.extend(final_functions.get(key, {}).get('dependencies', []))
    components, excluded = [], []
    for key, row in final_functions.items():
        if not row.get('has_body', True):
            continue
        if key != root['key'] and row['mode'] != 'Proof':
            continue
        body = function_body(final_source, row['name'], occurrence=row['occurrence'])
        baseline = baseline_functions.get(key)
        if baseline and (baseline['name'], baseline['occurrence'], baseline['mode']) != (
                row['name'], row['occurrence'], row['mode']):
            raise ValueError('Compiler identity changed between baseline and reference: ' + key)
        old_body = (function_body(baseline_source, baseline['name'], occurrence=baseline['occurrence'])
                    if baseline else '')
        changed = normalize_code_lines(body) != normalize_code_lines(old_body)
        if key != root['key'] and (key not in reachable or not changed):
            if changed:
                excluded.append(row)
            continue
        components.append({**row, 'is_target': key == root['key'], 'is_new': baseline is None,
                           'baseline_body': old_body})
    components.sort(key=lambda row: (not row['is_target'], row['declaration_line']))
    return {'root_key': root['key'], 'components': components,
            'excluded_changed_proofs': excluded,
            'dependency_kind': 'compiler-resolved VIR references, conservative static closure'}


def scoped_line_coverage(source: str, reference: str, components: list[dict]) -> dict:
    """Use a fixed denominator and never match a line across different functions."""
    details, matched, total, unknown = [], 0, 0, False
    for component in components:
        name, occurrence = component['name'], component['occurrence']
        ref = function_body(reference, name, occurrence=occurrence)
        denominator = len(normalize_code_lines(ref))
        if not denominator:
            details.append({'key': component['key'], 'matched_lines': 0, 'reference_lines': 0,
                            'coverage': None, 'status': 'empty_reference'})
            continue
        status, error = 'present', None
        try:
            current_count = sum(len(re.findall(rf'\bfn\s+{re.escape(name)}\b', line.split('//', 1)[0]))
                                for line in source.splitlines())
            reference_count = sum(len(re.findall(rf'\bfn\s+{re.escape(name)}\b', line.split('//', 1)[0]))
                                  for line in reference.splitlines())
            if reference_count > 1 and current_count != reference_count:
                raise ValueError('Ambiguous duplicate function identity: ' + name)
            current = function_body(source, name, occurrence=occurrence)
            count = proof_line_coverage(current, ref)['matched_final_lines']
        except ValueError as exc:
            declarations = sum(len(re.findall(rf'\bfn\s+{re.escape(name)}\b', line.split('//', 1)[0]))
                               for line in source.splitlines())
            if component['is_new'] and not component['is_target'] and declarations == 0:
                count, status = 0, 'not_created'
            else:
                count, status, error = None, 'unknown', str(exc)
                unknown = True
        matched += count or 0
        total += denominator
        details.append({'key': component['key'], 'matched_lines': count,
                        'reference_lines': denominator,
                        'coverage': count / denominator if count is not None else None,
                        'status': status, 'error': error})
    return {'coverage': matched / total if total and not unknown else None,
            'matched_final_lines': matched if not unknown else None, 'final_lines': total,
            'components': details}
