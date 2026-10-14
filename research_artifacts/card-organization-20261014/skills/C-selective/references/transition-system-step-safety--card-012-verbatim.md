# State-machine invariant and step-safety lemmas

## Scope

- Consult when: Goal is an invariant, preservation, or safety property over a finite state-machine transition relation
- Consult when: Step cases can be pattern-matched or decomposed into finite local analyses
- Not for: Transition relation is uninterpreted or unbounded
- Not for: Preservation is genuinely false without an additional missing invariant

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
