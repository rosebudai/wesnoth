#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 E## \"short description\" [extra paths...]" >&2
  exit 2
fi

EXPERIMENT_ID="$1"
shift
DESCRIPTION="$1"
shift || true

if [[ ! "${EXPERIMENT_ID}" =~ ^E[0-9]{2,}$ ]]; then
  echo "invalid experiment id: ${EXPERIMENT_ID} (expected E##)" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

EXPERIMENT_ENV_FILE="utils/dockerbuilds/current_experiment.env"
if [[ ! -f "${EXPERIMENT_ENV_FILE}" ]]; then
  echo "missing required experiment config: ${EXPERIMENT_ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${EXPERIMENT_ENV_FILE}"
if [[ -z "${EXP_ID:-}" ]]; then
  echo "EXP_ID is not set in ${EXPERIMENT_ENV_FILE}" >&2
  exit 1
fi
if [[ "${EXP_ID}" != "${EXPERIMENT_ID}" ]]; then
  echo "experiment mismatch: commit requested ${EXPERIMENT_ID}, but ${EXPERIMENT_ENV_FILE} has ${EXP_ID}" >&2
  echo "update ${EXPERIMENT_ENV_FILE} first to keep commit history reproducible" >&2
  exit 1
fi

"${REPO_ROOT}/utils/dockerbuilds/web_docs_sync_audit.sh"

BASE_FILES=(
  "AGENTS.md"
  "docs/web-experiment-matrix.md"
  "docs/web-run-log.md"
  "docs/web-current-build.md"
  "docs/web-rebuild-learnings.md"
  "docs/web-compaction-recovery.md"
  "utils/dockerbuilds/current_experiment.env"
  "utils/dockerbuilds/make_emscripten_build"
  "utils/dockerbuilds/record_web_history.sh"
  "utils/dockerbuilds/web_rehydrate_context.sh"
  "utils/dockerbuilds/web_docs_sync_audit.sh"
  "utils/dockerbuilds/commit_web_experiment.sh"
)

TO_ADD=()
for f in "${BASE_FILES[@]}"; do
  if [[ -e "${f}" ]]; then
    TO_ADD+=("${f}")
  fi
done

for f in "$@"; do
  if [[ -e "${f}" ]]; then
    TO_ADD+=("${f}")
  else
    echo "warning: skipped missing path: ${f}" >&2
  fi
done

if [[ ${#TO_ADD[@]} -eq 0 ]]; then
  echo "nothing to add" >&2
  exit 1
fi

git add -- "${TO_ADD[@]}"

if git diff --cached --quiet; then
  echo "no staged changes for commit" >&2
  exit 1
fi

MSG="web: ${EXPERIMENT_ID} ${DESCRIPTION}"

git commit -m "${MSG}"

echo "created commit: ${MSG}"
