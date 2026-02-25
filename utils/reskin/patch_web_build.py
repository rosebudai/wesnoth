#!/usr/bin/env python3
"""Patch reskinned assets into a Wesnoth Emscripten web build.

Replaces image files in the source data tree with reskinned versions,
then repackages the data into a new LZ4-compressed wesnoth.data blob
using Emscripten's file_packager.py.

This ensures the C++ rendering engine reads the modified images through
its normal file I/O path (boost::iostreams → POSIX open → MEMFS).

Usage:
    python patch_web_build.py \\
        --build-dir <web-build-dir> \\
        --reskin-dir <reskin-output-dir> \\
        --output-dir <patched-dir> \\
        --wesnoth-root <path-to-wesnoth-repo>
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


IMAGE_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg", ".bmp"}

# Default location for emsdk file_packager.py
DEFAULT_FILE_PACKAGER = "/tmp/emsdk/upstream/emscripten/tools/file_packager.py"


def find_file_packager():
    """Locate Emscripten's file_packager.py."""
    # Check environment
    emsdk = os.environ.get("EMSDK", "")
    if emsdk:
        fp = os.path.join(emsdk, "upstream", "emscripten", "tools", "file_packager.py")
        if os.path.isfile(fp):
            return fp

    # Check default location
    if os.path.isfile(DEFAULT_FILE_PACKAGER):
        return DEFAULT_FILE_PACKAGER

    # Check PATH
    for p in os.environ.get("PATH", "").split(":"):
        fp = os.path.join(p, "file_packager.py")
        if os.path.isfile(fp):
            return fp

    return None


def build_reskin_map(reskin_dir):
    """Build a mapping from relative image path to reskinned file path.

    reskin_dir contains files like:
        units/human-loyalists/cavalryman/cavalryman.png
        attacks/axe.png
        portraits/humans/knight.png

    Returns dict mapping relative path (under data/core/images/) to local file.
    """
    reskin_map = {}
    for root, _, files in os.walk(reskin_dir):
        for fname in files:
            if os.path.splitext(fname)[1].lower() not in IMAGE_EXTENSIONS:
                continue
            full_path = os.path.join(root, fname)
            rel = os.path.relpath(full_path, reskin_dir)
            reskin_map[rel] = full_path
    return reskin_map


def stage_data(wesnoth_root, reskin_map, staging_dir):
    """Create a staging directory with original data + reskinned overlays.

    Copies the four data directories (data, images, fonts, sounds) into
    staging_dir using rsync (handles symlinks gracefully), then overlays
    reskinned files on top.
    """
    dirs_to_copy = ["data", "images", "fonts", "sounds"]
    for d in dirs_to_copy:
        src = os.path.join(wesnoth_root, d)
        dst = os.path.join(staging_dir, d)
        if os.path.isdir(src):
            print(f"  Copying {d}/...")
            # cp -rL follows symlinks. The Wesnoth data tree has many
            # symlinks that resolve to the same target, causing harmless
            # "File exists" errors — we ignore them.
            subprocess.run(
                ["cp", "-rL", "--no-clobber", src, dst],
                check=False,
            )

    # Overlay reskinned images
    images_base = os.path.join(staging_dir, "data", "core", "images")
    replaced = 0
    for rel_path, local_path in sorted(reskin_map.items()):
        target = os.path.join(images_base, rel_path)
        if os.path.exists(target):
            shutil.copy2(local_path, target)
            replaced += 1
        else:
            # File doesn't exist in original tree — create parent dirs
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(local_path, target)
            replaced += 1

    return replaced


def repackage_data(file_packager, staging_dir, output_dir, use_lz4=True):
    """Run file_packager.py to create new wesnoth.data + wesnoth.data.js."""
    data_file = os.path.join(output_dir, "wesnoth.data")
    js_file = os.path.join(output_dir, "wesnoth.data.js")

    cmd = [
        sys.executable, file_packager,
        data_file,
        f"--js-output={js_file}",
        "--use-preload-cache",
    ]

    if use_lz4:
        cmd.append("--lz4")

    # Preload the four directories with same VFS mapping as the original build
    for d in ["data", "images", "fonts", "sounds"]:
        src = os.path.join(staging_dir, d)
        if os.path.isdir(src):
            cmd.extend(["--preload", f"{src}@/{d}"])

    print(f"  Running file_packager.py...")
    print(f"  Command: {' '.join(cmd[:6])}...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"ERROR: file_packager.py failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    data_size_mb = os.path.getsize(data_file) / (1024 * 1024)
    print(f"  Generated wesnoth.data ({data_size_mb:.1f} MB)")
    return data_file, js_file


def patch_build(build_dir, reskin_map, output_dir, wesnoth_root, file_packager):
    """Create a patched web build with reskinned assets baked in."""
    os.makedirs(output_dir, exist_ok=True)

    # Copy static build files (wasm, js, html, etc.) — skip data files
    # we'll regenerate
    skip_files = {"wesnoth.data", "wesnoth.data.js", "reskin-overlay.js"}
    copied = 0
    for fname in os.listdir(build_dir):
        if fname in skip_files:
            continue
        src = os.path.join(build_dir, fname)
        dst = os.path.join(output_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            copied += 1

    print(f"Copied {copied} build files (skipped data files for regeneration)")

    # Stage data with reskinned overlays
    print(f"\nStaging data with {len(reskin_map)} reskinned assets...")
    staging_dir = tempfile.mkdtemp(prefix="wesnoth-reskin-stage-")
    try:
        replaced = stage_data(wesnoth_root, reskin_map, staging_dir)
        print(f"  {replaced} files overlaid")

        # Repackage
        print(f"\nRepackaging data...")
        repackage_data(file_packager, staging_dir, output_dir, use_lz4=True)
    finally:
        print(f"\nCleaning up staging dir...")
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(f"\nPatched build written to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Patch reskinned assets into web build by repackaging data"
    )
    parser.add_argument(
        "--build-dir", required=True,
        help="Path to original web build (containing wesnoth.wasm, etc.)"
    )
    parser.add_argument(
        "--reskin-dir", required=True,
        help="Path to reskinned assets (e.g., output/cyberpunk/)"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Path to write patched build"
    )
    parser.add_argument(
        "--wesnoth-root", default=None,
        help="Path to Wesnoth repo root (defaults to ../../ relative to this script)"
    )
    parser.add_argument(
        "--file-packager", default=None,
        help="Path to Emscripten file_packager.py"
    )
    parser.add_argument(
        "--no-lz4", action="store_true",
        help="Disable LZ4 compression (faster packaging, larger output)"
    )
    args = parser.parse_args()

    # Resolve wesnoth root
    if args.wesnoth_root:
        wesnoth_root = os.path.abspath(args.wesnoth_root)
    else:
        wesnoth_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    if not os.path.isdir(os.path.join(wesnoth_root, "data", "core")):
        print(f"ERROR: {wesnoth_root} doesn't look like a Wesnoth repo root",
              file=sys.stderr)
        sys.exit(1)

    # Find file_packager
    file_packager = args.file_packager or find_file_packager()
    if not file_packager or not os.path.isfile(file_packager):
        print(
            "ERROR: Cannot find file_packager.py. Install emsdk or pass --file-packager",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Using file_packager: {file_packager}")

    reskin_map = build_reskin_map(args.reskin_dir)
    if not reskin_map:
        print("ERROR: No reskinned assets found", file=sys.stderr)
        sys.exit(1)

    print(f"Reskinned assets: {len(reskin_map)}")
    patch_build(
        args.build_dir, reskin_map, args.output_dir, wesnoth_root, file_packager
    )


if __name__ == "__main__":
    main()
