#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

python3 - <<'PY'
import os
import re
import glob
import sys

root = os.getcwd()
matrix_path = os.path.join(root, "docs", "web-experiment-matrix.md")
runlog_path = os.path.join(root, "docs", "web-run-log.md")
experiment_env_path = os.path.join(root, "utils", "dockerbuilds", "current_experiment.env")

for p in (matrix_path, runlog_path):
    if not os.path.exists(p):
        print(f"ERROR: missing required doc: {p}")
        sys.exit(2)

def parse_matrix_ids(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"\|\s*E(\d+)\s*\|", line)
            if m:
                out.append(int(m.group(1)))
    return sorted(set(out))

def parse_runlog_ids(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"###\s+E(\d+)\b", line)
            if m:
                out.append(int(m.group(1)))
    return sorted(set(out))

def parse_artifact_ids():
    out = []
    for p in glob.glob(os.path.join(root, "output", "playwright", "wesnoth-e*")):
        m = re.search(r"wesnoth-e(\d+)", os.path.basename(p))
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))

def parse_exp_id(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"\s*EXP_ID\s*=\s*['\"]?([^'\"#\n]+)", line)
            if m:
                return m.group(1).strip()
    return None

matrix_ids = parse_matrix_ids(matrix_path)
runlog_ids = parse_runlog_ids(runlog_path)
artifact_ids = parse_artifact_ids()
exp_id = parse_exp_id(experiment_env_path)

print("Web docs sync audit")
print(f"matrix count:   {len(matrix_ids)}")
print(f"run-log count:  {len(runlog_ids)}")
print(f"artifact count: {len(artifact_ids)}")

ok = True

if matrix_ids:
    print(f"matrix head:    E{matrix_ids[-1]:02d}")
if runlog_ids:
    print(f"run-log head:   E{runlog_ids[-1]:02d}")
if artifact_ids:
    print(f"artifact head:  E{artifact_ids[-1]:02d}")
print(f"current EXP_ID: {exp_id if exp_id else 'missing'}")

matrix_missing_from_run = [i for i in matrix_ids if i not in runlog_ids]
run_missing_from_matrix = [i for i in runlog_ids if i not in matrix_ids]
art_missing_from_matrix = [i for i in artifact_ids if i not in matrix_ids]
art_missing_from_run = [i for i in artifact_ids if i not in runlog_ids]

if matrix_missing_from_run:
    ok = False
    print("ERROR: matrix IDs missing from run-log:", ", ".join(f"E{i:02d}" for i in matrix_missing_from_run))

if run_missing_from_matrix:
    ok = False
    print("ERROR: run-log IDs missing from matrix:", ", ".join(f"E{i:02d}" for i in run_missing_from_matrix))

if art_missing_from_matrix:
    ok = False
    print("ERROR: artifact IDs missing from matrix:", ", ".join(f"E{i:02d}" for i in art_missing_from_matrix))

if art_missing_from_run:
    ok = False
    print("ERROR: artifact IDs missing from run-log:", ", ".join(f"E{i:02d}" for i in art_missing_from_run))

if not exp_id:
    ok = False
    print(f"ERROR: missing EXP_ID in {experiment_env_path}")
else:
    m = re.match(r"E(\d+)$", exp_id)
    if not m:
        ok = False
        print(f"ERROR: EXP_ID has invalid format in {experiment_env_path}: {exp_id}")
    else:
        exp_num = int(m.group(1))
        if exp_num not in matrix_ids:
            ok = False
            print(f"ERROR: current EXP_ID {exp_id} is missing from matrix")
        if exp_num not in runlog_ids:
            ok = False
            print(f"ERROR: current EXP_ID {exp_id} is missing from run-log")
        history_glob = os.path.join(root, "output", "web-build-history", f"{exp_id}-*.txt")
        history_files = sorted(glob.glob(history_glob))
        if history_files:
            print(f"history file:   {os.path.relpath(history_files[-1], root)}")
        else:
            print(f"WARNING: no build history file found for {exp_id} under output/web-build-history")

if ok:
    print("OK: matrix, run-log, and artifact IDs are aligned.")
    sys.exit(0)

print("\nAction: backfill docs before running more experiments.")
sys.exit(1)
PY
