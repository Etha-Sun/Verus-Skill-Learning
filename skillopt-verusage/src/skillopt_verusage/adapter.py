from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter

from skillopt_verusage.dataloader import VeruSAGEDataLoader


class VeruSAGEAdapter(EnvAdapter):
    def __init__(
        self,
        *,
        split_dir: str,
        verusage_src_root: str,
        verus_bin: str,
        lynette_bin: str,
        model: str = "deepseek-v4-flash",
        workers: int = 16,
        analyst_workers: int = 16,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        repair_attempts: int = 20,
        request_cap: int = 512,
        action_output_tokens: int = 32768,
        reasoning_output_tokens: int = 32768,
        retry_action_output_tokens: int = 262144,
        retry_reasoning_output_tokens: int = 262144,
        max_action_output_tokens: int = 384000,
        max_reasoning_output_tokens: int = 384000,
        task_retries: int = 2,
        request_timeout_seconds: int = 1800,
        task_timeout_seconds: int = 86400,
        budget_state_path: str | None = None,
        budget_approval_limit_usd: float = 20.0,
        budget_prior_spend_usd: float = 0.0,
        budget_optimizer_reserve_usd: float = 1.0,
        budget_request_reserve_usd: float = 0.3,
        seed: int = 42,
    ):
        self.verusage_src_root = Path(verusage_src_root).resolve()
        self.verus_bin = Path(verus_bin).resolve()
        self.lynette_bin = Path(lynette_bin).resolve()
        self.model = model
        self.workers = int(workers)
        self.analyst_workers = int(analyst_workers)
        self.failure_only = bool(failure_only)
        self.minibatch_size = int(minibatch_size)
        self.edit_budget = int(edit_budget)
        self.repair_attempts = int(repair_attempts)
        self.request_cap = int(request_cap)
        self.action_output_tokens = int(action_output_tokens)
        self.reasoning_output_tokens = int(reasoning_output_tokens)
        self.retry_action_output_tokens = int(retry_action_output_tokens)
        self.retry_reasoning_output_tokens = int(retry_reasoning_output_tokens)
        self.max_action_output_tokens = int(max_action_output_tokens)
        self.max_reasoning_output_tokens = int(max_reasoning_output_tokens)
        self.task_retries = int(task_retries)
        self.request_timeout_seconds = int(request_timeout_seconds)
        self.task_timeout_seconds = int(task_timeout_seconds)
        self.budget_state_path = budget_state_path
        self.budget_approval_limit_usd = float(budget_approval_limit_usd)
        self.budget_prior_spend_usd = float(budget_prior_spend_usd)
        self.budget_optimizer_reserve_usd = float(budget_optimizer_reserve_usd)
        self.budget_request_reserve_usd = float(budget_request_reserve_usd)
        self._process_lock = threading.Lock()
        self._active_processes: set[subprocess.Popen[str]] = set()
        self.dataloader = VeruSAGEDataLoader(
            split_dir=split_dir,
            split_mode="split_dir",
            seed=seed,
        )

    def setup(self, cfg: dict) -> None:
        super().setup(cfg)
        self.dataloader.setup(cfg)
        root_text = os.environ.get("VERUS_SKILL_RUN_ROOT", "")
        if not root_text:
            raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
        root = Path(root_text).resolve()
        out_root = Path(str(cfg["out_root"])).resolve()
        if out_root != root and root not in out_root.parents:
            raise ValueError(f"out_root must be below VERUS_SKILL_RUN_ROOT: {out_root}")

    def get_dataloader(self):
        return self.dataloader

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        return self.build_env_from_batch(
            self.dataloader.build_train_batch(batch_size, seed, **kwargs)
        )

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        return self.build_env_from_batch(
            self.dataloader.build_eval_batch(env_num, split, seed, **kwargs)
        )

    def _fallback_result(
        self,
        item: dict[str, Any],
        task_dir: Path,
        reason: str,
    ) -> dict[str, Any]:
        task_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "id": item["id"],
            "hard": 0,
            "soft": 0.0,
            "task_type": item["task_type"],
            "task_description": "Repair a Verus proof while preserving executable behavior.",
            "fail_reason": reason,
            "n_turns": 0,
            "fidelity": "V0_INVALID",
        }
        (task_dir / "conversation.json").write_text(
            json.dumps(
                [{"role": "system", "content": f"Rollout failed: {reason}"}],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (task_dir / "result.json").write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    def _run_one_attempt(
        self,
        item: dict[str, Any],
        prediction_dir: Path,
        skill_file: Path,
    ) -> dict[str, Any]:
        task_dir = prediction_dir / item["id"]
        command = [
            sys.executable,
            "-m",
            "skillopt_verusage.runner",
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
            "--model",
            self.model,
            "--verusage-src-root",
            str(self.verusage_src_root),
            "--verus-bin",
            str(self.verus_bin),
            "--lynette-bin",
            str(self.lynette_bin),
            "--repair-attempts",
            str(self.repair_attempts),
            "--request-cap",
            str(self.request_cap),
            "--action-output-tokens",
            str(self.action_output_tokens),
            "--reasoning-output-tokens",
            str(self.reasoning_output_tokens),
            "--retry-action-output-tokens",
            str(self.retry_action_output_tokens),
            "--retry-reasoning-output-tokens",
            str(self.retry_reasoning_output_tokens),
            "--max-action-output-tokens",
            str(self.max_action_output_tokens),
            "--max-reasoning-output-tokens",
            str(self.max_reasoning_output_tokens),
            "--request-timeout-seconds",
            str(self.request_timeout_seconds),
            "--budget-approval-limit-usd",
            str(self.budget_approval_limit_usd),
            "--budget-prior-spend-usd",
            str(self.budget_prior_spend_usd),
            "--budget-optimizer-reserve-usd",
            str(self.budget_optimizer_reserve_usd),
            "--budget-request-reserve-usd",
            str(self.budget_request_reserve_usd),
        ]
        if self.budget_state_path:
            command.extend(["--budget-state-path", self.budget_state_path])
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
            _, stderr = process.communicate(timeout=self.task_timeout_seconds)
            result_path = task_dir / "result.json"
            if result_path.is_file():
                return json.loads(result_path.read_text(encoding="utf-8"))
            return self._fallback_result(
                item,
                task_dir,
                f"runner exit={process.returncode}: {stderr[-1000:]}",
            )
        except subprocess.TimeoutExpired:
            if process is not None:
                self._terminate_process(process)
            return self._fallback_result(item, task_dir, "task subprocess timed out")
        finally:
            if process is not None:
                with self._process_lock:
                    self._active_processes.discard(process)

    @staticmethod
    def _archive_attempt(task_dir: Path, attempt_index: int) -> None:
        archive_root = task_dir.parent / "_attempts" / task_dir.name
        archive_dir = archive_root / f"attempt-{attempt_index:02d}"
        archive_dir.mkdir(parents=True)
        for path in list(task_dir.iterdir()):
            shutil.move(str(path), archive_dir / path.name)

    def _run_one(
        self,
        item: dict[str, Any],
        prediction_dir: Path,
        skill_file: Path,
    ) -> dict[str, Any]:
        task_dir = prediction_dir / item["id"]
        for attempt_index in range(1, self.task_retries + 2):
            result = self._run_one_attempt(item, prediction_dir, skill_file)
            result["task_attempt_index"] = attempt_index
            (task_dir / "result.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if result.get("fidelity") != "V0_INVALID":
                return result
            if attempt_index <= self.task_retries:
                self._archive_attempt(task_dir, attempt_index)
        return result

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def _terminate_active_processes(self) -> None:
        with self._process_lock:
            processes = list(self._active_processes)
        for process in processes:
            self._terminate_process(process)

    def rollout(
        self,
        env_manager,
        skill_content: str,
        out_dir: str,
        **kwargs,
    ) -> list[dict]:
        del kwargs
        items: list[dict[str, Any]] = list(env_manager)
        root = Path(out_dir)
        prediction_dir = root / "predictions"
        prediction_dir.mkdir(parents=True, exist_ok=True)
        skill_file = root / "skill.md"
        skill_file.write_text(skill_content, encoding="utf-8")
        results: list[dict[str, Any]] = []
        executor = ThreadPoolExecutor(max_workers=self.workers)
        try:
            futures = {
                executor.submit(self._run_one, item, prediction_dir, skill_file): item
                for item in items
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                except Exception as error:
                    result = self._fallback_result(
                        item,
                        prediction_dir / item["id"],
                        f"{type(error).__name__}: {error}",
                    )
                if result.get("fidelity") == "V0_INVALID":
                    raise RuntimeError(
                        f"HARNESS_INVALID after task retries: {item['id']}: "
                        f"{result.get('fail_reason', '')}"
                    )
                results.append(result)
        except BaseException:
            for future in futures:
                future.cancel()
            self._terminate_active_processes()
            executor.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)
        by_id = {row["id"]: row for row in results}
        return [by_id[item["id"]] for item in items]

    def get_task_types(self) -> list[str]:
        return self.dataloader.get_task_types()
