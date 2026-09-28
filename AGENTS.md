# AGENTS.md — comfyui-stylebook

650+ visual styles for ComfyUI, every one with a rendered preview you can browse before you commit. Each ships a written description, a keyword list, a matching negative prompt, plus 1000+ artists with descriptors. Zero dependencies, fully offline. Built on ComfyUI V3 API, category: `conditioning/stylebook`.

**Deep references:**
- `ARCHITECTURE.md` (chain protocol, layout, design rationale — read before engine changes)
- `docs/custom-styles.md` (field reference for `user_styles.json`)

## Current state

_Last verified: 2026-09-27_

- **Status:** v0.16.0 is the current release on `main` (merged from `revision-0.16.0` by pull request); v0.16.1 is on branch `revision-0.16.1`, not yet merged. Published to ComfyUI Manager but unadvertised. `.github/workflows/publish_action.yml` fires on a `pyproject.toml` version change on `main` — a commit touching nothing the registry ships needs no bump. `.comfyignore` says what the registry package leaves out; its patterns are gitignore-style, so root-only ones carry a leading slash.
- **Works:** all five nodes (Style, Artist, Modifier, Blend, Sheet) over the `STYLEBOOK_CHAIN` protocol; a rendered preview tile for every style and every modifier on all six axes, packed into WebP sprite atlases; the two-line node-face readout plus Copy-resolved-prompt and Pin-this-pick context items; the right-click Auto-advance cycle toggle; the "New in x.y.z" tab, new ribbon and A-Z/Newest sort driven by `data/versions.py`; optional `user_styles.json` validated and merged at load; the public gallery plus artist and modifier reference pages on GitHub Pages; the full CI gate including a jsdom frontend suite and a no-GPU preview `--check`.
- **0.16.0:** the six modifier tiles earlier releases left known-imperfect are fixed and re-rendered (`pastel_wash`, `near_future`, `awe`, `tense`, `light_leak`, `orthochromatic`) — the recurring cause, now in `ARCHITECTURE.md` ("Writing style text"), is that **a colour named as a noun or a quantity is drawn as a shape**. New styles include franchise looks (Pixar 3D Animation, Spider-Verse, Arcane, Classic Disney Animation, Looney Tunes, The Simpsons, South Park, Muppets, Funko Pop, LEGO Brick Build and others) plus material and folk traditions (Marble Statue, Porcelain Figurine, Pattachitra, Topographic Contour, Pop Surrealism); franchise names stay in the label and aliases, never the prose (rule and the measured exceptions in `ARCHITECTURE.md`). New artists cover animation, pin-up, manga and contemporary illustration; artists who have publicly asked not to be used as AI prompts, and names known mainly for explicit work, are left out on purpose. Several near-duplicates became aliases on existing records instead (e.g. gel lighting on Neon Noir, gacha splash art on Anime Key Visual, low-key on Chiaroscuro). `build_previews.py --prune` now also drops a removed style's manifest entry. `python tests/validate_data.py` reports the true totals.
- **0.16.1:** a reopened picker keeps its remembered search query (the grid was already filtered by it) and now shows that text in the search box, selected so the first keystroke replaces it. No data or tile changes, so by design there is no "New in 0.16.1" tab. `stamp_versions.py --stamp` now adds the current version to `RELEASES` even when it stamps nothing, matching `--from-history` and `test_this_version_is_a_known_release`.
- **Known gaps / next steps:** the Dragon Ball tile draws a house-style character whatever the wording (documented as the limit of the franchise rule); the Porcelain Figurine tile shows the material but a faceless figure; the two Krea example workflows in `examples/` use third-party nodes (`ShowText|pysssss`, `ResolutionSelector`), so users without those packs see missing nodes. Settled non-gaps, worth not re-deriving: the `era` and `mood` axes are closed to new records and `color_grade` was audited with nothing to add (`ARCHITECTURE.md` says why); artist preview tiles are declined; there is no CONDITIONING-output node. Operational facts: `build_previews.py --build` exits non-zero when it cannot reach ComfyUI — trust it only when run in the foreground, since a backgrounded wrapper reports its own status; it refuses to render without an explicit `--model`; ComfyUI caches the Python data layer at startup, so new entries fail node validation until it restarts; the namesake detector cannot see an adjectival label ("Sirkian Melodrama"), so those are declared by hand.

## Architecture in 60 seconds

- **Chain protocol.** Every node takes an optional `style_chain` and emits one on a dedicated `STYLEBOOK_CHAIN` socket type (not STRING — prevents silent miswiring). Carries JSON: style + modifiers + artists + user_prompt metadata.
- **Five nodes.** Style (exclusive medium axis), Artist (additive, chainable), Modifier (one per axis), Blend (two styles at a ratio), Sheet (one subject, many styles as a list).
- **Gallery-first UX.** Each style ships a rendered preview image. Open gallery → look → click. 1000+ artists each have a written descriptor so the look lands even when the model doesn't know the name.
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
- **Preview renders are deterministic.** `build_previews.RENDER["seed"]` is a
  fixed 42 for every tile, so a tile is a pure function of the text that
  produced it. An old-vs-new tile comparison is therefore *signal, not
  variance*: if a tile changed, the wording changed it. Reverting a record to
  its shipped text and re-rendering reproduces the shipped tile — confirmed on
  `fluorescent_overhead`, whose reverted tile differs from the committed one by
  ~1.0/channel, the same magnitude as untouched neighbours (WebP re-encode
  noise) against ~27 for a genuinely changed tile. Compare tiles by cropping
  them out of the committed atlas with `js/previews/index.json`; `previews/src/`
  is gitignored and holds only the newest render.
- **A franchise name goes in the label and aliases, not the prose or tags** —
  in the prose it summons the franchise's characters. Exceptions and the
  measured cases are in `ARCHITECTURE.md` ("Franchise names live in the label").
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
- **A modifier's aliases are checked, and a modifier tile is measured, not
  argued about.** `_check_modifier_alias_content` rejects a scene or entity noun
  in a modifier's alias list: aliases never reach the encoder, but "submerged"
  and "neon street" were the only surviving evidence that two records still
  delivered a whole scene after their prose had been cleaned. And
  `MODIFIER_BASE_STYLE` in `scripts/build_previews.py` must anchor the scene and
  framing while asserting nothing about the rendering — too thin and the modifier
  renders *as the subject*, too assertive and it suppresses the axis. Both limits
  were found by A/B render, and `ARCHITECTURE.md` says to re-run that comparison
  rather than reason about it. A modifier names the light or finish's *behaviour*:
  naming its **shape** (edge, boundary, void, halo) renders an object, naming a
  **medium or place** renders a scene, and over-protecting the subject suppresses
  the axis. All three are invisible in text review and obvious in a tile.
- **A picker's layout follows the record, never the tab.** An entry shows
  everything it carries: a style has a picture and no descriptor, so tiles; an
  artist has a descriptor and no picture, so plain rows; a modifier has both,
  so rows with a 128px thumbnail. 0.14.0 shipped a per-*group* layout
  (`groupLayout` / `previewGroups`) because three modifier axes had tiles and
  three did not — missing data wearing a layout's clothes. Both are deleted:
  `activeLayout()` returns `config.layout` and `activePreviews()` returns
  `config.showPreviews`, ungated by the query, which is what stopped a search
  from dropping the pictures. The grid's className still belongs in
  `renderGrid()`, never the constructor. `PREVIEW_AXES` in
  `scripts/build_previews.py` is now `tuple(AXES)` and the frontend declares no
  axis list at all; `tests/test_previews.py` asserts that equality **and** that
  no `PREVIEWED_AXES` came back, so a seventh axis cannot ship picture-less.
- **The preview atlas index is keyed by picker *group*.** A modifier's group is
  its axis, which is why axis atlases needed no new lookup code anywhere. A
  modifier is addressed by *label* everywhere else in the pack, so the picker
  item carries `previewId` (the record id) for the atlas — ids are stable,
  labels get reworded. Modifier tiles live in `previews/src/mod/` and the
  manifest's `modifier_tiles` section because `chiaroscuro` is both a style id
  and a modifier id.
- `user_styles.json` is optional — `data/user_data.py` validates and merges it.
  A custom style's `scene`, `depicts` and `aliases` reach the gallery like a
  built-in's; `namesake` deliberately does not, because it promises a matching
  artist record that nothing can enforce for a user file.
- **A build step that produces artefacts re-verifies them before exiting 0.**
  `build_previews.py --build` re-runs `survey()` and `stale_atlas_revs()` after
  packing and fails with a named list, so "it exited 0" means "the artefacts are
  current" rather than "the code ran".
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
