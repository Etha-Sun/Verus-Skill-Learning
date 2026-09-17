# CP4 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 69

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -13,8 +13,20 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
+        let left = s1 + suffix;
+        let right = s2 + suffix;
+        assert(left.len() == right.len());
+        assert(left.len() == s1.len() + suffix.len());
+        assert(right.len() == s2.len() + suffix.len());
+        assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
-        assert_seqs_equal!(s1, s2);
+        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
+            assert(left[i] == right[i]);
+            assert(left[i] == s1[i]);
+            assert(right[i] == s2[i]);
+        };
+        assert(s1 =~= s2);
+        assert(s1 == s2);
     }
 }
 

```

## Source change event 77

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -20,7 +20,7 @@
         assert(right.len() == s2.len() + suffix.len());
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
-        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
+        assert forall|i: int| 0 <= i < s1.len() implies s1[i] == s2[i] by {
             assert(left[i] == right[i]);
             assert(left[i] == s1[i]);
             assert(right[i] == s2[i]);

```

## Source change event 90

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 

```

## Recorded checks

### Event 23 (exit 1)

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

### Event 71 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
23 |         assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
   |         ^^^^^^
9 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 |             assert(left[i] == right[i]);
   |                    ^^^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
24 |             assert(left[i] == right[i]);
   |                               ^^^^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
error: assertion failed
25 |             assert(left[i] == s1[i]);
   |                    ^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
26 |             assert(right[i] == s2[i]);
   |                    ^^^^^^^^^^^^^^
```

### Event 79 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 84 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 92 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 96 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
