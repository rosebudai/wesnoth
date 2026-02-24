# Reskin Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that reskins Wesnoth assets for a given faction into a themed style (e.g., cyberpunk, fairy princess) using AI img2img for sprites/portraits and algorithmic palette swap for icons.

**Architecture:** Python CLI at `utils/reskin/`. Asset discovery walks source directories, classifies each image (sprite/portrait/icon), routes to the appropriate transform (AI or palette swap), tracks progress in a manifest for resumability, outputs reskinned images mirroring the source directory structure.

**Tech Stack:** Python 3.11, Pillow (image I/O + palette swap), pytest, argparse, JSON configs

**Relevant docs:**
- Design: `docs/plans/2026-02-24-reskin-pipeline-design.md`
- Unit sprites: `data/core/images/units/<faction>/*.png` (742 files for human-loyalists)
- Portraits: `data/core/images/portraits/<faction>/*.webp` (63 files for humans)
- Attack icons: `data/core/images/attacks/*.png` (173 files)
- Existing image tools: `utils/compare_images.py`, `utils/woptipng.py`

---

### Task 1: Project scaffolding

**Files:**
- Create: `utils/reskin/__init__.py`
- Create: `utils/reskin/tests/__init__.py`
- Create: `utils/reskin/providers/__init__.py`
- Create: `utils/reskin/transforms/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p utils/reskin/providers utils/reskin/transforms utils/reskin/themes utils/reskin/tests
```

**Step 2: Create empty `__init__.py` files**

Create these empty files:
- `utils/reskin/__init__.py`
- `utils/reskin/providers/__init__.py`
- `utils/reskin/transforms/__init__.py`
- `utils/reskin/tests/__init__.py`

**Step 3: Add output directory to `.gitignore`**

Append to `utils/reskin/.gitignore`:

```
output/
```

**Step 4: Commit**

```bash
/commit
```

---

### Task 2: Theme config loading

**Files:**
- Create: `utils/reskin/config.py`
- Create: `utils/reskin/tests/test_config.py`
- Create: `utils/reskin/themes/cyberpunk.json`
- Create: `utils/reskin/themes/fairy_princess.json`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_config.py`:

```python
import json
import os
import pytest
import tempfile

from utils.reskin.config import load_theme, ThemeConfig, ValidationError


@pytest.fixture
def cyberpunk_theme_data():
    return {
        "name": "cyberpunk",
        "description": "Neon-lit sci-fi warriors",
        "prompt": "cyberpunk neon sci-fi style, glowing circuits",
        "palette": {
            "browns": "#0a0a2e",
            "greens": "#00ff88"
        }
    }


@pytest.fixture
def theme_file(cyberpunk_theme_data, tmp_path):
    path = tmp_path / "cyberpunk.json"
    path.write_text(json.dumps(cyberpunk_theme_data))
    return str(path)


def test_load_theme_returns_theme_config(theme_file):
    theme = load_theme(theme_file)
    assert isinstance(theme, ThemeConfig)
    assert theme.name == "cyberpunk"
    assert theme.prompt == "cyberpunk neon sci-fi style, glowing circuits"
    assert theme.palette["browns"] == "#0a0a2e"


def test_load_theme_missing_file():
    with pytest.raises(FileNotFoundError):
        load_theme("/nonexistent/theme.json")


def test_load_theme_missing_required_field(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "bad"}))
    with pytest.raises(ValidationError):
        load_theme(str(path))


def test_load_theme_by_name():
    """Load a theme by name from the themes/ directory."""
    theme = load_theme("cyberpunk")
    assert theme.name == "cyberpunk"
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'utils.reskin.config'`

**Step 3: Write the theme config files**

Create `utils/reskin/themes/cyberpunk.json`:

```json
{
    "name": "cyberpunk",
    "description": "Neon-lit sci-fi warriors with glowing circuits and chrome armor",
    "prompt": "cyberpunk neon sci-fi style, glowing circuits, chrome metal, dark background",
    "palette": {
        "browns": "#0a0a2e",
        "greens": "#00ff88",
        "silvers": "#c0c0ff",
        "reds": "#ff0044"
    }
}
```

Create `utils/reskin/themes/fairy_princess.json`:

```json
{
    "name": "fairy_princess",
    "description": "Enchanted pastel warriors with sparkles and flower motifs",
    "prompt": "fairy tale princess style, pastel colors, sparkles, flowers, magical glow",
    "palette": {
        "browns": "#e8b4d8",
        "greens": "#98fb98",
        "silvers": "#fff0f5",
        "reds": "#ff69b4"
    }
}
```

**Step 4: Write minimal implementation**

Create `utils/reskin/config.py`:

```python
"""Theme configuration loading and validation."""

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

THEMES_DIR = os.path.join(os.path.dirname(__file__), "themes")
REQUIRED_FIELDS = ["name", "prompt", "palette"]


class ValidationError(Exception):
    pass


@dataclass
class ThemeConfig:
    name: str
    description: str
    prompt: str
    palette: Dict[str, str]


def load_theme(path_or_name: str) -> ThemeConfig:
    """Load a theme from a JSON file path or by name from themes/ directory."""
    if os.path.isfile(path_or_name):
        path = path_or_name
    else:
        path = os.path.join(THEMES_DIR, f"{path_or_name}.json")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Theme file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

    return ThemeConfig(
        name=data["name"],
        description=data.get("description", ""),
        prompt=data["prompt"],
        palette=data["palette"],
    )
```

**Step 5: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_config.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
/commit
```

---

### Task 3: Asset discovery

**Files:**
- Create: `utils/reskin/discovery.py`
- Create: `utils/reskin/tests/test_discovery.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_discovery.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `utils/reskin/discovery.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_discovery.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 4: Provider interface + echo provider

**Files:**
- Create: `utils/reskin/providers/base.py`
- Create: `utils/reskin/providers/echo.py`
- Create: `utils/reskin/tests/test_providers.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_providers.py`:

```python
import os
import pytest
from PIL import Image
import io

from utils.reskin.providers.base import ReskinProvider
from utils.reskin.providers.echo import EchoProvider


@pytest.fixture
def sample_image(tmp_path):
    """Create a small test PNG image."""
    img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
    path = tmp_path / "test.png"
    img.save(str(path))
    return str(path)


def test_base_provider_is_abstract():
    provider = ReskinProvider()
    with pytest.raises(NotImplementedError):
        provider.transform("path.png", "prompt", {})


def test_echo_provider_returns_original_bytes(sample_image):
    provider = EchoProvider()
    result = provider.transform(sample_image, "any prompt", {})
    assert isinstance(result, bytes)
    # Verify it's a valid image
    img = Image.open(io.BytesIO(result))
    assert img.size == (32, 32)


def test_echo_provider_preserves_transparency(tmp_path):
    """Echo provider must preserve RGBA transparency."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    path = tmp_path / "transparent.png"
    img.save(str(path))

    provider = EchoProvider()
    result = provider.transform(str(path), "prompt", {})
    result_img = Image.open(io.BytesIO(result))
    assert result_img.mode == "RGBA"
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_providers.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/providers/base.py`:

```python
"""Base provider interface for reskin transforms."""


class ReskinProvider:
    """Abstract base class for reskin providers."""

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        """Transform an image according to the given style prompt.

        Args:
            image_path: Absolute path to the source image.
            prompt: Fully constructed style prompt.
            params: Additional provider-specific parameters.

        Returns:
            Reskinned image as bytes (PNG format).
        """
        raise NotImplementedError
```

Create `utils/reskin/providers/echo.py`:

```python
"""Echo provider — returns the original image unchanged. For testing."""

import io
from PIL import Image
from utils.reskin.providers.base import ReskinProvider


class EchoProvider(ReskinProvider):
    """Returns the original image unchanged. Useful for testing the pipeline."""

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        img = Image.open(image_path)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_providers.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 5: Manifest / progress tracking

**Files:**
- Create: `utils/reskin/manifest.py`
- Create: `utils/reskin/tests/test_manifest.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_manifest.py`:

```python
import json
import os
import pytest

from utils.reskin.manifest import Manifest


@pytest.fixture
def manifest_path(tmp_path):
    return str(tmp_path / "manifest.json")


def test_new_manifest_creates_file(manifest_path):
    m = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m.save()
    assert os.path.exists(manifest_path)


def test_manifest_mark_completed(manifest_path):
    m = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m.mark_completed("units/bowman.png", source_hash="abc123", output_path="/out/bowman.png")
    assert m.is_completed("units/bowman.png", source_hash="abc123")


def test_manifest_completed_wrong_hash(manifest_path):
    m = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m.mark_completed("units/bowman.png", source_hash="abc123", output_path="/out/bowman.png")
    assert not m.is_completed("units/bowman.png", source_hash="different")


def test_manifest_mark_failed(manifest_path):
    m = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m.mark_failed("units/bowman.png", error="API timeout")
    status = m.get_status("units/bowman.png")
    assert status["status"] == "failed"
    assert status["error"] == "API timeout"


def test_manifest_load_existing(manifest_path):
    m1 = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m1.mark_completed("units/bowman.png", source_hash="abc123", output_path="/out/bowman.png")
    m1.save()

    m2 = Manifest.load(manifest_path)
    assert m2.is_completed("units/bowman.png", source_hash="abc123")


def test_manifest_summary(manifest_path):
    m = Manifest(manifest_path, theme="cyberpunk", faction="human-loyalists", provider="echo")
    m.mark_completed("a.png", source_hash="h1", output_path="/out/a.png")
    m.mark_completed("b.png", source_hash="h2", output_path="/out/b.png")
    m.mark_failed("c.png", error="timeout")
    summary = m.summary()
    assert summary["completed"] == 2
    assert summary["failed"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_manifest.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/manifest.py`:

```python
"""Progress tracking manifest for resumable reskin runs."""

import json
import os
from datetime import datetime, timezone
from typing import Optional


class Manifest:
    def __init__(self, path: str, theme: str, faction: str, provider: str):
        self.path = path
        self.data = {
            "theme": theme,
            "faction": faction,
            "provider": provider,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "assets": {},
        }

    @classmethod
    def load(cls, path: str) -> "Manifest":
        """Load an existing manifest from disk."""
        with open(path) as f:
            data = json.load(f)
        m = cls.__new__(cls)
        m.path = path
        m.data = data
        return m

    def save(self):
        """Flush manifest to disk."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def is_completed(self, relative_path: str, source_hash: str) -> bool:
        """Check if an asset was already processed with the same source hash."""
        entry = self.data["assets"].get(relative_path)
        if entry is None:
            return False
        return entry.get("status") == "completed" and entry.get("source_hash") == source_hash

    def get_status(self, relative_path: str) -> Optional[dict]:
        return self.data["assets"].get(relative_path)

    def mark_completed(self, relative_path: str, source_hash: str, output_path: str):
        self.data["assets"][relative_path] = {
            "status": "completed",
            "source_hash": source_hash,
            "output_path": output_path,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def mark_failed(self, relative_path: str, error: str):
        entry = self.data["assets"].get(relative_path, {})
        attempts = entry.get("attempts", 0) + 1
        self.data["assets"][relative_path] = {
            "status": "failed",
            "error": error,
            "attempts": attempts,
        }
        self.save()

    def summary(self) -> dict:
        assets = self.data["assets"]
        return {
            "completed": sum(1 for a in assets.values() if a["status"] == "completed"),
            "failed": sum(1 for a in assets.values() if a["status"] == "failed"),
            "total": len(assets),
        }
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_manifest.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 6: Palette swap transform

**Files:**
- Create: `utils/reskin/transforms/palette_swap.py`
- Create: `utils/reskin/tests/test_palette_swap.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_palette_swap.py`:

```python
import io
import pytest
from PIL import Image

from utils.reskin.transforms.palette_swap import palette_swap


@pytest.fixture
def red_icon(tmp_path):
    """Create a small icon that is mostly red."""
    img = Image.new("RGBA", (16, 16), (200, 50, 50, 255))
    path = tmp_path / "red_icon.png"
    img.save(str(path))
    return str(path)


@pytest.fixture
def palette():
    return {"reds": "#00ff88"}


def test_palette_swap_returns_bytes(red_icon, palette):
    result = palette_swap(red_icon, palette)
    assert isinstance(result, bytes)


def test_palette_swap_produces_valid_image(red_icon, palette):
    result = palette_swap(red_icon, palette)
    img = Image.open(io.BytesIO(result))
    assert img.size == (16, 16)
    assert img.mode == "RGBA"


def test_palette_swap_changes_colors(red_icon, palette):
    result = palette_swap(red_icon, palette)
    img = Image.open(io.BytesIO(result))
    pixel = img.getpixel((8, 8))
    # Should have shifted away from red toward green
    assert pixel[1] > pixel[0]  # green channel > red channel


def test_palette_swap_preserves_transparency(tmp_path):
    """Transparent pixels must stay transparent."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    path = tmp_path / "transparent.png"
    img.save(str(path))

    result = palette_swap(str(path), {"reds": "#ff0000"})
    result_img = Image.open(io.BytesIO(result))
    pixel = result_img.getpixel((8, 8))
    assert pixel[3] == 0  # alpha stays 0
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_palette_swap.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/transforms/palette_swap.py`:

```python
"""Algorithmic palette swap for icons and simple assets."""

import io
from typing import Dict, Tuple

from PIL import Image
import colorsys


# Color family hue ranges (in degrees, 0-360)
COLOR_FAMILIES = {
    "reds": ((-15, 15), (345, 360)),      # wraps around 0
    "browns": ((15, 45),),
    "greens": ((75, 165),),
    "silvers": None,                        # handled by saturation check
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)


def _classify_pixel_color(r: int, g: int, b: int) -> str:
    h, s, v = _rgb_to_hsv(r, g, b)
    hue_deg = h * 360

    if s < 0.15 and v > 0.5:
        return "silvers"
    if s < 0.1:
        return "unknown"

    if hue_deg <= 15 or hue_deg >= 345:
        return "reds"
    if 15 < hue_deg <= 45:
        return "browns"
    if 75 <= hue_deg <= 165:
        return "greens"

    return "unknown"


def palette_swap(image_path: str, palette: Dict[str, str]) -> bytes:
    """Swap color families in an image according to a palette mapping.

    Args:
        image_path: Path to source image.
        palette: Dict mapping color family names to target hex colors.

    Returns:
        Recolored image as PNG bytes.
    """
    img = Image.open(image_path).convert("RGBA")
    pixels = img.load()
    width, height = img.size

    # Precompute target HSV values
    targets = {}
    for family, hex_color in palette.items():
        tr, tg, tb = _hex_to_rgb(hex_color)
        targets[family] = _rgb_to_hsv(tr, tg, tb)

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue

            family = _classify_pixel_color(r, g, b)
            if family not in targets:
                continue

            # Preserve relative brightness, shift hue and saturation
            _, _, src_v = _rgb_to_hsv(r, g, b)
            tgt_h, tgt_s, tgt_v = targets[family]

            # Blend: use target hue/sat, mix brightness
            new_v = (src_v * 0.6) + (tgt_v * 0.4)
            new_r, new_g, new_b = colorsys.hsv_to_rgb(tgt_h, tgt_s, new_v)

            pixels[x, y] = (
                int(new_r * 255),
                int(new_g * 255),
                int(new_b * 255),
                a,
            )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_palette_swap.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 7: AI reskin transform

**Files:**
- Create: `utils/reskin/transforms/ai_reskin.py`
- Create: `utils/reskin/tests/test_ai_reskin.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_ai_reskin.py`:

```python
import io
import pytest
from PIL import Image

from utils.reskin.transforms.ai_reskin import build_prompt, ai_reskin
from utils.reskin.providers.echo import EchoProvider


def test_build_prompt_sprite():
    result = build_prompt("sprite", "cyberpunk neon style")
    assert "sprite" in result.lower()
    assert "cyberpunk neon style" in result
    assert "transparency" in result.lower()


def test_build_prompt_portrait():
    result = build_prompt("portrait", "fairy tale style")
    assert "portrait" in result.lower()
    assert "fairy tale style" in result


@pytest.fixture
def sample_sprite(tmp_path):
    img = Image.new("RGBA", (72, 72), (100, 100, 200, 255))
    path = tmp_path / "sprite.png"
    img.save(str(path))
    return str(path)


def test_ai_reskin_returns_bytes(sample_sprite):
    provider = EchoProvider()
    result = ai_reskin(sample_sprite, "sprite", "cyberpunk style", provider)
    assert isinstance(result, bytes)


def test_ai_reskin_produces_valid_image(sample_sprite):
    provider = EchoProvider()
    result = ai_reskin(sample_sprite, "sprite", "cyberpunk style", provider)
    img = Image.open(io.BytesIO(result))
    assert img.size == (72, 72)
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_ai_reskin.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/transforms/ai_reskin.py`:

```python
"""AI-powered reskinning via img2img providers."""

from utils.reskin.providers.base import ReskinProvider

PROMPT_TEMPLATES = {
    "sprite": (
        "Reskin this 2D pixel art game unit sprite. "
        "Preserve transparency, silhouette, and animation pose. "
        "Style: {style}"
    ),
    "portrait": (
        "Reskin this fantasy character portrait. "
        "Preserve face composition and expression. "
        "Style: {style}"
    ),
}


def build_prompt(category: str, style_prompt: str) -> str:
    """Build a full prompt from asset category and theme style prompt."""
    template = PROMPT_TEMPLATES.get(category, PROMPT_TEMPLATES["sprite"])
    return template.format(style=style_prompt)


def ai_reskin(
    image_path: str,
    category: str,
    style_prompt: str,
    provider: ReskinProvider,
    params: dict = None,
) -> bytes:
    """Reskin an image using an AI provider.

    Args:
        image_path: Path to source image.
        category: Asset category ("sprite" or "portrait").
        style_prompt: Theme style prompt.
        provider: ReskinProvider instance.
        params: Optional provider-specific parameters.

    Returns:
        Reskinned image as bytes.
    """
    prompt = build_prompt(category, style_prompt)
    return provider.transform(image_path, prompt, params or {})
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_ai_reskin.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 8: Nano Banana provider stub

**Files:**
- Create: `utils/reskin/providers/nano_banana.py`
- Create: `utils/reskin/tests/test_nano_banana.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_nano_banana.py`:

```python
import os
import pytest

from utils.reskin.providers.nano_banana import NanoBananaProvider


def test_init_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("NANO_BANANA_API_KEY", "test-key-123")
    provider = NanoBananaProvider()
    assert provider.api_key == "test-key-123"


def test_init_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("NANO_BANANA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="NANO_BANANA_API_KEY"):
        NanoBananaProvider()
```

Note: We don't test the actual API call here — that requires a real API key and network. The transform method will be implemented as a stub that raises `NotImplementedError("Nano Banana API integration pending — use echo provider for testing")` until we have the actual API spec.

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_nano_banana.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/providers/nano_banana.py`:

```python
"""Nano Banana AI provider for img2img reskinning."""

import os
from utils.reskin.providers.base import ReskinProvider


class NanoBananaProvider(ReskinProvider):
    """Nano Banana img2img provider.

    Requires NANO_BANANA_API_KEY environment variable.
    """

    def __init__(self, model: str = "default"):
        self.api_key = os.environ.get("NANO_BANANA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NANO_BANANA_API_KEY environment variable is required. "
                "Set it to your Nano Banana API key."
            )
        self.model = model

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        # TODO: Implement actual Nano Banana API call
        # Expected flow:
        #   1. Read image, base64 encode
        #   2. POST to Nano Banana img2img endpoint
        #   3. Return response image bytes
        raise NotImplementedError(
            "Nano Banana API integration pending. "
            "Use --dry-run (echo provider) for pipeline testing."
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_nano_banana.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 9: CLI entry point — wiring it all together

**Files:**
- Create: `utils/reskin/reskin.py`
- Create: `utils/reskin/tests/test_reskin_cli.py`

**Step 1: Write the failing tests**

Create `utils/reskin/tests/test_reskin_cli.py`:

```python
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
    # Should have created output PNG files
    output_attacks = os.path.join(output_dir, "cyberpunk", "human-loyalists", "attacks")
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_reskin_cli.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `utils/reskin/reskin.py`:

```python
#!/usr/bin/env python3
"""Reskin pipeline CLI — reskin Wesnoth assets into themed styles."""

import argparse
import hashlib
import os
import sys

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
    # For icons (attacks/), strip the leading path component
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
```

Note: The script uses relative imports via direct module names because it's run as `python utils/reskin/reskin.py`. The `sys.path` will include `utils/reskin/` automatically. If this causes import issues when running tests via pytest, add this to the top of `reskin.py` before the imports:

```python
# Ensure utils/reskin is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))
```

**Step 4: Run tests to verify they pass**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_reskin_cli.py -v`
Expected: All passed

**Step 5: Commit**

```bash
/commit
```

---

### Task 10: Final integration test + cleanup

**Files:**
- Modify: `utils/reskin/.gitignore` — ensure `output/` is ignored
- Create: `utils/reskin/tests/test_integration.py`

**Step 1: Write integration test**

Create `utils/reskin/tests/test_integration.py`:

```python
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
```

**Step 2: Run integration test**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/test_integration.py -v --timeout=120`
Expected: PASS

**Step 3: Run the full test suite**

Run: `cd /workspace/wesnoth && python -m pytest utils/reskin/tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
/commit
```
