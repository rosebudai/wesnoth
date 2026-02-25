#!/usr/bin/env python3
"""Reskin pipeline CLI — reskin Wesnoth assets into themed styles."""

import argparse
import hashlib
import os
import sys

# Ensure utils/reskin is on the path when run directly as a script.
# Also add the repo root so that submodule package imports work
# (e.g., echo.py's "from utils.reskin.providers.base import ...").
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import load_theme
from discovery import discover_assets
from manifest import Manifest
from providers.echo import EchoProvider
from providers.base import ReskinProvider
from transforms.ai_reskin import ai_reskin
from transforms.palette_swap import palette_swap

WESNOTH_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
MAX_RETRIES = 3


def get_provider(name: str) -> ReskinProvider:
    """Instantiate a provider by name."""
    if name == "echo":
        return EchoProvider()
    if name == "nano_banana":
        from providers.nano_banana import NanoBananaProvider
        return NanoBananaProvider()
    if name == "fal_gemini":
        from providers.fal_gemini import FalGeminiProvider
        return FalGeminiProvider()
    raise ValueError(f"Unknown provider: {name}")


def file_hash(path: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def process_asset(asset, theme, provider, output_dir, palette_only=False):
    """Process a single asset through the appropriate transform.

    Returns (output_path, image_bytes) on success, raises on failure.
    """
    if asset.category == "icon" or palette_only:
        image_bytes = palette_swap(asset.source_path, theme.palette)
    else:
        image_bytes = ai_reskin(
            asset.source_path, asset.category, theme.prompt, provider
        )

    # Build output path mirroring source structure
    out_rel = asset.relative_path
    # Always output as PNG
    out_rel = os.path.splitext(out_rel)[0] + ".png"
    output_path = os.path.join(output_dir, theme.name, out_rel)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    return output_path


def run_batch(args, theme, provider):
    """Batch mode: group assets into 4x4 grids and restyle via AI.

    Steps:
      1. Discover assets
      2. Build 4x4 grid images (16 sprites each)
      3. Send each grid to AI provider
      4. Extract restyled sprites, restore alpha masks, save individually
    """
    from transforms.grid_batch import (
        build_grids,
        build_grid_prompt,
        extract_and_save,
    )

    assets = discover_assets(
        args.wesnoth_root, args.faction, category=args.category
    )
    print(f"Discovered {len(assets)} assets")
    if not assets:
        print("No assets found. Check faction name and category.")
        sys.exit(1)

    theme_output = os.path.join(args.output_dir, theme.name)
    grids_dir = os.path.join(theme_output, "grids")
    restyled_dir = os.path.join(theme_output, "restyled")
    sprites_dir = os.path.join(theme_output)

    # Step 1: Build grids
    print("\n=== Building grids ===")
    manifest = build_grids(assets, grids_dir)

    # Step 2: Send each grid to AI provider
    print("\n=== Restyling grids via AI ===")
    os.makedirs(restyled_dir, exist_ok=True)
    total_batches = len(manifest["batches"])

    for i, batch_meta in enumerate(manifest["batches"], 1):
        batch_id = batch_meta["batch_id"]
        grid_path = batch_meta["grid_file"]
        output_path = os.path.join(restyled_dir, f"{batch_id}_restyled.png")

        if not args.force and os.path.exists(output_path):
            print(f"[{i}/{total_batches}] {batch_id}: skipping (exists)")
            continue

        n_sprites = len(batch_meta["sprites"])
        print(
            f"[{i}/{total_batches}] {batch_id}: "
            f"{n_sprites} sprites...",
            end=" ",
            flush=True,
        )

        prompt = build_grid_prompt(batch_meta, theme.prompt)

        # Save prompt for debugging
        prompt_path = os.path.join(restyled_dir, f"{batch_id}_prompt.txt")
        with open(prompt_path, "w") as f:
            f.write(prompt)

        ok = provider.transform_grid(grid_path, prompt, output_path)
        print("OK" if ok else "FAILED")

    # Step 3: Extract individual sprites
    print("\n=== Extracting sprites ===")
    tiling = getattr(args, "tiling", False)
    results = extract_and_save(
        manifest, restyled_dir, sprites_dir, tiling=tiling
    )

    print(f"\n--- Summary ---")
    print(f"Grids:     {total_batches}")
    print(f"Extracted: {len(results)}")
    print(f"Output:    {sprites_dir}")


def main():
    parser = argparse.ArgumentParser(description="Reskin Wesnoth assets into themed styles.")
    parser.add_argument("--theme", required=True, help="Theme name or path to theme JSON")
    parser.add_argument("--faction", required=True, help="Faction name (e.g., human-loyalists)")
    parser.add_argument("--category", choices=["sprites", "portraits", "icons"], help="Process only this category")
    parser.add_argument("--provider", default="nano_banana", help="AI provider name (default: nano_banana)")
    parser.add_argument("--dry-run", action="store_true", help="Use echo provider (no API calls)")
    parser.add_argument("--force", action="store_true", help="Reprocess all assets, ignore manifest")
    parser.add_argument("--palette-only", action="store_true", help="Use palette swap for all categories (skip AI provider)")
    parser.add_argument("--batch", action="store_true", help="Use grid batching (4x4 grids, 16x fewer API calls)")
    parser.add_argument("--tiling", action="store_true", help="Blend tile edges for seamless terrain (use with --batch)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--wesnoth-root", default=WESNOTH_ROOT, help="Path to Wesnoth repo root")

    args = parser.parse_args()

    # Load theme
    theme = load_theme(args.theme)
    print(f"Theme: {theme.name} — {theme.description}")

    # Get provider (palette-only mode doesn't need a real provider)
    if args.dry_run or args.palette_only:
        provider = EchoProvider()
        provider_name = "echo"
    else:
        provider = get_provider(args.provider)
        provider_name = args.provider

    # Batch mode: grid-based AI restyling
    if args.batch:
        run_batch(args, theme, provider)
        return

    # Standard mode: process assets one at a time
    assets = discover_assets(args.wesnoth_root, args.faction, category=args.category)
    print(f"Discovered {len(assets)} assets")

    if not assets:
        print("No assets found. Check faction name and category.")
        sys.exit(1)

    # Load or create manifest
    manifest_dir = os.path.join(args.output_dir, theme.name, args.faction)
    manifest_path = os.path.join(manifest_dir, "manifest.json")

    if os.path.exists(manifest_path) and not args.force:
        manifest = Manifest.load(manifest_path)
    else:
        manifest = Manifest(manifest_path, theme=theme.name, faction=args.faction, provider=provider_name)

    # Process assets
    completed = 0
    failed = 0
    skipped = 0

    for i, asset in enumerate(assets, 1):
        source_hash = file_hash(asset.source_path)

        # Check manifest for already-completed assets
        if not args.force and manifest.is_completed(asset.relative_path, source_hash):
            skipped += 1
            continue

        print(f"[{i}/{len(assets)}] {asset.relative_path} ({asset.category})...", end=" ", flush=True)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                output_path = process_asset(asset, theme, provider, args.output_dir, palette_only=args.palette_only)
                manifest.mark_completed(asset.relative_path, source_hash, output_path)
                completed += 1
                print("OK")
                break
            except NotImplementedError as e:
                # Provider not yet implemented
                manifest.mark_failed(asset.relative_path, str(e))
                failed += 1
                print(f"SKIP ({e})")
                break
            except Exception as e:
                if attempt == MAX_RETRIES:
                    manifest.mark_failed(asset.relative_path, str(e))
                    failed += 1
                    print(f"FAILED ({e})")
                else:
                    print(f"retry {attempt}...", end=" ", flush=True)

    # Summary
    print(f"\n--- Summary ---")
    print(f"Completed: {completed}")
    print(f"Skipped:   {skipped}")
    print(f"Failed:    {failed}")
    print(f"Total:     {len(assets)}")
    print(f"Output:    {os.path.join(args.output_dir, theme.name)}")


if __name__ == "__main__":
    main()
