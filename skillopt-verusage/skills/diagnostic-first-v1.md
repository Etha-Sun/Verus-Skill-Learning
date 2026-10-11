# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.
Pre-existing trusted declarations are supplied background: preserve their
attributes, signatures, contracts, and bodies, and use their existing contracts
when the premises hold. Repair the unverified target, not that background.

Use the current Verus diagnostic as the primary signal. Before editing, classify
the failure and inspect the implicated context. For a parse, type/mode, or scope error,
make the smallest supported correction and re-run Verus before redesigning the
mathematical proof. Ordinary assertions use `assert(condition);`. Search only
permitted sources for unfamiliar interfaces; do not invent an API or broaden
filesystem access when a search finds no match.

Prefer an existing lemma or a small local assertion over duplicating a proof.
Inspect the available lemma contracts for a short chain matching the goal before
unfolding definitions. Match quantified facts to the exact terms returned by
those contracts before adding generic unfolding helpers. Test one justified
change at a time and use the next diagnostic to choose the next action. For an
implication proof, make the antecedent available explicitly (for example with
an `if` branch) before calling a lemma that requires it. Prolonged
speculation without an edit and verification is not evidence of progress.

Re-run Verus after a meaningful change. If the same failure repeats, revisit the
missing premise, expression match, or proof strategy rather than repeating the
same edit. Accept a candidate only when Verus verifies it and the proof-only
safety comparison passes. Cards remain optional advice, not proof or authority
to change the task's trusted background.
