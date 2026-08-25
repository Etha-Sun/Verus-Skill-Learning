from pathlib import Path

import pytest

from skill_evolution_pilot.actor_isolation import (
    ActorIsolationConfig,
    build_isolated_actor_command,
)


def test_isolation_command_records_namespace_and_forbidden_paths(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    workspace = scratch / "runs" / "task" / "workspace"
    verus_root = tmp_path / "verus"
    rust_root = tmp_path / "rust"
    for path in (workspace, verus_root, rust_root):
        path.mkdir(parents=True)
    codex = tmp_path / "codex"
    lynette = tmp_path / "lynette"
    for path in (codex, lynette):
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)
    config = ActorIsolationConfig(
        scratch_root=scratch,
        verus_root=verus_root,
        rust_root=rust_root,
        bridge_port=18080,
        forbidden_paths=(scratch / "repository",),
    )
    command = build_isolated_actor_command(
        [str(codex), "exec"],
        workspace=workspace,
        codex_bin=codex,
        lynette_bin=lynette,
        config=config,
    )
    assert command[:6] == [
        "/usr/bin/unshare",
        "--user",
        "--map-root-user",
        "--mount",
        "--fork",
        "--kill-child=SIGKILL",
    ]
    assert command[-2:] == [str(codex), "exec"]
    assert "--forbidden-path" in command
    assert config.manifest()["mode"] == "trace2skill-linux-mount-network-seccomp-v1"


def test_isolation_rejects_workspace_outside_scratch(tmp_path: Path) -> None:
    tool = tmp_path / "tool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(0o755)
    config = ActorIsolationConfig(
        scratch_root=tmp_path / "scratch",
        verus_root=tmp_path,
        rust_root=tmp_path,
        bridge_port=18080,
    )
    with pytest.raises(ValueError, match="strict child"):
        build_isolated_actor_command(
            [str(tool)],
            workspace=tmp_path / "outside",
            codex_bin=tool,
            lynette_bin=tool,
            config=config,
        )


def test_isolation_rejects_a_broad_tool_root(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    workspace = scratch / "workspace"
    workspace.mkdir(parents=True)
    tool = tmp_path / "tool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(0o755)
    config = ActorIsolationConfig(
        scratch_root=scratch,
        verus_root=scratch,
        rust_root=tmp_path,
        bridge_port=18080,
    )
    with pytest.raises(ValueError, match="too broad"):
        build_isolated_actor_command(
            [str(tool)],
            workspace=workspace,
            codex_bin=tool,
            lynette_bin=tool,
            config=config,
        )


def test_isolation_rejects_tool_root_that_contains_scratch(tmp_path: Path) -> None:
    scratch = tmp_path / "shared" / "scratch"
    workspace = scratch / "workspace"
    workspace.mkdir(parents=True)
    rust_root = tmp_path / "rust"
    rust_root.mkdir()
    tool = tmp_path / "tool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(0o755)
    config = ActorIsolationConfig(
        scratch_root=scratch,
        verus_root=tmp_path / "shared",
        rust_root=rust_root,
        bridge_port=18080,
    )
    with pytest.raises(ValueError, match="too broad"):
        build_isolated_actor_command(
            [str(tool)],
            workspace=workspace,
            codex_bin=tool,
            lynette_bin=tool,
            config=config,
        )


def test_isolation_rejects_actor_home_as_tool_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor_home = tmp_path / "home" / "actor"
    actor_home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(actor_home))
    scratch = tmp_path / "scratch"
    workspace = scratch / "workspace"
    workspace.mkdir(parents=True)
    rust_root = tmp_path / "rust"
    rust_root.mkdir()
    tool = tmp_path / "tool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(0o755)
    config = ActorIsolationConfig(
        scratch_root=scratch,
        verus_root=actor_home,
        rust_root=rust_root,
        bridge_port=18080,
    )
    with pytest.raises(ValueError, match="too broad"):
        build_isolated_actor_command(
            [str(tool)],
            workspace=workspace,
            codex_bin=tool,
            lynette_bin=tool,
            config=config,
        )
