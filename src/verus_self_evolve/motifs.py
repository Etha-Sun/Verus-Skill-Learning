from __future__ import annotations

from .models import Trace


MOTIF_KEYWORDS = {
    "temporal": (
        "always",
        "eventually",
        "leads_to",
        "weak_fairness",
        "tla_forall",
        "tla_exists",
        "init_invariant",
        "stable",
    ),
    "quantifier": ("forall", "exists", "trigger"),
    "arithmetic": ("mod", "div", "mul", "sub", "add", "aligned", "pow2", "nat", "int"),
    "bitvector": ("bit", "mask", "bitmap", "addr_mask", "flag"),
    "sequence_set_map": ("seq", "set", "map", "filter", "fold", "append", "subrange"),
    "induction": ("rec", "recursive", "induct", "rank"),
    "refinement": ("refines", "refinement", "interp", "view", "marshal", "serialize"),
    "state_machine": ("state", "step", "transition", "next", "invariant", "preserves"),
}


def trace_text(trace: Trace) -> str:
    parts = [trace.project, trace.file]
    parts.extend(trace.lemmas)
    parts.extend(trace.recursive_functions)
    parts.extend(trace.opaque_functions)
    return " ".join(parts).lower()


def motifs_for_trace(trace: Trace) -> tuple[str, ...]:
    text = trace_text(trace)
    motifs = []
    for motif, keywords in MOTIF_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            motifs.append(motif)
    if trace.opaque_functions:
        motifs.append("opaque")
    if trace.recursive_functions:
        motifs.append("recursive")
    return tuple(sorted(set(motifs)))

