# AGENTS.md — comfyui-stylebook

450+ visual styles for ComfyUI, every one with a rendered preview you can browse before you commit. Each ships a written description, a keyword list, a matching negative prompt, plus 700+ artists with descriptors. Zero dependencies, fully offline. Built on ComfyUI V3 API, category: `conditioning/stylebook`.

**Deep references:**
- `ARCHITECTURE.md` (chain protocol, layout, design rationale — read before engine changes)
- `docs/custom-styles.md` (field reference for `user_styles.json`)

## Architecture in 60 seconds

- **Chain protocol.** Every node takes an optional `style_chain` and emits one on a dedicated `STYLEBOOK_CHAIN` socket type (not STRING — prevents silent miswiring). Carries JSON: style + modifiers + artists + user_prompt metadata.
- **Five nodes.** Style (exclusive medium axis), Artist (additive, chainable), Modifier (one per axis), Blend (two styles at a ratio), Sheet (one subject, many styles as a list).
- **Gallery-first UX.** Each style ships a rendered preview image. Open gallery → look → click. 700+ artists each have a written descriptor so the look lands even when the model doesn't know the name.
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

# Regenerate JS data after any change under data/
python scripts/generate_js_data.py

# The full gate, in the order CI runs it (.github/workflows/ci.yml)
python tests/validate_data.py
python -m unittest discover -s tests -t .   # -t . is required
python scripts/generate_js_data.py --check
python scripts/dump_frontend_fixtures.py --check
python scripts/build_previews.py --check    # no GPU needed for --check
npm run test:frontend
python -m ruff check .
```

Rendering new preview tiles (`build_previews.py --build`) needs a running ComfyUI
and a Chroma checkpoint; `--check` needs neither.

## Conventions & gotchas

- Zero dependencies. Python ≥3.10. Drops into ComfyUI's `custom_nodes/` — no pip install.
- The chain socket type (`STYLEBOOK_CHAIN`) is distinct from STRING by design — prevents silent miswiring when connecting prompt to style_chain.
- `js/stylebook_data.js` is generated. Never edit by hand.
- `js/stylebook_gallery.js` is hand-written. The generator never touches it.
- One ordering rule, `data/ordering.py`, mirrored in the gallery by `Intl.Collator`
  and bound to it by a cross-check test. Modifier axes are exempt on purpose.
  Rationale in `ARCHITECTURE.md`.
- Sprite atlases: `previews/src/` is gitignored (rebuildable); `previews/manifest.json` drives incremental rebuilds.
- `user_styles.json` is optional — `data/user_data.py` validates and merges it.
- Tests run without ComfyUI installed (comfy_stub provides a stand-in `comfy_api.latest.io`).

## Security

This file is **public-safe by default**. Never add local paths, credentials, API keys, personal data, infrastructure details, or subscription info.

Before pushing a change to this file or CLAUDE.md, run the maintainer's denylist
checker over both. It lives outside this repo (it is shared across repos, not
shipped here), so use the path from your own environment notes; it must exit 0.

Deep architecture, chain protocol, and design rationale: `ARCHITECTURE.md`. Custom style field reference: `docs/custom-styles.md`.

## Maintenance

**Update rule:** When you change the architecture, build/test commands, or conventions, update this AGENTS.md in the same commit. Keep under 200 lines. Link to `ARCHITECTURE.md` and `docs/custom-styles.md` for detail.

**CLAUDE.md:** One-line shim: `@AGENTS.md`.

**New-repo rule:** Create AGENTS.md in the first session a new repo is worked on.

**No-overlap rule:** Explanatory prose lives in one file. AGENTS.md = agent-facing summary; `ARCHITECTURE.md` = deep reference; `docs/custom-styles.md` = field reference. Identical build/test commands may be restated verbatim. Explanatory prose must not be duplicated — link instead.
