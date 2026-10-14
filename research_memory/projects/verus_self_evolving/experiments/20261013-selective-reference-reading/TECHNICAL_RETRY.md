# Authorized single-cell technical retry

## Authorization and evidence

The user reports accidentally killing the process and requests restarting that
task. The authorized cell is B, `dev_old--3f17ea7c76a0ce99c098`, API request
preserves matching pods. Its actor ended after 463.99 seconds with return code
`-9`, before the 600-second limit. Final proof verification failed; the raw
actor events end with stream-disconnection errors. External intervention is
user-reported; the kernel-level cause was not independently established.

This is not authorization to repeat ordinary timeouts, other failures, or the C
cell of this pair. The original record and all charges remain intact.

## Execution

- Original service: `verus-selective-eval-20261013-v1.service`.
- Retry service: `verus-selective-retry-20261013-v1.service`.
- Latest launch check: both active/running; original completed 16/40 episodes;
  retry PID2719262, status `waiting_for_parent`.
- Retry output: `skillopt-verusage/selective-reference-evaluation-20261013-retry-v1/`
  below the external run root.
- Script: `scripts/retry_selective_interruption.py`; six zero-API tests pass.

The persistent server service waits for the original execution lock to be
released. It requires a clean, drained original 40-cell summary and no pending
budget reservations. It then runs one fresh B episode with the original frozen
model, prompt, skill, tools, permissions and 600-second deadline. This deliberately
avoids adding a third simultaneous actor or disturbing the original queue.
The service uses Restart=no and cannot silently repeat its own completed attempt.
If the parent stops abnormally, this safety gate blocks the replacement pending
review. Local PC shutdown does not stop the server service.

The original campaign's shared, file-locked budget guard is reused: USD30 total,
including the interrupted attempt and replacement. No fresh budget is allocated.
Frozen evaluation sources and packages were not modified. No raw/sealed data was
changed. The initial service-management tool call hit an approval-quota error;
the later narrowly scoped launch succeeded and was separately verified.

## Reporting

After the retry finishes and its provider calls drain, `combined/report.json`
and `combined/episodes.csv` select 39 original cells plus this replacement,
regardless of whether the replacement solves the proof. There are 41 actual
attempts but only 40 selected comparison cells; no best-of selection. Combined
budget includes all attempts, while selected-cell token totals exclude the
interrupted attempt. Both ledger hashes and the excluded attempt pointer are
retained in `combined/summary.json`. The original report is not overwritten.

At this check the service is queued, not yet running a paid retry episode.
