# CP3 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 39

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -13,14 +13,10 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
-        lemma_seq_add_len(s1, suffix);
-        lemma_seq_add_len(s2, suffix);
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
         assert forall |i: int| 0 <= i < s1.len() implies #[trigger] s1[i] == s2[i] by {
             assert((s1 + suffix)[i] == (s2 + suffix)[i]);
-            lemma_seq_add_index(s1, suffix, i);
-            lemma_seq_add_index(s2, suffix, i);
         };
         assert(s1 =~= s2);
     }

```

## Source change event 47

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -13,6 +13,9 @@
         assert(s1 + suffix == s2 + suffix);
     }
     if s1 + suffix == s2 + suffix {
+        assert((s1 + suffix).len() == (s2 + suffix).len());
+        assert((s1 + suffix).len() == s1.len() + suffix.len());
+        assert((s2 + suffix).len() == s2.len() + suffix.len());
         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
         assert(s1.len() == s2.len());
         assert forall |i: int| 0 <= i < s1.len() implies #[trigger] s1[i] == s2[i] by {

```

## Source change event 60

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 

```

## Recorded checks

### Event 24 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error[E0425]: cannot find function `lemma_seq_add_len` in this scope
16 |         lemma_seq_add_len(s1, suffix);
   |         ^^^^^^^^^^^^^^^^^ help: a function with a similar name exists: `lemma_seq_take_len`
error[E0425]: cannot find function `lemma_seq_add_len` in this scope
17 |         lemma_seq_add_len(s2, suffix);
   |         ^^^^^^^^^^^^^^^^^ help: a function with a similar name exists: `lemma_seq_take_len`
error[E0425]: cannot find function `lemma_seq_add_index` in this scope
22 |             lemma_seq_add_index(s1, suffix, i);
   |             ^^^^^^^^^^^^^^^^^^^ help: a function with a similar name exists: `lemma_seq_take_index`
error[E0425]: cannot find function `lemma_seq_add_index` in this scope
23 |             lemma_seq_add_index(s2, suffix, i);
   |             ^^^^^^^^^^^^^^^^^^^ help: a function with a similar name exists: `lemma_seq_take_index`
error: aborting due to 4 previous errors
```

### Event 41 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: assertion failed
16 |         assert(s1.len() + suffix.len() == s2.len() + suffix.len());
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error
```

### Event 49 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 54 (exit 1)

```text
/bin/bash -lc ./tools/run_lynette.sh
Files are different
```

### Event 62 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 66 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
