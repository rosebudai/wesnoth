#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <snapshot-tag>" >&2
  exit 2
fi

snapshot_tag="$1"
repo_root="$(cd "$(dirname "$0")/../../../.." && pwd)"
build_dir="$repo_root/utils/dockerbuilds/emscriptenbuild"
snapshot_root="$repo_root/output/web-build-snapshots"
snapshot_dir="$snapshot_root/$snapshot_tag"
bundle_dir="$snapshot_dir/bundle"
manifest="$snapshot_dir/manifest.txt"

if [[ ! -d "$build_dir" ]]; then
  echo "Build dir not found: $build_dir" >&2
  exit 1
fi

mkdir -p "$bundle_dir"
rsync -a --delete "$build_dir/" "$bundle_dir/"

{
  echo "snapshot_tag: $snapshot_tag"
  echo "created_at_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source_build_dir: $build_dir"
  echo "git_branch: $(git -C "$repo_root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "git_head: $(git -C "$repo_root" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo ""
  echo "artifact_hashes_sha256:"
  for f in index.html wesnoth.js wesnoth.wasm wesnoth.data wesnoth.data.js wesnoth.worker.js serve_coi.py; do
    if [[ -f "$bundle_dir/$f" ]]; then
      sha256sum "$bundle_dir/$f"
    else
      echo "MISSING  $bundle_dir/$f"
    fi
  done
  echo ""
  echo "git_status_short:"
  git -C "$repo_root" status --short || true
} > "$manifest"

echo "Snapshot created: $snapshot_dir"
echo "Manifest: $manifest"
