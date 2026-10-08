import unittest

from verus_self_evolve.proof_dependencies import compiler_functions, proof_scope, scoped_line_coverage
from verus_self_evolve.proof_progress import greedy_prune_proof_lines


def vir_function(name, line, dependencies=(), mode='Proof'):
    refs = ' '.join(f'(Fun :path "candidate!{dep}")' for dep in dependencies)
    return (f'(@ "candidate.rs:{line}:1: {line}:40 (#0)" (Function '
            f':name (Fun :path "candidate!{name}") :owning_module "candidate!." '
            f':mode {mode} :body ({refs})))\n')


class ProofDependenciesTest(unittest.TestCase):
    def test_compiler_scope_selects_changed_transitive_helpers_not_unused_or_library_code(self):
        original = 'proof fn target() {\n}\nproof fn unchanged() {\n    assert(old);\n}\n'
        final = ('proof fn target() {\n    helper();\n}\n'
                 'proof fn unchanged() {\n    assert(old);\n}\n'
                 'proof fn helper() {\n    nested();\n}\n'
                 'proof fn nested() {\n    assert(needed);\n}\n'
                 'proof fn unused() {\n    assert(wasted);\n}\n')
        vir = (vir_function('target.', 1, ['helper.', 'unchanged.']) +
               vir_function('unchanged.', 4) + vir_function('helper.', 7, ['nested.']) +
               vir_function('nested.', 10) + vir_function('unused.', 13))
        functions = compiler_functions(vir, final, 'candidate.rs')
        baseline = compiler_functions(vir_function('target.', 1) + vir_function('unchanged.', 3),
                                      original, 'candidate.rs')
        scope = proof_scope(functions, baseline, final, original, 'target', 0)
        self.assertEqual([c['name'] for c in scope['components']], ['target', 'helper', 'nested'])
        self.assertEqual([c['name'] for c in scope['excluded_changed_proofs']], ['unused'])

    def test_qualified_duplicate_target_uses_declaration_span(self):
        source = ('impl A {\nfn target() {\n    first();\n}\n}\n'
                  'impl B {\nfn target() {\n    second();\n}\n}\n')
        vir = vir_function('impl&%0.target.', 2, mode='Exec') + vir_function('impl&%1.target.', 7, mode='Exec')
        functions = compiler_functions(vir, source, 'candidate.rs')
        scope = proof_scope(functions, functions, source, source, 'target', 1)
        self.assertEqual(scope['root_key'], 'impl&%1.target.')

    def test_generated_or_imported_functions_do_not_become_source_components(self):
        source = 'proof fn target() {\n}\n'
        text = vir_function('target.', 1) + vir_function('generated.', 1)
        text += vir_function('library.', 1).replace('candidate.rs:', 'vstd/lib.rs:')
        self.assertEqual(set(compiler_functions(text, source, 'candidate.rs')), {'target.'})

    def test_missing_compiler_root_is_an_error_not_text_guessing(self):
        with self.assertRaisesRegex(ValueError, 'compiler-qualified'):
            proof_scope({}, {}, '', '', 'target', 0)

    def test_external_or_bodyless_declarations_are_not_proof_components(self):
        source = 'proof fn target() {\n    external();\n}\nproof fn external();\n'
        text = vir_function('target.', 1, ['external.'])
        text += vir_function('external.', 4).replace(':body ()', ':body None :extra_dependencies ()')
        functions = compiler_functions(text, source, 'candidate.rs')
        scope = proof_scope(functions, functions, source, source, 'target', 0)
        self.assertEqual([c['name'] for c in scope['components']], ['target'])

    def test_component_matching_cannot_borrow_lines_from_another_function(self):
        reference = ('proof fn target() {\n    first();\n}\n'
                     'proof fn helper() {\n    second();\n}\n')
        source = ('proof fn target() {\n    first();\n    second();\n}\n'
                  'proof fn helper() {\n}\n')
        components = [{'key': 'target.', 'name': 'target', 'occurrence': 0, 'is_target': True, 'is_new': False},
                      {'key': 'helper.', 'name': 'helper', 'occurrence': 0, 'is_target': False, 'is_new': True}]
        result = scoped_line_coverage(source, reference, components)
        self.assertEqual(result['coverage'], 0.5)
        self.assertEqual(result['components'][1]['coverage'], 0)

    def test_new_helper_absence_is_zero_but_target_absence_is_unknown(self):
        reference = ('proof fn target() {\n    helper();\n}\n'
                     'proof fn helper() {\n    assert(needed);\n}\n')
        components = [{'key': 'target.', 'name': 'target', 'occurrence': 0, 'is_target': True, 'is_new': False},
                      {'key': 'helper.', 'name': 'helper', 'occurrence': 0, 'is_target': False, 'is_new': True}]
        result = scoped_line_coverage('proof fn target() {\n}\n', reference, components)
        self.assertEqual(result['coverage'], 0)
        self.assertEqual(result['final_lines'], 2)
        self.assertEqual(result['components'][1]['status'], 'not_created')
        probe = scoped_line_coverage('proof fn probe() {\n}\n', reference, components)
        self.assertIsNone(probe['coverage'])

    def test_unbalanced_existing_helper_is_unknown_not_not_created(self):
        reference = 'proof fn helper() {\n    assert(needed);\n}\n'
        components = [{'key': 'helper.', 'name': 'helper', 'occurrence': 0, 'is_target': False, 'is_new': True}]
        result = scoped_line_coverage('proof fn helper() {\n', reference, components)
        self.assertIsNone(result['coverage'])
        self.assertEqual(result['components'][0]['status'], 'unknown')

    def test_duplicate_occurrence_drift_is_unknown_not_borrowed(self):
        reference = ('impl A {\nproof fn helper() {\n    assert(a);\n}\n}\n'
                     'impl B {\nproof fn helper() {\n    assert(b);\n}\n}\n')
        source = 'impl B {\nproof fn helper() {\n    assert(b);\n}\n}\n'
        components = [{'key':'impl&%0.helper.','name':'helper','occurrence':0,
                       'is_target':False,'is_new':False}]
        result = scoped_line_coverage(source, reference, components)
        self.assertIsNone(result['coverage'])
        self.assertIn('Ambiguous duplicate', result['components'][0]['error'])

    def test_new_helper_pruning_uses_explicit_body_not_an_altered_preservation_input(self):
        original = 'proof fn target() {\n}\n'
        final = original + 'proof fn helper() {\n    assert(needed);\n    assert(extra);\n}\n'
        seen = []
        def verify(source):
            seen.append(source)
            return 'assert(needed);' in source, 'checked'
        result = greedy_prune_proof_lines(original, final, 'helper', verify, baseline_body='')
        self.assertIn('assert(needed);', result['pruned_source'])
        self.assertNotIn('assert(extra);', result['pruned_source'])
        self.assertTrue(all(source.startswith(original) for source in seen))


if __name__ == '__main__':
    unittest.main()
