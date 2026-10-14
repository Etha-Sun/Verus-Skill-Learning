# State-machine invariant and step-safety lemmas

## Scope

- Consult when: Goal is an invariant, preservation, or safety property over a finite state-machine transition relation
- Consult when: Step cases can be pattern-matched or decomposed into finite local analyses
- Not for: Transition relation is uninterpreted or unbounded
- Not for: Preservation is genuinely false without an additional missing invariant

## Rules

- [card-010](#card-010-verbatim)
- [card-011](#card-011-verbatim)
- [card-012](#card-012-verbatim)

<a id="card-010-verbatim"></a>
## card-010

Source cards: card-010

**Trigger:** Verus reports an unsatisfied temporal postcondition requiring a specification to entail that a state predicate holds at every point in the future, while the relevant proof function body is empty.

**Action:** Use the supplied temporal induction rule for state invariants. Establish both premises: every initial state satisfying the system initialization also satisfies the state predicate, and whenever a state satisfying the predicate takes a next transition, the successor state also satisfies it. Prove the preservation premise by matching on every top-level step variant and reusing the corresponding transition identities.

**Why:** The state-invariant induction rule's conclusion exactly matches the temporal target. Because the system specification includes initial-state and next-transition entailments, discharging those two premises closes the goal without manually reasoning about arbitrary execution indices.

**Validate:** Run the Verus checker and expect zero errors with all proof functions verified, then run the proof-safety comparison tool and require exit zero.

**Avoid when:** The environment does not provide such an induction rule, the transition relation is not defined as a finite step match, or preservation is genuinely false because some step can introduce a bad state without an additional missing invariant.

<a id="card-011-verbatim"></a>
## card-011

Source cards: card-011

**Trigger:** The invariant is about messages in a network multiset, and transition cases update the network by removing at most one received message and adding a multiset of newly sent messages.

**Action:** Introduce a multiset-level safety predicate. Prove a lemma that if the updated multiset is produced by removing one received message and adding a send multiset, then any message in the updated multiset was either already present before the update or belongs to the send multiset. Apply this lemma after showing the send multiset itself is safe for the specified controller and external destination.

**Why:** This isolates the general multiset update reasoning from the differing behavior of each host state machine. It reduces preservation of the network invariant to a per-send safety obligation that can be discharged by small finite case analyses.

**Validate:** Run the Verus checker and require the new lemmas and invariant proof to verify with zero errors; run the proof-safety comparison tool and require exit zero.

**Avoid when:** The system can add messages through a source that is not constrained by a send multiset, or a host transition chooses an arbitrary external message with no finite case analysis available.

<a id="card-012-verbatim"></a>
## card-012

Source cards: card-012

**Trigger:** The controller-step preservation case needs to rule out the possibility that the target controller sends a request to its own external system.

**Action:** Write a helper lemma about the controller's reconciler core by pattern-matching all local step states and verifying that every emitted request is an ordinary Kubernetes request rather than an external request. Lift this to the installed reconcile-model transition by reconstructing the marshal and response views as needed.

**Why:** In this model the reconciler core is an open function defined by a finite match on its local step; exhaustive branch reasoning therefore proves the absence of external requests for all possible states. Once lifted, the controller state machine cannot construct the forbidden outgoing message because it only emits messages from the reconciler's requested content.

**Validate:** Run the Verus checker after adding the helper and the controller helper that invokes it; both should verify with zero errors. Then run the proof-safety comparison tool and require exit zero.

**Avoid when:** The reconciler transition is uninterpreted or can return external requests, or multiple controller models are equipped with external systems whose transitions are not covered by the helper.

- Distinguish from [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.

- Related [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.
