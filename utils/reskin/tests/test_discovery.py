import os
import pytest

from utils.reskin.discovery import discover_assets, classify_asset, AssetInfo


# Use real Wesnoth assets for integration-style tests
WESNOTH_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def test_classify_sprite():
    assert classify_asset("data/core/images/units/human-loyalists/bowman-bow.png") == "sprite"


def test_classify_portrait():
    assert classify_asset("data/core/images/portraits/humans/bowman.webp") == "portrait"


def test_classify_icon():
    assert classify_asset("data/core/images/attacks/axe.png") == "icon"


def test_classify_unknown():
    assert classify_asset("data/core/images/misc/random.png") == "unknown"


def test_discover_assets_finds_sprites():
    assets = discover_assets(WESNOTH_ROOT, "human-loyalists")
    sprites = [a for a in assets if a.category == "sprite"]
    assert len(sprites) > 100  # human-loyalists has 402 sprites


def test_discover_assets_finds_portraits():
    assets = discover_assets(WESNOTH_ROOT, "human-loyalists")
    portraits = [a for a in assets if a.category == "portrait"]
    assert len(portraits) > 10  # humans has 63 portraits


def test_discover_assets_finds_icons():
    assets = discover_assets(WESNOTH_ROOT, "human-loyalists")
    icons = [a for a in assets if a.category == "icon"]
    assert len(icons) > 50  # 173 attack icons


def test_discover_assets_category_filter():
    assets = discover_assets(WESNOTH_ROOT, "human-loyalists", category="sprites")
    assert all(a.category == "sprite" for a in assets)
    assert len(assets) > 100


def test_asset_info_has_required_fields():
    assets = discover_assets(WESNOTH_ROOT, "human-loyalists", category="sprites")
    asset = assets[0]
    assert isinstance(asset, AssetInfo)
    assert os.path.isabs(asset.source_path)
    assert os.path.exists(asset.source_path)
    assert asset.relative_path.startswith("units/")
    assert asset.category == "sprite"
