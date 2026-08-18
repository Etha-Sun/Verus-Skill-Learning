"""Semantic-routed variant of the native Trace2Skill MAP/REDUCE evolver.

The MAP, within-family REDUCE, TRANSLATE, APPLY, and verification phases are
the native implementation.  The only changed construction step is that MAP
items are partitioned by proof mechanism before REDUCE.  Family results are
coalesced deterministically instead of being compressed by one final global
REDUCE call.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

from react_agent.models import Message, ModelSettings
from skill_evolver.parallel_evolving_agent import SemanticPatch, SemanticPatchItem
from skill_evolver.parallel_success_evolving_agent import CombinedParallelSkillEvolver
from skill_evolver.prompt_loader import load_prompt_template


_FAMILY_ID = re.compile(r"^[a-z][a-z0-9_-]*$")
_REFERENCE_FILE = re.compile(r"^references/[a-z0-9][a-z0-9-]*\.md$")

SEMANTIC_ROUTER_SYSTEM_PROMPT = load_prompt_template(
    "semantic_reduce_evolving_agent/router_system_prompt"
)
SEMANTIC_REDUCE_MERGE_GUARD = load_prompt_template(
    "semantic_reduce_evolving_agent/merge_guard"
)


def enumerate_patch_items(patches: list[SemanticPatch]) -> list[dict[str, Any]]:
    """Give every MAP item a stable ID and retain its complete semantic text."""
    rows: list[dict[str, Any]] = []
    for patch_index, patch in enumerate(patches, start=1):
        for item_index, item in enumerate(patch.items, start=1):
            rows.append(
                {
                    "item_id": f"map_{patch_index:04d}_item_{item_index:03d}",
                    "map_patch_index": patch_index,
                    "map_batch_index": patch.batch_index,
                    "patch_reasoning": patch.reasoning,
                    "target_file": item.target_file,
                    "edit_intent": item.edit_intent,
                    "location_hint": item.location_hint,
                    "change_instruction": item.change_instruction,
                }
            )
    return rows


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse one JSON object, accepting an optional fenced response."""
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        if start < 0:
            raise
        value, _ = json.JSONDecoder().raw_decode(candidate[start:])
    if not isinstance(value, dict):
        raise ValueError("semantic router response must be a JSON object")
    return value


def validate_partition(payload: dict[str, Any], expected_item_ids: list[str]) -> None:
    """Require an exact, non-overlapping semantic partition with safe paths."""
    families = payload.get("families")
    if not isinstance(families, list) or not families:
        raise ValueError("semantic partition must contain a non-empty families list")

    family_ids: list[str] = []
    reference_files: list[str] = []
    actual_item_ids: list[str] = []
    for family in families:
        if not isinstance(family, dict):
            raise ValueError("every semantic family must be an object")
        family_id = family.get("family_id")
        reference_file = family.get("reference_file")
        member_ids = family.get("member_item_ids")
        if not isinstance(family_id, str) or not _FAMILY_ID.fullmatch(family_id):
            raise ValueError(f"invalid semantic family_id: {family_id!r}")
        if not isinstance(reference_file, str) or not _REFERENCE_FILE.fullmatch(reference_file):
            raise ValueError(f"invalid semantic reference_file: {reference_file!r}")
        if not isinstance(member_ids, list) or not member_ids or not all(
            isinstance(item_id, str) for item_id in member_ids
        ):
            raise ValueError(f"family {family_id} must contain member_item_ids")
        family_ids.append(family_id)
        reference_files.append(reference_file)
        actual_item_ids.extend(member_ids)

    if len(family_ids) != len(set(family_ids)):
        raise ValueError("semantic family_id values must be unique")
    if len(reference_files) != len(set(reference_files)):
        raise ValueError("semantic reference_file values must be unique")
    if sorted(actual_item_ids) != sorted(expected_item_ids):
        missing = sorted(set(expected_item_ids) - set(actual_item_ids))
        unexpected = sorted(set(actual_item_ids) - set(expected_item_ids))
        duplicates = sorted(
            item_id for item_id in set(actual_item_ids) if actual_item_ids.count(item_id) != 1
        )
        raise ValueError(
            "semantic partition must assign every MAP item exactly once; "
            f"missing={missing}, unexpected={unexpected}, duplicates={duplicates}"
        )


def family_patch(
    family: dict[str, Any],
    rows_by_id: dict[str, dict[str, Any]],
) -> list[SemanticPatch]:
    """Materialize one-item patches routed to a family's canonical reference."""
    reference_file = family["reference_file"]
    title = str(family.get("title", family["family_id"]))
    patches: list[SemanticPatch] = []
    for item_id in family["member_item_ids"]:
        row = rows_by_id[item_id]
        item = SemanticPatchItem(
            target_file=f"SKILL.md, {reference_file}",
            edit_intent=row["edit_intent"],
            location_hint=f"Semantic family: {title}; canonical reference: {reference_file}",
            change_instruction=(
                f"Put detailed guidance for this mechanism in `{reference_file}` and add only "
                "a concise consult-when route in `SKILL.md`. Preserve the evidence-backed "
                "procedure, checks, limitations, and contraindications; do not replace them "
                "with generic advice. Original MAP instruction:\n"
                f"{row['change_instruction']}"
            ),
            source_item_ids=(item_id,),
        )
        patches.append(
            SemanticPatch(
                reasoning=f"{family['family_id']} / {item_id}: {row['patch_reasoning']}",
                items=[item],
                changelog_entries=[f"Route {item_id} to {reference_file}"],
                batch_index=int(row.get("map_batch_index", -1)),
            )
        )
    return patches


def patch_source_item_ids(patches: list[SemanticPatch]) -> list[str]:
    """Flatten source lineage from a semantic patch list in stable order."""
    return [
        item_id
        for patch in patches
        for item in patch.items
        for item_id in item.source_item_ids
    ]


def validate_exact_once_provenance(
    input_patches: list[SemanticPatch],
    output_patches: list[SemanticPatch],
) -> dict[str, Any]:
    """Require a REDUCE output to disposition every input MAP item exactly once."""
    expected = patch_source_item_ids(input_patches)
    actual = patch_source_item_ids(output_patches)
    expected_counts = Counter(expected)
    actual_counts = Counter(actual)
    duplicated_inputs = sorted(
        item_id for item_id, count in expected_counts.items() if count != 1
    )
    missing = sorted((expected_counts - actual_counts).elements())
    unexpected = sorted((actual_counts - expected_counts).elements())
    duplicates = sorted(
        item_id
        for item_id, count in actual_counts.items()
        if count > expected_counts.get(item_id, 0)
    )
    audit = {
        "expected_source_item_ids": expected,
        "actual_source_item_ids": actual,
        "missing_source_item_ids": missing,
        "unexpected_source_item_ids": unexpected,
        "duplicate_source_item_ids": duplicates,
        "duplicated_input_source_item_ids": duplicated_inputs,
        "exact_once": (
            bool(expected)
            and not duplicated_inputs
            and expected_counts == actual_counts
        ),
    }
    if not audit["exact_once"]:
        raise ValueError(
            "semantic REDUCE provenance must preserve every source MAP item exactly once; "
            f"missing={missing}, unexpected={unexpected}, duplicates={duplicates}, "
            f"duplicated_inputs={duplicated_inputs}"
        )
    return audit


def collapse_family_result(
    family: dict[str, Any],
    reduced: SemanticPatch,
) -> SemanticPatch:
    """Bundle a family into one translation unit without dropping any item text.

    Native semantic translation handles each item independently. A new
    reference must therefore be represented by exactly one item, otherwise
    parallel translators could each try to create the same file.
    """
    if not reduced.items:
        raise ValueError(f"within-family REDUCE deleted every item for {family['family_id']}")
    expected_ids = list(family.get("member_item_ids", []))
    actual_ids = patch_source_item_ids([reduced])
    if Counter(expected_ids) != Counter(actual_ids) or len(actual_ids) != len(set(actual_ids)):
        raise ValueError(
            f"family {family['family_id']} final REDUCE provenance does not match its partition"
        )
    reference_file = family["reference_file"]
    sections: list[str] = []
    for index, item in enumerate(reduced.items, start=1):
        sections.extend(
            [
                f"### Preserved family contribution {index}: {item.edit_intent}",
                f"Location hint: {item.location_hint}",
                item.change_instruction,
            ]
        )
    return SemanticPatch(
        reasoning=reduced.reasoning,
        items=[
            SemanticPatchItem(
                target_file=f"SKILL.md, {reference_file}",
                edit_intent=f"Create and route semantic family: {family.get('title', family['family_id'])}",
                location_hint=(
                    f"Create {reference_file}; add one concise consult-when route in SKILL.md"
                ),
                change_instruction=(
                    "Create the canonical reference once. Incorporate every preserved contribution "
                    "below, deduplicating equivalent wording only; retain distinct procedures, "
                    "checks, limitations, and contraindications. Keep SKILL.md to a concise route.\n\n"
                    + "\n\n".join(sections)
                ),
                source_item_ids=tuple(actual_ids),
            )
        ],
        changelog_entries=list(reduced.changelog_entries),
        batch_index=reduced.batch_index,
        raw_markdown=reduced.raw_markdown,
    )


class SemanticReduceParallelSkillEvolver(CombinedParallelSkillEvolver):
    """Combined evolver that applies native REDUCE only within semantic families."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("patch_pipeline", "json") != "markdown":
            raise ValueError("semantic REDUCE requires patch_pipeline='markdown'")
        super().__init__(*args, **kwargs)
        self._merge_system_prompt = (
            self._merge_system_prompt.rstrip() + "\n\n" + SEMANTIC_REDUCE_MERGE_GUARD
        )
        self.semantic_reduce_manifest: dict[str, Any] | None = None
        self.semantic_family_bundles: list[SemanticPatch] = []
        self._provenance_audit_events: list[dict[str, Any]] = []
        self._provenance_audit_lock = Lock()
        self._active_family_id = ""

    def _run_single_merge_markdown(
        self,
        skill_state: dict[str, str],
        patches: list[SemanticPatch],
        level: int,
        merge_idx: int,
    ) -> list[SemanticPatch]:
        """Run native MERGE and reject any output with broken MAP-item lineage."""
        merged = super()._run_single_merge_markdown(
            skill_state, patches, level, merge_idx
        )
        try:
            audit = validate_exact_once_provenance(patches, merged)
        except ValueError as exc:
            audit = {
                "expected_source_item_ids": patch_source_item_ids(patches),
                "actual_source_item_ids": patch_source_item_ids(merged),
                "exact_once": False,
                "error": str(exc),
            }
            with self._provenance_audit_lock:
                self._provenance_audit_events.append(
                    {
                        "family_id": self._active_family_id,
                        "level": level,
                        "merge_index": merge_idx,
                        "input_patch_count": len(patches),
                        "output_patch_count": len(merged),
                        **audit,
                    }
                )
            raise
        with self._provenance_audit_lock:
            self._provenance_audit_events.append(
                {
                    "family_id": self._active_family_id,
                    "level": level,
                    "merge_index": merge_idx,
                    "input_patch_count": len(patches),
                    "output_patch_count": len(merged),
                    **audit,
                }
            )
        return merged

    def _route_semantic_items(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        user_message = (
            "Partition the following complete MAP semantic items. Return JSON only.\n\n"
            + json.dumps({"items": rows}, ensure_ascii=False, indent=2)
        )
        messages = [
            Message(role="system", content=SEMANTIC_ROUTER_SYSTEM_PROMPT),
            Message(role="user", content=user_message),
        ]
        settings = ModelSettings(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            extra_body={"thinking": {"type": "disabled"}},
        )
        response = self.client.chat(messages, settings)
        self._save_prompt_response(
            "semantic_reduce_routing",
            "global_partition",
            SEMANTIC_ROUTER_SYSTEM_PROMPT,
            user_message,
            response,
        )
        payload = parse_json_object(response)
        validate_partition(payload, [row["item_id"] for row in rows])
        return payload

    def run_reduce_phase_markdown(
        self,
        skill_state: dict[str, str],
        patches: list[SemanticPatch],
    ) -> SemanticPatch | None:
        if not patches:
            return None
        rows = enumerate_patch_items(patches)
        if not rows:
            return None
        partition = self._route_semantic_items(rows)
        self._provenance_audit_events = []
        rows_by_id = {row["item_id"]: row for row in rows}
        original_output_dir = self.output_dir
        family_results: list[SemanticPatch] = []
        family_summaries: list[dict[str, Any]] = []
        try:
            for family in partition["families"]:
                self._active_family_id = family["family_id"]
                if original_output_dir is not None:
                    self.output_dir = (
                        Path(original_output_dir)
                        / "semantic_reduce"
                        / "families"
                        / family["family_id"]
                    )
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                routed = family_patch(family, rows_by_id)
                validate_exact_once_provenance(routed, routed)
                reduced = super().run_reduce_phase_markdown(skill_state, routed)
                if reduced is None:
                    raise ValueError(f"within-family REDUCE failed for {family['family_id']}")
                bundled = collapse_family_result(family, reduced)
                family_results.append(bundled)
                bundle_relative_path = (
                    Path("semantic_reduce")
                    / "candidate_units"
                    / f"{len(family_results):04d}_{family['family_id']}.md"
                )
                if original_output_dir is not None:
                    self._save_semantic_patch(
                        bundled, Path(original_output_dir) / bundle_relative_path
                    )
                family_summaries.append(
                    {
                        "family_id": family["family_id"],
                        "title": family.get("title", ""),
                        "reference_file": family["reference_file"],
                        "member_item_ids": list(family["member_item_ids"]),
                        "within_family_reduce_item_count": len(reduced.items),
                        "translation_unit_count": len(bundled.items),
                        "candidate_unit_order": len(family_results),
                        "candidate_unit_path": bundle_relative_path.as_posix(),
                        "source_item_ids": patch_source_item_ids([bundled]),
                    }
                )
        finally:
            self.output_dir = original_output_dir
            self._active_family_id = ""

        self.semantic_family_bundles = list(family_results)
        self.semantic_reduce_manifest = {
            "strategy": "semantic_route_then_native_within_family_reduce",
            "router_thinking": "disabled",
            "map_item_count": len(rows),
            "map_items": [
                {
                    "item_id": row["item_id"],
                    "map_patch_index": row["map_patch_index"],
                    "map_batch_index": row["map_batch_index"],
                }
                for row in rows
            ],
            "family_count": len(family_summaries),
            "families": family_summaries,
            "provenance_audit": {
                "policy": "exactly_once_per_reduce_call",
                "event_count": len(self._provenance_audit_events),
                "rejected_output_count": sum(
                    not event["exact_once"] for event in self._provenance_audit_events
                ),
                "events": sorted(
                    self._provenance_audit_events,
                    key=lambda event: (
                        event["family_id"], event["level"], event["merge_index"]
                    ),
                ),
            },
            "cross_family_llm_reduce": False,
        }
        if original_output_dir is not None:
            manifest_path = Path(original_output_dir) / "semantic_reduce" / "partition.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(self.semantic_reduce_manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return self._coalesce_semantic_patches(family_results)

    def run(self, records: list[dict], input_mode: str = "records") -> dict:
        result = super().run(records, input_mode=input_mode)
        result["reduce_strategy"] = "semantic"
        result["semantic_reduce"] = self.semantic_reduce_manifest
        return result
