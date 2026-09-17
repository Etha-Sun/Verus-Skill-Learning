# CP5 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 68

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4901,6 +4901,56 @@
 	}
 
 
+pub proof fn lemma_exists_list_resp_has_concrete_witness(
+    vrs: VReplicaSetView, controller_id: int, s: ClusterState
+)
+    requires
+        exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s),
+    ensures
+        exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s),
+{
+    let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+
+    assert(exists |resp_msg: Message| {
+        &&& #[trigger] s.in_flight().contains(resp_msg)
+        &&& resp_msg_matches_req_msg(resp_msg, msg)
+        &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+    });
+
+    let resp_msg = choose |resp_msg: Message| {
+        &&& #[trigger] s.in_flight().contains(resp_msg)
+        &&& resp_msg_matches_req_msg(resp_msg, msg)
+        &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+    };
+
+    assert(at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterListPods)(s));
+    assert(Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), msg));
+    assert(msg.src == HostId::Controller(controller_id, vrs.object_ref()));
+    assert(req_msg_is_list_pods_req(vrs, msg));
+    assert(s.in_flight().contains(resp_msg));
+    assert(resp_msg_matches_req_msg(resp_msg, msg));
+    assert(resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg));
+    assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+}
+
+pub proof fn lemma_pending_req_has_concrete_witness(
+    vrs: VReplicaSetView, controller_id: int, diff: nat, s: ClusterState
+)
+    requires
+        pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, diff)(s),
+    ensures
+        exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, diff)(s),
+{
+    let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+
+    assert(at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(diff))(s));
+    assert(Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg));
+    assert(s.in_flight().contains(req_msg));
+    assert(req_msg.src == HostId::Controller(controller_id, vrs.object_ref()));
+    assert(req_msg_is_create_matching_pod_req(vrs, req_msg));
+    assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, diff)(s));
+}
+
 pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
 )

```

## Source change event 71

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5038,9 +5038,11 @@
     assert(p.entails(tla_exists(p_resp))) by {
         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
             let s = ex.head();
-            assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            lemma_exists_list_resp_has_concrete_witness(vrs, controller_id, s);
+            let resp_msg = choose |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s);
+            assert(p_resp(resp_msg).satisfied_by(ex));
+            assert(tla_exists(p_resp).satisfied_by(ex));
         };
     };
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
@@ -5054,9 +5056,11 @@
     assert(q_mid.entails(tla_exists(p_req))) by {
         assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
             let s = ex.head();
-            assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+            lemma_pending_req_has_concrete_witness(vrs, controller_id, d, s);
+            let req_msg = choose |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s);
+            assert(p_req(req_msg).satisfied_by(ex));
+            assert(tla_exists(p_req).satisfied_by(ex));
         };
     };
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));

```

## Recorded checks

### Event 18 (exit 1)

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
4989 |         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
     |                                                                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
4993 |             assert(exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
     |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verificatio
```

### Event 74 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
verification results:: 3 verified, 0 errors
```

### Event 79 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
