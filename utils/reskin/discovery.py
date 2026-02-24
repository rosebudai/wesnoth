"""Asset discovery and classification for the reskin pipeline."""

import os
from dataclasses import dataclass
from typing import List, Optional

IMAGE_EXTENSIONS = {".png", ".webp"}

# Faction name mapping: unit dir name -> portrait dir name
# Units use faction names like "human-loyalists", portraits use "humans"
PORTRAIT_DIR_MAP = {
    "human-loyalists": "humans",
    "human-magi": "humans",
    "human-outlaws": "humans",
    "human-peasants": "humans",
    "elves-wood": "elves",
    "undead-necromancers": "undead",
    "undead-skeletal": "undead",
    "undead-spirit": "undead",
}


@dataclass
class AssetInfo:
    source_path: str       # Absolute path to source image
    relative_path: str     # Path relative to images dir (e.g., "units/human-loyalists/bowman.png")
    category: str          # "sprite", "portrait", or "icon"


def classify_asset(relative_path: str) -> str:
    """Classify an asset by its path into sprite, portrait, icon, or unknown."""
    if "/units/" in relative_path:
        return "sprite"
    if "/portraits/" in relative_path:
        return "portrait"
    if "/attacks/" in relative_path:
        return "icon"
    return "unknown"


def _collect_images(directory: str) -> List[str]:
    """Collect all image files from a directory."""
    images = []
    if not os.path.isdir(directory):
        return images
    for filename in sorted(os.listdir(directory)):
        if os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
            images.append(os.path.join(directory, filename))
    return images


def discover_assets(
    wesnoth_root: str,
    faction: str,
    category: Optional[str] = None,
) -> List[AssetInfo]:
    """Discover all reskinnable assets for a faction.

    Args:
        wesnoth_root: Path to the Wesnoth repository root.
        faction: Faction name as used in units dir (e.g., "human-loyalists").
        category: Optional filter — "sprites", "portraits", or "icons".

    Returns:
        List of AssetInfo objects for discovered assets.
    """
    images_root = os.path.join(wesnoth_root, "data", "core", "images")
    assets: List[AssetInfo] = []

    # Unit sprites
    if category is None or category == "sprites":
        units_dir = os.path.join(images_root, "units", faction)
        for path in _collect_images(units_dir):
            rel = os.path.relpath(path, images_root)
            assets.append(AssetInfo(source_path=path, relative_path=rel, category="sprite"))

    # Portraits
    if category is None or category == "portraits":
        portrait_faction = PORTRAIT_DIR_MAP.get(faction, faction)
        portraits_dir = os.path.join(images_root, "portraits", portrait_faction)
        for path in _collect_images(portraits_dir):
            rel = os.path.relpath(path, images_root)
            assets.append(AssetInfo(source_path=path, relative_path=rel, category="portrait"))

    # Attack icons (shared across factions)
    if category is None or category == "icons":
        attacks_dir = os.path.join(images_root, "attacks")
        for path in _collect_images(attacks_dir):
            rel = os.path.relpath(path, images_root)
            assets.append(AssetInfo(source_path=path, relative_path=rel, category="icon"))

    return assets
