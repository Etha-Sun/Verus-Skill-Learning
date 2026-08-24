#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -gt 1 ]]; then
  echo "usage: $0 [checkout-directory]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
target="${1:-$repo_root/trace2skill-verusage/Trace2Skill}"
upstream_url="https://github.com/Qwen-Applications/Trace2Skill.git"
upstream_commit="3d0b52a140f002a512930252b613c49048f7d5ac"
patch_path="$repo_root/trace2skill-verusage/patches/0001-verus-native-official-producer.patch"
config_root="$repo_root/trace2skill-verusage/baselines/native-official-20260819/configuration"
expected_patched_tree_id="b015929acebda3f6400dcb830d75f1f778971147"

modified_paths=(
  "skill_evolver/prompts/parallel_evolving_agent/translation_system_prompt.txt"
  "skill_evolver/prompts/parallel_evolving_agent/verification_system_prompt.txt"
  "skill_evolver/prompts/skill_evolving_agent/system_prompt_base.txt"
  "skill_evolver/run_parallel_skill_evolution.py"
  "skill_evolver/skill_evolving_agent.py"
)
expected_sha256=(
  "3870a22f3cd2ff066220393f6e991c7c2858c0f67e1e90601408920b4084802e"
  "bb925b81873aed35af89bc9a1116ec5e70f4a1eb01371db91023e0115e9ad91a"
  "4bdafecb8340e6023517dda14c8de5da669ab8b20ef10f09beac9f8f77d436ca"
  "2c7b98116eec761bc485f1287f2d1ab7604aec642e591e5273b2ab34929724b7"
  "acde25b9352ba4bd1fc0756f2770229afffeba0c04b74bbd6e9115a38bee3f2b"
)

if [[ ! -e "$target" ]]; then
  mkdir -p "$(dirname "$target")"
  git clone --no-checkout "$upstream_url" "$target"
  git -C "$target" checkout --detach "$upstream_commit"
fi
if [[ ! -d "$target/.git" ]]; then
  echo "Trace2Skill target is not a Git checkout: $target" >&2
  exit 1
fi

actual_commit="$(git -C "$target" rev-parse HEAD)"
if [[ "$actual_commit" != "$upstream_commit" ]]; then
  echo "Trace2Skill checkout must be pinned at $upstream_commit, got $actual_commit" >&2
  exit 1
fi
if ! git -C "$target" diff --cached --quiet; then
  echo "Trace2Skill checkout has staged changes" >&2
  exit 1
fi
if [[ -n "$(git -C "$target" ls-files --others --exclude-standard)" ]]; then
  echo "Trace2Skill checkout has unexpected untracked files" >&2
  exit 1
fi

mapfile -t changed_paths < <(git -C "$target" diff --name-only)
if [[ "${#changed_paths[@]}" -eq 0 ]]; then
  git -C "$target" apply --ignore-space-change --whitespace=nowarn "$patch_path"
  cp "$config_root/map_system_prompt.txt" \
    "$target/skill_evolver/prompts/skill_evolving_agent/system_prompt_base.txt"
  cp "$config_root/merge_system_prompt.txt" \
    "$target/skill_evolver/prompts/success_evolving_agent/combined_merge_system_prompt.txt"
  cp "$config_root/translation_system_prompt.txt" \
    "$target/skill_evolver/prompts/parallel_evolving_agent/translation_system_prompt.txt"
  cp "$config_root/verification_system_prompt.txt" \
    "$target/skill_evolver/prompts/parallel_evolving_agent/verification_system_prompt.txt"
  mapfile -t changed_paths < <(git -C "$target" diff --name-only)
fi
if [[ "${changed_paths[*]}" != "${modified_paths[*]}" ]]; then
  echo "Trace2Skill checkout has changes outside the reviewed producer patch" >&2
  printf '  %s\n' "${changed_paths[@]}" >&2
  exit 1
fi
if ! git -C "$target" diff --check; then
  echo "Trace2Skill checkout patch has whitespace errors" >&2
  exit 1
fi

for index in "${!modified_paths[@]}"; do
  relative="${modified_paths[$index]}"
  actual="$(sha256sum "$target/$relative" | awk '{print $1}')"
  if [[ "$actual" != "${expected_sha256[$index]}" ]]; then
    echo "patched Trace2Skill file hash mismatch: $relative" >&2
    exit 1
  fi
done
merge_hash="$(sha256sum "$target/skill_evolver/prompts/success_evolving_agent/combined_merge_system_prompt.txt" | awk '{print $1}')"
if [[ "$merge_hash" != "c9b707e3dafacd96536c92fe43b78507d3b20e6b6d1552d67e61d3b5377e706f" ]]; then
  echo "Trace2Skill merge prompt hash mismatch" >&2
  exit 1
fi

verify_dir="$(mktemp -d "${TMPDIR:-/tmp}/trace2skill-tree-check.XXXXXX")"
trap 'rm -rf -- "$verify_dir"' EXIT
GIT_INDEX_FILE="$verify_dir/index" git -C "$target" read-tree HEAD
GIT_INDEX_FILE="$verify_dir/index" git -C "$target" add -u -- .
actual_patched_tree_id="$(
  GIT_INDEX_FILE="$verify_dir/index" git -C "$target" write-tree
)"
if [[ "$actual_patched_tree_id" != "$expected_patched_tree_id" ]]; then
  echo "patched Trace2Skill tree mismatch: $actual_patched_tree_id" >&2
  exit 1
fi

echo "Trace2Skill ready"
echo "  commit: $upstream_commit"
echo "  patched tree: $actual_patched_tree_id"
