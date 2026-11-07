## Post-verification cost procedure

Once the file verifies, you will be shown the exact solver cost (Z3 rlimit and
quantifier instantiations) of each function. Use it to make the proof cheaper:
1. Look first at the most expensive function you wrote or changed.
2. In it, find asserts whose statement is a large predicate (a wf/invariant
   predicate, a step/refinement relation, an equality of whole structs,
   sequences or maps, or a quantified `forall`/`exists`) that is not used as a
   stepping stone by the next proof step. Each such assert is a separate proof
   obligation; proving it forces the solver to unfold definitions.
3. Delete or simplify one or two such statements per round, or replace
   pointwise/extensional reasoning with a single call to an existing lemma.
4. Keep any statement that establishes a precondition of a lemma call, a loop
   invariant, or a trigger for a quantified fact. If a deletion breaks the
   proof, restore it and try another.
Stop (reply done) when no candidate remains.
