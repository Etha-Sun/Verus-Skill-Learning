# State-machine invariant and step-safety lemmas

## Scope

- Consult when: Goal is an invariant, preservation, or safety property over a finite state-machine transition relation
- Consult when: Step cases can be pattern-matched or decomposed into finite local analyses
- Not for: Transition relation is uninterpreted or unbounded
- Not for: Preservation is genuinely false without an additional missing invariant

## Rules

Routing cues only; read the selected full rule before acting.

**Relationship:** 010 covers the outer all-future invariant; 011 a network-multiset update preservation subgoal; 012 the controller's no-external-request subcase. These are proof levels that can be needed together, not rival answers to one identical local obligation.

<a id="card-010-verbatim"></a>
- [card-010-verbatim](transition-system-step-safety--card-010-verbatim.md): Temporal invariant with finite transition cases.
  - When: An empty proof must show that a specification entails a state predicate at every future point.
  - Avoid: No induction rule, no finite step match, or a transition needs a missing invariant.

<a id="card-011-verbatim"></a>
- [card-011-verbatim](transition-system-step-safety--card-011-verbatim.md): Network multiset message invariant.
  - When: Transitions remove at most one received message and add a multiset of sent messages.
  - Avoid: Unconstrained message sources or arbitrary external messages without finite case analysis.

<a id="card-012-verbatim"></a>
- [card-012-verbatim](transition-system-step-safety--card-012-verbatim.md): Controller cannot send its own external request.
  - When: The controller preservation case must exclude a request to its own external system.
  - Avoid: Uninterpreted or request-producing reconciler, or uncovered external-system models.

Read: `python3 reference_read.py transition-system-step-safety --rules ID [ID ...]`

Whole reference: `python3 reference_read.py transition-system-step-safety --full` or [transition-system-step-safety--full.md](transition-system-step-safety--full.md).
