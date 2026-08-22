from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from skillopt_verusage.adapter import VeruSAGEAdapter
from skill_evolution_pilot.codex_runner import (
    build_cross_provider_prompt,
    build_prompt,
)
from skill_evolution_pilot.workspace import sha256_file


class CodexDeepSeekAdapter(VeruSAGEAdapter):
    """SkillOpt adapter whose DeepSeek target runs inside the Codex CLI."""

    def __init__(
        self,
        *,
        split_dir: str,
        codex_bin: str,
        verus_bin: str,
        lynette_bin: str,
        bridge_url: str,
        bridge_ledger_path: str,
        bridge_manifest_path: str,
        model: str = "deepseek-v4-flash",
        reasoning_effort: str = "high",
        workers: int = 60,
        analyst_workers: int = 60,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        task_retries: int = 2,
        timeout_retries: int | None = None,
        codex_timeout_seconds: int = 1200,
        max_codex_timeout_seconds: int = 1200,
        model_context_window: int = 262144,
        fail_on_invalid: bool = True,
        seed: int = 42,
        actor_contract_profile: str = "project",
        condition_skill_present: bool = True,
        codex_provider_id: str = "deepseek_bridge",
        run_stage: str = "skillopt_actor_rollout",
        actor_isolation_scratch_root: str | None = None,
        actor_isolation_verus_root: str | None = None,
        actor_isolation_rust_root: str | None = None,
        actor_isolation_forbidden_paths: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            split_dir=split_dir,
            verusage_src_root=".",
            verus_bin=verus_bin,
            lynette_bin=lynette_bin,
            model=model,
            workers=workers,
            analyst_workers=analyst_workers,
            failure_only=failure_only,
            minibatch_size=minibatch_size,
            edit_budget=edit_budget,
            task_retries=task_retries,
            task_timeout_seconds=max_codex_timeout_seconds + 120,
            fail_on_invalid=fail_on_invalid,
            seed=seed,
        )
        self.codex_bin = Path(codex_bin).resolve()
        self.actor_model = model
        self.reasoning_effort = reasoning_effort
        self.bridge_url = bridge_url.rstrip("/")
        self.bridge_ledger_path = Path(bridge_ledger_path).resolve()
        self.bridge_manifest_path = Path(bridge_manifest_path).resolve()
        self.codex_timeout_seconds = int(codex_timeout_seconds)
        self.max_codex_timeout_seconds = int(max_codex_timeout_seconds)
        self.timeout_retries = (
            self.task_retries if timeout_retries is None else int(timeout_retries)
        )
        self.model_context_window = int(model_context_window)
        if actor_contract_profile not in {"project", "cross_provider_20260819"}:
            raise ValueError(
                f"unsupported actor contract profile: {actor_contract_profile}"
            )
        self.actor_contract_profile = actor_contract_profile
        self.condition_skill_present = bool(condition_skill_present)
        self.codex_provider_id = codex_provider_id
        if not run_stage.strip():
            raise ValueError("run_stage must be non-empty")
        self.run_stage = run_stage
        isolation_values = (
            actor_isolation_scratch_root,
            actor_isolation_verus_root,
            actor_isolation_rust_root,
        )
        if any(isolation_values) and not all(isolation_values):
            raise ValueError(
                "actor isolation requires scratch, Verus, and Rust roots"
            )
        self.actor_isolation_scratch_root = (
            str(Path(actor_isolation_scratch_root).resolve())
            if actor_isolation_scratch_root
            else None
        )
        self.actor_isolation_verus_root = (
            str(Path(actor_isolation_verus_root).resolve())
            if actor_isolation_verus_root
            else None
        )
        self.actor_isolation_rust_root = (
            str(Path(actor_isolation_rust_root).resolve())
            if actor_isolation_rust_root
            else None
        )
        self.actor_isolation_forbidden_paths = tuple(
            str(Path(path).resolve()) for path in actor_isolation_forbidden_paths
        )
        self._codex_version = subprocess.run(
            [str(self.codex_bin), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if self._codex_version.returncode != 0:
            raise ValueError(f"Codex CLI is not executable: {self.codex_bin}")
        self._verus_version = subprocess.run(
            [str(self.verus_bin), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if self._verus_version.returncode != 0:
            raise ValueError(f"Verus is not executable: {self.verus_bin}")
        verus_implementation = self.verus_bin.parent / "rust_verify"
        if not verus_implementation.is_file():
            verus_implementation = self.verus_bin
        self._verus_implementation_sha256 = sha256_file(verus_implementation)

    def _actor_isolation_matches(self, manifest: dict[str, Any]) -> bool:
        actual = manifest.get("actor_isolation") or {}
        if not self.actor_isolation_scratch_root:
            return actual.get("requested") is False
        return actual == {
            "requested": True,
            "mode": "trace2skill-linux-mount-network-seccomp-v1",
            "scratch_root": self.actor_isolation_scratch_root,
            "verus_root": self.actor_isolation_verus_root,
            "rust_root": self.actor_isolation_rust_root,
            "bridge_port": urlparse(self.bridge_url).port,
            "forbidden_paths": list(self.actor_isolation_forbidden_paths),
        }

    def _resume_result(
        self,
        task_dir: Path,
        *,
        item: dict[str, Any],
        skill_sha256: str,
        timeout_seconds: int,
    ) -> dict[str, Any] | None:
        result_path = task_dir / "result.json"
        manifest_path = task_dir / "run_manifest.json"
        if not result_path.is_file() or not manifest_path.is_file():
            return None
        result = json.loads(result_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bridge_manifest = json.loads(
            self.bridge_manifest_path.read_text(encoding="utf-8")
        )
        attempt_index = int(result.get("task_attempt_index", 1) or 1)
        task_key = self._task_key(task_dir, attempt_index)
        expected_provider_url = self.bridge_url + f"/tasks/{task_key}/v1"
        tools = manifest.get("tools") or {}
        provider = manifest.get("provider") or {}
        bridge = manifest.get("bridge") or {}
        allowed_timeouts = {
            min(self.max_codex_timeout_seconds, timeout_seconds * attempt)
            for attempt in range(1, self.task_retries + 2)
        }
        if (
            result.get("id") == task_dir.name
            and result.get("actor_model") == self.actor_model
            and result.get("actor_reasoning_effort") == self.reasoning_effort
            and result.get("fidelity") in {
                "V2_TRACE",
                "V1_TRUNCATED",
                "V0_INVALID",
            }
            and manifest.get("source_sha256") == item["source_sha256"]
            and manifest.get("condition_skill_sha256") == skill_sha256
            and manifest.get("prompt_sha256")
            == hashlib.sha256(
                (
                    build_cross_provider_prompt(
                        skill_present=self.condition_skill_present,
                        verus_bin=self.verus_bin,
                        lynette_bin=self.lynette_bin,
                    )
                    if self.actor_contract_profile == "cross_provider_20260819"
                    else build_prompt()
                ).encode("utf-8")
            ).hexdigest()
            and manifest.get("model") == self.actor_model
            and manifest.get("contract_profile") == self.actor_contract_profile
            and manifest.get("condition_skill_present")
            == self.condition_skill_present
            and manifest.get("codex_provider_id") == self.codex_provider_id
            and manifest.get("stage") == self.run_stage
            and manifest.get("timeout_seconds") in allowed_timeouts
            and provider.get("base_url") == expected_provider_url
            and provider.get("wire_api") == "responses"
            and provider.get("model_context_window") == self.model_context_window
            and tools.get("codex", {}).get("sha256") == sha256_file(self.codex_bin)
            and tools.get("codex", {}).get("version", {}).get("stdout")
            == self._codex_version.stdout
            and tools.get("verus", {}).get("sha256") == sha256_file(self.verus_bin)
            and tools.get("verus", {}).get("implementation_sha256")
            == self._verus_implementation_sha256
            and tools.get("verus", {}).get("version", {}).get("stdout")
            == self._verus_version.stdout
            and tools.get("lynette", {}).get("sha256") == sha256_file(self.lynette_bin)
            and bridge.get("task_key") == task_key
            and bridge.get("config_sha256") == bridge_manifest.get("config_sha256")
            and bridge.get("implementation_sha256")
            == bridge_manifest.get("implementation_sha256")
            and bridge.get("protocol") == bridge_manifest.get("protocol")
            and bridge.get("native_responses")
            == bridge_manifest.get("native_responses")
            and bridge.get("fake_mode") is False
            and self._actor_isolation_matches(manifest)
            and not (result.get("timed_out") and not result.get("hard"))
        ):
            return result
        return None

    def _run_one_attempt_with_timeout(
        self,
        item: dict[str, Any],
        prediction_dir: Path,
        skill_file: Path,
        *,
        attempt_index: int,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        task_dir = prediction_dir / item["id"]
        task_key = self._task_key(task_dir, attempt_index)
        command = [
            sys.executable,
            "-m",
            "skillopt_verusage.codex_flash_runner",
            "--item-id",
            item["id"],
            "--source",
            item["source_path"],
            "--expected-source-sha256",
            item["source_sha256"],
            "--directory-group",
            item["directory_group"],
            "--out-dir",
            str(task_dir),
            "--skill-file",
            str(skill_file),
            "--codex-bin",
            str(self.codex_bin),
            "--verus-bin",
            str(self.verus_bin),
            "--lynette-bin",
            str(self.lynette_bin),
            "--bridge-url",
            self.bridge_url,
            "--bridge-ledger-path",
            str(self.bridge_ledger_path),
            "--bridge-manifest-path",
            str(self.bridge_manifest_path),
            "--bridge-task-key",
            task_key,
            "--model",
            self.actor_model,
            "--reasoning-effort",
            self.reasoning_effort,
            "--timeout-seconds",
            str(timeout_seconds),
            "--model-context-window",
            str(self.model_context_window),
            "--actor-contract-profile",
            self.actor_contract_profile,
            "--codex-provider-id",
            self.codex_provider_id,
            "--run-stage",
            self.run_stage,
        ]
        if not self.condition_skill_present:
            command.append("--condition-skill-absent")
        if self.actor_isolation_scratch_root:
            command.extend(
                [
                    "--actor-isolation-scratch-root",
                    self.actor_isolation_scratch_root,
                    "--actor-isolation-verus-root",
                    str(self.actor_isolation_verus_root),
                    "--actor-isolation-rust-root",
                    str(self.actor_isolation_rust_root),
                ]
            )
            for path in self.actor_isolation_forbidden_paths:
                command.extend(["--actor-isolation-forbidden-path", path])
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            with self._process_lock:
                self._active_processes.add(process)
            _, stderr = process.communicate(timeout=timeout_seconds + 120)
            result_path = task_dir / "result.json"
            if result_path.is_file():
                return json.loads(result_path.read_text(encoding="utf-8"))
            return self._fallback_result(
                item,
                task_dir,
                f"Codex runner exit={process.returncode}: {stderr[-2000:]}",
            )
        except subprocess.TimeoutExpired:
            if process is not None:
                self._terminate_process(process)
            return self._fallback_result(
                item, task_dir, "Codex runner exceeded host watchdog"
            )
        finally:
            if process is not None:
                with self._process_lock:
                    self._active_processes.discard(process)

    def _run_one(
        self,
        item: dict[str, Any],
        prediction_dir: Path,
        skill_file: Path,
    ) -> dict[str, Any]:
        task_dir = prediction_dir / item["id"]
        skill_sha = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        resumed = self._resume_result(
            task_dir,
            item=item,
            skill_sha256=skill_sha,
            timeout_seconds=self.codex_timeout_seconds,
        )
        if resumed is not None:
            resumed["resumed"] = True
            return resumed
        if task_dir.is_dir() and any(task_dir.iterdir()):
            self._archive_safely(task_dir, 0)

        result: dict[str, Any] = {}
        for attempt_index in range(1, self.task_retries + 2):
            timeout_seconds = min(
                self.max_codex_timeout_seconds,
                self.codex_timeout_seconds * attempt_index,
            )
            result = self._run_one_attempt_with_timeout(
                item,
                prediction_dir,
                skill_file,
                attempt_index=attempt_index,
                timeout_seconds=timeout_seconds,
            )
            result["task_attempt_index"] = attempt_index
            result["resumed"] = False
            (task_dir / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            retry = bool(
                result.get("timed_out")
                and not result.get("hard")
                and attempt_index <= self.timeout_retries
            )
            if not retry or attempt_index > self.task_retries:
                return result
            self._archive_safely(task_dir, attempt_index)
        return result

    @staticmethod
    def _archive_safely(task_dir: Path, attempt_index: int) -> None:
        archive_root = task_dir.parent / "_attempts" / task_dir.name
        suffix = 0
        while True:
            label = f"attempt-{attempt_index:02d}"
            if suffix:
                label += f"-{suffix:02d}"
            archive_dir = archive_root / label
            if not archive_dir.exists():
                break
            suffix += 1
        archive_dir.mkdir(parents=True)
        for path in list(task_dir.iterdir()):
            shutil.move(str(path), archive_dir / path.name)

    @staticmethod
    def _task_key(task_dir: Path, attempt_index: int) -> str:
        phase_dir = (
            task_dir.parent.parent
            if task_dir.parent.name == "predictions"
            else task_dir.parent
        )
        phase = phase_dir.name
        if phase_dir.parent.name.startswith("step_"):
            phase = f"{phase_dir.parent.name}-{phase}"
        phase = "".join(
            char if char.isalnum() or char in "_-" else "_" for char in phase
        )
        return f"{phase}--{task_dir.name}--a{attempt_index:02d}"


# Backward-compatible import for the isolated Flash preflight configuration.
CodexFlashAdapter = CodexDeepSeekAdapter
