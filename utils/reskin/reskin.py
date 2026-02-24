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
    raise ValueError(f"Unknown provider: {name}")


def file_hash(path: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def process_asset(asset, theme, provider, output_dir):
    """Process a single asset through the appropriate transform.

    Returns (output_path, image_bytes) on success, raises on failure.
    """
    if asset.category == "icon":
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


def main():
    parser = argparse.ArgumentParser(description="Reskin Wesnoth assets into themed styles.")
    parser.add_argument("--theme", required=True, help="Theme name or path to theme JSON")
    parser.add_argument("--faction", required=True, help="Faction name (e.g., human-loyalists)")
    parser.add_argument("--category", choices=["sprites", "portraits", "icons"], help="Process only this category")
    parser.add_argument("--provider", default="nano_banana", help="AI provider name (default: nano_banana)")
    parser.add_argument("--dry-run", action="store_true", help="Use echo provider (no API calls)")
    parser.add_argument("--force", action="store_true", help="Reprocess all assets, ignore manifest")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--wesnoth-root", default=WESNOTH_ROOT, help="Path to Wesnoth repo root")

    args = parser.parse_args()

    # Load theme
    theme = load_theme(args.theme)
    print(f"Theme: {theme.name} — {theme.description}")

    # Get provider
    if args.dry_run:
        provider = EchoProvider()
        provider_name = "echo"
    else:
        provider = get_provider(args.provider)
        provider_name = args.provider

    # Discover assets
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
                output_path = process_asset(asset, theme, provider, args.output_dir)
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
