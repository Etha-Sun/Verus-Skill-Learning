# CP2 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 34

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

## Source change event 48

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4985,7 +4985,17 @@
     };
     leads_to_exists_intro(spec, p_resp, q_mid);
 
-    assert(p.entails(tla_exists(p_resp)));
+    assert(p.entails(tla_exists(p_resp))) by {
+        assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+            let s = ex.head();
+            let resp_msg = choose |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
+            assert(p_resp(resp_msg).satisfied_by(ex));
+        };
+    }
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
     leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
 

```

## Source change event 56

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4986,11 +4986,19 @@
     leads_to_exists_intro(spec, p_resp, q_mid);
 
     assert(p.entails(tla_exists(p_resp))) by {
-        assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+        assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
             let s = ex.head();
+            assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert exists |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
             let resp_msg = choose |resp_msg: Message| {
                 &&& #[trigger] s.in_flight().contains(resp_msg)
-                &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
+                &&& resp_msg_matches_req_msg(resp_msg, msg)
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
             };
             assert(p_resp(resp_msg).satisfied_by(ex));

```

## Source change event 63

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4991,11 +4991,11 @@
             assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
             let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-            assert exists |resp_msg: Message| {
+            assert(exists |resp_msg: Message| {
                 &&& #[trigger] s.in_flight().contains(resp_msg)
                 &&& resp_msg_matches_req_msg(resp_msg, msg)
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
-            };
+            });
             let resp_msg = choose |resp_msg: Message| {
                 &&& #[trigger] s.in_flight().contains(resp_msg)
                 &&& resp_msg_matches_req_msg(resp_msg, msg)

```

## Source change event 71

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5012,7 +5012,15 @@
     };
     leads_to_exists_intro(spec, p_req, r);
 
-    assert(q_mid.entails(tla_exists(p_req)));
+    assert(q_mid.entails(tla_exists(p_req))) by {
+        assert forall |ex: Execution<ClusterState>| q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
+            let s = ex.head();
+            assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert(p_req(req_msg).satisfied_by(ex));
+        };
+    }
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, tla_exists(p_req), r);

```

## Recorded checks

### Event 26 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
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

### Event 36 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
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

### Event 50 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
4992 |                   &&& #[trigger] s.in_flight().contains(resp_msg)
     |  _____________________^
4993 | |                 &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
4994 | |                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
     | |________________________________
```

### Event 58 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'

```

### Event 65 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: assertion failed
5015 |     assert(q_mid.entails(tla_exists(p_req)));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |                                                     ^^^^^^^^^^^^^^^^^^
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 73 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
4989 |         assert forall |ex: Execution<ClusterState>| p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |                                                     ^^^^^^^^^^^^^^^^^^
5016 |         assert forall |ex: Execution<ClusterState>| q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
     |         ^^^^^^
5016 |         assert forall |ex: Execution<ClusterState>| q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
     |                                                     ^^^^^^^^^^^^^^^^^^^^^^
5016 |         assert forall |ex: Execution<ClusterState>| q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
     |         ^^^^^^
verification 
```

### Event 78 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
