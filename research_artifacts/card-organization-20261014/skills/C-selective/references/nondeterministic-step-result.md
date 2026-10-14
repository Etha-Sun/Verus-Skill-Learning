# Nondeterministic transition result without a chosen witness

## Scope

- Consult when: Helper asserts computed machine result equals transition of one manually chosen enabling step
- Consult when: Several steps share the same precondition and choice is not unique
- Not for: Step is unique
- Not for: Universal per-step safety fact or host-result equality premise is missing

## Rules

- [Nondeterministic transition result without a chosen witness](#rule-card-013-verbatim)

<a id="rule-card-013-verbatim"></a>
## Nondeterministic transition result without a chosen witness

Source cards: card-013

**Trigger:** A helper that reasons about a nondeterministic state-machine result fails on an assertion equating the computed result with the transition of one manually chosen enabling step, especially when several steps share the same precondition and the choice is not unique.

**Action:** Do not reconstruct the machine result through that chosen witness. Keep the universal fact already proved for every enabled step that its transition output is safe, and use the premises that the machine result equals the supplied enabled host result. Assert the desired safety property directly on the host result, allowing the verifier to instantiate the universal fact with the internal witness.

**Why:** If multiple steps are simultaneously enabled, a chosen step is not a uniquely determined witness, so two syntactically separate choices are not provably equal. Direct assertion avoids relying on that equality and still uses the universal transition property plus the host-result relationship.

**Validate:** Rerun the Verus checker and verify the helper with zero errors; run the proof-safety comparison tool and require exit zero.

**Avoid when:** The universal per-step property has not been established, the desired conclusion requires comparing two different result computations, or the verifier still cannot trigger the universal fact and a proof of step uniqueness is available instead.

- Distinguish from [transition-system-step-safety](transition-system-step-safety.md): Transition-step safety proves per-step or preservation facts; this route avoids using a nonunique chosen step as an equality witness.

- Related [transition-system-step-safety](transition-system-step-safety.md): Transition-step safety proves per-step or preservation facts; this route avoids using a nonunique chosen step as an equality witness and instead reuses an already-proved universal per-step safety fact together with host-result equality.

- Related [universal-instantiation-concrete](universal-instantiation-concrete.md): Universal-instantiation route explicitly instantiates an available universal fact at a concrete term; this route avoids reconstructing a result through a chosen step witness and lets the verifier instantiate the universal per-step fact through the supplied host-result premises.
