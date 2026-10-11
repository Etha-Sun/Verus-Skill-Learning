import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    'failure_probes', Path(__file__).resolve().parents[1] / 'scripts/probe_guidance_failure_cases.py')
probes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probes)


def test_parentheses_probe_preserves_quantified_assertions_and_other_statements():
    source = '    assert stable(spec).satisfied_by(ex);\n    assert forall |i: nat| p(i) by {\n    };\n'
    fixed = probes.fix_assert_parentheses(source)
    assert fixed == '    assert(stable(spec).satisfied_by(ex));\n    assert forall |i: nat| p(i) by {\n    };\n'


def test_body_probe_preserves_supplied_contract_and_trusted_background():
    source = ('#[verifier::external_body]\nproof fn supplied() { unimplemented!() }\n'
              'proof fn target()\n    ensures true,\n{\n}\n')
    result = probes.replace_body(source, 'target', '    assert(true);\n')
    assert result == source.replace('{\n}\n', '{\n    assert(true);\n}\n')


def test_missing_probe_target_fails_closed():
    import pytest
    with pytest.raises(ValueError, match='not found'):
        probes.replace_body('fn main() {}\n', 'missing', '')
