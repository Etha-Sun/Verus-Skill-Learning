# CP3 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 56

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4805,6 +4805,125 @@
     };
 }
 
+pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
+    vrs: VReplicaSetView, controller_id: int, diff: int
+)
+    ensures
+        lift_state(
+            |s: ClusterState| {
+                &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).entails(
+            tla_exists(
+                |resp_msg: Message| lift_state(
+                    |s: ClusterState| {
+                        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+                        &&& num_diff_pods_is(vrs, diff)(s)
+                    }
+                )
+            )
+        ),
+{
+    assert forall |ex: Execution<ClusterState>|
+        lift_state(
+            |s: ClusterState| {
+                &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).satisfied_by(ex)
+        ==> tla_exists(
+            |resp_msg: Message| lift_state(
+                |s: ClusterState| {
+                    &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+                    &&& num_diff_pods_is(vrs, diff)(s)
+                }
+            )
+        ).satisfied_by(ex)
+    by {
+        let s = ex.head();
+        if lift_state(
+            |s: ClusterState| {
+                &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).satisfied_by(ex) {
+            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
+                && resp_msg_matches_req_msg(resp_msg, msg)
+                && resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg);
+            assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            assert(tla_exists(
+                |resp_msg: Message| lift_state(
+                    |s: ClusterState| {
+                        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+                        &&& num_diff_pods_is(vrs, diff)(s)
+                    }
+                )
+            ).satisfied_by(ex));
+        }
+    };
+}
+
+pub proof fn lemma_pending_create_req_entails_concrete_create_req(
+    vrs: VReplicaSetView, controller_id: int, diff: int, d: nat
+)
+    ensures
+        lift_state(
+            |s: ClusterState| {
+                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).entails(
+            tla_exists(
+                |req_msg: Message| lift_state(
+                    |s: ClusterState| {
+                        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+                        &&& num_diff_pods_is(vrs, diff)(s)
+                    }
+                )
+            )
+        ),
+{
+    assert forall |ex: Execution<ClusterState>|
+        lift_state(
+            |s: ClusterState| {
+                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).satisfied_by(ex)
+        ==> tla_exists(
+            |req_msg: Message| lift_state(
+                |s: ClusterState| {
+                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+                    &&& num_diff_pods_is(vrs, diff)(s)
+                }
+            )
+        ).satisfied_by(ex)
+    by {
+        let s = ex.head();
+        if lift_state(
+            |s: ClusterState| {
+                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+                &&& num_diff_pods_is(vrs, diff)(s)
+            }
+        ).satisfied_by(ex) {
+            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+            assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            assert(tla_exists(
+                |req_msg: Message| lift_state(
+                    |s: ClusterState| {
+                        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+                        &&& num_diff_pods_is(vrs, diff)(s)
+                    }
+                )
+            ).satisfied_by(ex));
+        }
+    };
+}
+
 // File: controllers/vreplicaset_controller/proof/liveness/resource_match.rs
 	#[verifier::external_body]
 pub proof fn lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(

```

## Source change event 59

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -5104,6 +5104,7 @@
     };
     leads_to_exists_intro(spec, p_resp, q_mid);
 
+    lemma_list_resp_exists_entails_concrete_list_resp(vrs, controller_id, diff);
     assert(p.entails(tla_exists(p_resp)));
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
     leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
@@ -5113,6 +5114,7 @@
     };
     leads_to_exists_intro(spec, p_req, r);
 
+    lemma_pending_create_req_entails_concrete_create_req(vrs, controller_id, diff, d);
     assert(q_mid.entails(tla_exists(p_req)));
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, q_mid, tla_exists(p_req));

```

## Source change event 69

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4826,13 +4826,13 @@
         ),
 {
     assert forall |ex: Execution<ClusterState>|
-        lift_state(
+        #[trigger] lift_state(
             |s: ClusterState| {
                 &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
                 &&& num_diff_pods_is(vrs, diff)(s)
             }
         ).satisfied_by(ex)
-        ==> tla_exists(
+        implies tla_exists(
             |resp_msg: Message| lift_state(
                 |s: ClusterState| {
                     &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
@@ -4842,27 +4842,20 @@
         ).satisfied_by(ex)
     by {
         let s = ex.head();
-        if lift_state(
-            |s: ClusterState| {
-                &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).satisfied_by(ex) {
-            let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-            let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
-                && resp_msg_matches_req_msg(resp_msg, msg)
-                && resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg);
-            assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
-            assert(num_diff_pods_is(vrs, diff)(s));
-            assert(tla_exists(
-                |resp_msg: Message| lift_state(
-                    |s: ClusterState| {
-                        &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
-                        &&& num_diff_pods_is(vrs, diff)(s)
-                    }
-                )
-            ).satisfied_by(ex));
-        }
+        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
+            && resp_msg_matches_req_msg(resp_msg, msg)
+            && resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg);
+        assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+        assert(num_diff_pods_is(vrs, diff)(s));
+        assert(tla_exists(
+            |resp_msg: Message| lift_state(
+                |s: ClusterState| {
+                    &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+                    &&& num_diff_pods_is(vrs, diff)(s)
+                }
+            )
+        ).satisfied_by(ex));
     };
 }
 
@@ -4887,13 +4880,13 @@
         ),
 {
     assert forall |ex: Execution<ClusterState>|
-        lift_state(
+        #[trigger] lift_state(
             |s: ClusterState| {
                 &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
                 &&& num_diff_pods_is(vrs, diff)(s)
             }
         ).satisfied_by(ex)
-        ==> tla_exists(
+        implies tla_exists(
             |req_msg: Message| lift_state(
                 |s: ClusterState| {
                     &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
@@ -4903,24 +4896,17 @@
         ).satisfied_by(ex)
     by {
         let s = ex.head();
-        if lift_state(
-            |s: ClusterState| {
-                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).satisfied_by(ex) {
-            let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-            assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
-            assert(num_diff_pods_is(vrs, diff)(s));
-            assert(tla_exists(
-                |req_msg: Message| lift_state(
-                    |s: ClusterState| {
-                        &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
-                        &&& num_diff_pods_is(vrs, diff)(s)
-                    }
-                )
-            ).satisfied_by(ex));
-        }
+        let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+        assert(num_diff_pods_is(vrs, diff)(s));
+        assert(tla_exists(
+            |req_msg: Message| lift_state(
+                |s: ClusterState| {
+                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+                    &&& num_diff_pods_is(vrs, diff)(s)
+                }
+            )
+        ).satisfied_by(ex));
     };
 }
 

```

## Source change event 76

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4825,38 +4825,35 @@
             )
         ),
 {
-    assert forall |ex: Execution<ClusterState>|
-        #[trigger] lift_state(
-            |s: ClusterState| {
-                &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).satisfied_by(ex)
-        implies tla_exists(
+    assert forall |s: ClusterState|
+        #[trigger] exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s),
+        #[trigger] num_diff_pods_is(vrs, diff)(s)
+        implies exists |resp_msg: Message|
+            resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+            && num_diff_pods_is(vrs, diff)(s)
+    by {
+        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
+            && resp_msg_matches_req_msg(resp_msg, msg)
+            && resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg);
+        assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+        assert(num_diff_pods_is(vrs, diff)(s));
+    };
+    assert(lift_state(
+        |s: ClusterState| {
+            &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    ).entails(
+        tla_exists(
             |resp_msg: Message| lift_state(
                 |s: ClusterState| {
                     &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
                     &&& num_diff_pods_is(vrs, diff)(s)
                 }
             )
-        ).satisfied_by(ex)
-    by {
-        let s = ex.head();
-        let msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
-            && resp_msg_matches_req_msg(resp_msg, msg)
-            && resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg);
-        assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
-        assert(num_diff_pods_is(vrs, diff)(s));
-        assert(tla_exists(
-            |resp_msg: Message| lift_state(
-                |s: ClusterState| {
-                    &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
-                    &&& num_diff_pods_is(vrs, diff)(s)
-                }
-            )
-        ).satisfied_by(ex));
-    };
+        )
+    ));
 }
 
 pub proof fn lemma_pending_create_req_entails_concrete_create_req(
@@ -4879,35 +4876,32 @@
             )
         ),
 {
-    assert forall |ex: Execution<ClusterState>|
-        #[trigger] lift_state(
-            |s: ClusterState| {
-                &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
-                &&& num_diff_pods_is(vrs, diff)(s)
-            }
-        ).satisfied_by(ex)
-        implies tla_exists(
+    assert forall |s: ClusterState|
+        #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s),
+        #[trigger] num_diff_pods_is(vrs, diff)(s)
+        implies exists |req_msg: Message|
+            req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+            && num_diff_pods_is(vrs, diff)(s)
+    by {
+        let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
+        assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+        assert(num_diff_pods_is(vrs, diff)(s));
+    };
+    assert(lift_state(
+        |s: ClusterState| {
+            &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    ).entails(
+        tla_exists(
             |req_msg: Message| lift_state(
                 |s: ClusterState| {
                     &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
                     &&& num_diff_pods_is(vrs, diff)(s)
                 }
             )
-        ).satisfied_by(ex)
-    by {
-        let s = ex.head();
-        let req_msg = s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0;
-        assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
-        assert(num_diff_pods_is(vrs, diff)(s));
-        assert(tla_exists(
-            |req_msg: Message| lift_state(
-                |s: ClusterState| {
-                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
-                    &&& num_diff_pods_is(vrs, diff)(s)
-                }
-            )
-        ).satisfied_by(ex));
-    };
+        )
+    ));
 }
 
 // File: controllers/vreplicaset_controller/proof/liveness/resource_match.rs

```

## Source change event 89

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4826,8 +4826,8 @@
         ),
 {
     assert forall |s: ClusterState|
-        #[trigger] exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s),
-        #[trigger] num_diff_pods_is(vrs, diff)(s)
+        #[trigger] exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+        && num_diff_pods_is(vrs, diff)(s)
         implies exists |resp_msg: Message|
             resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
             && num_diff_pods_is(vrs, diff)(s)
@@ -4877,8 +4877,8 @@
         ),
 {
     assert forall |s: ClusterState|
-        #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s),
-        #[trigger] num_diff_pods_is(vrs, diff)(s)
+        #[trigger] pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+        && num_diff_pods_is(vrs, diff)(s)
         implies exists |req_msg: Message|
             req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
             && num_diff_pods_is(vrs, diff)(s)

```

## Source change event 100

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -2873,6 +2873,26 @@
 
 pub open spec fn valid<T>(temp_pred: TempPred<T>) -> bool {
     forall |ex: Execution<T>| temp_pred.satisfied_by(ex)
+}
+
+pub proof fn lemma_lift_state_exists_entails_tla_exists<T, A>(
+    state_pred: StatePred<T>,
+    a_to_state_pred: spec_fn(A) -> StatePred<T>
+)
+    requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| a_to_state_pred(a)(s),
+    ensures lift_state(state_pred).entails(tla_exists(|a: A| lift_state(a_to_state_pred(a)))),
+{
+    assert forall |ex: Execution<T>|
+        #[trigger] lift_state(state_pred).satisfied_by(ex)
+        implies tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex)
+    by {
+        let s = ex.head();
+        assert(state_pred(s));
+        let a = choose |a: A| #[trigger] a_to_state_pred(a)(s);
+        assert(a_to_state_pred(a)(s));
+        assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
+        assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));
+    };
 }
 
 

```

## Source change event 103

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4859,21 +4859,16 @@
         assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
         assert(num_diff_pods_is(vrs, diff)(s));
     };
-    assert(lift_state(
+    lemma_lift_state_exists_entails_tla_exists(
         |s: ClusterState| {
             &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
             &&& num_diff_pods_is(vrs, diff)(s)
-        }
-    ).entails(
-        tla_exists(
-            |resp_msg: Message| lift_state(
-                |s: ClusterState| {
-                    &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
-                    &&& num_diff_pods_is(vrs, diff)(s)
-                }
-            )
-        )
-    ));
+        },
+        |resp_msg: Message| |s: ClusterState| {
+            &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
 }
 
 pub proof fn lemma_pending_create_req_entails_concrete_create_req(
@@ -4907,21 +4902,16 @@
         assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
         assert(num_diff_pods_is(vrs, diff)(s));
     };
-    assert(lift_state(
+    lemma_lift_state_exists_entails_tla_exists(
         |s: ClusterState| {
             &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
             &&& num_diff_pods_is(vrs, diff)(s)
-        }
-    ).entails(
-        tla_exists(
-            |req_msg: Message| lift_state(
-                |s: ClusterState| {
-                    &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
-                    &&& num_diff_pods_is(vrs, diff)(s)
-                }
-            )
-        )
-    ));
+        },
+        |req_msg: Message| |s: ClusterState| {
+            &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
 }
 
 // File: controllers/vreplicaset_controller/proof/liveness/resource_match.rs

```

## Source change event 110

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -2879,7 +2879,7 @@
     state_pred: StatePred<T>,
     a_to_state_pred: spec_fn(A) -> StatePred<T>
 )
-    requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| a_to_state_pred(a)(s),
+    requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| #[trigger] a_to_state_pred(a)(s),
     ensures lift_state(state_pred).entails(tla_exists(|a: A| lift_state(a_to_state_pred(a)))),
 {
     assert forall |ex: Execution<T>|

```

## Source change event 117

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -2891,6 +2891,9 @@
         let a = choose |a: A| #[trigger] a_to_state_pred(a)(s);
         assert(a_to_state_pred(a)(s));
         assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
+        assert(exists |a: A| lift_state(a_to_state_pred(a)).satisfied_by(ex)) by {
+            assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
+        };
         assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));
     };
 }

```

## Source change event 124

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -2891,7 +2891,7 @@
         let a = choose |a: A| #[trigger] a_to_state_pred(a)(s);
         assert(a_to_state_pred(a)(s));
         assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
-        assert(exists |a: A| lift_state(a_to_state_pred(a)).satisfied_by(ex)) by {
+        assert(exists |a: A| #[trigger] lift_state(a_to_state_pred(a)).satisfied_by(ex)) by {
             assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
         };
         assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));

```

## Source change event 131

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -2882,19 +2882,20 @@
     requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| #[trigger] a_to_state_pred(a)(s),
     ensures lift_state(state_pred).entails(tla_exists(|a: A| lift_state(a_to_state_pred(a)))),
 {
+    let a_to_temp_pred = |a: A| lift_state(a_to_state_pred(a));
     assert forall |ex: Execution<T>|
         #[trigger] lift_state(state_pred).satisfied_by(ex)
-        implies tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex)
+        implies tla_exists(a_to_temp_pred).satisfied_by(ex)
     by {
         let s = ex.head();
         assert(state_pred(s));
         let a = choose |a: A| #[trigger] a_to_state_pred(a)(s);
         assert(a_to_state_pred(a)(s));
-        assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
-        assert(exists |a: A| #[trigger] lift_state(a_to_state_pred(a)).satisfied_by(ex)) by {
-            assert(lift_state(a_to_state_pred(a)).satisfied_by(ex));
+        assert(a_to_temp_pred(a).satisfied_by(ex));
+        assert(exists |a: A| #[trigger] a_to_temp_pred(a).satisfied_by(ex)) by {
+            assert(a_to_temp_pred(a).satisfied_by(ex));
         };
-        assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));
+        assert(tla_exists(a_to_temp_pred).satisfied_by(ex));
     };
 }
 

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

### Event 61 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4828 |     assert forall |ex: Execution<ClusterState>|
     |     ^^^^^^
warning: using ==> in `assert forall` does not currently assume the antecedent in the body; consider using `implies` instead of `==>`
4889 |     assert forall |ex: Execution<ClusterState>|
     |     ^^^^^^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
4828 |     assert forall |ex: Execution<ClusterState>|
     |     ^^^^^^
error: aborting due to 1 previous error; 3 warnings emitted
```

### Event 71 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: triggers cannot contain let/forall/exists/lambda/choose
4830 | /             |s: ClusterState| {
4831 | |                 &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4832 | |                 &&& num_diff_pods_is(vrs, diff)(s)
4833 | |             }
     | |_____________^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 78 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
error: expected `by`
4829 |         #[trigger] exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s),
     |                                                                                        ^
error: aborting due to 1 previous error
```

### Event 91 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: assertion failed
4842 |       assert(lift_state(
     |  ____________^
4843 | |         |s: ClusterState| {
4844 | |             &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4845 | |             &&& num_diff_pods_is(vrs, diff)(s)
4856 | |     ));
     | |_____^ assertion failed
error: assertion failed
4890 |       assert(lift_state(
     |  ____________^
4891 | |         |s: ClusterState| {
4892 | |             &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
4893 | |             &&& num_diff_pods_is(vrs, diff)(s)
4904 | |     ));
     | |_____^ assertion failed
4836 |           let resp_msg = choose |resp_msg| s.in_flight().contains(resp_msg)
     |  ________________________^
4837 | |             && resp_msg_matches_req_msg(resp_msg, msg)
4838 | |             && resp_msg_is_ok_list_resp_containing_matching_p
```

### Event 105 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
2882 |     requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| a_to_state_pred(a)(s),
     |                                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 112 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: assertion failed
2894 |         assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));
     |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4828 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4829 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4830 | | )
     | |_^
error: postcondition not satisfied
4828 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4829 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4830 | | )
     | |_- at the end of the function body
4831 |       ensures
4832 | /         lift_state(
4833 | |             |s: ClusterState| {
4834 | |                 &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4835 | |                 &&& num_diff_pods_is(vrs, diff)(s)
4846 | |         ),
     |
```

### Event 119 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: Could not automatically infer triggers for this quantifer.  Use #[trigger] annotations to manually mark trigger terms instead.
2894 |         assert(exists |a: A| lift_state(a_to_state_pred(a)).satisfied_by(ex)) by {
     |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
error: aborting due to 1 previous error; 1 warning emitted
```

### Event 126 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: assertion failed
2897 |         assert(tla_exists(|a: A| lift_state(a_to_state_pred(a))).satisfied_by(ex));
     |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ assertion failed
4831 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4832 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4833 | | )
     | |_^
error: postcondition not satisfied
4831 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4832 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4833 | | )
     | |_- at the end of the function body
4834 |       ensures
4835 | /         lift_state(
4836 | |             |s: ClusterState| {
4837 | |                 &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4838 | |                 &&& num_diff_pods_is(vrs, diff)(s)
4849 | |         ),
     |
```

### Event 133 (exit 1)

```text
/bin/bash -lc './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
4832 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4833 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4834 | | )
     | |_^
error: postcondition not satisfied
4832 | / pub proof fn lemma_list_resp_exists_entails_concrete_list_resp(
4833 | |     vrs: VReplicaSetView, controller_id: int, diff: int
4834 | | )
     | |_- at the end of the function body
4835 |       ensures
4836 | /         lift_state(
4837 | |             |s: ClusterState| {
4838 | |                 &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
4839 | |                 &&& num_diff_pods_is(vrs, diff)(s)
4850 | |         ),
     | |_________^ failed this postcondition
error: precondition not satisfied
2882 |       requires forall |s: T| #[trigger] state_pred(s) ==> exists |a: A| #[trigger] a_to_state_pred(a)(s),
     |                -------------
```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
