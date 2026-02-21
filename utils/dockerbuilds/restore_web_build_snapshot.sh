#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <snapshot-tag>" >&2
  exit 2
fi

snapshot_tag="$1"
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
snapshot_dir="$repo_root/output/web-build-snapshots/$snapshot_tag"
src_bundle="$snapshot_dir/bundle"
dst_build="$repo_root/utils/dockerbuilds/emscriptenbuild"

if [[ ! -d "$src_bundle" ]]; then
  echo "Snapshot bundle not found: $src_bundle" >&2
  exit 1
fi

mkdir -p "$dst_build"
rsync -a --delete "$src_bundle/" "$dst_build/"

echo "Restored snapshot '$snapshot_tag' to: $dst_build"
sha256sum "$dst_build"/index.html "$dst_build"/wesnoth.js "$dst_build"/wesnoth.wasm 2>/dev/null || true
