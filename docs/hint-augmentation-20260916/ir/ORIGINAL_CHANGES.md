# Original source changes

Extracted diffs only; full raw conversations remain external.

## Event 30

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -6,6 +6,9 @@
     ensures
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
+    assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
+        assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
+    });
 }
 
 } // verus!

```

## Event 37

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -1,4 +1,5 @@
 use vstd::prelude::*;
+use vstd::assert_sets_equal;
 fn main() {}
 verus! {
 

```

## Event 45

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -8,7 +8,31 @@
         (s1 + s2).map(f) == s1.map(f) + s2.map(f),
 {
     assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
-        assert(((s1 + s2).map(f)).contains(x) == (s1.map(f) + s2.map(f)).contains(x));
+        assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
+            let a = choose |a: A| #[trigger] ((s1 + s2).contains(a) && f(a) == x);
+            assert((s1 + s2).contains(a) && f(a) == x);
+            assert(s1.contains(a) || s2.contains(a));
+            if s1.contains(a) {
+                assert(s1.map(f).contains(x));
+            } else {
+                assert(s2.contains(a));
+                assert(s2.map(f).contains(x));
+            }
+            assert(s1.map(f).contains(x) || s2.map(f).contains(x));
+        };
+        assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
+            if s1.map(f).contains(x) {
+                let a = choose |a: A| #[trigger] (s1.contains(a) && f(a) == x);
+                assert(s1.contains(a) && f(a) == x);
+                assert((s1 + s2).contains(a));
+                assert(((s1 + s2).map(f)).contains(x));
+            } else {
+                let a = choose |a: A| #[trigger] (s2.contains(a) && f(a) == x);
+                assert(s2.contains(a) && f(a) == x);
+                assert((s1 + s2).contains(a));
+                assert(((s1 + s2).map(f)).contains(x));
+            }
+        };
     });
 }
 

```

## Event 52

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -9,7 +9,7 @@
 {
     assert_sets_equal!((s1 + s2).map(f), s1.map(f) + s2.map(f), x => {
         assert(((s1 + s2).map(f)).contains(x) ==> (s1.map(f) + s2.map(f)).contains(x)) by {
-            let a = choose |a: A| #[trigger] ((s1 + s2).contains(a) && f(a) == x);
+            let a = choose |a: A| ((s1 + s2).contains(a) && f(a) == x);
             assert((s1 + s2).contains(a) && f(a) == x);
             assert(s1.contains(a) || s2.contains(a));
             if s1.contains(a) {
@@ -22,12 +22,12 @@
         };
         assert((s1.map(f) + s2.map(f)).contains(x) ==> ((s1 + s2).map(f)).contains(x)) by {
             if s1.map(f).contains(x) {
-                let a = choose |a: A| #[trigger] (s1.contains(a) && f(a) == x);
+                let a = choose |a: A| (s1.contains(a) && f(a) == x);
                 assert(s1.contains(a) && f(a) == x);
                 assert((s1 + s2).contains(a));
                 assert(((s1 + s2).map(f)).contains(x));
             } else {
-                let a = choose |a: A| #[trigger] (s2.contains(a) && f(a) == x);
+                let a = choose |a: A| (s2.contains(a) && f(a) == x);
                 assert(s2.contains(a) && f(a) == x);
                 assert((s1 + s2).contains(a));
                 assert(((s1 + s2).map(f)).contains(x));

```

## Event 60

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -9,28 +9,32 @@
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
+                    let a = choose |a: A| (s2.contains(a) && f(a) == x);
+                    assert(s2.contains(a) && f(a) == x);
+                    assert((s1 + s2).contains(a));
+                    assert(((s1 + s2).map(f)).contains(x));
+                }
             }
         };
     });

```

## Event 82

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

