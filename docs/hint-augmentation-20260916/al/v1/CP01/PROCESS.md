# CP1 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 32

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -8,6 +8,15 @@
 pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
     ensures s1 == s2 <==> s1 + suffix == s2 + suffix
 {
+    if s1 == s2 {
+        assert(s1 + suffix == s2 + suffix);
+    } else {
+        assert(s1 + suffix == s2 + suffix) by {
+            // Backward direction is not yet established; keep this branch explicit
+            // so the verifier reports the remaining subgoal.
+        }
+        assert(s1 == s2);
+    }
 }
 
 }

```

## Source change event 40

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -10,11 +10,19 @@
 {
     if s1 == s2 {
         assert(s1 + suffix == s2 + suffix);
-    } else {
-        assert(s1 + suffix == s2 + suffix) by {
-            // Backward direction is not yet established; keep this branch explicit
-            // so the verifier reports the remaining subgoal.
-        }
+    }
+    if s1 + suffix == s2 + suffix {
+        assert((s1 + suffix).len() == (s2 + suffix).len());
+        assert((s1 + suffix).len() == s1.len() + suffix.len());
+        assert((s2 + suffix).len() == s2.len() + suffix.len());
+        assert(s1.len() == s2.len());
+
+        assert(forall|i: int| 0 <= i < s1.len() ==> (s1 + suffix)[i] == (s2 + suffix)[i]);
+        assert(forall|i: int| 0 <= i < s1.len() ==> (s1 + suffix)[i] == s1[i]);
+        assert(forall|i: int| 0 <= i < s1.len() ==> (s2 + suffix)[i] == s2[i]);
+        assert(forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i]);
+
+        assert(s1.ext_equal(s2));
         assert(s1 == s2);
     }
 }

```

## Source change event 48

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -22,7 +22,6 @@
         assert(forall|i: int| 0 <= i < s1.len() ==> (s2 + suffix)[i] == s2[i]);
         assert(forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i]);
 
-        assert(s1.ext_equal(s2));
         assert(s1 == s2);
     }
 }

```

## Recorded checks

### Event 23 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: postcondition not satisfied
8 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ---------------------------------------------------------------------------------- at the end of the function body
9 |     ensures s1 == s2 <==> s1 + suffix == s2 + suffix
  |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ failed this postcondition
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 34 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
8 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: assertion failed
14 |         assert(s1 + suffix == s2 + suffix) by {
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
18 |         assert(s1 == s2);
   |                ^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 2 previous errors
```

### Event 42 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error[E0599]: no method named `ext_equal` found for struct `vstd::seq::Seq` in the current scope
25 |         assert(s1.ext_equal(s2));
   |                   ^^^^^^^^^ method not found in `Seq<A>`
error: aborting due to 1 previous error
```

### Event 50 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
21 |         assert(forall|i: int| 0 <= i < s1.len() ==> (s1 + suffix)[i] == s1[i]);
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |         assert(forall|i: int| 0 <= i < s1.len() ==> (s1 + suffix)[i] == s1[i]);
   |                                                                         ^^^^^
22 |         assert(forall|i: int| 0 <= i < s1.len() ==> (s2 + suffix)[i] == s2[i]);
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
22 |         assert(forall|i: int| 0 <= i < s1.len() ==> (s2 + suffix)[i] == s2[i]);
   |                                                                         ^^^^^
22 |         assert(forall|i: int| 0 <= i < s1.len() ==> (s2 + suffix)[i] == s2[i]);
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
verification results:: 1 verified, 0 errors
```

### Event 55 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
