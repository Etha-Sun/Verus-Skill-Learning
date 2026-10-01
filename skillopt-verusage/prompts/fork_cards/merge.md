You merge task-level Verus skill-card proposals into a compact card bank.
Each source patch represents one task; checkpoints within it are correlated.

Deduplicate overlapping cards while preserving distinct observable triggers,
actions, verifier validation, and failure boundaries supported by the source
patches. Do not narrow a merged trigger so that it loses one source case, or
turn a conditional failure boundary into a universal prohibition. Preserve
supporting and contradicting evidence paths in the top-level reasoning.
Teacher hints are interventions, not verifier evidence. Repeated occurrences
within a task are not independent support. support_count counts source tasks.

Every edit MUST use op "append" and contain one complete Markdown card with
all four explicit labels: **Trigger:**, **Action:**, **Validate:**,
**Avoid when:**. Preserve the existing skill verbatim. Do not convert cards
to prose insertions, split a card into multiple edits, or insert inside a
sentence. Include at most six nonredundant cards; ranking will retain at most
four. Keep each card at most 700 UTF-8 bytes so four cards plus the seed fit
the 4000-byte total. Do not copy proof code or put task IDs, task-specific
function names, or paths in deployable card content. Keep those in reasoning.

Return JSON only:
{"reasoning":"evidence and consolidation rationale","edits":[
  {"op":"append","content":"### Title\n\n**Trigger:** ...\n**Action:** ...\n**Validate:** ...\n**Avoid when:** ...",
   "support_count":1,"source_type":"failure"}
]}
