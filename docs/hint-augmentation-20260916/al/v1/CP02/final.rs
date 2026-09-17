use vstd::prelude::*;

fn main() {}

verus!{


pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
    ensures s1 == s2 <==> s1 + suffix == s2 + suffix
{
    if s1 == s2 {
        assert(s1 + suffix == s2 + suffix);
    }
    if s1 + suffix == s2 + suffix {
        broadcast use vstd::seq::group_seq_axioms;

        let a = s1 + suffix;
        let b = s2 + suffix;
        assert(a.len() == b.len());
        assert(a.len() == s1.len() + suffix.len());
        assert(b.len() == s2.len() + suffix.len());
        assert(s1.len() == s2.len());

        assert forall|i: int| 0 <= i < s1.len() implies s1[i] == s2[i] by {
            assert(a[i] == b[i]);
            assert(a[i] == s1[i]);
            assert(b[i] == s2[i]);
        };

        assert(s1 =~= s2);
        assert(s1 == s2);
    }
}

}
