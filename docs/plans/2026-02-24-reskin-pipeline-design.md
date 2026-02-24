# Reskin Pipeline Design

## Problem

Wesnoth has ~14,355 PNG assets with no mechanism to retheme them. We want to generate themed asset packs (e.g., "cyberpunk", "fairy princess") from existing art.

## Scope

- **CLI tool** at `utils/reskin/` — no game code or web UI changes
- **One faction end-to-end** as proof of concept (sprites + portraits + attack icons)
- **Hybrid approach:** AI img2img for sprites/portraits, algorithmic palette swap for icons
- **Provider-agnostic** with Nano Banana as primary target

## Project Layout

```
utils/reskin/
├── reskin.py              # CLI entry point
├── config.py              # Theme config loading & validation
├── manifest.py            # Progress tracking (skip completed images)
├── providers/
│   ├── __init__.py        # Provider base class
│   ├── nano_banana.py     # Nano Banana adapter
│   └── echo.py            # Dry-run provider (copies originals)
├── transforms/
│   ├── __init__.py
│   ├── ai_reskin.py       # AI img2img transform
│   └── palette_swap.py    # Algorithmic palette swap
├── themes/
│   ├── cyberpunk.json
│   └── fairy_princess.json
└── output/                # Generated output (gitignored)
```

## CLI Interface

```bash
# Full faction reskin
python utils/reskin/reskin.py --theme cyberpunk --faction human-loyalists

# Specific category only
python utils/reskin/reskin.py --theme cyberpunk --faction human-loyalists --category portraits

# Dry run (echo provider, no API calls)
python utils/reskin/reskin.py --theme cyberpunk --faction human-loyalists --dry-run

# Different provider
python utils/reskin/reskin.py --theme cyberpunk --faction human-loyalists --provider openai

# Force reprocess (ignore manifest)
python utils/reskin/reskin.py --theme cyberpunk --faction human-loyalists --force
```

## Theme Config Format

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

- `prompt` — sent to AI provider for sprites/portraits, prepended with asset-type context
- `palette` — color family mappings for algorithmic palette swap on icons
- Extensible: future fields (`prompt_portraits`, `strength`, `overlay_effects`) can be added without breaking existing configs

## Provider Interface

```python
class ReskinProvider:
    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        """Takes input image + style prompt, returns reskinned image bytes."""
        raise NotImplementedError
```

- Synchronous, one image at a time
- Provider receives fully-built prompt; pipeline handles prompt construction
- Returns bytes; pipeline handles file I/O
- API keys from environment variables (`NANO_BANANA_API_KEY`, etc.)

## Asset Discovery & Routing

| Asset type    | Source path                                  | Transform    |
|---------------|----------------------------------------------|--------------|
| Unit sprites  | `data/core/images/units/<faction>/*.png`     | AI (img2img) |
| Portraits     | `data/core/images/portraits/<faction>/*.png` | AI (img2img) |
| Attack icons  | `data/core/images/attacks/*.png`             | Palette swap |

Prompt construction varies by type:
- **Sprites:** "Reskin this 2D pixel art game unit sprite. Preserve transparency, silhouette, and animation pose. Style: {theme.prompt}"
- **Portraits:** "Reskin this fantasy character portrait. Preserve face composition and expression. Style: {theme.prompt}"
- **Icons:** No prompt — uses palette swap with theme.palette

Output mirrors source structure under `output/<theme>/<faction>/`.

## Manifest & Progress Tracking

Written to `output/<theme>/<faction>/manifest.json`:

```json
{
  "theme": "cyberpunk",
  "faction": "human-loyalists",
  "provider": "nano_banana",
  "started_at": "2026-02-24T10:00:00Z",
  "assets": {
    "units/human-loyalists/bowman-bow.png": {
      "status": "completed",
      "source_hash": "a3f2c1...",
      "output_path": "output/cyberpunk/human-loyalists/units/bowman-bow.png",
      "completed_at": "2026-02-24T10:00:05Z"
    }
  }
}
```

- Skip completed assets whose source hash still matches
- Flush to disk after each successful transform (crash-safe)
- Retry failed assets up to 3 times
- `--force` ignores manifest and reprocesses everything
- Summary printed at end: succeeded / failed / skipped
