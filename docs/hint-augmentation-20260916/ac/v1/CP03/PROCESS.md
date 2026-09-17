# CP3 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 56

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4980,6 +4980,18 @@
         }
     );
 
+    assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==>
+        tla_exists(p_resp).satisfied_by(ex) by {
+        let s = ex.head();
+        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        let resp_witness = choose |resp_msg: Message| {
+            &&& #[trigger] s.in_flight().contains(resp_msg)
+            &&& resp_msg_matches_req_msg(resp_msg, msg)
+            &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+        };
+        assert(p_resp(resp_witness).satisfied_by(ex));
+    };
+
     assert forall |resp_msg: Message| #[trigger] spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
     };
@@ -4994,6 +5006,19 @@
     };
     leads_to_exists_intro(spec, p_req, r);
 
+    assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==>
+        tla_exists(p_req).satisfied_by(ex) by {
+        let s = ex.head();
+        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        let req_witness = choose |req_msg: Message| {
+            &&& #[trigger] s.in_flight().contains(req_msg)
+            &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
+            &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())
+            &&& req_msg_is_create_matching_pod_req(vrs, req_msg)
+        };
+        assert(p_req(req_witness).satisfied_by(ex));
+    };
+
     assert(q_mid.entails(tla_exists(p_req)));
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, q_mid, tla_exists(p_req));

```

## Source change event 64

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4982,14 +4982,17 @@
 
     assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==>
         tla_exists(p_resp).satisfied_by(ex) by {
-        let s = ex.head();
-        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        let resp_witness = choose |resp_msg: Message| {
-            &&& #[trigger] s.in_flight().contains(resp_msg)
-            &&& resp_msg_matches_req_msg(resp_msg, msg)
-            &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
-        };
-        assert(p_resp(resp_witness).satisfied_by(ex));
+        if p.satisfied_by(ex) {
+            let s = ex.head();
+            assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
+            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            let resp_witness = choose |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, msg)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
+            assert(p_resp(resp_witness).satisfied_by(ex));
+        }
     };
 
     assert forall |resp_msg: Message| #[trigger] spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
@@ -5008,15 +5011,18 @@
 
     assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==>
         tla_exists(p_req).satisfied_by(ex) by {
-        let s = ex.head();
-        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        let req_witness = choose |req_msg: Message| {
-            &&& #[trigger] s.in_flight().contains(req_msg)
-            &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
-            &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())
-            &&& req_msg_is_create_matching_pod_req(vrs, req_msg)
-        };
-        assert(p_req(req_witness).satisfied_by(ex));
+        if q_mid.satisfied_by(ex) {
+            let s = ex.head();
+            assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
+            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            let req_witness = choose |req_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(req_msg)
+                &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
+                &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())
+                &&& req_msg_is_create_matching_pod_req(vrs, req_msg)
+            };
+            assert(p_req(req_witness).satisfied_by(ex));
+        }
     };
 
     assert(q_mid.entails(tla_exists(p_req)));

```

## Recorded checks

### Event 14 (exit 1)

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

### Event 58 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4983 |     assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==>
     |     ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5009 |     assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==>
     |     ^^^^^^
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_^
4986 |         let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
     |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

### Event 66 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4983 |     assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==>
     |     ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5012 |     assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==>
     |     ^^^^^^
verification results:: 1 verified, 0 errors
```

### Event 71 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
