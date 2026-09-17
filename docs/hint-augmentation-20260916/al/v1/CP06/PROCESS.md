# CP6 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 55

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -16,7 +16,13 @@
         assert((s1 + suffix).len() == (s2 + suffix).len());
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
-        assert_seqs_equal!(s1, s2);
+        assert_seqs_equal!(s1, s2, i => {
+            broadcast use group_seq_axioms;
+            assert((s1 + suffix)[i] == (s2 + suffix)[i]);
+            assert((s1 + suffix)[i] == s1[i]);
+            assert((s2 + suffix)[i] == s2[i]);
+            assert(s1[i] == s2[i]);
+        });
     }
 }
 

```

## Source change event 63

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -17,7 +17,7 @@
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
         assert_seqs_equal!(s1, s2, i => {
-            broadcast use group_seq_axioms;
+            broadcast use vstd::seq::group_seq_axioms;
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);
             assert((s1 + suffix)[i] == s1[i]);
             assert((s2 + suffix)[i] == s2[i]);

```

## Source change event 76

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 
@@ -16,7 +15,7 @@
         assert((s1 + suffix).len() == (s2 + suffix).len());
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
-        assert_seqs_equal!(s1, s2, i => {
+        vstd::seq_lib::assert_seqs_equal!(s1, s2, i => {
             broadcast use vstd::seq::group_seq_axioms;
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);
             assert((s1 + suffix)[i] == s1[i]);

```

## Recorded checks

### Event 25 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: assertion failed
19 |         assert_seqs_equal!(s1, s2);
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 57 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error[E0425]: cannot find value `group_seq_axioms` in this scope
20 |             broadcast use group_seq_axioms;
   |                           ^^^^^^^^^^^^^^^^ not found in this scope
error: aborting due to 1 previous error
```

### Event 65 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 70 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 78 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 82 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
