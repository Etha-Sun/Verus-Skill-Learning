from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "trace2skill-verusage" / "src"))

from trace2skill_verusage.producer import (
    EXCLUDED_EXPERIMENT_PATHS,
    OFFICIAL_NEUTRAL_SEED_SHA256,
    OFFICIAL_RECORDS_SHA256,
    SOURCE_SNAPSHOT_COMMIT,
    SOURCE_SNAPSHOT_PATH,
    VERUS_RUNTIME_TREE_SHA256,
    build_runtime_command,
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
    snapshot = json.loads(
        (WORKSTREAM / "vendor" / "SNAPSHOT.json").read_text(encoding="utf-8")
    )
    runtime = provenance["integrated_producer_runtime"]
    assert runtime["source_snapshot_commit"] == SOURCE_SNAPSHOT_COMMIT
    assert runtime["source_snapshot_path"] == SOURCE_SNAPSHOT_PATH
    assert runtime["runtime_tree_sha256"] == VERUS_RUNTIME_TREE_SHA256
    assert snapshot["source_repository_commit"] == SOURCE_SNAPSHOT_COMMIT
    assert snapshot["source_path"] == SOURCE_SNAPSHOT_PATH
    assert snapshot["integrated_runtime_tree_sha256"] == VERUS_RUNTIME_TREE_SHA256
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


def test_runtime_command_has_native_global_contract_and_no_secret(
    tmp_path: Path,
) -> None:
    command = build_runtime_command(
        runtime_root=tmp_path / "runtime",
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


def test_model_free_preflight_verifies_vendored_runtime(tmp_path: Path) -> None:
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
        runtime_root=WORKSTREAM / "vendor" / "trace2skill_verus",
        seed_dir=WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
        validator=WORKSTREAM / "tools" / "quick_validate.py",
        expected_records_sha256=digest,
        model="deepseek-v4-pro",
        base_url=None,
        api_key_env="TEST_TRACE2SKILL_API_KEY",
    )
    assert check["status"] == "ok"
    assert check["network_requests"] == 0
    assert check["runtime"]["source_snapshot_commit"] == SOURCE_SNAPSHOT_COMMIT
    assert check["runtime"]["runtime_tree_sha256"] == VERUS_RUNTIME_TREE_SHA256
    assert check["configuration"]["api_key_configured"] is False


def test_model_free_execute_writes_external_manifest_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [record("error", "error-1"), record("success", "success-1")]
    run_dir = tmp_path / "runs" / "candidate"
    secret = "producer-secret-must-not-be-recorded"
    monkeypatch.setenv("TEST_TRACE2SKILL_API_KEY", secret)

    validator_path = WORKSTREAM / "tools" / "quick_validate.py"
    original_run = subprocess.run

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        stdout: object = None,
        stderr: object = None,
        check: bool = False,
        text: bool = True,
        capture_output: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if len(command) > 1 and Path(command[1]).resolve() == validator_path.resolve():
            return original_run(
                command,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
            )
        assert cwd == run_dir
        assert env is not None
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
        runtime_root=WORKSTREAM / "vendor" / "trace2skill_verus",
        seed_dir=WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
        validator=WORKSTREAM / "tools" / "quick_validate.py",
        model="deepseek-v4-pro",
        base_url="https://example.invalid/v1",
        api_key_env="TEST_TRACE2SKILL_API_KEY",
    )
    stored = (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    assert manifest["status"] == "complete"
    assert manifest["final_validation"]["status"] == "passed"
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


def test_vendored_runtime_is_pinned_and_excludes_custom_semantic_reduce() -> None:
    runtime = WORKSTREAM / "vendor" / "trace2skill_verus"
    assert hash_skill_tree(runtime) == VERUS_RUNTIME_TREE_SHA256
    for relative in EXCLUDED_EXPERIMENT_PATHS:
        assert not (runtime / relative).exists()
    combined_runner = (
        runtime / "skill_evolver" / "run_parallel_combined_skill_evolution.py"
    ).read_text(encoding="utf-8")
    assert "SemanticReduceParallelSkillEvolver" not in combined_runner
    assert "--reduce-strategy" not in combined_runner


def test_vendored_native_combined_cli_imports_without_external_checkout() -> None:
    runtime = WORKSTREAM / "vendor" / "trace2skill_verus"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(runtime)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill_evolver.run_parallel_combined_skill_evolution",
            "--help",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--error-json" in result.stdout
    assert "--success-json" in result.stdout
    assert "--reduce-strategy" not in result.stdout


def test_execute_marks_invalid_final_skill_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [record("error", "error-1"), record("success", "success-1")]
    run_dir = tmp_path / "runs" / "invalid-candidate"
    validator_path = WORKSTREAM / "tools" / "quick_validate.py"
    original_run = subprocess.run
    monkeypatch.setenv("TEST_TRACE2SKILL_API_KEY", "test-secret")

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        stdout: object = None,
        stderr: object = None,
        check: bool = False,
        text: bool = True,
        capture_output: bool = False,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if len(command) > 1 and Path(command[1]).resolve() == validator_path.resolve():
            return original_run(
                command,
                check=check,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
            )
        final = run_dir / "final_skill" / "verus-proof-repair"
        final.mkdir()
        (final / "SKILL.md").write_text("# Missing frontmatter\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    import trace2skill_verusage.producer as producer_module

    monkeypatch.setattr(producer_module.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="invalid final skill"):
        execute(
            records=rows,
            check={
                "schema_version": "trace2skill-verus-producer-v1",
                "status": "ok",
                "records": {
                    "path": str(tmp_path / "source.json"),
                    "sha256": "b" * 64,
                    "record_count": 2,
                    "error_record_count": 1,
                    "success_record_count": 1,
                    "item_count": 2,
                },
                "runtime": {},
                "configuration": {},
            },
            output_dir=run_dir,
            runtime_root=WORKSTREAM / "vendor" / "trace2skill_verus",
            seed_dir=WORKSTREAM / "producer" / "neutral-seed" / "verus-proof-repair",
            validator=validator_path,
            model="deepseek-v4-pro",
            base_url="https://example.invalid/v1",
            api_key_env="TEST_TRACE2SKILL_API_KEY",
        )

    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["returncode"] == 0
    assert manifest["final_validation"]["status"] == "failed"
    assert manifest["final_validation"]["returncode"] == 1
    assert "final_skill" not in manifest


def test_vendored_license_and_modification_notices_are_complete() -> None:
    vendor = WORKSTREAM / "vendor"
    license_text = (vendor / "LICENSE").read_text(encoding="utf-8")
    notices = (vendor / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    snapshot = json.loads((vendor / "SNAPSHOT.json").read_text(encoding="utf-8"))

    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text
    assert snapshot["license_file"] == "LICENSE"
    assert snapshot["third_party_notices"] == "THIRD_PARTY_NOTICES.md"
    assert "Qwen-Applications/Trace2Skill" in notices
    assert "3d0b52a140f002a512930252b613c49048f7d5ac" in notices

    modified_python = [
        "__init__.py",
        "model_clients.py",
        "parallel_evolving_agent.py",
        "parallel_success_evolving_agent.py",
        "run_parallel_combined_skill_evolution.py",
        "run_parallel_skill_evolution.py",
        "skill_evolving_agent.py",
    ]
    source_root = vendor / "trace2skill_verus" / "skill_evolver"
    for relative_path in modified_python:
        text = (source_root / relative_path).read_text(encoding="utf-8")
        assert "Modified for Verus-Skill-Learning in 2026" in text
        assert relative_path in notices
