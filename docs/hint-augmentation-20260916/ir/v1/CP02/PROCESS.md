# CP2 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 27

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -6,7 +6,7 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
-    assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
+    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
         assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
     });
 }

```

## Source change event 53

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -6,9 +6,7 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
-    vstd::assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
-        assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
-    });
+    s1.lemma_map_union_commute(s2, f);
 }
 
 } // verus!

```

## Recorded checks

### Event 20 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: cannot find macro `assert_sets_equal` in this scope
9 |     assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
  |     ^^^^^^^^^^^^^^^^^
error: aborting due to 1 previous error
```

### Event 29 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: assertion failed
10 |         assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 55 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 60 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
