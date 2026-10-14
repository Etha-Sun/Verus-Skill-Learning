# State-machine invariant and step-safety lemmas

## Scope

- Consult when: Goal is an invariant, preservation, or safety property over a finite state-machine transition relation
- Consult when: Step cases can be pattern-matched or decomposed into finite local analyses
- Not for: Transition relation is uninterpreted or unbounded
- Not for: Preservation is genuinely false without an additional missing invariant

<a id="card-011-verbatim"></a>
## card-011

Source cards: card-011

**Trigger:** The invariant is about messages in a network multiset, and transition cases update the network by removing at most one received message and adding a multiset of newly sent messages.

**Action:** Introduce a multiset-level safety predicate. Prove a lemma that if the updated multiset is produced by removing one received message and adding a send multiset, then any message in the updated multiset was either already present before the update or belongs to the send multiset. Apply this lemma after showing the send multiset itself is safe for the specified controller and external destination.

**Why:** This isolates the general multiset update reasoning from the differing behavior of each host state machine. It reduces preservation of the network invariant to a per-send safety obligation that can be discharged by small finite case analyses.

**Validate:** Run the Verus checker and require the new lemmas and invariant proof to verify with zero errors; run the proof-safety comparison tool and require exit zero.

**Avoid when:** The system can add messages through a source that is not constrained by a send multiset, or a host transition chooses an arbitrary external message with no finite case analysis available.

- Distinguish from [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.

- Related [nondeterministic-step-result](nondeterministic-step-result.md): Nondeterministic-step route is about not reconstructing a result through one nonunique witness, rather than proving preservation lemmas.
