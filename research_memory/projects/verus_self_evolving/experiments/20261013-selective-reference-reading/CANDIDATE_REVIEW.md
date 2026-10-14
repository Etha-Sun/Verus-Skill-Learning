# Selective-reference candidate review

Historical selective-v1 implementation review. For the current selective-v2
semantic review,23 revised cues and5 corrected navigation Scope prefixes, see
ROUTING_REVIEW_V2.md. Its full-reference byte-preservation statement supersedes
the v1-only statement below; all original rule blocks remain unchanged.

Status: implementation and offline checks complete; user review pending;
evaluation NOT started. This is a coding-assistant review, not an independent
DeepSeek semantic review or a measured inference result. New API cost: USD0.

Run-root suffix: skillopt-verusage/card-organization-20261013-selective-v1/.

## Inspect these files

- candidate/SKILL.md: unchanged Executive and 37 top-level index entries.
- candidate/references/direct-existing-lemma-bridge.md: example three-rule directory.
- candidate/references/direct-existing-lemma-bridge--original-card-003.md:
  complete original rule, original shared scope and conditional links.
- candidate/references/direct-existing-lemma-bridge--full.md: byte-identical old reference.
- control/: byte-identical snapshot of compact-v1 B, not the repaired78 flat A arm.
- candidate_manifest.json: file hashes, 72 original rule hashes, parent evidence,
  78-card coverage, inherited unresolved review items, review/evaluation gates.

## Interface

From candidate/ (or the future isolated actor workspace):

```bash
python3 reference_read.py direct-existing-lemma-bridge
python3 reference_read.py direct-existing-lemma-bridge --rules original-card-003
python3 reference_read.py direct-existing-lemma-bridge --rules original-card-003 original-card-043
python3 reference_read.py direct-existing-lemma-bridge --full
```

The first command returns a directory. Other commands return selected body/bodies
or the original full reference. Single-rule families return the original full
reference immediately. JSON differentiates index/read_single/read_rules/read_full,
rule_ids, body_read, delivered source_card_ids, content bytes and SHA256.
Unknown/repeated IDs, cross-family selections, conflicting flags, changed files,
symlinks and traversal fail rather than silently returning all rules.

## Offline findings

- 37 references: 16 single-rule; 9 two-rule; 10 three-rule; 2 four-rule.
- All 72 rule blocks preserved byte-for-byte, covering each of 78 source cards
  exactly once; family assignment and rule order unchanged.
- Full fallback bytes match original references; all 16 single-rule entry files
  remain byte-identical. No top-level descriptions or Executive text changed.
- Main SKILL: 7,957 -> 8,195 bytes (+238 bytes, about 3.0%); only reader instructions
  grow, not the 37-entry index. No YAML frontmatter was added to this existing
  evaluation-specific plain-Markdown skill package.
- Multi-rule directories: 1,327-2,544 bytes, median 1,760; combined 36,903 bytes
  versus 123,046 bytes for the 21 original full references. This is static size,
  not measured token consumption or an instruction to read all directories.
- Across 56 possible single-rule selections in those families, directory plus
  selected-file content is median 79.46% of the original full-reference bytes.
  Three selections are already larger (maximum 106.79%) because shared context
  and routing overhead outweigh the omitted rules. No post-hoc exception was
  introduced: all 21 multi-rule families still use the approved design.
- Example equal-serialization-to-equal-view rule: directory 1,847 bytes plus
  selected body 3,289 = 5,136, versus whole reference 6,567 (21.79% fewer content
  bytes). This excludes JSON wrappers, new tool-call tokens and conversation
  replay; it is NOT an expected 21.79% inference-cost saving.
- Shared scope/conditional links accompany each selected rule so narrowing the
  payload does not remove applicability restrictions. Multi-select emits shared
  context once. Direct-file reading sees the same scope and restrictions.
- 19 focused tests pass, including exhaustive real-candidate construction,
  full/individual/multi-select preservation and every local Markdown link/anchor.
  Actual generated reader CLI probed for directory, selected rule and full fallback.

## Review attention

Internal title/when/avoid cues are hand-authored source-only routing summaries,
not an LLM-generated replacement for Trigger/Action/Why/Validate/Avoid. Review
whether their distinctions are clear without forcing a strategy. All original
rule constraints remain authoritative. Existing ambiguity in card-018 and the
separate premises of cards 003/043 are retained, not silently resolved.

Scope text and cross-links still contain inherited routing language; they are
not newly optimized. The selective design may increase interaction overhead,
discourage follow-up reads, or lead to a poor choice despite a relevant family.
The next live experiment must measure these risks rather than assuming benefit.

Before launch: approve candidate and a new cost cap, implement both-arm event
classification/package wiring in a new evaluation contract, and perform zero-API
service preflight. Previous USD30 authorization is not silently reused.
