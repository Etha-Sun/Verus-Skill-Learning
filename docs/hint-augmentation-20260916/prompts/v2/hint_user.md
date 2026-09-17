Produce one hint for the checkpoint identified below. The original final proof is available to you as privileged evidence, but the continuation solver will receive only the task, the checkpoint code, the existing solver protocol, and your hint_text.

# Selected task and checkpoint
{{task_and_checkpoint_json}}

# Original task instructions and immutable input.rs
{{original_task_json}}

# Current checkpoint: full code and its actual recorded diagnostic
{{checkpoint_json}}

# Complete original trajectory (chronological records)
{{original_trajectory_json}}

# Original source snapshots (content-addressed; events refer to their hashes)
{{source_snapshots_json}}

# Original final verified proof and validation evidence
{{original_final_json}}

# Evidence index: IDs permitted in evidence_refs
{{evidence_index_json}}

The actor-facing hint must explain the logical gap and the next proof objective in natural language; do not supply Verus statements, replacement snippets, or an exact edit recipe.

Before returning, check both the main proof blocker and relevant structural differences from the original input. If the evidence supports a compatibility concern, include one concise reminder and distinguish an observed failure from an untested risk. Do not infer that a removed import caused Lynette failure merely because the cleaned final proof passed.

Return the JSON object specified by the system instructions. The focus is useful continuation evidence for SkillOpt, not mandatory strategy novelty or copying the original next edit. Do not silently infer that the current checkpoint passed both validators merely because the original final proof did.
