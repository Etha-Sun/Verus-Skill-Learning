# CP5 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 21

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -9,28 +9,33 @@
 {
     assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
         assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
-            let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
-            assert((s1 + s2).contains(a) && f(a) == x);
-            assert(s1.contains(a) || s2.contains(a));
-            if s1.contains(a) {
-                assert(s1.map(f).contains(x));
-            } else {
-                assert(s2.contains(a));
-                assert(s2.map(f).contains(x));
+            if ((s1 + s2).map(f)).contains(x) {
+                let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
+                assert((s1 + s2).contains(a) && f(a) == x);
+                assert(s1.contains(a) || s2.contains(a));
+                if s1.contains(a) {
+                    assert(s1.map(f).contains(x));
+                } else {
+                    assert(s2.contains(a));
+                    assert(s2.map(f).contains(x));
+                }
+                assert(s1.map(f).contains(x) || s2.map(f).contains(x));
             }
-            assert(s1.map(f).contains(x) || s2.map(f).contains(x));
         };
         assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
-            if s1.map(f).contains(x) {
-                let a = choose |a: A| (s1.contains(a) && f(a) == x);
-                assert(s1.contains(a) && f(a) == x);
-                assert((s1 + s2).contains(a));
-                assert(((s1 + s2).map(f)).contains(x));
-            } else {
-                let a = choose |a: A| (s2.contains(a) && f(a) == x);
-                assert(s2.contains(a) && f(a) == x);
-                assert((s1 + s2).contains(a));
-                assert(((s1 + s2).map(f)).contains(x));
+            if (s1.map(f) + s2.map(f)).contains(x) {
+                if s1.map(f).contains(x) {
+                    let a = choose |a: A| (s1.contains(a) && f(a) == x);
+                    assert(s1.contains(a) && f(a) == x);
+                    assert((s1 + s2).contains(a));
+                    assert(((s1 + s2).map(f)).contains(x));
+                } else {
+                    assert(s2.map(f).contains(x));
+                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
+                    assert(s2.contains(a) && f(a) == x);
+                    assert((s1 + s2).contains(a));
+                    assert(((s1 + s2).map(f)).contains(x));
+                }
             }
         };
     });

```

## Source change event 38

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::assert_sets_equal;
 fn main() {}
 verus! {
 
@@ -7,7 +6,7 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
-    assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
+    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
         assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
             if ((s1 + s2).map(f)).contains(x) {
                 let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);

```

## Recorded checks

### Event 15 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
6 | pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
12 |             let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
   |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: assertion failed
13 |             assert((s1 + s2).contains(a) && f(a) == x);
   |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
30 |                 let a = choose |a: A| (s2.contains(a) && f(a) == x);
   |                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: assertion failed
31 |                 assert(s2.contains(a) && f(a) == x);
   |                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 2 previous errors
```

### Event 23 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 28 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 40 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 45 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
