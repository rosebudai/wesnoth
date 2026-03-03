---
name: wesnoth-playtest
description: "Use when playtesting the Wesnoth web build — serving, navigating, and visually verifying via Playwright MCP and visual-judge. Covers loading screen, title, menus, and gameplay."
---

# Wesnoth Web Build Playtesting

Agent-driven playtesting of the Wesnoth Emscripten web build using Playwright MCP for browser interaction and visual-judge for screenshot analysis.

## When to Use

- Verifying the web build loads and renders correctly
- Playtesting after UI or loading screen changes
- Checking that the loading overlay works (progress bar, fade-out)
- Verifying gameplay flows (campaigns, multiplayer lobby, editor)
- Before claiming any visual change is "done"

## When NOT to Use

- Running CI smoke tests (use the legacy scripts in `utils/dockerbuilds/emscripten/`)
- Reskin-specific verification (use `reskin-verify` skill instead)

## Prerequisites

- A web build served with COOP/COEP headers
- Playwright MCP tools available (loaded via ToolSearch)

## Serving the Build

```bash
# From a pre-built bundle:
cd /path/to/build && nohup python3 /workspace/wesnoth/utils/dockerbuilds/emscripten/serve_coi.py \
  --port 8040 > /dev/null 2>&1 &

# Verify:
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8040/
# Expected: 200
```

`serve_coi.py` sets Cross-Origin-Opener-Policy and Cross-Origin-Embedder-Policy headers required for SharedArrayBuffer (multi-threaded WASM). Without these, the game won't start.

## Playtesting with Playwright MCP

Use the `playwright-capture` skill. Key Wesnoth-specific notes:

### Canvas Interactions

Wesnoth renders to a `<canvas>` element. Standard ref-based clicks won't work inside the game canvas.

- **Use `browser_mouse_click_xy`** for all in-game clicks (menus, buttons, units)
- **Use `browser_take_screenshot`** to see what's on screen (accessibility snapshots don't see canvas content)
- **Use `browser_evaluate`** to interact with game JS APIs or dismiss overlays

### Loading Phase (~15-25 seconds)

The game downloads a large data blob and compiles WASM. During this time:

1. The loading overlay shows progress (bar + "Rosie" messages)
2. Wait for the overlay to fade out before interacting
3. After overlay dismisses, the title screen canvas renders

```
browser_navigate → wait ~20s → take_screenshot → verify title screen visible
```

### Key Screens to Verify

| Screen | How to reach | What to check |
|--------|-------------|---------------|
| Loading overlay | Navigate to URL | Progress bar animates, messages rotate |
| Title screen | Wait for load complete | Background renders, menu buttons visible |
| Campaign list | Click "Campaigns" | Campaign entries load, thumbnails render |
| Multiplayer lobby | Click "Multiplayer" | Server selection dialog appears |
| Map editor | Click "Map Editor" | Editor canvas renders with terrain |
| Preferences | Click gear icon | Dialog opens with settings |

### Screenshot Output

All screenshots go to `.playwright/screenshots/` (gitignored). Use naming pattern:
`{timestamp}-{description}.png` (e.g., `20260303T120000-title-screen.png`)

## Visual Verification

After capturing screenshots, use the `visual-judge` skill for pixel-level analysis:

1. Copy relevant screenshots to a temp directory (max 3 at a time)
2. Invoke the multimodal tool with a specific prompt about what to verify
3. Incorporate the verdict into your assessment

## Approach: Agent-Driven, Not Scripted

<HARD-GATE>
Do NOT write new Playwright scripts for playtesting. Use Playwright MCP interactively.
The legacy scripts (`test_hotseat_playwright.js`, `test_multiplayer_playwright.js`, etc.)
are CI smoke tests only — they break on UI changes and can't adapt to what's on screen.
</HARD-GATE>

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Black screen, no loading overlay | Missing COOP/COEP headers | Use `serve_coi.py`, not a plain HTTP server |
| Loading bar stuck at 0% | Data file not found / wrong path | Check that `wesnoth.data` exists alongside `index.html` |
| Canvas click does nothing | Using ref-based click on canvas | Switch to `browser_mouse_click_xy` |
| "Intercepts pointer events" error | Overlay or other element on top | Use `browser_evaluate` to hide the blocking element |
| Game loads but crashes immediately | WASM threading issue | Ensure SharedArrayBuffer is available (COOP/COEP) |
