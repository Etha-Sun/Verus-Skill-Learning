# CP2 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 32

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -12,7 +12,18 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
-        assert(s1 == s2);
+        let a = s1 + suffix;
+        let b = s2 + suffix;
+        assert(a.len() == b.len());
+        assert(a.len() == s1.len() + suffix.len());
+        assert(b.len() == s2.len() + suffix.len());
+        assert(s1.len() == s2.len());
+        assert forall |i| 0 <= i < s1.len() implies #[trigger] s1[i] == s2[i] by {
+            assert(s1[i] == a[i]);
+            assert(s2[i] == b[i]);
+            assert(a[i] == b[i]);
+        }
+        assert(s1 =~= s2);
     }
 }
 

```

## Recorded checks

### Event 26 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
error: assertion failed
15 |         assert(s1 == s2);
   |                ^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 34 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 39 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
