# VeruSAGE Executive Skill

Repair only proof and ghost code. Preserve executable behavior, function
signatures, specifications, and termination requirements. Never introduce
`assume`, `admit`, `external_body`, new axioms, or a verification bypass.

Use the current Verus diagnostic as the primary signal. Before editing, classify
the failure (precondition, postcondition, invariant entry/exit, quantifier,
arithmetic, type/mode/scope, or termination), inspect the implicated context,
and choose the narrowest matching VeruSAGE action. Prefer an existing lemma or a
small local assertion over duplicating a proof. Re-run Verus after a meaningful
change; if the same failure repeats, change the proof strategy rather than
repeating the same edit. Accept a candidate only when Verus verifies it and the
proof-only safety comparison passes.

## On-demand proof repair cards

An optional card library is available in this workspace. The complete index
below lists every card's title and routing description. You decide whether, when, and which
cards to read based on your current proof state; no retrieval ranking or fixed
card count is imposed. Read any indexed card by ID:

    python3 card_read.py card-001

You may read additional cards, decline their advice, or continue without them.
Check Trigger and Avoid when against the current state, perform required
prechecks, and use normal verification and preservation tools after acting.
Cards are fallible advice, not proof. Briefly identify a consulted card's ID
and why it applies or why you decline it in your progress message. Do not
bulk-read cards.json or modify library files. Reading is optional and uses the
normal task time and context budget.

Index descriptions are routing cues only. Read the full Trigger and Avoid when before acting.

### When a card can help

Treat the index as a map, not a replacement for a card's conditions. Consider
reading a matching card before inventing an unfamiliar helper, choosing between
proof strategies, or repeating an edit after the same obligation fails again.
An unfamiliar diagnostic, uncertain lemma contract, or no clear next logical
step is also a reason to consult the index. These are decision cues, not a
mandatory stall detector or a requirement to read a fixed number of cards.

Choose by the current failed obligation, available premises, and attempted
action, not by a shared topic word alone. Read the selected card's full Trigger,
Action, Validate and Avoid when before relying on its advice. A missing
antecedent, missing trigger, and missing logical premise are different problems;
similarly, raw state predicates, lifted temporal predicates and always wrappers
are different types of argument. Check the exact current diagnostic and local
helper contract. If adjacent cards suggest different routes, inspect the
relevant alternatives rather than assuming the first match is applicable.

After reading, briefly say which condition matches (or why you decline), try
one justified proof-only change, and check its diagnostics and preservation.
Do not keep rereading the same advice when a premise is absent. Prefer a known
small repair or a confirmed local lemma without a card when that is sufficient;
no matching card is a valid outcome. A warning after verification is optional
cleanup, not a failed proof. Once both checks pass, stop unless cleanup is
worth its cost. A card read or an index mention is not itself progress.

## Card index

- card-001: Known library algebraic obligation; inspect and reuse a lemma with matching conclusion and premises.
- card-002: Set or image equality without a matching lemma; membership extensionality and reverse-direction witnesses.
- card-003: Marshalable values with equal serialization; use an existing trait bridge to view equality.
- card-004: Record equality from pointwise-equal function fields; first try a local field-equality assertion.
- card-005: Direct function-field equality fails and helpers are unavailable; consider built-in extensional equality.
- card-006: Quantified proof lacks its antecedent: diagnostic-guided implication operator or explicit branch; not trigger inference.
- card-007: Weak-fairness liveness remains open; separate pointwise precondition, action outcome and post-state preservation proofs.
- card-008: Eventual action is known but post-state existence fails; choose an occurrence and instantiate its state consequence.
- card-009: Raw-state witness exists at a shifted index; bridge it to nested-suffix eventual satisfaction.
- card-010: Empty temporal invariant proof; establish initialization and every transition's preservation through existing induction.
- card-011: Network multiset updates; separate surviving old messages from newly sent messages for invariant preservation.
- card-012: Controller must not send to its external system; analyze reconciler branches and lift request-kind safety.
- card-013: Nonunique enabled-step witness invalidates result equality; reuse universal safety for the supplied host result.
- card-014: Nested always postcondition; unfold suffix satisfaction and reuse an existing forward-shift helper.
- card-015: Mixed proof diagnostics: distinguish method/function-field syntax from missing quantified antecedents before repairing.
- card-016: Message-existential leads-to goal with per-witness lemmas; match predicate templates and existential lifting.
- card-017: Finiteness of a fold-produced set; induct on finite input cardinality and preserve finiteness on insertion.
- card-018: Witness or per-witness assertion reports trigger inference or missing antecedent; diagnose and repair each separately.
- card-019: Fuel reveal rejected for a nonrecursive spec wrapper; consider a recursive proof helper for its underlying fold.
- card-020: Predicate equals its conjunction with an entailed predicate; establish mutual entailment using existing rules.
- card-021: Opaque fixed-width serialization length; require matching open counterpart and connector before transferring length.
- card-022: Generic fold lemmas fail to connect concrete bounds; use specialized recursive element and serialization facts.
- card-023: Quantified bounds unavailable: check binder shadowing and antecedent scope before calling dependent helpers.
- card-024: Verification passes but module-scope proof directive breaks preservation; consider placing it inside proof bodies.
- card-025: Always-lifted action premise must hold on every suffix; invoke the existing unfolding helper.
- card-026: Compound stability includes universal fairness/action obligations; prove instances, lift quantifiers, then combine conjuncts.
- card-027: Specialized fairness action causes binder-type mismatch; quantify only the remaining payload, keeping identifiers fixed.
- card-028: Pointwise record equality encounters function-field syntax or trigger errors; fix projection/application and quantifier triggers.
- card-029: Temporal equality with universal and always operators; existing commutation helpers and reflexive entailment premises.
- card-030: Phase-descent precondition mismatches the base bundle; bridge recursive phase accumulation before descending.
- card-031: Final liveness theorem with existing invariant, stability and phase helpers; assemble their premise-compatible chain.
- card-032: Existential leads-to intermediates with witness-specific helpers; lift witnesses and compose intermediate entailments.
- card-033: Existential temporal equality with available equality/witness rules; prove both entailments and introduce witnesses explicitly.
- card-034: Actual trigger-inference error in assertion or witness choice; annotate a relevant bound-variable term, then recheck.
- card-035: Counting loop lacks termination measure; remaining iterations plus index bounds may discharge termination.
- card-036: Loop-body call loses function-entry assumptions; carry necessary facts and entry-state snapshots as invariants.
- card-037: Whole-sequence property fails at one loop index; instantiate it through an in-bounds element helper.
- card-038: Verus passes but preservation rejects borrow/ghost-return shape; retain original executable call and return structure.
- card-039: Temporal proof at arbitrary natural offset; recursive induction and extensional execution equality bridges.
- card-040: Natural predecessor assignment has integer type; prove positive-index branch and convert the nonnegative predecessor.
- card-041: Packet-prefix loop set invariant fails; track emitted views, inherited facts and index-step set updates.
- card-042: Verified proof fails executable-shape comparison; restore original names, bindings, branches and statement order.
- card-043: Equal views must imply marshalability equality; first try existing view-equality and trait-lemma bridges.
- card-044: Marshalability bridge unavailable or cannot instantiate; constructor cases and per-field view/serialization facts.
- card-045: Always-conjunction stability using explicit rules; pass each inner temporal predicate and match left association.
- card-046: Constructor/deserializer success lacks representation bridge; use an existing round-trip fact before moving its input.
- card-047: Existing stabilization macro expects lifted temporal arguments; preserve lifting, omit extra always and trailing separator.
- card-048: Finite-set fold must equal an image; cardinality induction in a proof helper preserving the original contract.
- card-049: Duplicate-free sequence removal must match set removal; index-shift witnesses and membership extensionality.
- card-050: Verified set equality fails preservation due imports/macros; qualified proof references or direct extensional reasoning.
- card-051: Leads-to transitivity with existing temporal helpers; combine eventual witnesses and align summed execution suffixes.
- card-052: Proof already verifies: optional automatic-trigger or implication-warning cleanup, not failed-proof construction.
- card-053: Length-prefixed injectivity; establish fixed-width header contract before pointwise header and sequence equality.
- card-054: Ghost aggregate must contain empty sequences/set; replace an unconstrained witness with a concrete ghost aggregate.
- card-055: Missing proof helper/macro and import-preservation risk; confirm a qualified path before editing.
- card-056: Empty temporal entailment proof; establish pointwise/suffix implication, then lift and instantiate supplied premises.
- card-057: Quantified state/suffix assertion has trigger or antecedent diagnostic; target later predicate instantiation without conflating repairs.
- card-058: Entailment/validity premise remains uninstantiated; assert its full implication at the concrete execution first.
- card-059: Ghost unwrap of uninterpreted conversion fails recommendations; reason through surrounding specs without extracting its value.
- card-060: Function field mistaken for method, followed possibly by trigger failure; project before applying, then diagnose triggers.
- card-061: Existential temporal reachability needs a time witness; use supported choice with a valid trigger term.
- card-062: Empty always-conjunction stability proof; inspect local rule/macro contracts before selecting the existing route.
- card-063: Fold over sequence concatenation: induct on the second sequence and use concatenation associativity.
- card-064: Alternative concatenated-fold route: existing split lemma plus a helper for a nonempty initial accumulator.
- card-065: Out-of-scope proof macro with unsafe top-level import; qualified invocation, then diagnose empty-sequence type inference.
- card-066: Generic sequence type mismatch; annotate empty element type or convert length to the expected index type.
- card-067: Sequence equality with a common appended suffix; prove lengths and indexed elements in both directions.
- card-068: Sequence-equality closure helper out of scope; qualified reference after its length and element premises hold.
- card-069: Missing antecedent inside quantified proof; explicit disjunction/branch route or diagnostic-supported implication operator.
- card-070: Single-versus-nested temporal operator equality; mutual entailment and pointwise suffix-index identities.
- card-071: Always-conjunction stability chain; preserve state lifting and combine the intended temporal conjuncts.
- card-072: Conjunction stability fails after an extra always wrapper; remove that wrapper, retaining state-to-temporal lifting.
- card-073: Initializer's abstract history must be empty but ghost source is arbitrary; choose a concrete empty history.
- card-074: Helper precondition fails under quantified implication; explicit antecedent branch before the dependent call.
- card-075: Public spec-function field used as a method; correct projection/application consistently across occurrences.
- card-076: Recursive helper loses quantified suffix-stability facts; expand aliases and instantiate its precise hypotheses.
- card-077: Universal equivalence has different bodies; establish pointwise equivalence, then triggers or directional lemmas.
- card-078: Library operation facts inactive in pointwise proof; inspect allowed definitions and existing broadcast groups.
