# Post-verification warning and proof-preservation cleanup

## Scope

- Consult when: Verus verification is already successful
- Consult when: Remaining issue is a proof-only safety comparison difference or low-confidence auto-trigger/implication warning
- Not for: Any proof goal is still failing

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** After verification, distinguish executable-shape differences, module-scope directives, set-proof imports/macros, and warnings only. Directive and set-import cases may overlap and offer alternatives; a warning-only case is not evidence of a proof repair.

<a id="exec-shape-deghost-restore"></a>
- [exec-shape-deghost-restore](post-verification-cleanup--exec-shape-deghost-restore.md): Verified proof with executable-shape difference.
  - When: Verus succeeds but Lynette reports changed executable calls, bindings, branches, or returns.
  - Avoid: The proof strategy genuinely needs executable changes; semantic equivalence alone is insufficient.

<a id="module-scope-proof-directive-scope-down"></a>
- [module-scope-proof-directive-scope-down](post-verification-cleanup--module-scope-proof-directive-scope-down.md): Verified proof with module-scope directive difference.
  - When: A proof-import-like directive at module scope causes a safety-comparison difference after verification.
  - Avoid: The directive is illegal locally or cannot be partitioned across dependent proofs.

<a id="qualified-proof-helper-set-equality-no-import"></a>
- [qualified-proof-helper-set-equality-no-import](post-verification-cleanup--qualified-proof-helper-set-equality-no-import.md): Verified set proof with import or macro difference.
  - When: A set-equality proof verifies but safety comparison rejects a proof-only import or macro change.
  - Avoid: A real executable, signature, or specification difference.

<a id="post-verification-trigger-implication-warning-cleanup"></a>
- [post-verification-trigger-implication-warning-cleanup](post-verification-cleanup--post-verification-trigger-implication-warning-cleanup.md): Warnings after successful verification.
  - When: The proof already verifies and only automatic-trigger or quantified-implication warnings remain.
  - Avoid: An active quantifier or implication proof failure.

Read: `python3 reference_read.py post-verification-cleanup --rules ID [ID ...]`

Whole reference: `python3 reference_read.py post-verification-cleanup --full` or [post-verification-cleanup--full.md](post-verification-cleanup--full.md).
