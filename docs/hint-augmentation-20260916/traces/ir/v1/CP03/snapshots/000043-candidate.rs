use vstd::prelude::*;
fn main() {}
verus! {

pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
    ensures
        (s1 + s2).map(f) == s1.map(f) + s2.map(f),
{
    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
        assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
            if ((s1 + s2).map(f)).contains(x) {
                let a = choose|a: A| (s1 + s2).contains(a) && f(a) == x;
                assert((s1 + s2).contains(a));
                assert(s1.contains(a) || s2.contains(a));
                if s1.contains(a) {
                    assert(s1.map(f).contains(x));
                } else {
                    assert(s2.map(f).contains(x));
                }
                assert((s1.map(f) + s2.map(f)).contains(x));
            }
        };
        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
            if (s1.map(f) + s2.map(f)).contains(x) {
                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
                if s1.map(f).contains(x) {
                    let a = choose|a: A| s1.contains(a) && f(a) == x;
                    assert(s1.contains(a));
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                } else {
                    let a = choose|a: A| s2.contains(a) && f(a) == x;
                    assert(s2.contains(a));
                    assert((s1 + s2).contains(a));
                    assert(((s1 + s2).map(f)).contains(x));
                }
            }
        };
    });
}

} // verus!
