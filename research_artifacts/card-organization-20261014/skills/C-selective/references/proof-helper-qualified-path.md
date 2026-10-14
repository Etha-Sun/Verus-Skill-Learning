# Qualified proof-only helper/macro references

## Scope

- Consult when: Proof helper, macro, or closure is reported out of scope
- Consult when: Adding a top-level import would survive deghosting and cause a safety comparison difference
- Consult when: The item is exposed under a fully qualified path
- Not for: Difference is a real executable or contract change
- Not for: Fully qualified path is not the installed path

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** The sequence-equality closure entry specializes the general out-of-scope proof-helper route and adds its equality-obligation context. Both may match a sequence helper; choose by the missing item, not by an invented exclusion of sequence cases from the general rule.

<a id="qualified-proof-helper-macro-path"></a>
- [qualified-proof-helper-macro-path](proof-helper-qualified-path--qualified-proof-helper-macro-path.md): Proof helper or macro out of scope.
  - When: A proof-only helper or macro is unavailable locally and a new top-level import may violate preservation.
  - Avoid: No usable installed qualified path, executable artifacts, or an already harmless import.

<a id="sequence-equality-closure-qualified-path"></a>
- [sequence-equality-closure-qualified-path](proof-helper-qualified-path--sequence-equality-closure-qualified-path.md): Sequence-equality closure out of scope.
  - When: A sequence-equality closure mechanism is unavailable or its proposed import fails safety comparison.
  - Avoid: No library-root export or the local import policy already permits it.

Read: `python3 reference_read.py proof-helper-qualified-path --rules ID [ID ...]`

Whole reference: `python3 reference_read.py proof-helper-qualified-path --full` or [proof-helper-qualified-path--full.md](proof-helper-qualified-path--full.md).
