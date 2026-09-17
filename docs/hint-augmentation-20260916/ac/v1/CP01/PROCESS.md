# CP1 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 76

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4948,7 +4948,46 @@
             )
         ),
 {
-}
-
-
-}
+    let step_diff = (abs(diff) - 1) as nat;
+
+    let list_resp_to_pending = |resp_msg: Message| lift_state(|s: ClusterState| {
+        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+
+    let pending = lift_state(|s: ClusterState| {
+        &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+
+    let req_to_ok = |req_msg: Message| lift_state(|s: ClusterState| {
+        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    });
+
+    let exists_req = tla_exists(req_to_ok);
+
+    let ok = lift_state(|s: ClusterState| {
+        &&& exists_ok_resp_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff + 1)(s)
+    });
+
+    assert forall |resp_msg: Message| spec.entails(list_resp_to_pending(resp_msg).leads_to(pending)) by {
+        lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
+    }
+    leads_to_exists_intro(spec, list_resp_to_pending, pending);
+
+    assert forall |req_msg: Message| spec.entails(req_to_ok(req_msg).leads_to(ok)) by {
+        lemma_from_after_send_create_pod_req_to_receive_ok_resp(vrs, spec, cluster, controller_id, req_msg, diff);
+    }
+    leads_to_exists_intro(spec, req_to_ok, ok);
+
+    assert(pending.entails(exists_req));
+    entails_implies_leads_to(spec, pending, exists_req);
+
+    leads_to_trans(spec, pending, exists_req, ok);
+    leads_to_trans(spec, tla_exists(list_resp_to_pending), pending, ok);
+}
+
+
+}

```

## Source change event 83

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4972,12 +4972,12 @@
         &&& num_diff_pods_is(vrs, diff + 1)(s)
     });
 
-    assert forall |resp_msg: Message| spec.entails(list_resp_to_pending(resp_msg).leads_to(pending)) by {
+    assert forall |resp_msg: Message| #[trigger] spec.entails(list_resp_to_pending(resp_msg).leads_to(pending)) by {
         lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
     }
     leads_to_exists_intro(spec, list_resp_to_pending, pending);
 
-    assert forall |req_msg: Message| spec.entails(req_to_ok(req_msg).leads_to(ok)) by {
+    assert forall |req_msg: Message| #[trigger] spec.entails(req_to_ok(req_msg).leads_to(ok)) by {
         lemma_from_after_send_create_pod_req_to_receive_ok_resp(vrs, spec, cluster, controller_id, req_msg, diff);
     }
     leads_to_exists_intro(spec, req_to_ok, ok);

```

## Source change event 94

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4901,6 +4901,50 @@
 	}
 
 
+pub proof fn lemma_pending_req_entails_exists_req(
+    vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
+)
+    ensures
+        lift_state(
+            |s: ClusterState| {
+                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).entails(
+            tla_exists(
+                |req_msg: Message| lift_state(
+                    |s: ClusterState| {
+                        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+                        &&& num_diff_pods_is(vrs, diff)(s)
+                    }
+                )
+            )
+        ),
+{
+    assert forall |ex: Execution<ClusterState>|
+        #[trigger] lift_state(
+            |s: ClusterState| {
+                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).satisfied_by(ex)
+        ==> tla_exists(
+            |req_msg: Message| lift_state(
+                |s: ClusterState| {
+                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+                    &&& num_diff_pods_is(vrs, diff)(s)
+                }
+            )
+        ).satisfied_by(ex)
+    by {
+        let s = ex.head();
+        let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s));
+        assert(num_diff_pods_is(vrs, diff)(s));
+    };
+}
+
+
 pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
 )

```

## Source change event 97

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5026,7 +5026,7 @@
     }
     leads_to_exists_intro(spec, req_to_ok, ok);
 
-    assert(pending.entails(exists_req));
+    lemma_pending_req_entails_exists_req(vrs, controller_id, step_diff, diff);
     entails_implies_leads_to(spec, pending, exists_req);
 
     leads_to_trans(spec, pending, exists_req, ok);

```

## Source change event 104

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4921,23 +4921,13 @@
             )
         ),
 {
-    assert forall |ex: Execution<ClusterState>|
-        #[trigger] lift_state(
-            |s: ClusterState| {
-                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).satisfied_by(ex)
-        ==> tla_exists(
-            |req_msg: Message| lift_state(
-                |s: ClusterState| {
-                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
-                    &&& num_diff_pods_is(vrs, diff)(s)
-                }
-            )
-        ).satisfied_by(ex)
+    assert forall |s: ClusterState|
+        #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+        ==> exists |req_msg: Message|
+            req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
     by {
-        let s = ex.head();
         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
         assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s));
         assert(num_diff_pods_is(vrs, diff)(s));

```

## Source change event 111

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4921,13 +4921,13 @@
             )
         ),
 {
-    assert forall |s: ClusterState|
+    assert(forall |s: ClusterState|
         #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
-        &&& num_diff_pods_is(vrs, diff)(s)
-        ==> exists |req_msg: Message|
-            req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
             &&& num_diff_pods_is(vrs, diff)(s)
-    by {
+            ==> exists |req_msg: Message|
+                req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+    ) by {
         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
         assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s));
         assert(num_diff_pods_is(vrs, diff)(s));

```

## Source change event 121

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4921,13 +4921,7 @@
             )
         ),
 {
-    assert(forall |s: ClusterState|
-        #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
-            &&& num_diff_pods_is(vrs, diff)(s)
-            ==> exists |req_msg: Message|
-                req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-    ) by {
+    assert(forall |s: ClusterState| #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s) &&& num_diff_pods_is(vrs, diff)(s) ==> exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s) &&& num_diff_pods_is(vrs, diff)(s)) by {
         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
         assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s));
         assert(num_diff_pods_is(vrs, diff)(s));

```

## Source change event 129

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4624,6 +4624,36 @@
 }
 
 
+pub open spec fn pending_create_req_with_num_diff(
+    vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
+) -> StatePred<ClusterState> {
+    |s: ClusterState| {
+        &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    }
+}
+
+
+pub open spec fn req_create_with_num_diff(
+    vrs: VReplicaSetView, controller_id: int, req_msg: Message, step_diff: nat, diff: int
+) -> StatePred<ClusterState> {
+    |s: ClusterState| {
+        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    }
+}
+
+
+pub open spec fn list_resp_with_num_diff(
+    vrs: VReplicaSetView, controller_id: int, resp_msg: Message, diff: int
+) -> StatePred<ClusterState> {
+    |s: ClusterState| {
+        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+        &&& num_diff_pods_is(vrs, diff)(s)
+    }
+}
+
+
 // File: controllers/vreplicaset_controller/trusted/liveness_theorem.rs
 pub open spec fn matching_pods(vrs: VReplicaSetView, resources: StoredState) -> Set<DynamicObjectView> {
     resources.values().filter(|obj: DynamicObjectView| owned_selector_match_is(vrs, obj))

```

## Source change event 135

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4935,26 +4935,13 @@
     vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
 )
     ensures
-        lift_state(
-            |s: ClusterState| {
-                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).entails(
-            tla_exists(
-                |req_msg: Message| lift_state(
-                    |s: ClusterState| {
-                        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s)
-                        &&& num_diff_pods_is(vrs, diff)(s)
-                    }
-                )
-            )
+        lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(
+            tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))
         ),
 {
-    assert(forall |s: ClusterState| #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s) &&& num_diff_pods_is(vrs, diff)(s) ==> exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s) &&& num_diff_pods_is(vrs, diff)(s)) by {
+    assert(forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_msg: Message| req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s)) by {
         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, step_diff)(s));
-        assert(num_diff_pods_is(vrs, diff)(s));
+        assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
     };
 }
 

```

## Source change event 142

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4939,7 +4939,7 @@
             tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))
         ),
 {
-    assert(forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_msg: Message| req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s)) by {
+    assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_msg: Message| req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s) by {
         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
         assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
     };

```

## Source change event 158

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4940,8 +4940,10 @@
         ),
 {
     assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_msg: Message| req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s) by {
-        let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
+        if pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) {
+            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
+        }
     };
 }
 

```

## Source change event 165

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4945,6 +4945,7 @@
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
         }
     };
+    assert(lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))));
 }
 
 

```

## Source change event 175

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4939,13 +4939,13 @@
             tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))
         ),
 {
-    assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_msg: Message| req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s) by {
-        if pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) {
+    assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex) ==> tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) by {
+        if lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex) {
+            let s = ex.head();
             let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
         }
     };
-    assert(lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))));
 }
 
 

```

## Source change event 182

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4944,6 +4944,7 @@
             let s = ex.head();
             let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
+            assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
         }
     };
 }

```

## Source change event 189

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4944,6 +4944,7 @@
             let s = ex.head();
             let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
+            assert(lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
             assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
         }
     };

```

## Source change event 196

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4945,6 +4945,7 @@
             let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
             assert(lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
+            assert(exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
             assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
         }
     };

```

## Source change event 203

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4946,6 +4946,7 @@
             assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
             assert(lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
             assert(exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
+            assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) == exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
             assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
         }
     };

```

## Source change event 211

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4931,6 +4931,22 @@
 	}
 
 
+pub proof fn lemma_pending_req_state_has_witness(
+    ex: Execution<ClusterState>, vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
+)
+    requires
+        lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex),
+    ensures
+        tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex),
+{
+    let s = ex.head();
+    let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+    assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
+    assert(lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
+    assert(exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
+}
+
+
 pub proof fn lemma_pending_req_entails_exists_req(
     vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
 )
@@ -4940,15 +4956,7 @@
         ),
 {
     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex) ==> tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) by {
-        if lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex) {
-            let s = ex.head();
-            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-            assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
-            assert(lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
-            assert(exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
-            assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) == exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
-            assert(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
-        }
+        lemma_pending_req_state_has_witness(ex, vrs, controller_id, step_diff, diff);
     };
 }
 

```

## Recorded checks

### Event 37 (exit 1)

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

### Event 78 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
4975 |     assert forall |resp_msg: Message| spec.entails(list_resp_to_pending(resp_msg).leads_to(pending)) by {
     |     ^^^^^^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 85 (exit 1)

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
error: assertion failed
4985 |     assert(pending.entails(exists_req));
     |            
```

### Event 99 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4924 |     assert forall |ex: Execution<ClusterState>|
     |     ^^^^^^
error: triggers cannot contain let/forall/exists/lambda/choose
4926 | /             |s: ClusterState| {
4927 | |                 &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, step_diff)(s)
4928 | |                 &&& num_diff_pods_is(vrs, diff)(s)
4929 | |             }
     | |_____________^
error: aborting due to 1 previous error; 2 warnings emitted
```

### Event 106 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'

```

### Event 113 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'

```

### Event 123 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'

```

### Event 137 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error[E0425]: cannot find value `s` in this scope
4943 |         let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
     |                       ^ not found in this scope
error[E0425]: cannot find value `s` in this scope
4944 |         assert(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)(s));
     |                                                                                       ^ not found in this scope
error: aborting due to 2 previous errors; 1 warning emitted
```

### Event 144 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_m...
     |     ^^^^^^
4934 | / pub proof fn lemma_pending_req_entails_exists_req(
4935 | |     vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
4936 | | )
     | |_^
error: postcondition not satisfied
4934 | / pub proof fn lemma_pending_req_entails_exists_req(
4935 | |     vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
4936 | | )
     | |_- at the end of the function body
4937 |       ensures
4938 | /         lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(
4939 | |             tla_exists(|req_msg: Message| lift_state
```

### Event 160 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_m...
     |     ^^^^^^
error: postcondition not satisfied
4934 | / pub proof fn lemma_pending_req_entails_exists_req(
4935 | |     vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
4936 | | )
     | |_- at the end of the function body
4937 |       ensures
4938 | /         lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(
4939 | |             tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))
4940 | |         ),
     | |_________^ failed this postcondition
4951 | / pub proof fn le
```

### Event 167 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |s: ClusterState| #[trigger] pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)(s) ==> exists |req_m...
     |     ^^^^^^
error: assertion failed
4948 | ...rt(lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).entails(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)))));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4952 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4953 | |     v
```

### Event 177 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: assertion failed
4942 | ...>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, diff)).satisfied_by(ex) ==> tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) by {
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4952 | / pub proof fn
```

### Event 184 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: assertion failed
4947 | ...rt(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4953 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4954 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4955 | | )
     | |_^
error: postcondition not sa
```

### Event 191 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: assertion failed
4948 | ...rt(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4954 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4955 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4956 | | )
     | |_^
error: postcondition not sa
```

### Event 198 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: assertion failed
4949 | ...rt(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4955 | / pub proof fn lemma_from_after_receive_list_pods_resp_to_receive_create_pod_resp(
4956 | |     vrs: VReplicaSetView, spec: TempPred<ClusterState>, cluster: Cluster, controller_id: int, diff: int
4957 | | )
     | |_^
error: postcondition not sa
```

### Event 205 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4942 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: assertion failed
4949 | ...rt(tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex) == exists |req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff)).satisfied_by(ex));
     |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion f
```

### Event 213 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4958 |     assert forall |ex: Execution<ClusterState>| #[trigger] lift_state(pending_create_req_with_num_diff(vrs, controller_id, step_diff, dif...
     |     ^^^^^^
error: postcondition not satisfied
4934 | / pub proof fn lemma_pending_req_state_has_witness(
4935 | |     ex: Execution<ClusterState>, vrs: VReplicaSetView, controller_id: int, step_diff: nat, diff: int
4936 | | )
     | |_- at the end of the function body
4940 |           tla_exists(|req_msg: Message| lift_state(req_create_with_num_diff(vrs, controller_id, req_msg, step_diff, diff))).satisfied_by(ex),
     |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ failed this postcondition
er
```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
