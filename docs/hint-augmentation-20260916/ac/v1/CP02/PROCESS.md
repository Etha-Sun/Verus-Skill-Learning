# CP2 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 37

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4980,7 +4980,7 @@
         }
     );
 
-    assert forall |resp_msg: Message| spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
+    assert forall |resp_msg: Message| #[trigger] spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
     };
     leads_to_exists_intro(spec, p_resp, q_mid);
@@ -4989,7 +4989,7 @@
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
     leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
 
-    assert forall |req_msg: Message| spec.entails(p_req(req_msg).leads_to(r)) by {
+    assert forall |req_msg: Message| #[trigger] spec.entails(p_req(req_msg).leads_to(r)) by {
         lemma_from_after_send_create_pod_req_to_receive_ok_resp(vrs, spec, cluster, controller_id, req_msg, diff);
     };
     leads_to_exists_intro(spec, p_req, r);

```

## Source change event 61

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4949,12 +4949,11 @@
         ),
 {
     let d = (abs(diff) - 1) as nat;
-    let p_resp = |resp_msg: Message| lift_state(
-        |s: ClusterState| {
-            &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
-            &&& num_diff_pods_is(vrs, diff)(s)
-        }
-    );
+    let p_resp_state = |resp_msg: Message, s: ClusterState| {
+        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    };
+    let p_resp = |resp_msg: Message| lift_state(|s: ClusterState| p_resp_state(resp_msg, s));
     let q_mid = lift_state(
         |s: ClusterState| {
             &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
@@ -4973,19 +4972,43 @@
             &&& num_diff_pods_is(vrs, diff + 1)(s)
         }
     );
-    let p = lift_state(
-        |s: ClusterState| {
-            &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
-            &&& num_diff_pods_is(vrs, diff)(s)
-        }
-    );
+    let p_state = |s: ClusterState| {
+        &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    };
+    let p = lift_state(p_state);
 
     assert forall |resp_msg: Message| #[trigger] spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
     };
     leads_to_exists_intro(spec, p_resp, q_mid);
 
-    assert(p.entails(tla_exists(p_resp)));
+    assert(p.entails(tla_exists(p_resp))) by {
+        assert forall |s: ClusterState| p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
+            let s: ClusterState;
+            if p_state(s) {
+                let pending_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+                let resp_msg = choose |resp_msg: Message| {
+                    &&& #[trigger] s.in_flight().contains(resp_msg)
+                    &&& resp_msg_matches_req_msg(resp_msg, pending_msg)
+                    &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+                };
+                assert(p_resp_state(resp_msg, s));
+                assert(exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s));
+            }
+        };
+        assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+            let ex: Execution<ClusterState>;
+            if p.satisfied_by(ex) {
+                let s = ex.head();
+                assert(p_state(s));
+                let resp_msg = choose |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s);
+                assert(p_resp_state(resp_msg, s));
+                assert(p_resp(resp_msg).satisfied_by(ex));
+                assert(tla_exists(p_resp).satisfied_by(ex));
+            }
+        };
+    }
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
     leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
 

```

## Source change event 77

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4984,7 +4984,7 @@
     leads_to_exists_intro(spec, p_resp, q_mid);
 
     assert(p.entails(tla_exists(p_resp))) by {
-        assert forall |s: ClusterState| p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
+        assert forall |s: ClusterState| #[trigger] p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
             let s: ClusterState;
             if p_state(s) {
                 let pending_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
@@ -4997,7 +4997,7 @@
                 assert(exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s));
             }
         };
-        assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
             let ex: Execution<ClusterState>;
             if p.satisfied_by(ex) {
                 let s = ex.head();

```

## Source change event 86

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4953,7 +4953,12 @@
         &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
         &&& num_diff_pods_is(vrs, diff)(s)
     };
-    let p_resp = |resp_msg: Message| lift_state(|s: ClusterState| p_resp_state(resp_msg, s));
+    let p_resp = |resp_msg: Message| lift_state(
+        |s: ClusterState| {
+            &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
     let q_mid = lift_state(
         |s: ClusterState| {
             &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)

```

## Source change event 101

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4989,7 +4989,7 @@
     leads_to_exists_intro(spec, p_resp, q_mid);
 
     assert(p.entails(tla_exists(p_resp))) by {
-        assert forall |s: ClusterState| #[trigger] p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
+        assert forall |s: ClusterState| #[trigger] p_state(s) implies exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
             let s: ClusterState;
             if p_state(s) {
                 let pending_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
@@ -5002,7 +5002,7 @@
                 assert(exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s));
             }
         };
-        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
             let ex: Execution<ClusterState>;
             if p.satisfied_by(ex) {
                 let s = ex.head();

```

## Source change event 110

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4949,10 +4949,6 @@
         ),
 {
     let d = (abs(diff) - 1) as nat;
-    let p_resp_state = |resp_msg: Message, s: ClusterState| {
-        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
-        &&& num_diff_pods_is(vrs, diff)(s)
-    };
     let p_resp = |resp_msg: Message| lift_state(
         |s: ClusterState| {
             &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
@@ -4977,11 +4973,12 @@
             &&& num_diff_pods_is(vrs, diff + 1)(s)
         }
     );
-    let p_state = |s: ClusterState| {
-        &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
-        &&& num_diff_pods_is(vrs, diff)(s)
-    };
-    let p = lift_state(p_state);
+    let p = lift_state(
+        |s: ClusterState| {
+            &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
 
     assert forall |resp_msg: Message| #[trigger] spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
@@ -4989,29 +4986,21 @@
     leads_to_exists_intro(spec, p_resp, q_mid);
 
     assert(p.entails(tla_exists(p_resp))) by {
-        assert forall |s: ClusterState| #[trigger] p_state(s) implies exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
-            let s: ClusterState;
-            if p_state(s) {
-                let pending_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-                let resp_msg = choose |resp_msg: Message| {
-                    &&& #[trigger] s.in_flight().contains(resp_msg)
-                    &&& resp_msg_matches_req_msg(resp_msg, pending_msg)
-                    &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
-                };
-                assert(p_resp_state(resp_msg, s));
-                assert(exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s));
-            }
-        };
         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
-            let ex: Execution<ClusterState>;
-            if p.satisfied_by(ex) {
-                let s = ex.head();
-                assert(p_state(s));
-                let resp_msg = choose |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s);
-                assert(p_resp_state(resp_msg, s));
-                assert(p_resp(resp_msg).satisfied_by(ex));
-                assert(tla_exists(p_resp).satisfied_by(ex));
-            }
+            let s = ex.head();
+            let pending_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert(exists |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, pending_msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            });
+            let resp_msg = choose |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, pending_msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
+            assert(p_resp(resp_msg).satisfied_by(ex));
+            assert(tla_exists(p_resp).satisfied_by(ex));
         };
     }
     entails_implies_leads_to(spec, p, tla_exists(p_resp));

```

## Source change event 119

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5011,7 +5011,14 @@
     };
     leads_to_exists_intro(spec, p_req, r);
 
-    assert(q_mid.entails(tla_exists(p_req)));
+    assert(q_mid.entails(tla_exists(p_req))) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
+            let s = ex.head();
+            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert(p_req(req_msg).satisfied_by(ex));
+            assert(tla_exists(p_req).satisfied_by(ex));
+        };
+    }
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, tla_exists(p_req), r);

```

## Recorded checks

### Event 18 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
4983 |     assert forall |resp_msg: Message| spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
     |     ^^^^^^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 40 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
error: assertion failed
4988 |     assert(p.entails(tla_exists(p_resp)));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
4997 |     assert(q_mid.entails(tla_exists(p_req)));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 2 previous errors; 1 warning emitted
```

### Event 64 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4987 |         assert forall |s: ClusterState| p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
     |         ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5000 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
4987 |         assert forall |s: ClusterState| p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
     |         ^^^^^^
error: aborting due to 1 previ
```

### Event 80 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4987 |         assert forall |s: ClusterState| #[trigger] p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
     |         ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5000 |         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
error: assertion failed
4981 |     assert forall |resp_msg: Message| #
```

### Event 89 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4992 |         assert forall |s: ClusterState| #[trigger] p_state(s) ==> exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
     |         ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5005 |         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
error: assertion failed
4992 |         assert forall |s: ClusterState|
```

### Event 104 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
error: assertion failed
4992 |         assert forall |s: ClusterState| #[trigger] p_state(s) implies exists |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s) by {
     |                                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
5010 |                 let resp_msg = choose |resp_msg: Message| #[trigger] p_resp_state(resp_msg, s);
     |                                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^
error: assertion failed
5011 |                 assert(p_resp_state(resp_msg, s));
     |                        ^^^^^^^^^^^^^
```

### Event 113 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: assertion failed
5014 |     assert(q_mid.entails(tla_exists(p_req)));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 122 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
verification results:: 1 verified, 0 errors
```

### Event 127 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
