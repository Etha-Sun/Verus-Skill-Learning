# Serialization Proof Patterns

Use this reference when the current obligation matches one of these triggers:

- a proof needs the fixed length of a primitive serialization;
- an injectivity proof involves a length-prefixed serialization `len_bytes + data`;
- a trait lemma call fails because its `is_marshalable` preconditions are not yet explicit.

## Fixed length of primitive serializations

- Prefer an existing vstd lemma over manual unfolding or new axioms.
- For `spec_u64_to_le_bytes(...)`, call `vstd::bytes::lemma_auto_spec_u64_to_from_le_bytes()`.
- Then assert the resulting concrete length, e.g. `n == 8` and `m == 8`, instead of proving it by hand.

## Length-prefixed injectivity

1. Expand `Vec<u8>::ghost_serialize()` into `spec_u64_to_le_bytes(len as u64) + seq`.
2. Compare the fixed-length prefix bytewise first.
3. Apply an injectivity lemma to the length encoding and derive equal lengths.
4. Use the now-equal lengths to compare the data suffix bytewise.

## Discharging trait lemma preconditions

- Before calling a trait lemma such as `lemma_serialize_injective`, explicitly assert each required `is_marshalable()` precondition.
- Prove numeric cast bounds first, e.g. `x as int <= u64::MAX`, so the precondition assertion is accepted.

For example:

```rust
assert(self_len_usize.is_marshalable());
assert(other_len_usize.is_marshalable());
self_len_usize.lemma_serialize_injective(&other_len_usize);
```
