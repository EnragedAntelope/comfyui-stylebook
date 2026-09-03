# AGENTS.md — comfyui-stylebook

650+ visual styles for ComfyUI, every one with a rendered preview you can browse before you commit. Each ships a written description, a keyword list, a matching negative prompt, plus 900+ artists with descriptors. Zero dependencies, fully offline. Built on ComfyUI V3 API, category: `conditioning/stylebook`.

**Deep references:**
- `ARCHITECTURE.md` (chain protocol, layout, design rationale — read before engine changes)
- `docs/custom-styles.md` (field reference for `user_styles.json`)

## Current state

_Last verified: 2026-09-03_

- **Status:** in active development, `pyproject.toml` at v0.13.0 (unreleased; 0.12.0 is the last release on `main`). Work in progress on the `revision-0.13.0` branch. Published to ComfyUI Manager but unadvertised. `.github/workflows/publish_action.yml` fires on a `pyproject.toml` version change on `main` — a commit touching nothing the registry ships needs no bump. `.comfyignore` says what the registry package leaves out; its patterns are gitignore-style, so root-only ones carry a leading slash.
- **Works:** all five nodes (Style, Artist, Modifier, Blend, Sheet) over the `STYLEBOOK_CHAIN` protocol; every style ships a rendered preview tile packed into WebP sprite atlases; the two-line node-face readout plus Copy-resolved-prompt (with success/failure feedback) and Pin-this-pick context items; a right-click Auto-advance cycle toggle on Style/Artist/Modifier (on by default for Cycle mode) that steps `cycle_index` by one each run, wrapping at the pool size the backend reports (a node property, so old graphs load unchanged, and it can be turned off to hold a fixed index); a "New in x.y.z" tab, a new ribbon and an A-Z/Newest sort in every picker, driven by `data/versions.py`; optional `user_styles.json` validated and merged at load; a public browsable gallery plus public artist and modifier reference pages served by GitHub Pages from the repo root; the full CI gate including a jsdom frontend suite and a no-GPU preview `--check`.
- **In progress:** style and artist curation is the steady-state work rather than a milestone — each release adds entries and re-renders the affected tiles. 0.8.0 made the "describe the rendering, not the subject" rule enforceable via the optional `scene` field; 0.9.0 extended that check to modifiers (which get no `scene` escape) and rejected negated clauses in artist descriptors; 0.10.0 moved the person-named-style map out of the tests into the data as the optional `namesake` field, added a detector for the *missing* half of that promise, and moved the 300 KB corpus out of ComfyUI's `**/*.js` extension glob into a lazily fetched `js/stylebook_data.json`. 0.12.0 closes the companion hole the `scene` rule could not see: `_ENTITY_NOUNS` in `tests/validate_data.py` rejects garments, furniture and light fixtures in a modifier's positive text, all twenty `era` records were rewritten to describe light *behaviour* rather than fixtures, and the wardrobe text moved onto a new `period_dress` axis so nothing was lost. 0.13.0 makes that entity rule hot on **styles** too: the escape is the optional `depicts` field — a declaration on the record, badged in both galleries, rather than an exemption map nothing can keep honest — with `object_artifact` and `craft_material` exempt by category. It also cache-busts the sprite atlases with a content-hashed `?v=` (their filenames are stable, so a repack that changed a category's grid drew visibly *wrong* tiles for a returning visitor, not missing ones).
- **Known gaps / next steps:** rendering new preview tiles needs a running ComfyUI and a Chroma checkpoint, and a full run takes hours — `build_previews.py` refuses to render without an explicit `--model`, because substring model resolution once silently grabbed a Turbo merge and produced plausible-but-wrong tiles; ComfyUI caches the Python data layer at startup, so a newly added style or artist is rejected by node validation until it is restarted; the namesake detector cannot see an adjectival label ("Sirkian Melodrama" shares no word with "Douglas Sirk"), so those still need declaring by hand; there is no CONDITIONING-output node and that is a settled decision, not a gap (see `ARCHITECTURE.md`).

## Architecture in 60 seconds

- **Chain protocol.** Every node takes an optional `style_chain` and emits one on a dedicated `STYLEBOOK_CHAIN` socket type (not STRING — prevents silent miswiring). Carries JSON: style + modifiers + artists + user_prompt metadata.
- **Five nodes.** Style (exclusive medium axis), Artist (additive, chainable), Modifier (one per axis), Blend (two styles at a ratio), Sheet (one subject, many styles as a list).
- **Gallery-first UX.** Each style ships a rendered preview image. Open gallery → look → click. 900+ artists each have a written descriptor so the look lands even when the model doesn't know the name.
- **Three composition rules** (differ on purpose): style = exclusive replacement; modifiers = per-axis additive; artists = chainable additive.
- **Plain Python + plain JavaScript.** No OS-specific calls, paths via `pathlib`, nothing shells out. Runs the same on Windows/macOS/Linux. Test suite runs on a machine with no ComfyUI installed.
- **Generated JS data.** `js/stylebook_data.js` is generated — never edit by hand. `js/stylebook_gallery.js` is hand-written and the generator never touches it.

## Layout

| Directory / File | Purpose |
|------------------|---------|
| `data/styles/` | One module per category, each a dict of style records |
| `data/artists.py` | Artist records, keyed by id |
| `data/modifiers.py` | Modifier records grouped onto six axes (`era` and `period_dress` are a deliberate pair — see `ARCHITECTURE.md`) |
| `data/user_data.py` | Validates and merges optional `user_styles.json` |
| `stylebook_nodes/` | Engine (pure functions), schema options, node classes, routes |
| `js/` | Frontend: gallery, recreate, readout, shared helpers, generated data, previews |
| `js/stylebook_data.json` | Generated corpus, fetched on first picker open — a `.json` so ComfyUI's `**/*.js` glob does not parse it at app start |
| `data/versions.py` | Generated: which release each entry first shipped in |
| `js/previews/` | Sprite atlases + index.json, served statically and shipped to the registry |
| `previews/` | Build ledger: `manifest.json` (tracked) and gitignored source renders |
| `scripts/` | Build and validation tooling (not shipped to registry) |
| `tests/` | unittest suite, data-layer validator, comfy_stub, jsdom frontend tests |
| `docs/` | custom-styles.md (user_styles.json field reference) |
| `docs/gallery/` | Generated public style gallery, served by GitHub Pages from `main` |
| `docs/reference/` | Generated public artist + modifier reference pages, same serving |

## Build / test / run

```bash
# Install (drop into ComfyUI/custom_nodes/)
# No pip install needed — zero dependencies

# Regenerate JS data after any change under data/
python scripts/generate_js_data.py

# After adding styles, artists or modifiers
python scripts/stamp_versions.py --stamp

# The full gate, in the order CI runs it (.github/workflows/ci.yml)
python tests/validate_data.py
python -m unittest discover -s tests -t .   # -t . is required
python scripts/stamp_versions.py --check
python scripts/generate_js_data.py --check
python scripts/dump_frontend_fixtures.py --check
python scripts/build_previews.py --check    # no GPU needed for --check
python scripts/build_gallery_page.py --check
python scripts/build_reference_pages.py --check
npm run test:frontend
python -m ruff check .
```

Rendering new preview tiles (`build_previews.py --build`) needs a running ComfyUI
and a Chroma checkpoint named explicitly via `--model`; `--check` needs neither.

## Conventions & gotchas

- Zero dependencies. Python ≥3.10. Drops into ComfyUI's `custom_nodes/` — no pip install.
- The chain socket type (`STYLEBOOK_CHAIN`) is distinct from STRING by design — prevents silent miswiring when connecting prompt to style_chain.
- `js/stylebook_data.js` and `docs/gallery/index.html` are generated. Never edit by hand.
- `js/stylebook_gallery.js` is hand-written. The generator never touches it.
- One ordering rule, `data/ordering.py`, mirrored in the gallery by `Intl.Collator`
  and bound to it by a cross-check test. Modifier axes are exempt on purpose.
  Rationale in `ARCHITECTURE.md`.
- Sprite atlases: `previews/src/` is gitignored (rebuildable); `previews/manifest.json` drives incremental rebuilds. The packed atlases the gallery reads are `js/previews/`, which the registry package keeps.
- A style whose label names a real person declares `namesake` on its own record,
  and that artist must exist. Finding a style named for someone and then nothing
  in the artist picker is the pack contradicting itself. A style label sharing a
  five-plus-letter word with a shipped artist label must either declare `namesake`
  or be exempted with a reason in `tests/validate_data._NAMESAKE_EXEMPT`.
- Every entry carries a release stamp in `data/versions.py`, which drives the
  gallery's "New" tab and newest-first sort. `stamp_versions.py --stamp` after
  adding content; CI fails on an unstamped entry.
- `js/stylebook_data.js` must stay small. ComfyUI imports every `.js` under a
  pack's web directory at app start, so the corpus lives in `stylebook_data.json`
  and is fetched when a picker first opens. A test enforces the size.
- **A style describes the rendering, not the subject.** Naming a place puts
  that place in the picture whatever the user asked for. A style that is
  genuinely defined by its setting (Liminal Space, Vanitas, Ikebana)
  declares an optional `scene` phrase instead; the validator rejects scene
  nouns in any style that has not, and the gallery badges the ones that
  have. Full rule and rationale in `ARCHITECTURE.md`.
- **Nor may it add an object.** Same rule, different noun list: a garment,
  a chair or a lamp in a style's positive text puts one in the frame. A
  style that genuinely brings an object with it (Fashion Photography,
  Magical Girl Transformation) declares the optional `depicts` phrase, and
  gets an `adds` badge. `object_artifact` and `craft_material` are exempt
  by category — both already mean "the subject is rendered *as* the thing".
  The rule is hot on modifiers with no escape at all. Rationale, and why a
  declared field beat an exemption map, in `ARCHITECTURE.md`.
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
