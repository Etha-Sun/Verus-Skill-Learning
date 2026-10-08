# Train40 rerun plan

1. Freeze train40 and initial skill; verify all hashes and the formal Verus
   identity. Completed offline; namespace isolation preflight also passed.
2. Apply and test the native bridge default output-cap forwarding correction.
   Completed; 24 model-free bridge tests passed.
3. Obtain the configured DeepSeek credential and verify authenticated provider
   access. Completed: configured locally and authenticated model listing includes
   `deepseek-v4-pro`; no credential printed or copied.
4. Create a fresh external run directory and freeze model, max reasoning,
   1,800-second task limit, request output cap, concurrency, tool identities,
   isolation roots, and provider accounting configuration. Do not use full
   SkillOpt training entry points that also launch optimization or held-out gates.
   Initial execution settings: 4 concurrent tasks after a single first-task gate,
   explicit native request cap 131,072 output tokens, 1M model context, and a
   conservative USD 30 safety guard (not a provider billing guarantee). No
   automatic failed-task retries. All scripts, toolchain staging, and raw outputs
   live in a fresh external directory identified by suffix `KjQXKA`.
   A model-free full isolated probe of a historical crate-alias source passed:
   Rust 1.88 and formal Verus ran; it reached the expected missing-proof
   postcondition error, not a crate/compiler setup error. Lynette self-comparison
   passed and forbidden repository/data paths were hidden.
5. Execute exactly 40 original source tasks, preserving every attempted result
   and ledger. Check the first task's provider and isolation validity before
   launching the remaining tasks. Stop on infrastructure/provider invalidity;
   ordinary unsolved tasks are results, not automatic rerun candidates.
   First task is `3a77a3e4e72edf600e2a` from the same fixed train40; it counts as
   one of the 40, not an additional paid pilot. Remaining order follows the
   unchanged manifest. Run via detached tmux, preserving `bash.log`, bridge
   ledger, `run_manifest.json`, rolling `progress.json`, and per-task outputs.
   Revision: after the first gate succeeded, the user requested higher
   concurrency. Gracefully drain the current four-worker stage, preserve all
   task outcomes/ledger/budget state, then resume only unattempted sources with
   eight workers. The initial coordinator is intentionally interrupted in its
   ThreadPoolExecutor wait (not an actor); the updated launcher refuses any
   incomplete or invalid task directory rather than paying for a retry.
6. Audit complete coverage, input immutability, Verus plus preservation outcomes,
   terminal validity, and accounting completeness. Report fresh solved/40 and
   caveats versus the old 600-second run; update CURRENT and rebuild the index.
