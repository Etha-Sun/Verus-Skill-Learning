from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .codex_adapter import normalize_codex_jsonl
from .redaction import secret_match_count
from .workspace import inventory, sha256_file


PROFILES = ("aggressive", "conservative", "structural")
EVIDENCE_FILES = (
    "codex_events.raw.jsonl",
    "agent_events.jsonl",
    "provider_io.jsonl",
    "result.json",
    "fidelity_audit.json",
    "validation.json",
    "token_ledger.json",
    "run_manifest.json",
    "visibility_manifest.json",
    "prompt.txt",
    "last_message.txt",
    "candidate.diff",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def meta_output_schema(objective: str) -> dict[str, Any]:
    skill = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "skill_id",
            "profile",
            "title",
            "hypothesis",
            "applicability",
            "negative_scope",
            "content",
        ],
        "properties": {
            "skill_id": {
                "type": "string",
                "minLength": 1,
                "pattern": "^[a-z0-9][a-z0-9_-]*$",
            },
            "profile": {"type": "string", "enum": list(PROFILES)},
            "title": {"type": "string", "minLength": 1},
            "hypothesis": {"type": "string", "minLength": 1},
            "applicability": {"type": "string", "minLength": 1},
            "negative_scope": {"type": "string", "minLength": 1},
            "content": {"type": "string", "minLength": 1},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "objective",
            "diagnosis",
            "retained_principle",
            "rejected_principle",
            "revised_meta_skill",
            "skills",
        ],
        "properties": {
            "schema_version": {"type": "string", "const": "1"},
            "objective": {"type": "string", "const": objective},
            "diagnosis": {"type": "string", "minLength": 1},
            "retained_principle": {"type": "string", "minLength": 1},
            "rejected_principle": {"type": "string", "minLength": 1},
            "revised_meta_skill": {"type": "string", "minLength": 1},
            "skills": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": skill,
            },
        },
    }


def token_output_schema() -> dict[str, Any]:
    return meta_output_schema("token_cost")


def validate_meta_output(value: Any, objective: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["output is not a JSON object"]
    expected = {
        "schema_version",
        "objective",
        "diagnosis",
        "retained_principle",
        "rejected_principle",
        "revised_meta_skill",
        "skills",
    }
    if set(value) != expected:
        errors.append(f"top-level keys differ: {sorted(set(value) ^ expected)}")
    if value.get("schema_version") != "1":
        errors.append("schema_version must be 1")
    if value.get("objective") != objective:
        errors.append(f"objective must be {objective}")
    for field in (
        "diagnosis",
        "retained_principle",
        "rejected_principle",
        "revised_meta_skill",
    ):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"{field} must be non-empty")
    skills = value.get("skills")
    if not isinstance(skills, list) or len(skills) != 3:
        errors.append("skills must contain exactly three entries")
        return errors
    profiles = []
    skill_ids = []
    expected_skill_keys = {
        "skill_id",
        "profile",
        "title",
        "hypothesis",
        "applicability",
        "negative_scope",
        "content",
    }
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"skill {index} is not an object")
            continue
        if set(skill) != expected_skill_keys:
            errors.append(
                f"skill {index} keys differ: "
                f"{sorted(set(skill) ^ expected_skill_keys)}"
            )
        for field in expected_skill_keys:
            if not isinstance(skill.get(field), str) or not skill[field].strip():
                errors.append(f"skill {index} {field} must be non-empty")
        if isinstance(skill.get("skill_id"), str) and not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]*", skill["skill_id"]
        ):
            errors.append(f"skill {index} skill_id is unsafe")
        profiles.append(skill.get("profile"))
        skill_ids.append(skill.get("skill_id"))
    if sorted(profiles) != sorted(PROFILES):
        errors.append(f"profiles must be exactly {list(PROFILES)}")
    if len(set(skill_ids)) != 3:
        errors.append("skill_id values must be unique")
    return errors


def validate_token_meta_output(value: Any) -> list[str]:
    return validate_meta_output(value, "token_cost")


def _copy_evidence(run_dir: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    copied = 0
    for name in EVIDENCE_FILES:
        source = run_dir / name
        if source.is_file():
            shutil.copyfile(source, destination / name)
            copied += 1
    for relative in ("snapshots",):
        source = run_dir / relative
        if source.is_dir():
            shutil.copytree(source, destination / relative)
            copied += 1
    workspace = run_dir / "workspace"
    for name in ("input.rs", "candidate.rs"):
        source = workspace / name
        if source.is_file():
            shutil.copyfile(source, destination / name)
            copied += 1
    if copied == 0:
        raise ValueError(f"no allowlisted evidence found in {run_dir}")


def _meta_task(objective: str) -> str:
    if objective == "token_cost":
        return """You are the token-cost meta-skill agent for Verus proof repair.

Inspect every allowlisted file below evidence/. The raw Codex JSONL streams,
normalized event indexes, complete tool outputs, code snapshots, final
candidates, verifier outcomes, and token ledgers are evidence. Do not inspect
anything outside this workspace and do not use network access. Every command
must use relative paths contained in this workspace. Never use an absolute
path, `..`, `$HOME`, or a system temporary directory. If scratch files are
needed, create and use only `scratch/` inside this workspace.

Your sole objective is to reduce expected uncached Codex tokens to a valid
Verus+Lynette solution. Never reward shorter failed runs. Preserve correctness
and proof safety. Diagnose costly exploration patterns in H0, revise the
objective-specific meta-skill, and emit exactly three materially different
solver skills:

- aggressive: strongest intervention to cut exploration;
- conservative: minimal, robust guidance;
- structural: a different workflow or proof-decomposition strategy.

Each skill's content must be directly injectable as SKILL.md. It may teach a
general proof-repair procedure but must not copy a finished proof, task-specific
identifiers, or reference answers. State applicability and negative scope.
Return only the schema-conforming JSON object.
"""
    if objective == "small_model_solve_rate":
        return """You are the small-model meta-skill agent for Verus proof repair.

Inspect every allowlisted file below evidence/. These are complete H0 Codex
proof-repair traces used only as diagnostic evidence. Do not inspect anything
outside this workspace and do not use network access. Every command must use
relative paths contained in this workspace. Never use an absolute path, `..`,
`$HOME`, or a system temporary directory. If scratch files are needed, create
and use only `scratch/` inside this workspace.

Your sole objective is to improve verifier-safe solve rate of an agentic
Qwen3.6-27B solver under a fixed ten-request budget. Token count is recorded
but is not an optimization target, and a shorter failed run is never better.
Infer which parts of the stronger Codex behavior should be compiled into
simple, capacity-appropriate instructions. Revise the objective-specific
meta-skill and emit exactly three materially different solver skills:

- aggressive: explicit step-by-step scaffolding and recovery rules;
- conservative: minimal robust guidance that avoids overloading the student;
- structural: a different state-based proof-decomposition workflow.

Each skill's content must be directly injectable as SKILL.md and visible to
the Qwen solver. It may teach a general proof-repair procedure but must not
copy a finished proof, task-specific identifiers, task names, or reference
answers. State applicability and negative scope. Do not optimize token cost or
information gain. Return only the schema-conforming JSON object.
"""
    if objective == "information_gain":
        return """You are the information-gain meta-skill agent for Verus proof repair.

Inspect every allowlisted file below evidence/. These are complete H0 Codex
proof-repair traces used only to learn what proof-relevant information should
be made salient. Do not inspect anything outside this workspace and do not use
network access. Every command must use relative paths contained in this
workspace. Never use an absolute path, `..`, `$HOME`, or a system temporary
directory. If scratch files are needed, create and use only `scratch/`.

Your sole objective is to improve a frozen local Qwen3.6-27B scorer's
teacher-forced log likelihood of a complete reference proof. Each candidate
skill serves two roles: its text is the pre-run rationale, and it guides the
Codex solver's terminal repair summary used as the post-run rationale. The
reference proof is evaluator-only and is never visible here.

Emit exactly three materially different skills:

- aggressive: maximize explicit proof-state and obligation information;
- conservative: retain only likely sufficient proof-relevant facts;
- structural: organize information as dependencies, invariants, and bridges.

The skill must be directly injectable as SKILL.md and instruct the solver to
end with a concise terminal repair summary containing the diagnosed
obligation, key lemmas or invariants, decisive proof bridge, verifier outcome,
and unresolved blocker if any. Do not optimize solve rate or token cost. Do
not copy task names, task-specific identifiers, finished proofs, or reference
answers. State applicability and negative scope. Return only the
schema-conforming JSON object.
"""
    raise ValueError(f"unsupported meta objective: {objective}")


def prepare_meta_workspace(
    *,
    workspace: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
    objective: str,
    baseline_run_dirs: Iterable[Path] = (),
    prior_run_dirs: Iterable[Path] = (),
    prior_meta_output_path: Path | None = None,
    prior_summary_path: Path | None = None,
    design_brief_path: Path | None = None,
) -> dict[str, Any]:
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError(f"workspace must be empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    evidence_root = workspace / "evidence"
    evidence_root.mkdir()
    runs = list(h0_run_dirs)
    if not runs:
        raise ValueError("at least one H0 run is required")
    for index, run_dir in enumerate(runs, start=1):
        resolved = run_dir.resolve()
        _copy_evidence(resolved, evidence_root / f"run_{index:02d}_{resolved.name}")

    task = _meta_task(objective)
    baseline_runs = list(baseline_run_dirs)
    if baseline_runs:
        baseline_root = workspace / "small_model_baseline"
        baseline_root.mkdir()
        for index, run_dir in enumerate(baseline_runs, start=1):
            resolved = run_dir.resolve()
            _copy_evidence(
                resolved,
                baseline_root / f"run_{index:02d}_{resolved.name}",
            )
        task += """

small_model_baseline/ contains the matched no-skill Qwen executions. Use it as
the causal baseline for solve-rate comparisons; the stronger Codex evidence
is diagnostic teacher behavior, not the small-model baseline.
"""

    prior_runs = list(prior_run_dirs)
    prior_supplied = bool(
        prior_runs or prior_meta_output_path is not None or prior_summary_path is not None
    )
    if prior_supplied:
        if (
            not prior_runs
            or prior_meta_output_path is None
            or prior_summary_path is None
        ):
            raise ValueError(
                "prior round requires run dirs, meta output, and summary"
            )
        previous_root = workspace / "previous_round"
        previous_root.mkdir()
        shutil.copyfile(prior_meta_output_path.resolve(), previous_root / "meta_output.json")
        shutil.copyfile(prior_summary_path.resolve(), previous_root / "summary.json")
        previous_meta = json.loads(
            prior_meta_output_path.read_text(encoding="utf-8")
        )
        skills_root = previous_root / "skills"
        skills_root.mkdir()
        for skill in previous_meta.get("skills", []):
            skill_id = str(skill["skill_id"])
            (skills_root / f"{skill_id}.md").write_text(
                str(skill["content"]).rstrip() + "\n",
                encoding="utf-8",
            )
        runs_root = previous_root / "runs"
        runs_root.mkdir()
        for index, run_dir in enumerate(prior_runs, start=1):
            resolved = run_dir.resolve()
            _copy_evidence(
                resolved,
                runs_root / f"run_{index:02d}_{resolved.parent.name}_{resolved.name}",
            )
        task += """

previous_round/ contains the exact three prior candidate skills, the complete
branch-local aggregate summary, and selected representative prior solver
traces. Use the aggregate for full-matrix claims and the selected traces for
mechanism diagnosis. Compare all three candidates with the matched baseline,
identify the best and worst mechanisms per task, and revise the current
meta-skill. This is an evolution step: the new skills must be materially changed
in response to observed failures, not paraphrases of the previous
skills. Preserve useful behavior, reject ineffective behavior, and still
optimize only this branch's objective.
"""
    if design_brief_path is not None:
        if objective != "token_cost":
            raise ValueError("design brief is supported only for token_cost")
        shutil.copyfile(design_brief_path.resolve(), workspace / "DESIGN_BRIEF.md")
        task += """

DESIGN_BRIEF.md is an experimenter-supplied hypothesis menu, not empirical
evidence. Test only mechanisms that can be implemented by an injected textual
solver skill under the frozen harness. Do not claim that a general design
principle works here until the four-task matrix supports it.
Diagnose input and output token changes separately, retain an explicit no-skill/direct path
when guidance is unnecessary, and name the design mechanism exercised by each
candidate.
"""
    (workspace / "META_TASK.md").write_text(task, encoding="utf-8")
    (workspace / "CURRENT_META_SKILL.md").write_text(
        current_meta_skill.rstrip() + "\n",
        encoding="utf-8",
    )
    (workspace / "scratch").mkdir()
    schema = meta_output_schema(objective)
    (workspace / "OUTPUT_SCHEMA.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    initial = inventory(workspace)
    manifest = {
        "schema_version": "1",
        "objective": objective,
        "workspace": "$WORKSPACE",
        "reference_proof_visible": False,
        "other_objective_visible": False,
        "credential_visible": False,
        "small_model_baseline_visible": bool(baseline_runs),
        "previous_round_visible": prior_supplied,
        "design_brief_visible": design_brief_path is not None,
        "files": initial,
    }
    (workspace.parent / "meta_visibility_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def prepare_token_meta_workspace(
    *,
    workspace: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
) -> dict[str, Any]:
    return prepare_meta_workspace(
        workspace=workspace,
        h0_run_dirs=h0_run_dirs,
        current_meta_skill=current_meta_skill,
        objective="token_cost",
    )


def _outside_workspace_commands(raw_path: Path, workspace: Path) -> list[str]:
    suspects: list[str] = []
    allowed = str(workspace.resolve())
    runtime_paths = {"/usr/bin/bash", "/bin/bash", "/usr/bin/env", "/dev/null"}
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        item = row.get("item")
        if (
            row.get("type") != "item.completed"
            or not isinstance(item, dict)
            or item.get("type") != "command_execution"
        ):
            continue
        command = str(item.get("command") or "")
        try:
            outer = shlex.split(command)
        except ValueError:
            suspects.append(command)
            continue
        tokens = list(outer)
        if "-lc" in outer:
            index = outer.index("-lc")
            if index + 1 < len(outer):
                try:
                    tokens.extend(shlex.split(outer[index + 1]))
                except ValueError:
                    suspects.append(command)
                    continue
        paths = []
        for token in tokens:
            stripped = re.sub(r"^(?:[0-9]*[<>]+)", "", token).rstrip(";,")
            if (
                stripped in {"/", "//"}
                or stripped.startswith("/^")
                or re.fullmatch(r"/[^/]+/", stripped)
            ):
                continue
            if stripped.startswith("/") and len(stripped) > 1:
                paths.append(stripped)
        if any(
            not path.startswith(allowed) and path not in runtime_paths
            for path in paths
        ):
            suspects.append(command)
    return suspects


def reaudit_token_meta_agent(out_dir: Path) -> dict[str, Any]:
    raw_path = out_dir / "codex_events.raw.jsonl"
    output_path = out_dir / "meta_output.json"
    destination = out_dir / "meta_audit.recomputed.json"
    suffix = 2
    while destination.exists():
        destination = out_dir / f"meta_audit.recomputed-v{suffix}.json"
        suffix += 1
    parsed: Any = None
    parse_error = None
    try:
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parse_error = f"{type(exc).__name__}: {exc}"
    outside_commands = _outside_workspace_commands(raw_path, out_dir / "workspace")
    manifest_path = out_dir / "run_manifest.json"
    objective = "token_cost"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        objective = str(manifest.get("objective") or objective)
    audit = {
        "audit_kind": "posthoc_visibility_and_schema_replay",
        "created_at": _now(),
        "parse_error": parse_error,
        "objective": objective,
        "schema_errors": validate_meta_output(parsed, objective),
        "outside_workspace_command_count": len(outside_commands),
        "outside_workspace_commands": outside_commands,
        "secret_match_count": secret_match_count(out_dir, ()),
    }
    audit["valid"] = bool(
        parse_error is None
        and not audit["schema_errors"]
        and not outside_commands
        and audit["secret_match_count"] == 0
    )
    destination.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return audit


def run_meta_agent(
    *,
    out_dir: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
    codex_bin: Path,
    objective: str,
    baseline_run_dirs: Iterable[Path] = (),
    prior_run_dirs: Iterable[Path] = (),
    prior_meta_output_path: Path | None = None,
    prior_summary_path: Path | None = None,
    design_brief_path: Path | None = None,
    forbidden_terms: Iterable[str] = (),
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    root_text = os.environ.get("VERUS_SKILL_RUN_ROOT")
    if not root_text:
        raise ValueError("VERUS_SKILL_RUN_ROOT is not configured")
    root = Path(root_text).resolve()
    out_dir = out_dir.resolve()
    if out_dir == root or root not in out_dir.parents:
        raise ValueError("meta output must be below VERUS_SKILL_RUN_ROOT")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    codex_bin = codex_bin.resolve()
    if not codex_bin.is_file() or not os.access(codex_bin, os.X_OK):
        raise ValueError(f"codex is not executable: {codex_bin}")

    workspace = out_dir / "workspace"
    prepare_meta_workspace(
        workspace=workspace,
        h0_run_dirs=h0_run_dirs,
        current_meta_skill=current_meta_skill,
        objective=objective,
        baseline_run_dirs=baseline_run_dirs,
        prior_run_dirs=prior_run_dirs,
        prior_meta_output_path=prior_meta_output_path,
        prior_summary_path=prior_summary_path,
        design_brief_path=design_brief_path,
    )
    prompt = (
        "Read META_TASK.md, CURRENT_META_SKILL.md, OUTPUT_SCHEMA.json, and all "
        f"evidence files. Perform only the requested {objective} reflection."
    )
    (out_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    raw_path = out_dir / "codex_events.raw.jsonl"
    normalized_path = out_dir / "agent_events.jsonl"
    stderr_path = out_dir / "codex_stderr.log"
    last_message = out_dir / "meta_output.json"
    command = [
        str(codex_bin),
        "exec",
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        "-c",
        'model_reasoning_summary="detailed"',
        "-c",
        "model_supports_reasoning_summaries=true",
        "-c",
        "hide_agent_reasoning=false",
        "-c",
        "show_raw_agent_reasoning=true",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--color",
        "never",
        "--json",
        "-C",
        str(workspace),
        "--output-schema",
        str(workspace / "OUTPUT_SCHEMA.json"),
        "--output-last-message",
        str(last_message),
        "-",
    ]
    started = time.monotonic()
    timed_out = threading.Event()
    with raw_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        child_env = {**os.environ, "TMPDIR": str(workspace / "scratch")}
        secret = child_env.pop("OPENROUTER_API_KEY", "")
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.PIPE,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=True,
            env=child_env,
        )
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()

        def stop_process() -> None:
            if process.poll() is None:
                timed_out.set()
                os.killpg(process.pid, signal.SIGINT)

        timer = threading.Timer(timeout_seconds, stop_process)
        timer.start()
        try:
            try:
                returncode = process.wait(
                    timeout=15 if timed_out.is_set() else timeout_seconds + 15
                )
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                returncode = None
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        finally:
            timer.cancel()

    normalize_result = normalize_codex_jsonl(
        raw_path=raw_path,
        normalized_path=normalized_path,
        run_id=out_dir.name,
        candidate_path=None,
    )
    parsed: Any = None
    parse_error = None
    try:
        parsed = json.loads(last_message.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parse_error = f"{type(exc).__name__}: {exc}"
    schema_errors = validate_meta_output(parsed, objective)
    normalized_forbidden = sorted(
        {term.strip() for term in forbidden_terms if term.strip()}
    )
    output_text = json.dumps(parsed, ensure_ascii=False) if parsed is not None else ""
    forbidden_term_matches = [
        term for term in normalized_forbidden if term.lower() in output_text.lower()
    ]
    outside_commands = _outside_workspace_commands(raw_path, workspace)
    audit = {
        "returncode": returncode,
        "timed_out": timed_out.is_set(),
        "wall_seconds": time.monotonic() - started,
        "parse_error": parse_error,
        "schema_errors": schema_errors,
        "outside_workspace_command_count": len(outside_commands),
        "outside_workspace_commands": outside_commands,
        "forbidden_term_matches": forbidden_term_matches,
        "secret_match_count": secret_match_count(out_dir, (secret,)),
        "normalized_event_count": normalize_result.get("normalized_event_count"),
    }
    audit["valid"] = bool(
        returncode == 0
        and not timed_out.is_set()
        and parse_error is None
        and not schema_errors
        and not outside_commands
        and not forbidden_term_matches
        and audit["secret_match_count"] == 0
    )
    manifest = {
        "schema_version": "1",
        "created_at": _now(),
        "objective": objective,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "reasoning_summary": "detailed",
        "show_raw_agent_reasoning": True,
        "timeout_seconds": timeout_seconds,
        "prompt_sha256": sha256_file(out_dir / "prompt.txt"),
        "raw_log_uncompressed": True,
        "hidden_chain_of_thought_claimed": False,
    }
    for name, value in (
        ("run_manifest.json", manifest),
        ("meta_audit.json", audit),
    ):
        (out_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {"audit": audit, "output": parsed}


def run_token_meta_agent(
    *,
    out_dir: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
    codex_bin: Path,
    prior_run_dirs: Iterable[Path] = (),
    prior_meta_output_path: Path | None = None,
    prior_summary_path: Path | None = None,
    design_brief_path: Path | None = None,
    forbidden_terms: Iterable[str] = (),
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    return run_meta_agent(
        out_dir=out_dir,
        h0_run_dirs=h0_run_dirs,
        current_meta_skill=current_meta_skill,
        codex_bin=codex_bin,
        objective="token_cost",
        prior_run_dirs=prior_run_dirs,
        prior_meta_output_path=prior_meta_output_path,
        prior_summary_path=prior_summary_path,
        design_brief_path=design_brief_path,
        forbidden_terms=forbidden_terms,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )


def run_small_model_meta_agent(
    *,
    out_dir: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
    codex_bin: Path,
    baseline_run_dirs: Iterable[Path] = (),
    prior_run_dirs: Iterable[Path] = (),
    prior_meta_output_path: Path | None = None,
    prior_summary_path: Path | None = None,
    forbidden_terms: Iterable[str] = (),
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    return run_meta_agent(
        out_dir=out_dir,
        h0_run_dirs=h0_run_dirs,
        current_meta_skill=current_meta_skill,
        codex_bin=codex_bin,
        objective="small_model_solve_rate",
        baseline_run_dirs=baseline_run_dirs,
        prior_run_dirs=prior_run_dirs,
        prior_meta_output_path=prior_meta_output_path,
        prior_summary_path=prior_summary_path,
        forbidden_terms=forbidden_terms,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )


def run_information_gain_meta_agent(
    *,
    out_dir: Path,
    h0_run_dirs: Iterable[Path],
    current_meta_skill: str,
    codex_bin: Path,
    prior_run_dirs: Iterable[Path] = (),
    prior_meta_output_path: Path | None = None,
    prior_summary_path: Path | None = None,
    forbidden_terms: Iterable[str] = (),
    model: str = "gpt-5.6-sol",
    reasoning_effort: str = "high",
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    return run_meta_agent(
        out_dir=out_dir,
        h0_run_dirs=h0_run_dirs,
        current_meta_skill=current_meta_skill,
        codex_bin=codex_bin,
        objective="information_gain",
        prior_run_dirs=prior_run_dirs,
        prior_meta_output_path=prior_meta_output_path,
        prior_summary_path=prior_summary_path,
        forbidden_terms=forbidden_terms,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )
