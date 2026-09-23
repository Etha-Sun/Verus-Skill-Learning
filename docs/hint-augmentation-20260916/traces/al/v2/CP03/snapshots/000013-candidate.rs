use vstd::prelude::*;
use vstd::seq_lib::*;

fn main() {}

verus!{


pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
    ensures s1 == s2 <==> s1 + suffix == s2 + suffix
{
    if s1 == s2 {
        assert(s1 + suffix == s2 + suffix);
    }
    if s1 + suffix == s2 + suffix {
        lemma_seq_add_len(s1, suffix);
        lemma_seq_add_len(s2, suffix);
        assert(s1.len() + suffix.len() == s2.len() + suffix.len());
        assert(s1.len() == s2.len());
        assert forall |i: int| 0 <= i < s1.len() implies #[trigger] s1[i] == s2[i] by {
            assert((s1 + suffix)[i] == (s2 + suffix)[i]);
            lemma_seq_add_index(s1, suffix, i);
            lemma_seq_add_index(s2, suffix, i);
        };
        assert(s1 =~= s2);
    }
}

}
