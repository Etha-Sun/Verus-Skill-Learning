"""Recover idle native DeepScientist turns; never dispatch experiments directly."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import runpy
import time
import urllib.error
import urllib.request


def recovery_reason(snapshot, completed_at, idle_seconds, live_controller):
    if snapshot.get("status") in {"paused", "stopped", "completed", "error", "waiting_for_user"}:
        return None
    if snapshot.get("continuation_policy") in {"none", "wait_for_user_or_resume"}:
        return None
    if live_controller or idle_seconds < 300:
        return None
    if snapshot.get("active_run_id"):
        return "completed_turn_still_active" if completed_at else None
    return "native_continuation_idle"


def controller_alive(quest_root):
    # Run outside a process namespace sandbox: hidden /proc gives false negatives.
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = (proc / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if b"exec" in argv and any(b"codex" in a for a in argv[:3]):
            if any(str(quest_root).encode() in a for a in argv):
                return True
    return False


def api(url, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url + path, data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def check(home, quest_id, url, state_dir, last_recovery):
    quest = home / "quests" / quest_id
    endpoint = "/api/quests/" + quest_id
    try:
        snapshot = api(url, endpoint)
    except urllib.error.HTTPError as error:
        if error.code != 500:
            raise
        # The quest's raw array artifacts remain unchanged; repair only its cache.
        runpy.run_path(str(quest / "scripts/repair_artifact_projection.py"))
        snapshot = api(url, endpoint)
    now = time.time()
    run_id = snapshot.get("active_run_id")
    result = quest / ".ds/runs" / str(run_id) / "result.json"
    completed_at = None
    if run_id and result.exists():
        completed_at = json.loads(result.read_text()).get("completed_at")
    activity = [quest / ".ds/runtime_state.json"]
    if run_id:
        activity.extend([result, result.parent / "stdout.jsonl"])
    last_activity = max(p.stat().st_mtime for p in activity if p.exists())
    live = controller_alive(quest)
    idle = now - last_activity
    reason = recovery_reason(snapshot, completed_at, idle, live)
    state = {"checked_at_unix": now, "quest_id": quest_id,
             "active_run_id": run_id, "live_controller": live,
             "completed_at": completed_at, "idle_seconds": idle,
             "continuation_policy": snapshot.get("continuation_policy"),
             "recovery_reason": reason, "last_recovery_unix": last_recovery}
    if reason and now - last_recovery >= 600:
        # Framework reconciliation owns scheduling and avoids starting a duplicate.
        response = api(url, endpoint + "/control",
                       {"action": "resume", "source": "local:lifecycle-guardian"})
        if not response.get("ok"):
            raise RuntimeError("Native resume was rejected: " + str(response.get("message")))
        last_recovery = now
        state["last_recovery_unix"] = now
        state["native_resume_ok"] = True
        with (state_dir / "recoveries.jsonl").open("a") as stream:
            stream.write(json.dumps(state) + "\n")
    temporary = state_dir / "state.tmp"
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(state_dir / "state.json")
    return last_recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--quest-id", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:21001")
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    lock = (args.state_dir / "guardian.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.write(str(os.getpid()))
    lock.flush()
    state = args.state_dir / "state.json"
    last_recovery = json.loads(state.read_text()).get("last_recovery_unix", 0) if state.exists() else 0
    while True:
        try:
            last_recovery = check(args.home, args.quest_id, args.url, args.state_dir, last_recovery)
        except Exception as error:
            with (args.state_dir / "errors.jsonl").open("a") as stream:
                stream.write(json.dumps({"at_unix": time.time(), "error": str(error)}) + "\n")
            if args.once:
                raise
        if args.once:
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
