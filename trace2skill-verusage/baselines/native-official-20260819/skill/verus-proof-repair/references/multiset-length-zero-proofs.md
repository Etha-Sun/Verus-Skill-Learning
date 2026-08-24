# Multiset Length-Zero Proofs

## When to read

Use when a Verus obligation is `filtered.len() == 0` or requires showing
that a filtered multiset is empty iff no value satisfies the filter.

## Pattern

1. Search local vstd for an axiom or lemma that relates multiset length zero
   to per-element counts, such as `len_is_zero_means_count_for_each_value_is_zero`.
2. Use it to replace the length-zero condition with a count-for-every-value
   condition.
3. Prove each direction:
   - `filtered.len() == 0` gives zero counts for every value, so no value
     satisfies the filter.
   - No value satisfying the filter gives zero counts for every value, so
     `filtered.len() == 0`.
4. Validate the annotated proof in a separate `*_verified.rs` file and run
   Verus on that file.

## Do not

- Do not assert the equivalence without connecting counts.
- Do not use `assume`, `admit`, or any verification bypass for this connection.
