#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
cd "${REPO_ROOT}"

EXPERIMENT_ENV_FILE="${WESNOTH_EXPERIMENT_ENV_FILE:-${REPO_ROOT}/utils/dockerbuilds/emscripten/current_experiment.env}"
if [[ ! -f "${EXPERIMENT_ENV_FILE}" ]]; then
  echo "missing experiment config: ${EXPERIMENT_ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${EXPERIMENT_ENV_FILE}"

EXP_ID="${1:-${EXP_ID:-}}"
if [[ -z "${EXP_ID}" ]]; then
  echo "missing EXP_ID (arg1 or current_experiment.env)" >&2
  exit 2
fi

URL="${2:-http://127.0.0.1:8040/}"
WAIT_MS="${3:-170000}"

if command -v sha256sum >/dev/null 2>&1; then
  hash_file() { sha256sum "$1" | awk '{print $1}'; }
else
  hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }
fi

timestamp_utc="$(date -u +%Y%m%dT%H%M%SZ)"
history_info="$("${SCRIPT_DIR}/record_web_history.sh")"
history_file="$(printf '%s\n' "${history_info}" | awk -F= '$1=="history_file"{print $2}' | tail -n 1)"
bundle_dir="$(printf '%s\n' "${history_info}" | awk -F= '$1=="bundle_dir"{print $2}' | tail -n 1)"
if [[ -z "${history_file}" ]]; then
  history_file="missing"
fi
if [[ -z "${bundle_dir}" ]]; then
  bundle_dir="${REPO_ROOT}/output/web-build-bundles/${EXP_ID}-${timestamp_utc}-missing-bundle"
fi
run_root="${bundle_dir}/playability-runs"
mkdir -p "${run_root}"

console_json="${run_root}/${EXP_ID}-${timestamp_utc}-console.json"
result_json="${run_root}/${EXP_ID}-${timestamp_utc}-result.json"
screenshot_png="${run_root}/${EXP_ID}-${timestamp_utc}.png"
meta_txt="${run_root}/${EXP_ID}-${timestamp_utc}-meta.txt"

console_rel="${console_json#${REPO_ROOT}/}"
result_rel="${result_json#${REPO_ROOT}/}"
screenshot_rel="${screenshot_png#${REPO_ROOT}/}"
console_json_container="/workspace/${console_rel}"
result_json_container="/workspace/${result_rel}"
screenshot_png_container="/workspace/${screenshot_rel}"

run_probe_native() {
  node "${SCRIPT_DIR}/../tests/run_playwright_check.js" \
    "${URL}" \
    "${console_json}" \
    "${result_json}" \
    "${screenshot_png}" \
    "${WAIT_MS}" >/dev/null
}

run_probe_docker() {
  local pw_version="1.57.0"
  local image="${WESNOTH_PLAYWRIGHT_DOCKER_IMAGE:-mcr.microsoft.com/playwright:v${pw_version}-jammy}"
  docker run --rm \
    -v "${REPO_ROOT}:/workspace" \
    -v "wesnoth-playwright-node:/opt/wesnoth-playwright-node" \
    -w /workspace \
    "${image}" \
    bash -lc "
      set -euo pipefail
      pw_version='${pw_version}'
      mkdir -p /opt/wesnoth-playwright-node
      cd /opt/wesnoth-playwright-node
      if [[ ! -f node_modules/.pw_version ]] || [[ \"\\\$(cat node_modules/.pw_version)\" != \"\${pw_version}\" ]]; then
        rm -rf node_modules package.json package-lock.json
        npm init -y >/dev/null 2>&1 || true
        npm install --no-audit --no-fund --silent playwright@\${pw_version} >/dev/null
        echo \"\${pw_version}\" > node_modules/.pw_version
      fi
      export NODE_PATH=/opt/wesnoth-playwright-node/node_modules
      cd /workspace/utils/dockerbuilds/emscripten
      python3 ./serve_coi.py --host 127.0.0.1 --port 8040 --dir ../emscriptenbuild >/tmp/wesnoth-serve.log 2>&1 &
      srv=\$!
      cleanup() { kill \${srv} >/dev/null 2>&1 || true; wait \${srv} >/dev/null 2>&1 || true; }
      trap cleanup EXIT
      node ./tests/run_playwright_check.js \
        '${URL}' \
        '${console_json_container}' \
        '${result_json_container}' \
        '${screenshot_png_container}' \
        '${WAIT_MS}'
    " >/dev/null
}

mode="${WESNOTH_PLAYWRIGHT_MODE:-auto}"
case "${mode}" in
  native)
    run_probe_native
    ;;
  docker)
    run_probe_docker
    ;;
  auto)
    if node -e "require('playwright')" >/dev/null 2>&1; then
      run_probe_native
    else
      run_probe_docker
    fi
    ;;
  *)
    echo "invalid WESNOTH_PLAYWRIGHT_MODE: ${mode} (expected auto|native|docker)" >&2
    exit 2
    ;;
esac

classification="$(node -e 'const fs=require("fs");const p=process.argv[1];const d=JSON.parse(fs.readFileSync(p,"utf8"));process.stdout.write(String(d.classification||"UNKNOWN"));' "${result_json}")"

{
  echo "timestamp_utc=${timestamp_utc}"
  echo "experiment_id=${EXP_ID}"
  echo "url=${URL}"
  echo "wait_ms=${WAIT_MS}"
  echo "classification=${classification}"
  echo "git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "experiment_env_file=${EXPERIMENT_ENV_FILE}"
  echo "history_file=${history_file}"
  echo "bundle_dir=${bundle_dir}"
  echo "console_json=${console_json}"
  echo "result_json=${result_json}"
  echo "screenshot_png=${screenshot_png}"
  if [[ -f "${screenshot_png}" ]]; then
    echo "screenshot_sha256=$(hash_file "${screenshot_png}")"
  else
    echo "screenshot_sha256=missing"
  fi
} > "${meta_txt}"

legacy_root="${REPO_ROOT}/output/web-playability-runs"
mkdir -p "${legacy_root}"
ln -sfn "${console_json}" "${legacy_root}/$(basename "${console_json}")"
ln -sfn "${result_json}" "${legacy_root}/$(basename "${result_json}")"
ln -sfn "${screenshot_png}" "${legacy_root}/$(basename "${screenshot_png}")"
ln -sfn "${meta_txt}" "${legacy_root}/$(basename "${meta_txt}")"

echo "recorded playability run:"
echo "  meta: ${meta_txt}"
echo "  result: ${result_json}"
echo "  console: ${console_json}"
echo "  screenshot: ${screenshot_png}"
