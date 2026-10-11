# DeepScientist startup audit and trace experience subproject

## Objective

Determine whether an isolated DeepScientist service can start locally, choose the
subproject location, and make controller-versus-evaluated-model roles explicit.

## Decision

Use `trace-experience-autoresearch/` in this repository for integration code and
reviewed contracts. Canonical research memory stays in `research_memory/`.
Use the existing external run root selected in ignored `.agent-context.local.md`.
The subproject output prefix is `VERUS_SKILL_RUN_ROOT/trace-experience-autoresearch/`;
its `deepscientist/` child is the isolated service home. Do not change the existing
home or its quests. Do not reuse the repository-local `.env` run-root setting:
current output validation rejects repository-overlapping run roots.

Research controller: explicitly pinned Codex runner `gpt-6.1-sol`, effort `high`.
This follows the locally configured model and avoids another provider integration;
it is not evidence that this controller is optimal. Evaluated repair actor remains
`deepseek-v4-pro`, effort `max`, with the existing evaluator. The learned trace
analyzer model is a separate experimental choice, to be frozen across compared
methods; do not silently use the controller model for one experimental arm only.
Official configuration reference checked:
https://learn.chatgpt.com/docs/config-file/config-reference .

## Verified actions and evidence

- npm package is 1.6.0; existing Python environment distribution is 1.5.17.
  Started the existing **1.5.17 Python runtime**, not an upgraded 1.6.0 runtime.
  No install, upgrade, external source edit, or original-home modification.
- Created a fresh isolated service home below the external run root. Config
  validation passed; pinned controller model/high reasoning, workspace-write,
  on-request approval. No automatic retries, global skill synchronization,
  restored sessions, automatic Git checkpoint/push, cloud sync or connectors.
- Direct Python CLI daemon listens on `127.0.0.1:21001`. PID recorded in the
  external receipt. Two health checks returned status `ok`, matching home/PID;
  the web root returned HTTP200. Quest directory empty; sessions empty.
- External root passes `python3 -m verus_self_evolve.data_layout` with the local
  legacy data root: `ok=true`, zero missing directories and zero issues.
- Durable external files: `startup_receipt.json`, `service.pid`, `service.log`,
  and `bootstrap_empty_service.py` under the subproject output prefix.
  Bootstrap is fresh-home-only; it refuses to overwrite an existing home.
  This is a direct daemon, not a launcher-supervised instance: manage the recorded
  PID rather than assuming the npm launcher's `ds --stop` has its state.
- Local machine paths and restart command are in ignored `.agent-context.local.md`.
  Repository integration boundary is documented in
  `../../../../../trace-experience-autoresearch/README.md`.

## Evidence boundary

This establishes empty-service and web readiness only. No provider HELLO probe,
model response, research quest, evaluator integration, new DeepSeek call or paid
experiment was performed. Runtime/package version mismatch remains explicit;
upgrade in an isolated environment if a 1.6-only capability becomes necessary.
The proposed USD15 pilot is still a proposal, not spending authorization.
Existing train40/val20/test20 and all earlier efficacy caveats remain unchanged.

## Next step

Prepare a copilot intake contract using the saved objective and existing evidence,
then run the train-only lineage audit. Before automated model work, verify runner
connectivity with a bounded smoke request, freeze analyzer/model/token budgets,
and enforce the full concurrent cost cap. Do not equate empty-service health with
an operational autonomous experiment loop.

## Safety

Only new isolated runtime state, subproject documentation, ignored machine-local
context and compact research memory were written. Raw datasets, sealed data,
legacy storage, frozen benchmark sources and previous runs were unchanged.

## Local subfolder convenience follow-up

User prefers working from a subfolder of the current repository. Integration
code was already placed in `trace-experience-autoresearch/`; an ignored local
`runtime/` symlink now exposes the existing external subproject outputs there.
Verified the startup receipt and runner configuration are reachable through the
link. The service and stored files were not moved, restarted or duplicated.
Real output paths remain outside the repository as required by the current
validator. This adds browsing convenience, not model/evaluator readiness.
