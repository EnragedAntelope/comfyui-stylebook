# AGENTS.md — comfyui-stylebook

430+ visual styles for ComfyUI, every one with a rendered preview you can browse before you commit. Each ships a written description, a keyword list, a matching negative prompt, plus 650+ artists with descriptors. Zero dependencies, fully offline. Built on ComfyUI V3 API, category: `conditioning/stylebook`.

**Deep references:**
- `ARCHITECTURE.md` (chain protocol, layout, design rationale — read before engine changes)
- `docs/custom-styles.md` (field reference for `user_styles.json`)

## Architecture in 60 seconds

- **Chain protocol.** Every node takes an optional `style_chain` and emits one on a dedicated `STYLEBOOK_CHAIN` socket type (not STRING — prevents silent miswiring). Carries JSON: style + modifiers + artists + user_prompt metadata.
- **Five nodes.** Style (exclusive medium axis), Artist (additive, chainable), Modifier (one per axis), Blend (two styles at a ratio), Sheet (one subject, many styles as a list).
- **Gallery-first UX.** Each style ships a rendered preview image. Open gallery → look → click. 650+ artists each have a written descriptor so the look lands even when the model doesn't know the name.
- **Three composition rules** (differ on purpose): style = exclusive replacement; modifiers = per-axis additive; artists = chainable additive.
- **Plain Python + plain JavaScript.** No OS-specific calls, paths via `pathlib`, nothing shells out. Runs the same on Windows/macOS/Linux. Test suite runs on a machine with no ComfyUI installed.
- **Generated JS data.** `js/stylebook_data.js` is generated — never edit by hand. `js/stylebook_gallery.js` is hand-written and the generator never touches it.

## Layout

| Directory / File | Purpose |
|------------------|---------|
| `data/styles/` | One module per category, each a dict of style records |
| `data/artists.py` | Artist records, keyed by id |
| `data/modifiers.py` | Modifier records grouped onto five axes |
| `data/user_data.py` | Validates and merges optional `user_styles.json` |
| `stylebook_nodes/` | Engine (pure functions), schema options, node classes, routes |
| `js/` | Frontend: gallery, recreate, readout, shared helpers, generated data, previews |
| `previews/` | Sprite atlases + index.json (served statically) |
| `scripts/` | Build and validation tooling (not shipped to registry) |
| `tests/` | unittest suite, data-layer validator, comfy_stub, jsdom frontend tests |
| `docs/` | custom-styles.md (user_styles.json field reference) |

## Build / test / run

```bash
# Install (drop into ComfyUI/custom_nodes/)
# No pip install needed — zero dependencies

# Python tests
python -m unittest discover tests

# Frontend tests (jsdom smoke tests)
npm run test:frontend

# Regenerate JS data after style/artist/modifier changes
# (see scripts/ for exact command — varies by generator version)
```

## Conventions & gotchas

- Zero dependencies. Python ≥3.10. Drops into ComfyUI's `custom_nodes/` — no pip install.
- The chain socket type (`STYLEBOOK_CHAIN`) is distinct from STRING by design — prevents silent miswiring when connecting prompt to style_chain.
- `js/stylebook_data.js` is generated. Never edit by hand.
- `js/stylebook_gallery.js` is hand-written. The generator never touches it.
- Sprite atlases: `previews/src/` is gitignored (rebuildable); `previews/manifest.json` drives incremental rebuilds.
- `user_styles.json` is optional — `data/user_data.py` validates and merges it.
- Tests run without ComfyUI installed (comfy_stub provides a stand-in `comfy_api.latest.io`).

## Security

This file is **public-safe by default**. Never add local paths, credentials, API keys, personal data, infrastructure details, or subscription info.

Before pushing: `pwsh scripts/check-agents-md.ps1 AGENTS.md CLAUDE.md` — must exit 0.

Deep architecture, chain protocol, and design rationale: `ARCHITECTURE.md`. Custom style field reference: `docs/custom-styles.md`.

## Maintenance

**Update rule:** When you change the architecture, build/test commands, or conventions, update this AGENTS.md in the same commit. Keep under 200 lines. Link to `ARCHITECTURE.md` and `docs/custom-styles.md` for detail.

**CLAUDE.md:** One-line shim: `@AGENTS.md`.

**New-repo rule:** Create AGENTS.md in the first session a new repo is worked on.

**No-overlap rule:** Explanatory prose lives in one file. AGENTS.md = agent-facing summary; `ARCHITECTURE.md` = deep reference; `docs/custom-styles.md` = field reference. Identical build/test commands may be restated verbatim. Explanatory prose must not be duplicated — link instead.
