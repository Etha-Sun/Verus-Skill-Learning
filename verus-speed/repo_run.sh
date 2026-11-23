#!/bin/bash
# Verify one whole project crate with Verus and save the timing JSON.
# usage: repo_run.sh <project> <out.json> [extra verus flags...]
# Projects are expected under $VERUS_SPEED_REPOS, checked out at the commits
# listed in README.md.
set -u
CACHE="$HOME/.cache/verus-skill"
REPOS="${VERUS_SPEED_REPOS:-$CACHE/src/repos}"
VERUS="${VERUS:-$CACHE/toolchains/bb1f342/verus-release/verus}"
export RUSTUP_HOME="$CACHE/rustup" CARGO_HOME="$CACHE/cargo" PATH="$CACHE/cargo/bin:$PATH"
project="$1"; out="$2"; shift 2
case "$project" in
  ironkv)     dir="$REPOS/verified-ironkv/ironsht/src";  args=(lib.rs --crate-type=dylib) ;;
  nrkernel)   dir="$REPOS/verified-nrkernel/page-table/src"; args=(lib.rs --crate-type=lib --cfg 'feature="impl"' --rlimit 30) ;;
  noderep)    dir="$REPOS/verified-node-replication/verified-node-replication/src"; args=(lib.rs --crate-type=lib) ;;
  atmosphere) dir="$REPOS/atmosphere/kernel/verified"; args=(lib.rs --crate-type=lib) ;;
  anvil|anvil_vrs)
    dir="$REPOS/anvil/src"   # needs: (cd deps_hack && cargo +1.88.0 build)
    root=anvil.rs; [ "$project" = anvil_vrs ] && root=vreplicaset_controller.rs
    args=("$root" --crate-type=lib -L dependency=deps_hack/target/debug/deps
          --extern=deps_hack=deps_hack/target/debug/libdeps_hack.rlib --rlimit 50) ;;
  *) echo "unknown project $project" >&2; exit 2 ;;
esac
cd "$dir" || exit 2
start=$(date +%s.%N)
"$VERUS" "${args[@]}" --time-expanded --output-json "$@" > "$out" 2> "${out%.json}.stderr"
rc=$?
end=$(date +%s.%N)
echo "{\"project\":\"$project\",\"rc\":$rc,\"wall\":$(echo "$end - $start" | bc),\"flags\":\"$*\"}" > "${out%.json}.meta"
