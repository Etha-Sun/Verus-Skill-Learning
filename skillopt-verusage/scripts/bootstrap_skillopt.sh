#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -gt 1 ]]; then
  echo "usage: $0 [checkout-directory]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="${1:-$REPO_ROOT/skillopt-verusage/SkillOpt}"
UPSTREAM_URL="https://github.com/microsoft/SkillOpt"
UPSTREAM_COMMIT="9639719632daecacd1baaa47fe781f3c0253600a"
PATCH_PATH="$REPO_ROOT/skillopt-verusage/patches/0001-verusage-path-references.patch"
EXPECTED_PATCHED_TREE_ID="7e207482b0bf0238b21e13976f6f9da5f130072c"

MODIFIED_PATHS=(
  "skillopt/gradient/reflect.py"
  "skillopt/optimizer/slow_update.py"
  "skillopt/prompts/slow_update.md"
)
EXPECTED_SHA256=(
  "2a2c8b81974b67b3731334f09aa486059b58e867f83157f2d053938af54172e9"
  "161d3b3485642b52249bdb89e1cf3375cfd7baa4adebae949c181a75f5e8f87b"
  "4922a33734703a1c65d097765b9e25e32cfd64d8a13cdd6f9bef979982e0bac0"
)

if [[ ! -e "$TARGET" ]]; then
  mkdir -p "$(dirname "$TARGET")"
  git clone --no-checkout "$UPSTREAM_URL" "$TARGET"
  git -C "$TARGET" checkout --detach "$UPSTREAM_COMMIT"
fi
if [[ ! -d "$TARGET/.git" ]]; then
  echo "SkillOpt target is not a Git checkout: $TARGET" >&2
  exit 1
fi

ACTUAL_COMMIT="$(git -C "$TARGET" rev-parse HEAD)"
if [[ "$ACTUAL_COMMIT" != "$UPSTREAM_COMMIT" ]]; then
  echo "SkillOpt checkout must be pinned at $UPSTREAM_COMMIT, got $ACTUAL_COMMIT" >&2
  exit 1
fi
if ! git -C "$TARGET" diff --cached --quiet; then
  echo "SkillOpt checkout has staged changes" >&2
  exit 1
fi
if [[ -n "$(git -C "$TARGET" ls-files --others --exclude-standard)" ]]; then
  echo "SkillOpt checkout has unexpected untracked files" >&2
  exit 1
fi

mapfile -t CHANGED_PATHS < <(git -C "$TARGET" diff --name-only)
if [[ "${#CHANGED_PATHS[@]}" -eq 0 ]]; then
  git -C "$TARGET" apply --ignore-space-change --whitespace=nowarn "$PATCH_PATH"
  mapfile -t CHANGED_PATHS < <(git -C "$TARGET" diff --name-only)
fi
if [[ "${CHANGED_PATHS[*]}" != "${MODIFIED_PATHS[*]}" ]]; then
  echo "SkillOpt checkout has changes outside the reviewed patch" >&2
  printf '  %s\n' "${CHANGED_PATHS[@]}" >&2
  exit 1
fi

# Normalize patched files after applying the diff so the verified tree is
# identical across Git autocrlf configurations.
for relative in "${MODIFIED_PATHS[@]}"; do
  sed -i 's/\r$//' "$TARGET/$relative"
done

for index in "${!MODIFIED_PATHS[@]}"; do
  relative="${MODIFIED_PATHS[$index]}"
  actual="$(sha256sum "$TARGET/$relative" | awk '{print $1}')"
  if [[ "$actual" != "${EXPECTED_SHA256[$index]}" ]]; then
    echo "patched SkillOpt file hash mismatch: $relative" >&2
    exit 1
  fi
done

VERIFY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/skillopt-tree-check.XXXXXX")"
trap 'rm -rf -- "$VERIFY_DIR"' EXIT
GIT_INDEX_FILE="$VERIFY_DIR/index" git -C "$TARGET" read-tree HEAD
# The temporary index has no assume-unchanged/skip-worktree flags. Staging every
# tracked path therefore makes the tree check independent of the real index.
GIT_INDEX_FILE="$VERIFY_DIR/index" git -C "$TARGET" add -u -- .
ACTUAL_PATCHED_TREE_ID="$(
  GIT_INDEX_FILE="$VERIFY_DIR/index" git -C "$TARGET" write-tree
)"
if [[ "$ACTUAL_PATCHED_TREE_ID" != "$EXPECTED_PATCHED_TREE_ID" ]]; then
  echo "patched SkillOpt tree mismatch: $ACTUAL_PATCHED_TREE_ID" >&2
  exit 1
fi

echo "SkillOpt ready"
echo "  commit: $UPSTREAM_COMMIT"
echo "  patched tree: $ACTUAL_PATCHED_TREE_ID"
