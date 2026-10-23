from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from evaluate_structural_skeleton_hard import (
    ARMS, AUTHORIZATION, CASES, deadline_audit, expected_prompt, recognized_checks, schedule,
)
from skill_evolution_pilot.codex_runner import build_prompt, run_codex_smoke


def test_authorized_matrix_and_p0_has_no_empty_supplement(tmp_path):
    jobs = schedule(tmp_path)
    assert len(jobs) == AUTHORIZATION["episodes"] == 18
    assert {(job["id"], job["condition"], job["repeat"]) for job in jobs} == {
        (case["task"], arm, repeat) for case in CASES for arm in ARMS for repeat in range(2)}
    assert AUTHORIZATION["budget_usd"] == 10
    for job in jobs:
        assert ("knowledge_path" not in job) == (job["condition"] == "p0")
        if job["condition"] != "p0":
            assert Path(job["knowledge_path"]).is_relative_to(tmp_path / "packets")
    for arm in ("p1", "p2"):
        paths = [job["knowledge_path"] for job in jobs if job["condition"] == arm and job["repeat"] == 0]
        assert paths[0] == paths[1] and paths[0] != paths[2]


@pytest.mark.parametrize("command,output,code,expected", [
    ("/bin/bash -lc './tools/run_verus.sh candidate.rs'", "verification results:: 1 verified, 0 errors", 0, {"verus"}),
    ("/bin/bash -lc ./tools/run_lynette.sh", "", 0, {"lynette"}),
    ("./tools/run_verus.sh candidate.rs && ./tools/run_lynette.sh", "verification results:: 2 verified, 0 errors", 0, {"verus", "lynette"}),
    ("./tools/run_lynette.sh | tail -10", "", 0, set()),
    ("./tools/run_lynette.sh; echo exit=0", "exit=0", 0, set()),
    ("./tools/run_lynette.sh", "Files are different", 0, set()),
    ("./tools/run_verus.sh candidate.rs", "verification results:: 1 verified, 0 errors", 1, set()),
    ("cat tools/run_verus.sh", "verification results:: 1 verified, 0 errors", 0, set()),
])
def test_deadline_parser_does_not_trust_masked_exit(command, output, code, expected):
    assert recognized_checks(command, output, code) == expected


def write_events(tmp_path, entries):
    started = datetime(2026, 10, 19, tzinfo=timezone.utc)
    (tmp_path / "result.json").write_text(json.dumps({"started_at": started.isoformat()}))
    events = []
    for position, (seconds, candidate, tool) in enumerate(entries):
        command = "./tools/run_verus.sh candidate.rs" if tool == "verus" else "./tools/run_lynette.sh"
        for event_type, offset in (("item.started", -1), ("item.completed", 0)):
            events.append({"timestamp": (started + timedelta(seconds=seconds + offset)).isoformat(),
                "candidate_sha256": candidate, "data": {"raw_codex_event": {"type": event_type,
                    "item": {"id": str(position), "type": "command_execution", "command": command,
                             "aggregated_output": "verification results:: 1 verified, 0 errors" if tool == "verus" else "",
                             "exit_code": 0}}}})
    (tmp_path / "agent_events.jsonl").write_text("\n".join(map(json.dumps, events)))
    return events


@pytest.mark.parametrize("entries,first", [
    ([(100, "hash1", "verus"), (200, "hash1", "lynette")], 200),
    ([(100, "hash1", "lynette"), (200, "hash1", "verus")], 200),
    ([(100, "hash1", "verus"), (200, "hash2", "lynette")], None),
    ([(599, "hash1", "verus"), (601, "hash1", "lynette")], None),
    ([(599, "hash1", "verus"), (600, "hash1", "lynette")], 600),
])
def test_deadline_audit_checks_same_hash_and_completion_time(tmp_path, entries, first):
    write_events(tmp_path, entries)
    result = deadline_audit(tmp_path)
    assert result["first_confirmed_dual_seconds"] == first
    assert result["observed_dual_within_deadline"] == (first is not None)


def test_changed_during_check_is_not_certified(tmp_path):
    events = write_events(tmp_path, [(100, "hash1", "verus"), (200, "hash1", "lynette")])
    events[0]["candidate_sha256"] = "different"
    (tmp_path / "agent_events.jsonl").write_text("\n".join(map(json.dumps, events)))
    assert not deadline_audit(tmp_path)["observed_dual_within_deadline"]


@pytest.mark.parametrize("family", ["temporal-transfer", "semantic-equality"])
@pytest.mark.parametrize("arm", ARMS)
def test_all_arms_reach_actual_prompt_with_p0_no_supplement(tmp_path, monkeypatch, family, arm):
    monkeypatch.setenv("VERUS_SKILL_RUN_ROOT", str(tmp_path))
    source = tmp_path / "input.rs"
    source.write_text("fn main() {}\n")
    (tmp_path / "TASK.md").write_text(build_prompt())
    job = {"condition": arm}
    supplement = None
    if arm != "p0":
        path = tmp_path / "packets" / family / (arm + ".md")
        path.parent.mkdir(parents=True)
        supplement = "## Supplemental proof knowledge\n" + family + " / " + arm
        path.write_text(supplement)
        job["knowledge_path"] = str(path)
    codex = tmp_path / "codex"
    codex.write_text('''#!/usr/bin/python3
import json,sys
from pathlib import Path
if '--version' in sys.argv:
    print('codex-cli fake')
    raise SystemExit(0)
workspace=Path(sys.argv[sys.argv.index('-C')+1])
prompt=sys.stdin.read() if sys.argv[-1]=='-' else sys.argv[-1]
(workspace/'received_prompt.txt').write_text(prompt)
Path(sys.argv[sys.argv.index('--output-last-message')+1]).write_text('done')
print(json.dumps({'type':'thread.started','thread_id':'structural-test'}))
print(json.dumps({'type':'turn.started'}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))
''')
    verus = tmp_path / "verus"
    verus.write_text("#!/bin/sh\necho 'verification results:: 1 verified, 0 errors'\n")
    lynette = tmp_path / "lynette"
    lynette.write_text("#!/bin/sh\nexit 0\n")
    for tool in (codex, verus, lynette):
        tool.chmod(0o755)
    output = tmp_path / "episode"
    run_codex_smoke(source=source, out_dir=output, codex_bin=codex, verus_bin=verus,
                   lynette_bin=lynette, timeout_seconds=30, supplemental_prompt=supplement,
                   skill_text="Same Executive for every arm")
    assert (output / "prompt.txt").read_text() == expected_prompt(tmp_path, job)
    assert (output / "workspace/received_prompt.txt").read_text() == expected_prompt(tmp_path, job)
