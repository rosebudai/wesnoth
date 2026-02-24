"""Full end-to-end integration test with real Wesnoth assets."""

import json
import os
import subprocess
import sys
import pytest

WESNOTH_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
RESKIN_SCRIPT = os.path.join(WESNOTH_ROOT, "utils", "reskin", "reskin.py")


def test_full_faction_dry_run(tmp_path):
    """Process all asset types for human-loyalists with echo provider."""
    output_dir = str(tmp_path / "output")
    result = subprocess.run(
        [
            sys.executable, RESKIN_SCRIPT,
            "--theme", "cyberpunk",
            "--faction", "human-loyalists",
            "--dry-run",
            "--output-dir", output_dir,
        ],
        capture_output=True,
        text=True,
        cwd=WESNOTH_ROOT,
        timeout=120,
    )
    assert result.returncode == 0, f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}"

    # Check manifest
    manifest_path = os.path.join(output_dir, "cyberpunk", "human-loyalists", "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    completed = sum(1 for a in manifest["assets"].values() if a["status"] == "completed")
    # Should have processed sprites + portraits + icons
    assert completed > 500, f"Only {completed} assets completed"

    # Verify output directory has all three subdirs
    base = os.path.join(output_dir, "cyberpunk")
    assert os.path.isdir(os.path.join(base, "units", "human-loyalists"))
    assert os.path.isdir(os.path.join(base, "portraits", "humans"))
    assert os.path.isdir(os.path.join(base, "attacks"))
