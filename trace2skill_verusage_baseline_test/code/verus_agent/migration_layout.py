from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


CROSS_REFERENCE_NAVIGATION_BOUNDARIES: tuple[str, ...] = (
    "Prefer the card whose applicability names the concrete failed obligation; do not choose a generic contradiction, quantifier, or induction card merely because that syntax could appear in the eventual proof.",
    "For non-overlap, use `verus_global_019` when a required invariant precondition is unavailable and the proof needs guarded case analysis; use `verus_global_020` when a structural agreement lemma can turn assumed overlap directly into key equality.",
    "For hidden facts, use `verus_global_003` for a visible definitional consequence needing a checked instantiation point, `verus_global_022` for an explicitly opaque non-recursive spec, `verus_global_030` for insufficient unfolding of a recursive spec, and `verus_global_026` for extracting a consequence from a recursive predicate whose recommends clause is not a guarantee.",
    "For equality, use `verus_global_001` for field-by-field concrete-to-abstract preservation, `verus_global_010` for abstract predicate equality via an existing mutual-entailment lemma, `verus_global_031` for direct sequence extensionality, `verus_global_034` for direct set membership extensionality, and `verus_global_035` when sets come from sequences and direct membership reasoning has failed.",
)


REFERENCE_SELECTION_BOUNDARIES: dict[str, tuple[str, ...]] = {
    "arithmetic_bounds.md": (
        "Use `verus_global_008` when a decomposition result lacks component bounds required by a downstream call.",
        "Use `verus_global_032` when the immediate obligation is the lower or upper bound for a sequence index, including an indirect length connection.",
        "Use `verus_global_021` when the mathematical goal itself contains nonlinear multiplication, division, or modulo and linear arithmetic is insufficient.",
        "Use `verus_global_023` when Verus reports possible exec arithmetic overflow, especially when spec and exec expressions differ by substitutions or multiplication operand order.",
    ),
    "collections_sets_maps.md": (
        "Use `verus_global_015` for preservation of a universal correspondence invariant after synchronized writes to two structures.",
        "For map-insert preservation, use `verus_global_017` when key inequality must come from collection membership/non-membership; use `verus_global_018` when index ordering directly gives `i != k`.",
        "Use `verus_global_033` for an equal-cardinality subset contradiction with a known missing element; use `verus_global_036` when the goal is only set inequality and one counterexample witness suffices.",
    ),
    "custom_relations_contradiction.md": (
        "Use `verus_global_004` only for an already-isolated impossible branch whose current facts should directly imply false; prefer a specialized card below when an additional bridge, transitivity proof, or invariant split is still required.",
        "Use `verus_global_006` for negating custom equality when a method predicate must first be bridged to spec-view equality.",
        "Use `verus_global_007` for transitivity of a custom ordering, including a relation defined as the negation of another ordering.",
        "Use `verus_global_019` for non-overlap when the usual invariant has an unavailable precondition and the proof must split on that precondition.",
    ),
    "quantifiers_extensionality_part_1.md": (
        "Use `verus_global_009` to move an existing existential witness through an implication or equivalence into another existential.",
        "Use `verus_global_010` for equality of abstract predicate-like values when an extensional lemma expects forward and backward entailment.",
        "Use `verus_global_014` when a recursive universal range splits into the current base index and shifted tail indices.",
        "Use `verus_global_016` when a proof copied the wrong quantifier shape for the actual vstd type-specific predicate.",
        "Use `verus_global_020` for universal non-overlap when a structural agreement lemma makes overlapping distinct keys impossible.",
    ),
    "quantifiers_extensionality_part_2.md": (
        "Use `verus_global_024` to transfer a universally quantified property from an outer ordered range to a contained inner range.",
        "Use `verus_global_025` when an augmented structure extends coverage from indices `[0, N)` to `[0, N+1)` and the proof splits old indices from the new index.",
        "Use `verus_global_031` for direct sequence equality from equal lengths and element-wise indexed equality.",
        "Use `verus_global_034` for direct set equality from two membership implications.",
        "Use `verus_global_035` when both sets are derived from sequences and direct set-membership extensionality cannot expose the needed witnesses; prove the sequences equal first.",
    ),
    "recursive_induction_part_1.md": (
        "Use `verus_global_002` when a backward-recursive range predicate must establish a forward-facing property; this direction mismatch is more specific than generic structural induction.",
        "Use `verus_global_011` for a roundtrip theorem whose induction specifically depends on decomposing `fold_left` into a prefix and last element.",
        "Use `verus_global_026` when a recursive predicate is already known and a simpler consequence must be proved because its recommends clause is not a guarantee.",
        "Use `verus_global_027` when the recursive proof call itself fails because a recommends condition is unavailable and must become an explicit precondition.",
        "Use `verus_global_028` only when the immediate diagnostic is termination/decreases for an otherwise-defined recursive proof function.",
    ),
    "recursive_induction_part_2.md": (
        "Use `verus_global_037` when the proof body lacks the structural induction skeleton: case split, recursive self-call, and decreases measure.",
        "Use `verus_global_029` when the recursive call already provides the inductive hypothesis but Verus cannot reconstruct the current recursive spec case until its conjuncts are asserted explicitly.",
    ),
    "state_invariants_ghost.md": (
        "Prefer `verus_global_012` when an ensures clause explicitly requires a new Ghost-field value but the function body never assigns that field.",
        "Use `verus_global_005` when a property of another field must be re-derived after a sub-structure call whose postcondition provides no usable frame fact.",
        "Use `verus_global_013` when the desired invariant is guarded by a condition unavailable from the current requires clause.",
    ),
    "unfolding_bridges.md": (
        "Use `verus_global_001` when definitions are visible but a concrete-to-abstract equality needs field-by-field decomposition across elements.",
        "Use `verus_global_003` when a visible definitional fact needs a checked helper lemma as a named instantiation point rather than more unfolding.",
        "Use `verus_global_022` when the blocking spec is explicitly opaque or treated as opaque and a local plain `reveal` should expose it.",
        "Use `verus_global_030` when the blocking function is recursive and the proof needs controlled multi-level unfolding with `reveal_with_fuel`.",
    ),
}


@dataclass(frozen=True)
class ReferencePart:
    cluster_id: str
    cluster_title: str
    description: str
    filename: str
    part_number: int
    part_count: int
    cards: list[dict[str, Any]]

    @property
    def title(self) -> str:
        if self.part_count == 1:
            return self.cluster_title
        return f"{self.cluster_title} — Part {self.part_number} of {self.part_count}"


def _split_cards(
    cluster_id: str,
    title: str,
    description: str,
    cards: list[dict[str, Any]],
    render_reference: Callable[[str, str, str, list[dict[str, Any]]], str],
    max_lines: int,
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for card in cards:
        trial = current + [card]
        line_count = len(
            render_reference(cluster_id, title, description, trial).splitlines()
        )
        if current and line_count > max_lines:
            chunks.append(current)
            current = [card]
        else:
            current = trial
        single_lines = len(
            render_reference(cluster_id, title, description, current).splitlines()
        )
        if single_lines > max_lines:
            raise ValueError(
                f"one card cannot fit the {max_lines}-line reference limit: "
                f"{card['skill_id']} ({single_lines} lines)"
            )
    if current:
        chunks.append(current)
    return chunks


def build_parts(
    cluster_specs: tuple[tuple[str, str, str], ...],
    grouped: dict[str, list[dict[str, Any]]],
    render_reference: Callable[[str, str, str, list[dict[str, Any]]], str],
    max_lines: int = 300,
) -> list[ReferencePart]:
    parts: list[ReferencePart] = []
    for cluster_id, title, description in cluster_specs:
        chunks = _split_cards(
            cluster_id,
            title,
            description,
            grouped[cluster_id],
            render_reference,
            max_lines,
        )
        for index, cards in enumerate(chunks, start=1):
            filename = (
                f"{cluster_id}.md"
                if len(chunks) == 1
                else f"{cluster_id}_part_{index}.md"
            )
            parts.append(
                ReferencePart(
                    cluster_id=cluster_id,
                    cluster_title=title,
                    description=description,
                    filename=filename,
                    part_number=index,
                    part_count=len(chunks),
                    cards=cards,
                )
            )
    return parts


def render_index(parts: list[ReferencePart]) -> str:
    """Return the human-consolidated root procedure; parts remain in references."""
    del parts
    canonical_skill = (
        Path(__file__).resolve().parent / "skills/verus-proof-repair/SKILL.md"
    )
    if not canonical_skill.is_file():
        raise ValueError(f"canonical root skill does not exist: {canonical_skill}")
    return canonical_skill.read_text(encoding="utf-8")


def migrate_split(
    source: Path,
    cluster_root: Path,
    output: Path,
    provenance: Path,
    *,
    max_lines: int = 300,
) -> None:
    from .migrate_normalized_skill import (
        CLUSTERS,
        RUNTIME_LIST_FIELDS,
        RUNTIME_SCALAR_FIELDS,
        TIE_BREAKERS,
        _cluster_sources,
        _load_cards,
        _sha256,
        assign_clusters,
        render_reference,
    )

    cards = _load_cards(source)
    grouped = assign_clusters(cards, _cluster_sources(cluster_root))
    parts = build_parts(CLUSTERS, grouped, render_reference, max_lines=max_lines)

    output.mkdir(parents=True, exist_ok=True)
    references = output / "references"
    references.mkdir(parents=True, exist_ok=True)
    for stale in references.glob("*.md"):
        stale.unlink()
    (output / "SKILL.md").write_text(render_index(parts), encoding="utf-8")

    runtime_mapping: dict[str, str] = {}
    cluster_mapping: dict[str, str] = {}
    for part in parts:
        text = render_reference(
            part.cluster_id,
            part.title,
            part.description,
            part.cards,
        )
        if len(text.splitlines()) > max_lines:
            raise ValueError(f"generated reference exceeds {max_lines} lines: {part.filename}")
        (references / part.filename).write_text(text, encoding="utf-8")
        for card in part.cards:
            runtime_mapping[card["skill_id"]] = part.filename
            cluster_mapping[card["skill_id"]] = part.cluster_id

    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        json.dumps(
            {
                "source": str(source.resolve()),
                "source_sha256": _sha256(source),
                "cluster_source_root": str(cluster_root.resolve()),
                "runtime_injected": False,
                "card_count": len(cards),
                "logical_cluster_count": len(CLUSTERS),
                "reference_file_count": len(parts),
                "max_reference_lines": max_lines,
                "tie_breakers": TIE_BREAKERS,
                "mapping": runtime_mapping,
                "cluster_mapping": cluster_mapping,
                "runtime_fields": [
                    field for field, _ in RUNTIME_SCALAR_FIELDS
                ]
                + [field for field, _, _ in RUNTIME_LIST_FIELDS],
                "excluded_runtime_fields": [
                    "source_card_ids",
                    "source_trajectories",
                    "source_mappings",
                    "procedure_abstraction_audit",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
