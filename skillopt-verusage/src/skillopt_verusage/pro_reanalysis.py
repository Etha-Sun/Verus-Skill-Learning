from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, cast

from openai import OpenAI


MODEL = "deepseek-v4-pro"
MAX_OUTPUT_TOKENS = 384_000
PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing"
PRICE_CACHE_HIT_PER_M = 0.003625
PRICE_CACHE_MISS_PER_M = 0.435
PRICE_OUTPUT_PER_M = 0.87


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(vars(value))


def _usage_cost(usage: dict[str, Any]) -> float:
    prompt = int(usage.get("prompt_tokens", 0) or 0)
    cache_hit = int(usage.get("prompt_cache_hit_tokens", 0) or 0)
    cache_miss = usage.get("prompt_cache_miss_tokens")
    if cache_miss is None:
        cache_miss = max(prompt - cache_hit, 0)
    completion = int(usage.get("completion_tokens", 0) or 0)
    return (
        cache_hit * PRICE_CACHE_HIT_PER_M
        + int(cache_miss) * PRICE_CACHE_MISS_PER_M
        + completion * PRICE_OUTPUT_PER_M
    ) / 1_000_000


def _load_training_evidence(source_run: Path) -> tuple[str, str, list[dict[str, Any]], dict[str, Any]]:
    step_dir = source_run / "steps" / "step_0001"
    prediction_dir = step_dir / "rollout" / "predictions"
    initial_skill = (source_run / "selection_eval_baseline" / "skill.md").read_text(
        encoding="utf-8"
    )
    rejected_skill = (step_dir / "candidate_skill.md").read_text(encoding="utf-8")
    evidence: list[dict[str, Any]] = []
    for task_dir in sorted(prediction_dir.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith("_"):
            continue
        result_path = task_dir / "result.json"
        conversation_path = task_dir / "conversation.json"
        if not result_path.is_file() or not conversation_path.is_file():
            raise ValueError(f"incomplete training evidence: {task_dir}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("fidelity") == "V0_INVALID":
            raise ValueError(f"invalid training result: {task_dir.name}")
        evidence.append(
            {
                "training_item_id": result["id"],
                "task_type": result.get("task_type"),
                "strict_success": bool(result.get("hard")),
                "final_verus_passed": bool(result.get("final_verus_passed")),
                "final_lynette_passed": bool(result.get("final_lynette_passed")),
                "fail_reason": result.get("fail_reason"),
                "request_count": result.get("request_count"),
                "conversation": json.loads(
                    conversation_path.read_text(encoding="utf-8")
                ),
            }
        )
    if len(evidence) != 40:
        raise ValueError(f"expected 40 training trajectories, found {len(evidence)}")
    summary = json.loads((source_run / "summary.json").read_text(encoding="utf-8"))
    step = json.loads((step_dir / "step_record.json").read_text(encoding="utf-8"))
    aggregate = {
        "training_strict_successes": sum(row["strict_success"] for row in evidence),
        "training_total": len(evidence),
        "selection_initial_score": summary["baseline_selection_hard"],
        "selection_rejected_candidate_score": step["selection_hard"],
        "selection_detail_visibility": "aggregate scores only; no selection trajectories",
    }
    return initial_skill, rejected_skill, evidence, aggregate


def _analysis_messages(
    initial_skill: str,
    rejected_skill: str,
    evidence: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> list[dict[str, str]]:
    system = """You are the optimizer-side analyst for a Verus proof-repair skill.
Use as much internal analysis as needed. Infer only from the supplied training
trajectories and the aggregate selection scores. Do not infer selection-task
details. Diagnose semantic overgeneralization, contradictions, task-specific
leakage, prompt bloat, and missing negative scope.

Benchmark contract: the original task source is immutable trusted context.
Existing declarations, attributes, specifications, external_body annotations,
and helper lemmas may be referenced or called when the original program permits
it. A candidate must never introduce, delete, or modify such trusted context.
Do not conflate use of an existing declaration with introduction of a bypass.
A Lynette failure establishes an edit-scope failure, but does not by itself
identify which edit caused it. Do not make a causal claim without direct paired
edit evidence from the supplied trajectory.

Return one JSON object with keys: diagnosis, supported_principles,
rejected_principles, evidence_map, proposed_appendix. The analysis fields may
be as detailed as useful. proposed_appendix is the only candidate artifact:
it must contain at most two atomic globally applicable rules, at most 300
English words, no task names or identifiers, no concrete code/formula/example,
and no blanket prohibition on using trusted declarations already present in
the input. It must distinguish introducing a new verification bypass from
using frozen trusted context. Do not rewrite or repeat the seed skill."""
    user = (
        "## Immutable seed skill\n"
        + initial_skill
        + "\n\n## Rejected Flash-generated candidate metadata\n"
        + json.dumps(
            {
                "bytes": len(rejected_skill.encode("utf-8")),
                "sha256": _sha256(rejected_skill),
                "relationship_to_seed": "generated expansion; not identical to seed",
            },
            indent=2,
        )
        + "\n\n## Rejected Flash-generated candidate\n"
        + rejected_skill
        + "\n\n## Aggregate outcomes\n"
        + json.dumps(aggregate, ensure_ascii=False, indent=2)
        + "\n\n## Training trajectories\n"
        + json.dumps(evidence, ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _critic_messages(
    initial_skill: str,
    rejected_skill: str,
    analysis: dict[str, Any],
) -> list[dict[str, str]]:
    system = """Act as an adversarial Verus semantics and benchmark-contract
reviewer. Audit the proposed optimizer analysis for false general facts,
contradictions, unsupported universals, safety-contract confusion, and prompt
bloat. A rule may forbid introducing a new bypass, but must not forbid use of
trusted declarations frozen in the original task. Existing trusted declarations
and helper lemmas may be referenced or called; they must not be introduced,
deleted, or modified. A Lynette failure alone does not establish the cause.
Concrete proof identities
or task-specific recipes are not allowed in the final appendix.

Return one JSON object with keys: decision, issues, corrections,
final_appendix. decision must be approve, revise, or reject. final_appendix
must be empty on reject; otherwise it must contain at most two atomic rules,
at most 300 English words, and no code, formula, or example. Preserve the seed
skill by returning only an appendix."""
    user = (
        "## Immutable seed skill\n"
        + initial_skill
        + "\n\n## Previously rejected candidate\n"
        + rejected_skill
        + "\n\n## Pro analysis to audit\n"
        + json.dumps(analysis, ensure_ascii=False, indent=2)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _call_json(
    client: OpenAI,
    messages: list[dict[str, str]],
    stage: str,
    calls_path: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    response = client.chat.completions.create(
        model=MODEL,
        messages=cast(Any, messages),
        max_tokens=MAX_OUTPUT_TOKENS,
        response_format=cast(Any, {"type": "json_object"}),
    )
    choices = response.choices or []
    if not choices:
        raise RuntimeError(f"{stage}: provider returned no choices")
    choice = choices[0]
    finish_reason = str(choice.finish_reason or "")
    content = choice.message.content or ""
    if finish_reason == "length" or not content.strip():
        raise RuntimeError(f"{stage}: incomplete response ({finish_reason or 'empty'})")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{stage}: invalid JSON response: {error}") from error
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{stage}: JSON response is not an object")
    usage = _json_dict(response.usage)
    row = {
        "stage": stage,
        "model_requested": MODEL,
        "model_returned": response.model,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "finish_reason": finish_reason,
        "request_sha256": _sha256(json.dumps(messages, ensure_ascii=False)),
        "messages": messages,
        "content": content,
        "reasoning_content": getattr(choice.message, "reasoning_content", None),
        "usage": usage,
        "estimated_cost_usd": _usage_cost(usage),
        "wall_seconds": time.monotonic() - started,
    }
    with calls_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return parsed


def _normalize_appendix(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "\n".join(f"- {item.strip()}" for item in value if item.strip())
    return ""


def _audit_evidence_claims(
    analysis: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    by_id = {str(row["training_item_id"]): row for row in evidence}
    claims = analysis.get("evidence_map")
    if not isinstance(claims, list):
        return ["analysis evidence_map is missing or not a list"]
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append("analysis evidence_map contains a non-object claim")
            continue
        item_id = str(claim.get("training_item") or claim.get("training_item_id") or "")
        row = by_id.get(item_id)
        if row is None:
            errors.append(f"analysis cites unknown training item: {item_id or '<empty>'}")
            continue
        claimed_success = claim.get("success")
        if isinstance(claimed_success, bool) and claimed_success != row["strict_success"]:
            errors.append(f"analysis contradicts strict success label for {item_id}")
        claim_text = json.dumps(claim, ensure_ascii=False).lower()
        failure_words = r"(?:fail(?:ed|ure)?|reject(?:ed|ion)?)"
        if row["final_lynette_passed"] and (
            re.search(rf"lynette.{{0,100}}{failure_words}", claim_text)
            or re.search(rf"{failure_words}.{{0,100}}lynette", claim_text)
        ):
            errors.append(f"analysis falsely attributes failure to Lynette for {item_id}")
        if row["final_verus_passed"] and (
            re.search(rf"verus.{{0,100}}{failure_words}", claim_text)
            or re.search(rf"{failure_words}.{{0,100}}verus", claim_text)
        ):
            errors.append(f"analysis falsely attributes failure to Verus for {item_id}")
    return errors


def _lint_appendix(appendix: str, initial_skill: str) -> list[str]:
    errors: list[str] = []
    word_count = len(re.findall(r"\b\w+\b", appendix))
    if not appendix.strip():
        errors.append("appendix is empty")
    if word_count > 300:
        errors.append(f"appendix exceeds 300 words: {word_count}")
    if re.search(r"\b[0-9a-f]{20}\b", appendix, flags=re.IGNORECASE):
        errors.append("appendix contains a task-like identifier")
    forbidden_fragments = ("```", "assert(", "forall|", "==>", "==", ".fold_left(")
    for fragment in forbidden_fragments:
        if fragment in appendix:
            errors.append(f"appendix contains concrete code/formula fragment: {fragment}")
    lowered = appendix.lower()
    trusted_terms = ("trusted", "pre-existing", "preexisting", "already present", "existing")
    blanket_bans = ("must not be used", "may not be used", "never use", "do not use")
    if any(term in lowered for term in trusted_terms) and any(
        ban in lowered for ban in blanket_bans
    ):
        errors.append("appendix forbids use of frozen trusted context")
    candidate = initial_skill.rstrip() + "\n\n## Evidence-Grounded Update\n\n" + appendix.strip() + "\n"
    if len(candidate.encode("utf-8")) > 4_000:
        errors.append(f"candidate exceeds 4000 bytes: {len(candidate.encode('utf-8'))}")
    return errors


def run(source_run: Path, out_dir: Path) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    out_dir.mkdir(parents=True, exist_ok=False)
    calls_path = out_dir / "optimizer_calls.jsonl"
    initial_skill, rejected_skill, evidence, aggregate = _load_training_evidence(source_run)
    client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key, timeout=1800)
    analysis = _call_json(
        client,
        _analysis_messages(initial_skill, rejected_skill, evidence, aggregate),
        "pro_analysis",
        calls_path,
    )
    critic = _call_json(
        client,
        _critic_messages(initial_skill, rejected_skill, analysis),
        "pro_critic",
        calls_path,
    )
    appendix = _normalize_appendix(critic.get("final_appendix", ""))
    evidence_errors = _audit_evidence_claims(analysis, evidence)
    lint_errors = evidence_errors + _lint_appendix(appendix, initial_skill)
    decision = str(critic.get("decision", "")).strip().lower()
    ready = decision in {"approve", "revise"} and not lint_errors
    candidate = (
        initial_skill.rstrip()
        + "\n\n## Evidence-Grounded Update\n\n"
        + appendix.strip()
        + "\n"
        if ready
        else ""
    )
    rows = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    usage = {
        "calls": len(rows),
        "prompt_tokens": sum(int(row["usage"].get("prompt_tokens", 0) or 0) for row in rows),
        "completion_tokens": sum(int(row["usage"].get("completion_tokens", 0) or 0) for row in rows),
        "estimated_cost_usd": sum(float(row["estimated_cost_usd"]) for row in rows),
    }
    result = {
        "status": "candidate_ready" if ready else "rejected_by_audit",
        "source_run": str(source_run),
        "model": MODEL,
        "provider_max_output_tokens": MAX_OUTPUT_TOKENS,
        "analysis_budget_policy": "provider maximum; no lower artificial output cap",
        "candidate_word_count": len(re.findall(r"\b\w+\b", candidate)),
        "candidate_bytes": len(candidate.encode("utf-8")),
        "candidate_sha256": _sha256(candidate) if candidate else None,
        "critic_decision": decision,
        "evidence_claim_errors": evidence_errors,
        "lint_errors": lint_errors,
        "usage": usage,
        "pricing": {
            "source": PRICING_URL,
            "cache_hit_per_million": PRICE_CACHE_HIT_PER_M,
            "cache_miss_per_million": PRICE_CACHE_MISS_PER_M,
            "output_per_million": PRICE_OUTPUT_PER_M,
        },
    }
    (out_dir / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "critic.json").write_text(
        json.dumps(critic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if candidate:
        (out_dir / "candidate_skill.md").write_text(candidate, encoding="utf-8")
    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source_run.resolve(), args.out_dir.resolve()), indent=2))


if __name__ == "__main__":
    main()
