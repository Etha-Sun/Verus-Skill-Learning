# CP1 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 59

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -8,6 +8,27 @@
 pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
     ensures s1 == s2 <==> s1 + suffix == s2 + suffix
 {
+    if s1 == s2 {
+        assert(s1 + suffix == s2 + suffix);
+    }
+    if s1 + suffix == s2 + suffix {
+        broadcast use group_seq_axioms;
+
+        let left = s1 + suffix;
+        let right = s2 + suffix;
+
+        assert(left.len() == right.len());
+        assert(s1.len() + suffix.len() == s2.len() + suffix.len());
+        assert(s1.len() == s2.len());
+
+        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
+            assert(left[i] == right[i]);
+            assert(left[i] == s1[i]);
+            assert(right[i] == s2[i]);
+        }
+
+        assert(s1 == s2);
+    }
 }
 
 }

```

## Source change event 67

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -12,7 +12,7 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
-        broadcast use group_seq_axioms;
+        broadcast use vstd::seq::group_seq_axioms;
 
         let left = s1 + suffix;
         let right = s2 + suffix;

```

## Source change event 75

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -21,7 +21,7 @@
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
 
-        assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
+        assert forall|i: int| 0 <= i < s1.len() implies s1[i] == s2[i] by {
             assert(left[i] == right[i]);
             assert(left[i] == s1[i]);
             assert(right[i] == s2[i]);

```

## Recorded checks

### Event 17 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
error: postcondition not satisfied
8 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ---------------------------------------------------------------------------------- at the end of the function body
9 |     ensures s1 == s2 <==> s1 + suffix == s2 + suffix
  |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ failed this postcondition
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 61 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
error[E0425]: cannot find value `group_seq_axioms` in this scope
15 |         broadcast use group_seq_axioms;
   |                       ^^^^^^^^^^^^^^^^ not found in this scope
error: aborting due to 1 previous error
```

### Event 69 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
24 |         assert forall|i: int| 0 <= i < s1.len() ==> s1[i] == s2[i] by {
   |         ^^^^^^
8 | pub proof fn seq_equal_preserved_by_add<A>(s1: Seq<A>, s2: Seq<A>, suffix: Seq<A>)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
25 |             assert(left[i] == right[i]);
   |                    ^^^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
25 |             assert(left[i] == right[i]);
   |                               ^^^^^^^^
62 |             0 <= i < self.len(),
   |             ------------------- recommendation not met
error: assertion failed
26 |             assert(left[i] == s1[i]);
   |                    ^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
27 |             assert(right[i] == s2[i]);
   |                    ^^^^^^^^^^^^^^
```

### Event 77 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 82 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
