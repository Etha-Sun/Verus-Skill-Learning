from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "skillopt-verusage" / "src"))

from skillopt_verusage.trace2skill import hash_skill_tree


BASELINE_ROOT = (
    REPO_ROOT
    / "trace2skill-verusage"
    / "baselines"
    / "native-official-20260819"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_trace2skill_artifact_matches_provenance() -> None:
    provenance = json.loads((BASELINE_ROOT / "PROVENANCE.json").read_text())
    skill_dir = BASELINE_ROOT / "skill" / "verus-proof-repair"
    files = sorted(path for path in skill_dir.rglob("*") if path.is_file())

    assert not any(path.is_symlink() for path in skill_dir.rglob("*"))
    assert len(files) == provenance["artifact"]["file_count"]
    assert sum(path.stat().st_size for path in files) == provenance["artifact"]["total_bytes"]
    assert sha256(skill_dir / "SKILL.md") == provenance["artifact"]["entry_point_sha256"]
    assert hash_skill_tree(skill_dir) == provenance["artifact"]["skill_tree_sha256"]


def test_frozen_construction_prompts_match_provenance() -> None:
    provenance = json.loads((BASELINE_ROOT / "PROVENANCE.json").read_text())
    config_dir = BASELINE_ROOT / "configuration"
    assert {
        path.name: sha256(path)
        for path in sorted(config_dir.iterdir())
        if path.is_file()
    } == provenance["configuration_sha256"]


def test_launcher_rejects_unknown_provider_without_starting_evaluation() -> None:
    launcher = (
        REPO_ROOT
        / "trace2skill-verusage"
        / "scripts"
        / "run_native_official_fixed_test20.sh"
    )
    result = subprocess.run(
        [str(launcher), "unknown-provider"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unsupported provider" in result.stderr
