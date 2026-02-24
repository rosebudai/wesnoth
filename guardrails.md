# Guardrails — reskin-pipeline
# Add pitfalls discovered during ralph loop iterations here.
# Format: ## Title, **Trigger/Do/Don't/Context**

## Portraits are WebP not PNG
**Trigger:** Working with portrait assets
**Do:** Use IMAGE_EXTENSIONS = {".png", ".webp"} in discovery
**Don't:** Assume all assets are PNG
**Context:** data/core/images/portraits/ contains .webp files (284 webp, 2 png)

## Portrait directory naming differs from unit directory naming
**Trigger:** Looking up portraits for a faction
**Do:** Use PORTRAIT_DIR_MAP to translate faction names (e.g., human-loyalists -> humans)
**Don't:** Assume portrait dirs match unit dir names
**Context:** Units use "human-loyalists", portraits use "humans". Same for elves-wood->elves, undead-*->undead

## reskin.py uses script-style imports not package imports
**Trigger:** Writing imports in reskin.py or any module under utils/reskin/
**Do:** Use `from config import load_theme` (direct module import)
**Do:** Add `sys.path.insert(0, os.path.dirname(__file__))` at top of reskin.py
**Don't:** Use `from utils.reskin.config import load_theme` (package import) in reskin.py
**Context:** reskin.py runs as a script via `python utils/reskin/reskin.py`, so Python adds utils/reskin/ to sys.path. Tests that use subprocess also run it this way. However, test files that import modules directly (test_config.py etc.) DO use package imports like `from utils.reskin.config import load_theme` because pytest runs from the repo root.
