# CP6 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 29

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

### Event 19 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 23 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 32 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 37 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
