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
        assert(s1 == s2);
    }
}

}
