# CP7 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 25

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,5 +1,4 @@
 use vstd::prelude::*;
-use vstd::seq_lib::*;
 
 fn main() {}
 

```

## Recorded checks

### Event 19 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 27 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
verification results:: 1 verified, 0 errors
```

### Event 32 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
