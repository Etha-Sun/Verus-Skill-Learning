# CP4 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 46

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -13,8 +13,19 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
+        broadcast use group_seq_axioms;
+
+        assert((s1 + suffix).len() == s1.len() + suffix.len());
+        assert((s2 + suffix).len() == s2.len() + suffix.len());
+        assert((s1 + suffix).len() == (s2 + suffix).len());
         assert(s1.len() == s2.len());
-        assert_seqs_equal!(s1, s2);
+
+        assert_seqs_equal!(s1, s2, i => {
+            assert((s1 + suffix)[i] == s1[i]);
+            assert((s2 + suffix)[i] == s2[i]);
+            assert((s1 + suffix)[i] == (s2 + suffix)[i]);
+            assert(s1[i] == s2[i]);
+        });
     }
 }
 

```

## Source change event 54

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,6 @@
 use vstd::prelude::*;
 use vstd::seq_lib::*;
+use vstd::seq::group_seq_axioms;
 
 fn main() {}
 

```

## Source change event 76

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,6 +1,5 @@
 use vstd::prelude::*;
 use vstd::seq_lib::*;
-use vstd::seq::group_seq_axioms;
 
 fn main() {}
 
@@ -14,7 +13,7 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
-        broadcast use group_seq_axioms;
+        broadcast use vstd::seq::group_seq_axioms;
 
         assert((s1 + suffix).len() == s1.len() + suffix.len());
         assert((s2 + suffix).len() == s2.len() + suffix.len());

```

## Source change event 107

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 
@@ -20,12 +19,14 @@
         assert((s1 + suffix).len() == (s2 + suffix).len());
         assert(s1.len() == s2.len());
 
-        assert_seqs_equal!(s1, s2, i => {
+        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
             assert((s1 + suffix)[i] == s1[i]);
             assert((s2 + suffix)[i] == s2[i]);
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);
             assert(s1[i] == s2[i]);
-        });
+        };
+        assert(s1 =~= s2);
+        assert(s1 == s2);
     }
 }
 

```

## Source change event 115

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -19,7 +19,7 @@
         assert((s1 + suffix).len() == (s2 + suffix).len());
         assert(s1.len() == s2.len());
 
-        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
+        assert forall|i: int| 0 <= i < s1.len() implies s1[i] == s2[i] by {
             assert((s1 + suffix)[i] == s1[i]);
             assert((s2 + suffix)[i] == s2[i]);
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);

```

## Recorded checks

### Event 12 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
9 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: assertion failed
16 |         assert(s1.len() == s2.len());
   |                ^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
17 |         assert_seqs_equal!(s1, s2);
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 2 previous errors
```

### Event 48 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error[E0425]: cannot find value `group_seq_axioms` in this scope
16 |         broadcast use group_seq_axioms;
   |                       ^^^^^^^^^^^^^^^^ not found in this scope
error: aborting due to 1 previous error
```

### Event 56 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 61 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 78 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 82 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 109 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
22 |         assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
   |         ^^^^^^
8 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |             assert((s1 + suffix)[i] == s1[i]);
   |                    ^^^^^^^^^^^^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
error: assertion failed
23 |             assert((s1 + suffix)[i] == s1[i]);
   |                    ^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
23 |             assert((s1 + suffix)[i] == s1[i]);
   |                                        ^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
error: assertion failed
24 |             assert((s2 + suffix)
```

### Event 117 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 121 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
