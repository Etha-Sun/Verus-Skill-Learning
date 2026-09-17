use vstd::prelude::*;
use vstd::assert_sets_equal;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
    });
}

} // verus!
