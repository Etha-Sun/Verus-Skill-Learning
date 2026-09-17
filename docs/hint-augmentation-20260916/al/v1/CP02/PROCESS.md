# CP2 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 66

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -12,6 +12,22 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
+        broadcast use vstd::seq::group_seq_axioms;
+
+        let a = s1 + suffix;
+        let b = s2 + suffix;
+        assert(a.len() == b.len());
+        assert(a.len() == s1.len() + suffix.len());
+        assert(b.len() == s2.len() + suffix.len());
+        assert(s1.len() == s2.len());
+
+        assert forall|i: int| 0 <= i < s1.len() implies s1[i] == s2[i] by {
+            assert(a[i] == b[i]);
+            assert(a[i] == s1[i]);
+            assert(b[i] == s2[i]);
+        };
+
+        assert(s1 =~= s2);
         assert(s1 == s2);
     }
 }

```

## Recorded checks

### Event 23 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: assertion failed
15 |         assert(s1 == s2);
   |                ^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 68 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 73 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
