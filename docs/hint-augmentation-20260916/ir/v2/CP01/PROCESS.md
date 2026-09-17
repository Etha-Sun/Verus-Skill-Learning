# CP1 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 63

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -6,6 +6,7 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
+    vstd::set_lib::lemma_map_union_commute(s1, s2, f);
 }
 
 } // verus!

```

## Source change event 71

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -6,7 +6,7 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
-    vstd::set_lib::lemma_map_union_commute(s1, s2, f);
+    s1.lemma_map_union_commute(s2, f);
 }
 
 } // verus!

```

## Recorded checks

### Event 23 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
error: postcondition not satisfied
5 | pub proof fn set_map_union<A, B>(s1: Set<A>, s2: Set<A>, f: spec_fn(A) -> B)
  | ---------------------------------------------------------------------------- at the end of the function body
6 |     ensures
7 |         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ failed this postcondition
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 65 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
error[E0425]: cannot find function `lemma_map_union_commute` in module `vstd::set_lib`
9 |     vstd::set_lib::lemma_map_union_commute(s1, s2, f);
  |                    ^^^^^^^^^^^^^^^^^^^^^^^ not found in `vstd::set_lib`
error: aborting due to 1 previous error
```

### Event 73 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 78 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
