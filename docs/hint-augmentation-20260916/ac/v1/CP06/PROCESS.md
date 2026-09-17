# CP6 selected source and validation evidence

This is a reviewed extract, not the full actor conversation. Event numbers match the audit. Host paths are redacted; proof diffs are preserved.

## Source change event 31

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

## Recorded checks

### Event 22 (exit 1)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
error: cannot find attribute `auto` in this scope
4999 |                 #![auto]
     |                    ^^^^
error: cannot find attribute `auto` in this scope
5029 |                 #![auto]
     |                    ^^^^
error: aborting due to 2 previous errors; 1 warning emitted
```

### Event 33 (exit 0)

```text
/bin/bash -c './tools/run_verus.sh candidate.rs'
331 | / #[is_variant]
332 | | pub enum BuiltinControllersStep {
333 | |     RunGarbageCollector,
334 | | }
    | |_^
4998 |               let resp_msg = choose |resp_msg: Message| {
     |  ____________________________^
4999 | |                 &&& s.in_flight().contains(resp_msg)
5000 | |                 &&& resp_msg_matches_req_msg(resp_msg, s.ongoing_reconciles(controller_id)[vrs.object_ref()].pending_req_msg->0)
5001 | |                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
5002 | |             };
     | |_____________^
5001 |                 &&& resp_msg_is_ok_list_resp_containing_matching_pods(s, vrs, resp_msg)
     |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
5027 |               let req_msg = choose |req_msg: Message| {
     |  ___________________________^
5028 | |                 &&& s.in_flight().contains(req_msg)
5029 | |                 &&& Cluster::pending_req_msg_is(controller_id, s, vrs.object
```

### Event 38 (exit 0)

```text
/bin/bash -c ./tools/run_lynette.sh

```

Diagnostic snippets above were capped by the audit collector. The [final host validation](result.json) retains complete final diagnostics.
