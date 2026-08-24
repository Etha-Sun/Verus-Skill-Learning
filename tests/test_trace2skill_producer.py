from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "trace2skill-verusage" / "src"))

from trace2skill_verusage.producer import (
    OFFICIAL_NEUTRAL_SEED_SHA256,
    OFFICIAL_RECORDS_SHA256,
    PATCHED_TREE_ID,
    UPSTREAM_COMMIT,
    build_upstream_command,
    execute,
    hash_skill_tree,
    load_records,
    preflight,
    require_output_below_run_root,
)


WORKSTREAM = REPO_ROOT / "trace2skill-verusage"
PROVENANCE = (
    WORKSTREAM
    / "baselines"
    / "native-official-20260819"
    / "PROVENANCE.json"
)


def record(source: str, instance_id: str) -> dict[str, object]:
    return {
        "record_source": source,
        "instance_id": instance_id,
        "source_file": "trajectory.log",
        "items": [
            {
                "type": "success_memory" if source == "success" else "failure_memory",
                "number": 1,
                "title": "Reusable pattern",
                "description": "A grounded pattern.",
                "content": "Apply the grounded proof step.",
            }
        ],
    }


def write_records(path: Path, rows: list[dict[str, object]]) -> str:
    raw = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_producer_constants_match_published_provenance() -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    assert provenance["upstream_trace2skill_commit"] == UPSTREAM_COMMIT
    assert provenance["construction_input"]["records_sha256"] == OFFICIAL_RECORDS_SHA256
    assert (
        provenance["construction_input"]["neutral_seed_sha256"]
        == OFFICIAL_NEUTRAL_SEED_SHA256
    )


def test_neutral_seed_matches_published_tree_hash() -> None:
    seed = WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair"
    assert hash_skill_tree(seed) == OFFICIAL_NEUTRAL_SEED_SHA256


def test_load_records_validates_schema_hash_and_counts(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    digest = write_records(path, [record("error", "a"), record("success", "b")])
    rows, manifest = load_records(path, expected_sha256=digest)
    assert len(rows) == 2
    assert manifest["error_record_count"] == 1
    assert manifest["success_record_count"] == 1
    assert manifest["item_count"] == 2

    with pytest.raises(ValueError, match="records hash mismatch"):
        load_records(path, expected_sha256="0" * 64)


def test_load_records_rejects_duplicate_instances(tmp_path: Path) -> None:
    path = tmp_path / "records.json"
    write_records(path, [record("error", "same"), record("success", "same")])
    with pytest.raises(ValueError, match="must be unique"):
        load_records(path)


def test_output_must_stay_below_run_root(tmp_path: Path) -> None:
    run_root = tmp_path / "runs"
    assert require_output_below_run_root(run_root / "candidate", run_root) == (
        run_root / "candidate"
    ).resolve()
    with pytest.raises(ValueError, match="must be below"):
        require_output_below_run_root(tmp_path / "outside", run_root)


def test_upstream_command_has_native_official_contract_and_no_secret(
    tmp_path: Path,
) -> None:
    command = build_upstream_command(
        upstream_root=tmp_path / "upstream",
        error_json=tmp_path / "error.json",
        success_json=tmp_path / "success.json",
        working_skill=tmp_path / "working",
        output_skill=tmp_path / "final",
        run_dir=tmp_path / "run",
        model="deepseek-v4-pro",
    )
    joined = " ".join(command)
    assert "skill_evolver.run_parallel_combined_skill_evolution" in command
    assert "--batch-size 1" in joined
    assert "--merge-batch-size 5" in joined
    assert "--max-workers 4" in joined
    assert "--max-merge-levels 5" in joined
    assert "--patch-pipeline json" in joined
    assert "--api-key" not in command


def test_model_free_preflight_verifies_bootstrapped_runtime(tmp_path: Path) -> None:
    records_path = tmp_path / "records.json"
    digest = write_records(
        records_path,
        [record("error", "error-1"), record("success", "success-1")],
    )
    run_root = tmp_path / "runs"
    _, check = preflight(
        records_path=records_path,
        output_dir=run_root / "candidate",
        run_root=run_root,
        upstream_root=WORKSTREAM / "Trace2Skill",
        seed_dir=WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
        validator=WORKSTREAM / "tools" / "quick_validate.py",
        expected_records_sha256=digest,
        model="deepseek-v4-pro",
        base_url=None,
        api_key_env="TEST_TRACE2SKILL_API_KEY",
    )
    assert check["status"] == "ok"
    assert check["network_requests"] == 0
    assert check["runtime"]["upstream_commit"] == UPSTREAM_COMMIT
    assert check["runtime"]["patched_tree_id"] == PATCHED_TREE_ID
    assert check["configuration"]["api_key_configured"] is False


def test_model_free_execute_writes_external_manifest_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [record("error", "error-1"), record("success", "success-1")]
    run_dir = tmp_path / "runs" / "candidate"
    secret = "producer-secret-must-not-be-recorded"
    monkeypatch.setenv("TEST_TRACE2SKILL_API_KEY", secret)

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        stdout: object,
        stderr: object,
        check: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == run_dir
        assert env["OPENAI_API_KEY"] == secret
        assert secret not in " ".join(command)
        working = run_dir / "working_skill" / "verus-proof-repair"
        final = run_dir / "final_skill" / "verus-proof-repair"
        shutil.copytree(working, final)
        return subprocess.CompletedProcess(command, 0)

    import shutil
    import trace2skill_verusage.producer as producer_module

    monkeypatch.setattr(producer_module.subprocess, "run", fake_run)
    manifest = execute(
        records=rows,
        check={
            "schema_version": "trace2skill-verus-producer-v1",
            "status": "ok",
            "records": {
                "path": str(tmp_path / "source.json"),
                "sha256": "a" * 64,
                "record_count": 2,
                "error_record_count": 1,
                "success_record_count": 1,
                "item_count": 2,
            },
            "runtime": {},
            "configuration": {},
        },
        output_dir=run_dir,
        upstream_root=WORKSTREAM / "Trace2Skill",
        seed_dir=WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
        validator=WORKSTREAM / "tools" / "quick_validate.py",
        model="deepseek-v4-pro",
        base_url="https://example.invalid/v1",
        api_key_env="TEST_TRACE2SKILL_API_KEY",
    )
    stored = (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    assert manifest["status"] == "complete"
    assert secret not in stored
    assert "source.json" not in stored
    assert (run_dir / "inputs" / "error_records.json").is_file()
    assert (run_dir / "inputs" / "success_records.json").is_file()


@pytest.mark.parametrize(
    "skill_dir",
    [
        WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
        WORKSTREAM
        / "baselines"
        / "native-official-20260819"
        / "skill"
        / "verus-proof-repair",
    ],
)
def test_validator_accepts_published_skills(skill_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(WORKSTREAM / "tools" / "quick_validate.py"), str(skill_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Skill is valid" in result.stdout


def test_bootstrap_contract_pins_reviewed_upstream_and_tree() -> None:
    script = (WORKSTREAM / "scripts" / "bootstrap_trace2skill.sh").read_text()
    assert UPSTREAM_COMMIT in script
    assert PATCHED_TREE_ID in script
    assert "git clone --no-checkout" in script
    assert "changes outside the reviewed producer patch" in script
