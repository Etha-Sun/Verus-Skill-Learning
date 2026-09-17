# CP1 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 54

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4948,7 +4948,61 @@
             )
         ),
 {
-}
-
-
-}
+    let n: nat = (abs(diff) - 1) as nat;
+
+    let init = lift_state(|s: ClusterState| {
+        &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+    let final = lift_state(|s: ClusterState| {
+        &&& exists_ok_resp_in_flight_at_after_create_pod_step(vrs, controller_id, n)(s)
+        &&& num_diff_pods_is(vrs, diff + 1)(s)
+    });
+    let pending_create = lift_state(|s: ClusterState| {
+        &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, n)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+
+    let specific_resp = |resp_msg: Message| lift_state(|s: ClusterState| {
+        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+    let specific_req = |req_msg: Message| lift_state(|s: ClusterState| {
+        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, n)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+
+    let exists_resp = tla_exists(specific_resp);
+    let exists_req = tla_exists(specific_req);
+
+    assert forall |resp_msg: Message| spec.entails(
+        specific_resp(resp_msg).leads_to(pending_create)
+    ) by {
+        lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(
+            vrs, spec, cluster, controller_id, resp_msg, diff
+        );
+    };
+    leads_to_exists_intro::<ClusterState, Message>(spec, specific_resp, pending_create);
+
+    assert forall |req_msg: Message| spec.entails(
+        specific_req(req_msg).leads_to(final)
+    ) by {
+        lemma_from_after_send_create_pod_req_to_receive_ok_resp(
+            vrs, spec, cluster, controller_id, req_msg, diff
+        );
+    };
+    leads_to_exists_intro::<ClusterState, Message>(spec, specific_req, final);
+
+    assert(init.entails(exists_resp));
+    entails_implies_leads_to(spec, init, exists_resp);
+
+    assert(pending_create.entails(exists_req));
+    entails_implies_leads_to(spec, pending_create, exists_req);
+
+    leads_to_trans(spec, init, exists_resp, pending_create);
+    leads_to_trans(spec, init, pending_create, exists_req);
+    leads_to_trans(spec, init, exists_req, final);
+}
+
+
+}

```

## Source change event 62

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4954,7 +4954,7 @@
         &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
         &&& num_diff_pods_is(vrs, diff)(s)
     });
-    let final = lift_state(|s: ClusterState| {
+    let final_pred = lift_state(|s: ClusterState| {
         &&& exists_ok_resp_in_flight_at_after_create_pod_step(vrs, controller_id, n)(s)
         &&& num_diff_pods_is(vrs, diff + 1)(s)
     });
@@ -4985,13 +4985,13 @@
     leads_to_exists_intro::<ClusterState, Message>(spec, specific_resp, pending_create);
 
     assert forall |req_msg: Message| spec.entails(
-        specific_req(req_msg).leads_to(final)
+        specific_req(req_msg).leads_to(final_pred)
     ) by {
         lemma_from_after_send_create_pod_req_to_receive_ok_resp(
             vrs, spec, cluster, controller_id, req_msg, diff
         );
     };
-    leads_to_exists_intro::<ClusterState, Message>(spec, specific_req, final);
+    leads_to_exists_intro::<ClusterState, Message>(spec, specific_req, final_pred);
 
     assert(init.entails(exists_resp));
     entails_implies_leads_to(spec, init, exists_resp);
@@ -5001,8 +5001,8 @@
 
     leads_to_trans(spec, init, exists_resp, pending_create);
     leads_to_trans(spec, init, pending_create, exists_req);
-    leads_to_trans(spec, init, exists_req, final);
-}
-
-
-}
+    leads_to_trans(spec, init, exists_req, final_pred);
+}
+
+
+}

```

## Source change event 69

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4975,7 +4975,7 @@
     let exists_resp = tla_exists(specific_resp);
     let exists_req = tla_exists(specific_req);
 
-    assert forall |resp_msg: Message| spec.entails(
+    assert forall |resp_msg: Message| #[trigger] spec.entails(
         specific_resp(resp_msg).leads_to(pending_create)
     ) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(
@@ -4984,7 +4984,7 @@
     };
     leads_to_exists_intro::<ClusterState, Message>(spec, specific_resp, pending_create);
 
-    assert forall |req_msg: Message| spec.entails(
+    assert forall |req_msg: Message| #[trigger] spec.entails(
         specific_req(req_msg).leads_to(final_pred)
     ) by {
         lemma_from_after_send_create_pod_req_to_receive_ok_resp(

```

## Source change event 80

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4993,7 +4993,22 @@
     };
     leads_to_exists_intro::<ClusterState, Message>(spec, specific_req, final_pred);
 
-    assert(init.entails(exists_resp));
+    assert(init.entails(exists_resp)) by {
+        assert forall |ex: Execution<ClusterState>|
+            init.satisfied_by(ex) ==> exists_resp.satisfied_by(ex)
+        by {
+            if init.satisfied_by(ex) {
+                let s = ex.head();
+                let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+                let resp_msg = choose |resp_msg: Message| {
+                    &&& s.in_flight().contains(resp_msg)
+                    &&& resp_msg_matches_req_msg(resp_msg, msg)
+                    &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+                };
+                assert(specific_resp(resp_msg).satisfied_by(ex));
+            }
+        };
+    }
     entails_implies_leads_to(spec, init, exists_resp);
 
     assert(pending_create.entails(exists_req));

```

## Source change event 88

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5011,7 +5011,17 @@
     }
     entails_implies_leads_to(spec, init, exists_resp);
 
-    assert(pending_create.entails(exists_req));
+    assert(pending_create.entails(exists_req)) by {
+        assert forall |ex: Execution<ClusterState>|
+            pending_create.satisfied_by(ex) ==> exists_req.satisfied_by(ex)
+        by {
+            if pending_create.satisfied_by(ex) {
+                let s = ex.head();
+                let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+                assert(specific_req(req_msg).satisfied_by(ex));
+            }
+        };
+    }
     entails_implies_leads_to(spec, pending_create, exists_req);
 
     leads_to_trans(spec, init, exists_resp, pending_create);

```

## Recorded checks

### Event 17 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: postcondition not satisfied
4904 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4905 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4906 | | )
     | |_- at the end of the function body
4935 | /         spec.entails(
4936 | |             lift_state(
4937 | |                 |s: ClusterState| {
4938 | |                     &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4949 | |         ),
     | |_________^ failed this postcondition
verification results:: 0 verified, 1 errors
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 56 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: aborting due to 1 previous error
```

### Event 64 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
4978 |     assert forall |resp_msg: Message| spec.entails(
     |     ^^^^^^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 71 (exit 1)

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
4996 |     assert(init.entails(exists_resp));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
error: assertion failed
4999 |     assert(pending_create.entails(exists_req));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
verification results:: 0 verified, 1 errors
error: aborting due to 2 previous errors; 1 warning emitted
```

### Event 82 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4997 |         assert forall |ex: Execution<ClusterState>|
     |         ^^^^^^
error: assertion failed
5014 |     assert(pending_create.entails(exists_req));
     |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
5003 |                   let resp_msg = choose |resp_msg: Message| {
     |  ________________________________^
5004 | |                     &&& s.in_flight().contains(resp_msg)
5005 | |                     &&& resp_msg_matches_req_msg(resp_msg, msg)
5006 | |                     &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
5007 | |                 };
     | |_________________^
5005 |                     &&& resp_msg_matches_req_msg(resp_msg, msg)
     |                         ^^^^^^^^^^^
```

### Event 90 (exit 0)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4997 |         assert forall |ex: Execution<ClusterState>|
     |         ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
5015 |         assert forall |ex: Execution<ClusterState>|
     |         ^^^^^^
5003 |                   let resp_msg = choose |resp_msg: Message| {
     |  ________________________________^
5004 | |                     &&& s.in_flight().contains(resp_msg)
5005 | |                     &&& resp_msg_matches_req_msg(resp_msg, msg)
5006 | |                     &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
5007 | |                 };
     | |_________________^
5005 |                     &&& resp_msg_matches
```

### Event 95 (exit 0)

```text
/bin/bash -lc ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
