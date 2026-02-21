#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

MATRIX="${REPO_ROOT}/docs/web-experiment-matrix.md"
RUN_LOG="${REPO_ROOT}/docs/web-run-log.md"
CURRENT="${REPO_ROOT}/docs/web-current-build.md"
LEARNINGS="${REPO_ROOT}/docs/web-rebuild-learnings.md"
SNAPSHOT_DIR="${REPO_ROOT}/output/web-build-snapshots"

for file in "${MATRIX}" "${RUN_LOG}" "${CURRENT}" "${LEARNINGS}"; do
  if [[ ! -f "${file}" ]]; then
    echo "missing required file: ${file}" >&2
    exit 1
  fi
done

echo "=== Web Build Rehydrate ==="
echo "repo: ${REPO_ROOT}"
echo "time: $(date -u +'%Y-%m-%d %H:%M:%SZ')"
echo

echo "--- Git ---"
git rev-parse --abbrev-ref HEAD
if git rev-parse --short HEAD >/dev/null 2>&1; then
  echo "commit: $(git rev-parse --short HEAD)"
fi
echo "dirty files:"
git status --short | sed -n '1,40p'
echo

python3 - <<'PY'
import os, re, glob
root = os.getcwd()

def parse_last_from_matrix(path):
    ids = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r"\|\s*E(\d+)\s*\|", line)
            if m:
                ids.append(int(m.group(1)))
    return max(ids) if ids else None

def parse_last_from_runlog(path):
    ids = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r"###\s+E(\d+)\b", line)
            if m:
                ids.append(int(m.group(1)))
    return max(ids) if ids else None

def parse_last_from_artifacts():
    ids = []
    for p in glob.glob(os.path.join(root, "output", "playwright", "wesnoth-e*")):
        b = os.path.basename(p)
        m = re.search(r"wesnoth-e(\d+)", b)
        if m:
            ids.append(int(m.group(1)))
    return max(ids) if ids else None

def parse_exp_id(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r"\s*EXP_ID\s*=\s*['\"]?([^'\"#\n]+)", line)
            if m:
                return m.group(1).strip()
    return None

matrix_last = parse_last_from_matrix(os.path.join(root, "docs", "web-experiment-matrix.md"))
runlog_last = parse_last_from_runlog(os.path.join(root, "docs", "web-run-log.md"))
artifact_last = parse_last_from_artifacts()
exp_id = parse_exp_id(os.path.join(root, "utils", "dockerbuilds", "current_experiment.env"))

print("--- Sequence Heads ---")
print(f"matrix_last:    E{matrix_last:02d}" if matrix_last is not None else "matrix_last:    none")
print(f"run_log_last:   E{runlog_last:02d}" if runlog_last is not None else "run_log_last:   none")
print(f"artifact_last:  E{artifact_last:02d}" if artifact_last is not None else "artifact_last:  none")
print(f"current EXP_ID: {exp_id}" if exp_id else "current EXP_ID: missing")
print()

if matrix_last is not None and artifact_last is not None and matrix_last < artifact_last:
    print(f"WARNING: matrix trails artifacts by {artifact_last - matrix_last} experiment IDs")
if runlog_last is not None and artifact_last is not None and runlog_last < artifact_last:
    print(f"WARNING: run-log trails artifacts by {artifact_last - runlog_last} experiment IDs")
if matrix_last is not None and runlog_last is not None and matrix_last != runlog_last:
    print("WARNING: matrix and run-log are out of sync")
if exp_id and re.match(r"E(\d+)$", exp_id):
    exp_num = int(re.match(r"E(\d+)$", exp_id).group(1))
    if matrix_last is not None and exp_num > matrix_last:
        print(f"WARNING: current EXP_ID {exp_id} is ahead of matrix head E{matrix_last:02d}")
    if runlog_last is not None and exp_num > runlog_last:
        print(f"WARNING: current EXP_ID {exp_id} is ahead of run-log head E{runlog_last:02d}")

print("\n--- Last Run-Log Headings ---")
headings = []
with open(os.path.join(root, "docs", "web-run-log.md"), 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.match(r"###\s+(E\d+.*)$", line)
        if m:
            headings.append(m.group(1).strip())
for h in headings[-5:]:
    print(f"- {h}")

history_dir = os.path.join(root, "output", "web-build-history")
if exp_id:
    matches = sorted(glob.glob(os.path.join(history_dir, f"{exp_id}-*.txt")))
    print("\n--- Build History (current EXP_ID) ---")
    if matches:
        print(f"- {os.path.relpath(matches[-1], root)}")
    else:
        print("- missing")
PY

echo

echo "--- Current Build (top) ---"
sed -n '1,80p' "${CURRENT}"
echo

if [[ -d "${SNAPSHOT_DIR}" ]]; then
  echo "--- Snapshots (latest 5) ---"
  ls -1dt "${SNAPSHOT_DIR}"/* 2>/dev/null | sed -n '1,5p' || true
else
  echo "--- Snapshots ---"
  echo "none"
fi

echo
cat <<'TXT'
Next steps after compaction:
1. Run ./utils/dockerbuilds/web_docs_sync_audit.sh and fix any drift first.
2. Confirm current served artifact hashes in docs/web-current-build.md.
3. Confirm EXP_ID and flags in utils/dockerbuilds/current_experiment.env.
4. Reserve next experiment ID from docs/web-experiment-matrix.md before running.
TXT
