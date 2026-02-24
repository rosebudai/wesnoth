import json
import os
import subprocess
import sys
import pytest

WESNOTH_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
RESKIN_SCRIPT = os.path.join(WESNOTH_ROOT, "utils", "reskin", "reskin.py")


def test_cli_dry_run(tmp_path):
    """Full pipeline dry run with echo provider on a small category."""
    output_dir = str(tmp_path / "output")
    result = subprocess.run(
        [
            sys.executable, RESKIN_SCRIPT,
            "--theme", "cyberpunk",
            "--faction", "human-loyalists",
            "--category", "icons",
            "--dry-run",
            "--output-dir", output_dir,
        ],
        capture_output=True,
        text=True,
        cwd=WESNOTH_ROOT,
    )
    assert result.returncode == 0, f"STDERR: {result.stderr}"
    assert "completed" in result.stdout.lower() or "summary" in result.stdout.lower()

    # Check manifest was created
    manifest_path = os.path.join(output_dir, "cyberpunk", "human-loyalists", "manifest.json")
    assert os.path.exists(manifest_path)

    with open(manifest_path) as f:
        manifest = json.load(f)
    assert manifest["theme"] == "cyberpunk"
    assert len(manifest["assets"]) > 0


def test_cli_dry_run_creates_output_files(tmp_path):
    """Dry run should produce output image files."""
    output_dir = str(tmp_path / "output")
    subprocess.run(
        [
            sys.executable, RESKIN_SCRIPT,
            "--theme", "cyberpunk",
            "--faction", "human-loyalists",
            "--category", "icons",
            "--dry-run",
            "--output-dir", output_dir,
        ],
        capture_output=True,
        text=True,
        cwd=WESNOTH_ROOT,
    )
    # Icons output mirrors source structure: output/cyberpunk/attacks/*.png
    output_attacks = os.path.join(output_dir, "cyberpunk", "attacks")
    assert os.path.isdir(output_attacks)
    pngs = [f for f in os.listdir(output_attacks) if f.endswith(".png")]
    assert len(pngs) > 50  # 173 attack icons


def test_cli_missing_theme():
    result = subprocess.run(
        [sys.executable, RESKIN_SCRIPT, "--faction", "human-loyalists"],
        capture_output=True,
        text=True,
        cwd=WESNOTH_ROOT,
    )
    assert result.returncode != 0


def test_cli_resumability(tmp_path):
    """Running twice should skip already-completed assets."""
    output_dir = str(tmp_path / "output")
    args = [
        sys.executable, RESKIN_SCRIPT,
        "--theme", "cyberpunk",
        "--faction", "human-loyalists",
        "--category", "icons",
        "--dry-run",
        "--output-dir", output_dir,
    ]

    # First run
    subprocess.run(args, capture_output=True, text=True, cwd=WESNOTH_ROOT)

    # Second run — should skip everything
    result = subprocess.run(args, capture_output=True, text=True, cwd=WESNOTH_ROOT)
    assert result.returncode == 0
    assert "skipped" in result.stdout.lower() or "skip" in result.stdout.lower()
