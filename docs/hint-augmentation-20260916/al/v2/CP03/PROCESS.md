# CP3 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 35

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 
@@ -13,14 +12,15 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
-        lemma_seq_add_len(s1, suffix);
-        lemma_seq_add_len(s2, suffix);
+        assert((s1 + suffix).len() == (s2 + suffix).len());
+        assert((s1 + suffix).len() == s1.len() + suffix.len());
+        assert((s2 + suffix).len() == s2.len() + suffix.len());
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
         assert forall |i: int| 0 <= i < s1.len() implies #[trigger] s1[i] == s2[i] by {
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);
-            lemma_seq_add_index(s1, suffix, i);
-            lemma_seq_add_index(s2, suffix, i);
+            assert((s1 + suffix)[i] == s1[i]);
+            assert((s2 + suffix)[i] == s2[i]);
         };
         assert(s1 =~= s2);
     }

```

## Recorded checks

### Event 37 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 42 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
