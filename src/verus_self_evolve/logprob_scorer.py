from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .data_layout import validate_output_path


@dataclass(frozen=True)
class TokenScore:
    token_index: int
    token_id: int
    token: str
    prob: float
    logprob: float


LN2 = math.log(2.0)


def _chat_template_input_ids(tokenized) -> list[int]:
    if hasattr(tokenized, "get") and tokenized.get("input_ids") is not None:
        tokenized = tokenized["input_ids"]
    if tokenized and isinstance(tokenized[0], list):
        tokenized = tokenized[0]
    return list(tokenized)


def _context_token_ids(
    tokenizer,
    context: str,
    prompt_format: str,
    assistant_prefix: str = "",
) -> list[int]:
    if prompt_format == "raw":
        token_ids = list(tokenizer.encode(context, add_special_tokens=False))
        return token_ids + list(tokenizer.encode(assistant_prefix, add_special_tokens=False))
    if prompt_format == "chat_direct":
        rendered = tokenizer.apply_chat_template(
            [{"role": "user", "content": context}],
            tokenize=False,
            add_generation_prompt=False,
        )
        token_ids = list(tokenizer.encode(rendered + "<|im_start|>assistant\n", add_special_tokens=False))
        return token_ids + list(tokenizer.encode(assistant_prefix, add_special_tokens=False))
    if prompt_format not in {"chat", "chat_nonthinking"}:
        raise ValueError(f"unknown prompt format: {prompt_format}")
    if not getattr(tokenizer, "chat_template", None):
        raise ValueError("chat prompt format requires a tokenizer chat_template")
    token_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": context}],
        tokenize=True,
        add_generation_prompt=True,
        **({"enable_thinking": False} if prompt_format == "chat_nonthinking" else {}),
    )
    token_ids = _chat_template_input_ids(token_ids)
    return token_ids + list(tokenizer.encode(assistant_prefix, add_special_tokens=False))


def _context_target_ids(
    tokenizer,
    context: str,
    target: str,
    prompt_format: str,
    assistant_prefix: str = "",
) -> tuple[list[int], list[int]]:
    context_ids = _context_token_ids(tokenizer, context, prompt_format, assistant_prefix=assistant_prefix)
    target_ids = list(tokenizer.encode(target, add_special_tokens=False))
    return context_ids, target_ids


def normalize_log_scores(log_scores: dict[str, float]) -> dict[str, float]:
    if not log_scores:
        return {}
    maximum = max(log_scores.values())
    weights = {key: math.exp(value - maximum) for key, value in log_scores.items()}
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def entropy_bits(probabilities: dict[str, float]) -> float:
    return -sum(prob * math.log2(prob) for prob in probabilities.values() if prob > 0.0)


def information_density_bits(utility_bits: float, intervention_token_count: int) -> float | None:
    return utility_bits / intervention_token_count if intervention_token_count else None


def action_distribution_metrics(
    baseline_log_scores: dict[str, float],
    artifact_log_scores: dict[str, float],
    target: str,
) -> dict[str, object]:
    baseline = normalize_log_scores(baseline_log_scores)
    artifact = normalize_log_scores(artifact_log_scores)
    if target not in baseline or target not in artifact:
        raise ValueError(f"target {target!r} missing from candidate action scores")
    base_prob = baseline[target]
    artifact_prob = artifact[target]
    pmi_nats = math.log(artifact_prob) - math.log(base_prob)
    base_order = sorted(baseline, key=lambda key: (-baseline[key], key))
    artifact_order = sorted(artifact, key=lambda key: (-artifact[key], key))
    base_entropy = entropy_bits(baseline)
    artifact_entropy = entropy_bits(artifact)
    baseline_candidate_raw_mass = sum(math.exp(value) for value in baseline_log_scores.values())
    artifact_candidate_raw_mass = sum(math.exp(value) for value in artifact_log_scores.values())
    return {
        "baseline_probabilities": baseline,
        "artifact_probabilities": artifact,
        "observed_action_probability_baseline": base_prob,
        "observed_action_probability_artifact": artifact_prob,
        "observed_action_probability_delta": artifact_prob - base_prob,
        "decision_pmi_nats": pmi_nats,
        "decision_pmi_bits": pmi_nats / LN2,
        "entropy_baseline_bits": base_entropy,
        "entropy_artifact_bits": artifact_entropy,
        "entropy_reduction_bits": base_entropy - artifact_entropy,
        "observed_action_rank_baseline": base_order.index(target) + 1,
        "observed_action_rank_artifact": artifact_order.index(target) + 1,
        "observed_action_top1_baseline": base_order[0] == target,
        "observed_action_top1_artifact": artifact_order[0] == target,
        "baseline_candidate_raw_mass": baseline_candidate_raw_mass,
        "artifact_candidate_raw_mass": artifact_candidate_raw_mass,
    }


def _load_hf(model_path: str, device: str):
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "HF scoring requires torch and transformers. Install them in the active environment "
            "or use this command only in the QwQ scorer environment."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        model_path,
        torch_dtype="auto",
        device_map="balanced" if device == "auto" else None,
        trust_remote_code=True,
        attn_implementation="flash_attention_2",
    )
    if device != "auto":
        model = model.to(device)
    model.eval()
    return torch, tokenizer, model


def score_target_hf(
    model_path: str,
    context: str,
    target: str,
    device: str = "auto",
    prompt_format: str = "raw",
    assistant_prefix: str = "",
    prefill_chunk_size: int = 2048,
    score_chunk_size: int = 128,
    progress_callback=None,
) -> list[TokenScore]:
    torch, tokenizer, model = _load_hf(model_path, device)
    return score_target_hf_loaded(
        torch,
        tokenizer,
        model,
        context,
        target,
        prompt_format=prompt_format,
        assistant_prefix=assistant_prefix,
        prefill_chunk_size=prefill_chunk_size,
        score_chunk_size=score_chunk_size,
        progress_callback=progress_callback,
    )


def _scores_from_logits(torch, tokenizer, logits, token_ids: list[int], start_index: int) -> list[TokenScore]:
    if not token_ids:
        return []
    target_tensor = torch.tensor(token_ids, dtype=torch.long, device=logits.device)
    target_logits = logits.gather(-1, target_tensor.unsqueeze(-1)).squeeze(-1).float()
    log_normalizer = torch.logsumexp(logits.float(), dim=-1)
    logprobs = (target_logits - log_normalizer).detach().cpu().tolist()
    return [
        TokenScore(
            token_index=start_index + offset,
            token_id=int(token_id),
            token=tokenizer.decode([token_id]),
            prob=math.exp(float(logprob)),
            logprob=float(logprob),
        )
        for offset, (token_id, logprob) in enumerate(zip(token_ids, logprobs))
    ]


def score_target_hf_loaded(
    torch,
    tokenizer,
    model,
    context: str,
    target: str,
    prompt_format: str = "raw",
    assistant_prefix: str = "",
    prefill_chunk_size: int = 2048,
    score_chunk_size: int = 128,
    progress_callback=None,
) -> list[TokenScore]:
    context_token_ids, target_token_ids = _context_target_ids(
        tokenizer, context, target, prompt_format, assistant_prefix=assistant_prefix
    )
    if not target_token_ids:
        return []
    if not context_token_ids:
        raise ValueError("teacher-forced scoring requires at least one context token")
    input_device = model.get_input_embeddings().weight.device
    past_key_values = None
    next_token_logits = None
    with torch.inference_mode():
        for start in range(0, len(context_token_ids), prefill_chunk_size):
            chunk = context_token_ids[start : start + prefill_chunk_size]
            output = model(
                input_ids=torch.tensor([chunk], dtype=torch.long, device=input_device),
                past_key_values=past_key_values,
                use_cache=True,
                logits_to_keep=1,
            )
            past_key_values = output.past_key_values
            next_token_logits = output.logits[0, -1, :].clone()

        assert next_token_logits is not None
        scores = _scores_from_logits(
            torch, tokenizer, next_token_logits.unsqueeze(0), [target_token_ids[0]], 0
        )
        if progress_callback:
            progress_callback(1)
        for start in range(0, len(target_token_ids), score_chunk_size):
            chunk = target_token_ids[start : start + score_chunk_size]
            if start:
                scores.extend(
                    _scores_from_logits(
                        torch, tokenizer, next_token_logits.unsqueeze(0), [chunk[0]], start
                    )
                )
                if progress_callback:
                    progress_callback(1)
            output = model(
                input_ids=torch.tensor([chunk], dtype=torch.long, device=input_device),
                past_key_values=past_key_values,
                use_cache=True,
                logits_to_keep=len(chunk),
            )
            past_key_values = output.past_key_values
            if len(chunk) > 1:
                scores.extend(
                    _scores_from_logits(
                        torch,
                        tokenizer,
                        output.logits[0, :-1, :],
                        chunk[1:],
                        start + 1,
                    )
                )
                if progress_callback:
                    progress_callback(len(chunk) - 1)
            next_token_logits = output.logits[0, -1, :].clone()
    if len(scores) != len(target_token_ids):
        raise AssertionError(f"scored {len(scores)} of {len(target_token_ids)} target tokens")
    return scores


def _logprob_value(value) -> float:
    if hasattr(value, "logprob"):
        return float(value.logprob)
    if isinstance(value, dict) and "logprob" in value:
        return float(value["logprob"])
    return float(value)


def score_target_vllm(
    model_path: str,
    context: str,
    target: str,
    tensor_parallel_size: int = 4,
    max_model_len: int = 4096,
    gpu_memory_utilization: float = 0.8,
    prompt_format: str = "raw",
    assistant_prefix: str = "",
) -> list[TokenScore]:
    try:
        from vllm import LLM, SamplingParams
    except ImportError as exc:
        raise RuntimeError("vLLM scoring requires vllm in the active environment.") from exc

    llm = LLM(
        model=model_path,
        tensor_parallel_size=tensor_parallel_size,
        max_model_len=max_model_len,
        gpu_memory_utilization=gpu_memory_utilization,
        trust_remote_code=True,
    )
    return score_target_vllm_loaded(
        llm, context, target, prompt_format=prompt_format, assistant_prefix=assistant_prefix
    )


def score_target_vllm_loaded(
    llm,
    context: str,
    target: str,
    prompt_format: str = "raw",
    assistant_prefix: str = "",
) -> list[TokenScore]:
    from vllm import SamplingParams

    tokenizer = llm.get_tokenizer()
    context_ids, target_ids = _context_target_ids(
        tokenizer, context, target, prompt_format, assistant_prefix=assistant_prefix
    )
    prompt_ids = context_ids + target_ids
    if not target_ids:
        return []

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=1,
        prompt_logprobs=1,
    )
    outputs = llm.generate([{"prompt_token_ids": prompt_ids}], sampling_params=sampling_params)
    prompt_logprobs = outputs[0].prompt_logprobs
    scores: list[TokenScore] = []
    start = len(context_ids)
    for i, token_id in enumerate(target_ids):
        pos = start + i
        entry = prompt_logprobs[pos] if pos < len(prompt_logprobs) else None
        if entry is None:
            raise RuntimeError(f"vLLM did not return prompt logprob for target token position {pos}")
        if token_id not in entry:
            available = ", ".join(str(k) for k in list(entry.keys())[:5])
            raise RuntimeError(
                f"vLLM prompt_logprobs missing target token id {token_id} at position {pos}; available: {available}"
            )
        logprob = _logprob_value(entry[token_id])
        token = tokenizer.decode([token_id])
        scores.append(
            TokenScore(
                token_index=i,
                token_id=int(token_id),
                token=token,
                prob=math.exp(logprob),
                logprob=logprob,
            )
        )
    return scores


def score_file(args: argparse.Namespace) -> None:
    context = Path(args.context).read_text(errors="replace")
    target = Path(args.target).read_text(errors="replace")
    scores = score_target_hf(
        args.model_path,
        context=context,
        target=target,
        device=args.device,
        prompt_format=args.prompt_format,
    )
    out_path = validate_output_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for score in scores:
            f.write(json.dumps(score.__dict__, ensure_ascii=False) + "\n")
    aggregate = {
        "model_path": args.model_path,
        "context": args.context,
        "target": args.target,
        "token_count": len(scores),
        "sum_logprob": sum(row.logprob for row in scores),
        "avg_logprob": sum(row.logprob for row in scores) / len(scores) if scores else None,
    }
    Path(str(out_path) + ".summary.json").write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n")


def _score_cached(
    cache: dict[tuple[str, str, str, str], list[TokenScore]],
    args: argparse.Namespace,
    context: str,
    target: str,
    assistant_prefix: str = "",
    vllm_llm=None,
    hf_runtime=None,
    progress_callback=None,
) -> list[TokenScore]:
    key = (args.prompt_format, assistant_prefix, context, target)
    cache_hit = key in cache
    if not cache_hit:
        if args.backend == "hf":
            if hf_runtime is None:
                cache[key] = score_target_hf(
                    args.model_path,
                    context=context,
                    target=target,
                    device=args.device,
                    prompt_format=args.prompt_format,
                    assistant_prefix=assistant_prefix,
                    prefill_chunk_size=args.prefill_chunk_size,
                    score_chunk_size=args.score_chunk_size,
                    progress_callback=progress_callback,
                )
            else:
                cache[key] = score_target_hf_loaded(
                    *hf_runtime,
                    context=context,
                    target=target,
                    prompt_format=args.prompt_format,
                    assistant_prefix=assistant_prefix,
                    prefill_chunk_size=args.prefill_chunk_size,
                    score_chunk_size=args.score_chunk_size,
                    progress_callback=progress_callback,
                )
        elif args.backend == "vllm":
            if vllm_llm is not None:
                cache[key] = score_target_vllm_loaded(
                    vllm_llm,
                    context=context,
                    target=target,
                    prompt_format=args.prompt_format,
                    assistant_prefix=assistant_prefix,
                )
            else:
                cache[key] = score_target_vllm(
                    args.model_path,
                    context=context,
                    target=target,
                    tensor_parallel_size=args.tensor_parallel_size,
                    max_model_len=args.max_model_len,
                    gpu_memory_utilization=args.gpu_memory_utilization,
                    prompt_format=args.prompt_format,
                    assistant_prefix=assistant_prefix,
                )
        else:
            raise ValueError(f"unknown backend: {args.backend}")
    if progress_callback and (cache_hit or args.backend == "vllm"):
        progress_callback(len(cache[key]))
    return cache[key]


def _resolve_prepared_prompt_format(cases: list[dict[str, object]], requested: str | None) -> str:
    if any(not case.get("prepared_prompt_format") for case in cases):
        raise ValueError("every scoring case must declare prepared_prompt_format")
    if any(case.get("prepared_intervention_token_count") is None for case in cases):
        raise ValueError("every scoring case must declare prepared_intervention_token_count")
    prepared_formats = {str(case["prepared_prompt_format"]) for case in cases}
    if requested is None:
        if len(prepared_formats) != 1:
            raise ValueError("--prompt-format is required when cases do not declare one unique prepared format")
        return prepared_formats.pop()
    if prepared_formats != {requested}:
        raise ValueError(f"scoring prompt format {requested!r} differs from prepared cases {prepared_formats}")
    return requested


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _jsonl_text(rows: list[dict[str, object]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def _case_fingerprint(case: dict[str, object], args: argparse.Namespace) -> str:
    payload = {
        "output_schema_version": 2,
        "case": case,
        "model_path": args.model_path,
        "backend": args.backend,
        "prompt_format": args.prompt_format,
        "max_model_len": args.max_model_len,
        "language_model_only": bool(args.language_model_only),
        "chunk_size": args.chunk_size,
        "prefill_chunk_size": args.prefill_chunk_size,
        "score_chunk_size": args.score_chunk_size,
        "observed_target_only": bool(args.observed_target_only),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _target_chunk_metrics(
    baseline: list[TokenScore], artifact: list[TokenScore], chunk_size: int
) -> list[dict[str, object]]:
    if len(baseline) != len(artifact):
        raise ValueError("baseline and artifact target token counts differ")
    if [row.token_id for row in baseline] != [row.token_id for row in artifact]:
        raise ValueError("baseline and artifact target tokenizations differ")
    chunks = []
    for start in range(0, len(baseline), chunk_size):
        end = min(start + chunk_size, len(baseline))
        base_sum = sum(row.logprob for row in baseline[start:end])
        artifact_sum = sum(row.logprob for row in artifact[start:end])
        chunks.append(
            {
                "chunk_index": start // chunk_size,
                "token_start": start,
                "token_end_exclusive": end,
                "token_count": end - start,
                "sum_logprob_baseline": base_sum,
                "sum_logprob_artifact": artifact_sum,
                "loglikelihood_delta_nats": artifact_sum - base_sum,
                "loglikelihood_delta_bits": (artifact_sum - base_sum) / LN2,
            }
        )
    return chunks


def _checkpoint_complete(case_dir: Path, fingerprint: str) -> bool:
    aggregate_path = case_dir / "aggregate.json"
    token_path = case_dir / "token_scores.jsonl"
    if not aggregate_path.exists() or not token_path.exists():
        return False
    try:
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return aggregate.get("case_fingerprint") == fingerprint


def _materialize_checkpoints(cases: list[dict[str, object]], checkpoint_root: Path, out_dir: Path) -> None:
    token_parts = []
    aggregate_rows = []
    distribution_rows = []
    for case in cases:
        case_dir = checkpoint_root / str(case["case_id"])
        token_parts.append((case_dir / "token_scores.jsonl").read_text(encoding="utf-8"))
        aggregate_rows.append(json.loads((case_dir / "aggregate.json").read_text(encoding="utf-8")))
        distribution_path = case_dir / "action_distribution.json"
        if distribution_path.exists():
            distribution_rows.append(json.loads(distribution_path.read_text(encoding="utf-8")))
    _atomic_write_text(out_dir / "token_scores.jsonl", "".join(token_parts))
    _atomic_write_text(out_dir / "aggregates.jsonl", _jsonl_text(aggregate_rows))
    _atomic_write_text(out_dir / "action_distributions.jsonl", _jsonl_text(distribution_rows))


def score_cases(args: argparse.Namespace) -> None:
    cases_path = Path(args.cases)
    out_dir = validate_output_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    token_path = out_dir / "token_scores.jsonl"
    aggregate_path = out_dir / "aggregates.jsonl"
    distribution_path = out_dir / "action_distributions.jsonl"
    checkpoint_root = out_dir / "checkpoints"
    cases = []
    with cases_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    if args.target_types:
        target_types = set(args.target_types)
        cases = [case for case in cases if case["target_type"] in target_types]
    if args.artifact_types:
        artifact_types = set(args.artifact_types)
        cases = [case for case in cases if case["artifact_type"] in artifact_types]
    if args.sample_ids:
        sample_ids = set(args.sample_ids)
        cases = [case for case in cases if case["sample_id"] in sample_ids]
    if args.max_cases is not None:
        cases = cases[: args.max_cases]
    args.prompt_format = _resolve_prepared_prompt_format(cases, args.prompt_format)

    cache: dict[tuple[str, str, str, str], list[TokenScore]] = {}
    vllm_llm = None
    hf_runtime = None
    metric_tokenizer = None
    if args.backend == "vllm":
        try:
            from vllm import LLM
        except ImportError as exc:
            raise RuntimeError("vLLM scoring requires vllm in the active environment.") from exc
        vllm_llm = LLM(
            model=args.model_path,
            tensor_parallel_size=args.tensor_parallel_size,
            max_model_len=args.max_model_len,
            gpu_memory_utilization=args.gpu_memory_utilization,
            trust_remote_code=True,
            language_model_only=args.language_model_only,
        )
        metric_tokenizer = vllm_llm.get_tokenizer()
    else:
        hf_runtime = _load_hf(args.model_path, args.device)
        metric_tokenizer = hf_runtime[1]

    try:
        from tqdm.auto import tqdm
    except ImportError as exc:
        raise RuntimeError("case scoring requires tqdm for observable progress") from exc

    target_token_work = sum(
        2
        * sum(
            len(metric_tokenizer.encode(str(candidate), add_special_tokens=False))
            for candidate in (
                [case["target_text"]]
                if args.observed_target_only
                else (case.get("candidate_targets", []) or [case["target_text"]])
            )
        )
        for case in cases
    )
    resumed_cases = 0
    with (
        tqdm(cases, desc="IG cases", unit="case", disable=args.no_progress) as case_bar,
        tqdm(
            total=target_token_work,
            desc="Target tokens",
            unit="tok",
            disable=args.no_progress,
        ) as token_bar,
    ):
        for case in case_bar:
            target = str(case["target_text"])
            assistant_prefix = str(case.get("assistant_prefix", ""))
            candidate_targets = (
                [target]
                if args.observed_target_only
                else ([str(value) for value in case.get("candidate_targets", [])] or [target])
            )
            fingerprint = _case_fingerprint(case, args)
            case_dir = checkpoint_root / str(case["case_id"])
            if args.resume and _checkpoint_complete(case_dir, fingerprint):
                resumed_cases += 1
                resumed_tokens = 2 * sum(
                    len(metric_tokenizer.encode(candidate, add_special_tokens=False))
                    for candidate in candidate_targets
                )
                token_bar.update(resumed_tokens)
                case_bar.set_postfix(target=case["target_type"], status="resumed")
                continue

            target_token_count = len(metric_tokenizer.encode(target, add_special_tokens=False))
            context_token_counts = {
                "baseline": len(
                    _context_token_ids(
                        metric_tokenizer,
                        str(case["baseline_context"]),
                        args.prompt_format,
                        assistant_prefix=assistant_prefix,
                    )
                ),
                "artifact_conditioned": len(
                    _context_token_ids(
                        metric_tokenizer,
                        str(case["artifact_context"]),
                        args.prompt_format,
                        assistant_prefix=assistant_prefix,
                    )
                ),
            }
            longest_sequence = max(context_token_counts.values()) + target_token_count
            if longest_sequence > args.max_model_len:
                raise ValueError(
                    f"case {case['case_id']} requires {longest_sequence} tokens, exceeding "
                    f"--max-model-len={args.max_model_len}; no silent truncation is allowed"
                )

            case_bar.set_postfix(
                target=case["target_type"], tokens=target_token_count, artifact=case["artifact_type"]
            )
            score_sets: dict[str, dict[str, list[TokenScore]]] = {
                "baseline": {},
                "artifact_conditioned": {},
            }
            for candidate in candidate_targets:
                for condition, context_key in (
                    ("baseline", "baseline_context"),
                    ("artifact_conditioned", "artifact_context"),
                ):
                    token_bar.set_postfix(
                        case=str(case["case_id"])[:8], target=case["target_type"], condition=condition
                    )
                    score_sets[condition][candidate] = _score_cached(
                        cache,
                        args,
                        str(case[context_key]),
                        candidate,
                        assistant_prefix=assistant_prefix,
                        vllm_llm=vllm_llm,
                        hf_runtime=hf_runtime,
                        progress_callback=token_bar.update,
                    )

            token_rows: list[dict[str, object]] = []
            for condition, candidate_scores in score_sets.items():
                for candidate, scores in candidate_scores.items():
                    for row in scores:
                        token_rows.append(
                            {
                                "case_id": case["case_id"],
                                "sample_id": case["sample_id"],
                                "trace_id": case["trace_id"],
                                "prefix_id": case["prefix_id"],
                                "target_type": case["target_type"],
                                "artifact_type": case["artifact_type"],
                                "condition": condition,
                                "candidate_target": candidate if len(candidate) <= 256 else None,
                                "candidate_target_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
                                "is_observed_target": candidate == target,
                                "token_index": row.token_index,
                                "token_id": row.token_id,
                                "token": row.token,
                                "prob": row.prob,
                                "logprob": row.logprob,
                                "scorer_model": args.model_path,
                                "scorer_backend": args.backend,
                                "prompt_format": args.prompt_format,
                            }
                        )

            baseline_scores = score_sets["baseline"][target]
            artifact_scores = score_sets["artifact_conditioned"][target]
            base_log_scores = {
                candidate: sum(row.logprob for row in scores)
                for candidate, scores in score_sets["baseline"].items()
            }
            artifact_log_scores = {
                candidate: sum(row.logprob for row in scores)
                for candidate, scores in score_sets["artifact_conditioned"].items()
            }
            distribution_metrics: dict[str, object] = {}
            distribution = None
            if len(candidate_targets) > 1:
                distribution_metrics = action_distribution_metrics(base_log_scores, artifact_log_scores, target)
                distribution = {
                    "case_id": case["case_id"],
                    "sample_id": case["sample_id"],
                    "artifact_type": case["artifact_type"],
                    "observed_action_option": target,
                    "observed_action_text": case.get("observed_action_text", ""),
                    "action_accepted": case.get("action_accepted"),
                    "action_options": case.get("action_options", {}),
                    "baseline_log_scores": base_log_scores,
                    "artifact_log_scores": artifact_log_scores,
                    **distribution_metrics,
                }

            base_sum = sum(row.logprob for row in baseline_scores)
            art_sum = sum(row.logprob for row in artifact_scores)
            base_avg = base_sum / len(baseline_scores) if baseline_scores else None
            art_avg = art_sum / len(artifact_scores) if artifact_scores else None
            artifact_text = str(case.get("artifact_text", ""))
            artifact_token_count = len(metric_tokenizer.encode(artifact_text, add_special_tokens=False))
            intervention_token_count = (
                context_token_counts["artifact_conditioned"] - context_token_counts["baseline"]
            )
            if intervention_token_count < 0:
                raise ValueError("artifact context must not be shorter than baseline context")
            prepared_delta = case.get("prepared_intervention_token_count")
            if prepared_delta is None or intervention_token_count != int(prepared_delta):
                raise ValueError(
                    f"case {case['case_id']} intervention delta changed: prepared={prepared_delta}, "
                    f"actual={intervention_token_count}"
                )
            ig_nats = art_sum - base_sum
            ig_bits = ig_nats / LN2
            utility_bits = float(distribution_metrics.get("decision_pmi_bits", ig_bits))
            aggregate = {
                "case_id": case["case_id"],
                "case_fingerprint": fingerprint,
                "sample_id": case["sample_id"],
                "trace_id": case["trace_id"],
                "prefix_id": case["prefix_id"],
                "target_type": case["target_type"],
                "target_sha256": case.get("target_sha256"),
                "artifact_type": case["artifact_type"],
                "observed_action_text": case.get("observed_action_text", ""),
                "action_accepted": case.get("action_accepted"),
                "source_log_path": case.get("source_log_path", ""),
                "source_attempt_index": case.get("source_attempt_index"),
                "option_order_seed": case.get("option_order_seed"),
                "option_map_sha256": case.get("option_map_sha256"),
                "reference_artifact": case.get("reference_artifact"),
                "reference_intervention_token_count": case.get("reference_intervention_token_count"),
                "prepared_intervention_token_count": case.get("prepared_intervention_token_count"),
                "token_match_exact": case.get("token_match_exact"),
                "serialized_target": target,
                "assistant_prefix": assistant_prefix,
                "sum_logprob_baseline": base_sum,
                "sum_logprob_artifact": art_sum,
                "avg_logprob_baseline": base_avg,
                "avg_logprob_artifact": art_avg,
                "target_loglikelihood_ig_nats": ig_nats,
                "target_loglikelihood_ig_bits": ig_bits,
                "target_mean_loglikelihood_delta_nats": (
                    art_avg - base_avg if art_avg is not None and base_avg is not None else None
                ),
                "target_token_count": len(artifact_scores),
                "target_char_count": case["target_char_count"],
                "artifact_text_token_count": artifact_token_count,
                "intervention_token_count": intervention_token_count,
                "information_density_bits_per_intervention_token": information_density_bits(
                    utility_bits, intervention_token_count
                ),
                "context_token_count_baseline": context_token_counts["baseline"],
                "context_token_count_artifact": context_token_counts["artifact_conditioned"],
                "max_sequence_token_count": longest_sequence,
                "sequence_truncated": False,
                "candidate_count": len(candidate_targets),
                "chunk_size": args.chunk_size,
                "target_chunks": _target_chunk_metrics(baseline_scores, artifact_scores, args.chunk_size),
                **distribution_metrics,
                "scorer_model": args.model_path,
                "scorer_backend": args.backend,
                "prompt_format": args.prompt_format,
            }
            _atomic_write_text(case_dir / "token_scores.jsonl", _jsonl_text(token_rows))
            if distribution is not None:
                _atomic_write_text(
                    case_dir / "action_distribution.json",
                    json.dumps(distribution, indent=2, ensure_ascii=False) + "\n",
                )
            _atomic_write_text(
                case_dir / "aggregate.json", json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n"
            )

    _materialize_checkpoints(cases, checkpoint_root, out_dir)

    summary = {
        "cases_path": str(cases_path),
        "case_count": len(cases),
        "token_scores": str(token_path),
        "aggregates": str(aggregate_path),
        "action_distributions": str(distribution_path),
        "model_path": args.model_path,
        "backend": args.backend,
        "prompt_format": args.prompt_format,
        "resumed_case_count": resumed_cases,
        "checkpoint_root": str(checkpoint_root),
        "progress_enabled": not args.no_progress,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "aggregates_sha256": hashlib.sha256(aggregate_path.read_bytes()).hexdigest(),
        "token_scores_sha256": hashlib.sha256(token_path.read_bytes()).hexdigest(),
        "action_distributions_sha256": hashlib.sha256(distribution_path.read_bytes()).hexdigest(),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


def add_score_parser(subparsers) -> None:
    parser = subparsers.add_parser("ig-probe-score-file", help="score one target file with a local HF causal LM")
    parser.add_argument("--model-path", required=True, help="local model path, e.g. QwQ-32B")
    parser.add_argument("--context", required=True, help="context text file")
    parser.add_argument("--target", required=True, help="target text file")
    parser.add_argument("--out", required=True, help="JSONL token score output")
    parser.add_argument("--device", default="auto", help="auto, cuda, cuda:0, or cpu")
    parser.add_argument(
        "--prompt-format", choices=["raw", "chat", "chat_direct", "chat_nonthinking"], default="raw"
    )
    parser.set_defaults(func=score_file)

    cases = subparsers.add_parser("ig-probe-score-cases", help="score IG cases with a local HF causal LM")
    cases.add_argument("--model-path", required=True, help="local model path, e.g. QwQ-32B")
    cases.add_argument("--cases", required=True, help="JSONL produced by ig-probe-build-cases")
    cases.add_argument("--out-dir", required=True, help="output directory for token_scores and aggregates")
    cases.add_argument("--backend", choices=["hf", "vllm"], default="hf")
    cases.add_argument("--device", default="auto", help="auto, cuda, cuda:0, or cpu")
    cases.add_argument("--max-cases", type=int, default=None)
    cases.add_argument("--target-types", nargs="+", default=None)
    cases.add_argument("--artifact-types", nargs="+", default=None)
    cases.add_argument("--sample-ids", nargs="+", default=None)
    cases.add_argument("--tensor-parallel-size", type=int, default=4)
    cases.add_argument(
        "--max-model-len",
        type=int,
        default=131072,
        help="vLLM context limit; all cases are preflighted and over-limit inputs are rejected",
    )
    cases.add_argument("--gpu-memory-utilization", type=float, default=0.8)
    cases.add_argument(
        "--language-model-only",
        action="store_true",
        help="skip multimodal modules when the vLLM model supports text-only loading",
    )
    cases.add_argument("--resume", action="store_true", help="reuse valid per-case atomic checkpoints")
    cases.add_argument("--no-progress", action="store_true", help="disable tqdm progress bars")
    cases.add_argument("--chunk-size", type=int, default=512, help="tokens per reported proof-IG chunk")
    cases.add_argument("--prefill-chunk-size", type=int, default=2048)
    cases.add_argument("--score-chunk-size", type=int, default=128)
    cases.add_argument(
        "--observed-target-only",
        action="store_true",
        help="skip candidate-normalized action metrics and score only the demonstrator target",
    )
    cases.add_argument(
        "--prompt-format", choices=["raw", "chat", "chat_direct", "chat_nonthinking"], default=None
    )
    cases.set_defaults(func=score_cases)
