# Original source changes

Extracted diffs only; full raw conversations remain external.

## Event 74

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4948,7 +4948,57 @@
             )
         ),
 {
-}
-
-
-}
+    let d = (abs(diff) - 1) as nat;
+    let p_resp = |resp_msg: Message| lift_state(
+        |s: ClusterState| {
+            &&& resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
+    let q_mid = lift_state(
+        |s: ClusterState| {
+            &&& pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
+    let p_req = |req_msg: Message| lift_state(
+        |s: ClusterState| {
+            &&& req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
+    let r = lift_state(
+        |s: ClusterState| {
+            &&& exists_ok_resp_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s)
+            &&& num_diff_pods_is(vrs, diff + 1)(s)
+        }
+    );
+    let p = lift_state(
+        |s: ClusterState| {
+            &&& exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s)
+            &&& num_diff_pods_is(vrs, diff)(s)
+        }
+    );
+
+    assert forall |resp_msg: Message| spec.entails(p_resp(resp_msg).leads_to(q_mid)) by {
+        lemma_from_after_receive_list_pods_resp_to_send_create_pod_req(vrs, spec, cluster, controller_id, resp_msg, diff);
+    };
+    leads_to_exists_intro(spec, p_resp, q_mid);
+
+    assert(p.entails(tla_exists(p_resp)));
+    entails_implies_leads_to(spec, p, tla_exists(p_resp));
+    leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
+
+    assert forall |req_msg: Message| spec.entails(p_req(req_msg).leads_to(r)) by {
+        lemma_from_after_send_create_pod_req_to_receive_ok_resp(vrs, spec, cluster, controller_id, req_msg, diff);
+    };
+    leads_to_exists_intro(spec, p_req, r);
+
+    assert(q_mid.entails(tla_exists(p_req)));
+    entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
+    leads_to_trans(spec, p, q_mid, tla_exists(p_req));
+    leads_to_trans(spec, p, tla_exists(p_req), r);
+}
+
+
+}

```

## Event 81

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

## Event 89

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4985,7 +4985,14 @@
     };
     leads_to_exists_intro(spec, p_resp, q_mid);
 
-    assert(p.entails(tla_exists(p_resp)));
+    assert(p.entails(tla_exists(p_resp))) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] p.satisfied_by(ex) ==> tla_exists(p_resp).satisfied_by(ex) by {
+            let s = ex.head();
+            assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            assert(exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+        };
+    };
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
     leads_to_trans(spec, p, tla_exists(p_resp), q_mid);
 
@@ -4994,7 +5001,14 @@
     };
     leads_to_exists_intro(spec, p_req, r);
 
-    assert(q_mid.entails(tla_exists(p_req)));
+    assert(q_mid.entails(tla_exists(p_req))) by {
+        assert forall |ex: Execution<ClusterState>| #[trigger] q_mid.satisfied_by(ex) ==> tla_exists(p_req).satisfied_by(ex) by {
+            let s = ex.head();
+            assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
+            assert(num_diff_pods_is(vrs, diff)(s));
+            assert(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+        };
+    };
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, q_mid, tla_exists(p_req));
     leads_to_trans(spec, p, tla_exists(p_req), r);

```

## Event 97

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

## Event 108

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4990,7 +4990,18 @@
             let s = ex.head();
             assert(exists_resp_in_flight_at_after_list_pods_step(vrs, controller_id)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |resp_msg: Message| resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            assert(exists |resp_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            });
+            let resp_msg = choose |resp_msg: Message| {
+                &&& s.in_flight().contains(resp_msg)
+                &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
+                &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
+            };
+            assert(resp_msg_is_the_in_flight_list_resp_at_after_list_pods_step(vrs, controller_id, resp_msg)(s));
+            assert(p_resp(resp_msg).satisfied_by(ex));
         };
     };
     entails_implies_leads_to(spec, p, tla_exists(p_resp));
@@ -5006,7 +5017,22 @@
             let s = ex.head();
             assert(pending_req_in_flight_at_after_create_pod_step(vrs, controller_id, d)(s));
             assert(num_diff_pods_is(vrs, diff)(s));
-            assert(exists |req_msg: Message| req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+            assert(exists |req_msg: Message| {
+                &&& #[trigger] s.in_flight().contains(req_msg)
+                &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
+                &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())
+                &&& req_msg_is_create_matching_pod_req(vrs, req_msg)
+                &&& at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(d))(s)
+            });
+            let req_msg = choose |req_msg: Message| {
+                &&& s.in_flight().contains(req_msg)
+                &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
+                &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())
+                &&& req_msg_is_create_matching_pod_req(vrs, req_msg)
+                &&& at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(d))(s)
+            };
+            assert(req_msg_is_the_in_flight_create_request_at_after_create_pod_step(vrs, controller_id, req_msg, d)(s));
+            assert(p_req(req_msg).satisfied_by(ex));
         };
     };
     entails_implies_leads_to(spec, q_mid, tla_exists(p_req));

```

## Event 116

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4996,6 +4996,7 @@
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
             });
             let resp_msg = choose |resp_msg: Message| {
+                #![auto]
                 &&& s.in_flight().contains(resp_msg)
                 &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
@@ -5025,6 +5026,7 @@
                 &&& at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(d))(s)
             });
             let req_msg = choose |req_msg: Message| {
+                #![auto]
                 &&& s.in_flight().contains(req_msg)
                 &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
                 &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())

```

## Event 127

```diff
--- previous-candidate.rs
+++ candidate.rs
@@ -4996,7 +4996,6 @@
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
             });
             let resp_msg = choose |resp_msg: Message| {
-                #![auto]
                 &&& s.in_flight().contains(resp_msg)
                 &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
@@ -5026,7 +5025,6 @@
                 &&& at_vrs_step_with_vrs(vrs, controller_id, VReplicaSetRecStepView::AfterCreatePod(d))(s)
             });
             let req_msg = choose |req_msg: Message| {
-                #![auto]
                 &&& s.in_flight().contains(req_msg)
                 &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object_ref(), req_msg)
                 &&& req_msg.src == HostId::Controller(controller_id, vrs.object_ref())

```

