# CP4 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 49

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4986,7 +4986,7 @@
     leads_to_exists_intro(spec, p_resp, q_mid);
 
     assert(p.entails(tla_exists(p_resp))) by {
-        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
             let s = ex.head();
             assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
@@ -5002,7 +5002,7 @@
     leads_to_exists_intro(spec, p_req, r);
 
     assert(q_mid.entails(tla_exists(p_req))) by {
-        assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==> tla_exists(p_req).satisfied_by(ex) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
             let s = ex.head();
             assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
             assert(num_diff_pods_is(vrs, diff)(s));

```

## Source change event 70

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4988,9 +4988,27 @@
     assert(p.entails(tla_exists(p_resp))) by {
         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) implies tla_exists(p_resp).satisfied_by(ex) by {
             let s = ex.head();
+            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            assert(exists |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            });
+            let resp_msg = choose |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
+            assert(s.in_flight().contains(resp_msg));
+            assert(resp_msg_matches_req_msg(resp_msg, msg));
+            assert(resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg));
+            assert(at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterListPods)(s));
+            assert(Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), msg));
+            assert(msg.src == HostId::Controller(controller_id, vrs.object_ref()));
+            assert(req_msg_is_list_pods_req(vrs, msg));
+            assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
         };
     };
     entails_implies_leads_to(spec, p, tla_exists(p_resp));

```

## Source change event 78

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5009,6 +5009,8 @@
             assert(msg.src == HostId::Controller(controller_id, vrs.object_ref()));
             assert(req_msg_is_list_pods_req(vrs, msg));
             assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            assert(p_resp(resp_msg).satisfied_by(ex));
+            assert(tla_exists(p_resp).satisfied_by(ex));
         };
     };
     entails_implies_leads_to(spec, p, tla_exists(p_resp));

```

## Source change event 86

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5024,9 +5024,17 @@
     assert(q_mid.entails(tla_exists(p_req))) by {
         assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
             let s = ex.head();
+            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+            assert(at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(d))(s));
+            assert(Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg));
+            assert(s.in_flight().contains(req_msg));
+            assert(req_msg.src == HostId::Controller(controller_id, vrs.object_ref()));
+            assert(req_msg_is_create_matching_pod_req(vrs, req_msg));
+            assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
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
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4989 |         assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
     |         ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5005 |         assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==> tla_exists(p_req).satisfied_by(ex) by {
     |         ^^^^^^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
error: assertion failed
4991 |             assert(exists_resp_in_flight_at_
```

### Event 51 (exit 1)

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

### Event 72 (exit 1)

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
5027 | ...rt(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 
```

### Event 80 (exit 1)

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
5025 |         assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) implies tla_exists(p_req).satisfied_by(ex) by {
     |                                                                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
5029 | ...rt(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification result
```

### Event 88 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
verification results:: 1 verified, 0 errors
```

### Event 93 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
