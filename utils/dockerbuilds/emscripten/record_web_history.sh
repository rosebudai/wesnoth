#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

EXPERIMENT_ENV_FILE="${WESNOTH_EXPERIMENT_ENV_FILE:-${REPO_ROOT}/utils/dockerbuilds/current_experiment.env}"
if [[ ! -f "${EXPERIMENT_ENV_FILE}" ]]; then
  echo "missing experiment config: ${EXPERIMENT_ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${EXPERIMENT_ENV_FILE}"

if [[ -z "${EXP_ID:-}" ]]; then
  echo "EXP_ID is not set in ${EXPERIMENT_ENV_FILE}" >&2
  exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/utils/dockerbuilds/emscriptenbuild}"
if [[ ! -d "${OUTPUT_DIR}" ]]; then
  echo "output dir not found: ${OUTPUT_DIR}" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  hash_file() { sha256sum "$1" | awk '{print $1}'; }
else
  hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
fi

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${src}/" "${dst}/"
  else
    rm -rf "${dst}"
    mkdir -p "${dst}"
    cp -a "${src}/." "${dst}/"
  fi
}

timestamp_utc="$(date -u +%Y%m%dT%H%M%SZ)"
history_dir="${REPO_ROOT}/output/web-build-history"
mkdir -p "${history_dir}"
history_file="${history_dir}/${EXP_ID}-${timestamp_utc}.txt"
bundle_root="${REPO_ROOT}/output/web-build-bundles"
bundle_dir="${bundle_root}/${EXP_ID}-${timestamp_utc}"
bundle_build_dir="${bundle_dir}/build"

{
  echo "timestamp_utc=${timestamp_utc}"
  echo "provenance=artifact_reconstruction"
  echo "experiment_id=${EXP_ID}"
  echo "experiment_note=${EXP_DESCRIPTION:-}"
  echo "experiment_env_file=${EXPERIMENT_ENV_FILE}"
  echo "bundle_dir=${bundle_dir}"
  echo "git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "output_dir=${OUTPUT_DIR}"
  echo "WESNOTH_USE_PTHREADS=${EXP_WESNOTH_USE_PTHREADS:-}"
  echo "WESNOTH_PROXY_TO_PTHREAD=${EXP_WESNOTH_PROXY_TO_PTHREAD:-}"
  echo "WESNOTH_CMAKE_BUILD_TYPE=${EXP_WESNOTH_CMAKE_BUILD_TYPE:-}"
  echo "WESNOTH_EXTRA_CMAKE_ARGS=${EXP_WESNOTH_EXTRA_CMAKE_ARGS:-}"
  echo "WESNOTH_EXTRA_EM_FLAGS=${EXP_WESNOTH_EXTRA_EM_FLAGS:-}"
  echo "WESNOTH_EXTRA_EM_LINK_FLAGS=${EXP_WESNOTH_EXTRA_EM_LINK_FLAGS:-}"
  for artifact in index.html wesnoth.js wesnoth.wasm wesnoth.data wesnoth.data.js serve_coi.py; do
    artifact_path="${OUTPUT_DIR}/${artifact}"
    if [[ -f "${artifact_path}" ]]; then
      echo "${artifact}.sha256=$(hash_file "${artifact_path}")"
    else
      echo "${artifact}.sha256=missing"
    fi
  done
} > "${history_file}"

mkdir -p "${bundle_dir}"
copy_tree "${OUTPUT_DIR}" "${bundle_build_dir}"
cp -f "${history_file}" "${bundle_dir}/build-history.txt"
if [[ -f "${EXPERIMENT_ENV_FILE}" ]]; then
  cp -f "${EXPERIMENT_ENV_FILE}" "${bundle_dir}/experiment.env"
fi

{
  echo "history_file=${history_file}"
  echo "bundle_dir=${bundle_dir}"
}
