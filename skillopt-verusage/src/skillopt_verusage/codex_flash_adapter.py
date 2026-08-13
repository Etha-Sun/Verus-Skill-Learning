from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from skillopt_verusage.adapter import VeruSAGEAdapter
from skill_evolution_pilot.codex_runner import build_prompt
from skill_evolution_pilot.workspace import sha256_file


class CodexFlashAdapter(VeruSAGEAdapter):
    """SkillOpt adapter whose target is DeepSeek Flash inside Codex CLI."""

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
        workers: int = 60,
        analyst_workers: int = 60,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        task_retries: int = 2,
        codex_timeout_seconds: int = 1200,
        max_codex_timeout_seconds: int = 1200,
        model_context_window: int = 262144,
        seed: int = 42,
    ) -> None:
        super().__init__(
            split_dir=split_dir,
            verusage_src_root=".",
            verus_bin=verus_bin,
            lynette_bin=lynette_bin,
            model="deepseek-v4-flash",
            workers=workers,
            analyst_workers=analyst_workers,
            failure_only=failure_only,
            minibatch_size=minibatch_size,
            edit_budget=edit_budget,
            task_retries=task_retries,
            task_timeout_seconds=max_codex_timeout_seconds + 120,
            seed=seed,
        )
        self.codex_bin = Path(codex_bin).resolve()
        self.bridge_url = bridge_url.rstrip("/")
        self.bridge_ledger_path = Path(bridge_ledger_path).resolve()
        self.bridge_manifest_path = Path(bridge_manifest_path).resolve()
        self.codex_timeout_seconds = int(codex_timeout_seconds)
        self.max_codex_timeout_seconds = int(max_codex_timeout_seconds)
        self.model_context_window = int(model_context_window)
        self._codex_version = subprocess.run(
            [str(self.codex_bin), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if self._codex_version.returncode != 0:
            raise ValueError(f"Codex CLI is not executable: {self.codex_bin}")

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
        task_key = hashlib.sha256(
            f"{task_dir.resolve()}:{attempt_index}".encode("utf-8")
        ).hexdigest()[:24]
        expected_provider_url = self.bridge_url + f"/tasks/{task_key}/v1"
        tools = manifest.get("tools") or {}
        provider = manifest.get("provider") or {}
        bridge = manifest.get("bridge") or {}
        if (
            result.get("id") == task_dir.name
            and result.get("actor_model") == "deepseek-v4-flash"
            and result.get("fidelity") in {"V2_TRACE", "V1_TRUNCATED"}
            and manifest.get("source_sha256") == item["source_sha256"]
            and manifest.get("skill_sha256") == skill_sha256
            and manifest.get("prompt_sha256")
            == hashlib.sha256(build_prompt().encode("utf-8")).hexdigest()
            and manifest.get("model") == "deepseek-v4-flash"
            and manifest.get("timeout_seconds") == timeout_seconds
            and provider.get("base_url") == expected_provider_url
            and provider.get("wire_api") == "responses"
            and provider.get("model_context_window") == self.model_context_window
            and tools.get("codex", {}).get("sha256") == sha256_file(self.codex_bin)
            and tools.get("codex", {}).get("version", {}).get("stdout")
            == self._codex_version.stdout
            and tools.get("verus", {}).get("sha256") == sha256_file(self.verus_bin)
            and tools.get("lynette", {}).get("sha256") == sha256_file(self.lynette_bin)
            and bridge.get("task_key") == task_key
            and bridge.get("config_sha256") == bridge_manifest.get("config_sha256")
            and bridge.get("implementation_sha256")
            == bridge_manifest.get("implementation_sha256")
            and bridge.get("fake_mode") is False
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
        task_key = hashlib.sha256(
            f"{task_dir.resolve()}:{attempt_index}".encode("utf-8")
        ).hexdigest()[:24]
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
            "--timeout-seconds",
            str(timeout_seconds),
            "--model-context-window",
            str(self.model_context_window),
        ]
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
            retry = result.get("fidelity") == "V0_INVALID"
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
