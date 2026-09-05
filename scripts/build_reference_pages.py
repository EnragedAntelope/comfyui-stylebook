"""Build the public artist and modifier reference pages.

docs/reference/artists.html and docs/reference/modifiers.html. Companion
pages to the style gallery: the gallery answers "what does this style look
like", these answer "what is in the pack" -- every artist descriptor and
every modifier's exact emitted text, searchable, so gaps in coverage are
visible without installing anything.

Same architecture as ``build_gallery_page.py`` on purpose: one static page
per subject, data embedded as a JSON script tag, no dependencies. The
artist page is sprite-free -- a descriptor has nothing to show. The
modifier page carries tiles for the three purely visual axes (lighting,
colour grade, finish), each preceded once by the baseline render they are
all a deviation from; era, period dress and mood stay text-only.

GitHub Pages serves the **repo root**, not docs/, so an asset path here is
relative to docs/reference/ and has to climb two levels to reach the
committed atlases: ``../../js/previews/``. A plain ``python -m http.server``
from the repo root is the one arrangement in which a wrong prefix still
works, so it cannot verify this -- check the live URL.

Usage:
    python scripts/build_reference_pages.py            # write both
    python scripts/build_reference_pages.py --check    # verify (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Same guard as every other publisher: a maintainer's local
# user_styles.json must never reach a published page.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

TARGETS = {
    "artists": ROOT / "docs" / "reference" / "artists.html",
    "modifiers": ROOT / "docs" / "reference" / "modifiers.html",
}

#: Where the committed sprite atlases sit relative to a page in
#: docs/reference/. See the module docstring: Pages serves the repo root.
ASSET_PREFIX = "../../js/previews/"

#: Shared visual language with docs/gallery/index.html. Kept as a literal
#: rather than imported from that script: the two templates evolve at
#: different rates and a shared CSS module would couple their releases.
_CSS = """
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #14161a; --muted: #5c6470;
  --card: #f4f5f7; --line: #dfe3e8; --accent: #2b6fd4;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101216; --fg: #e8eaed; --muted: #99a1ad;
    --card: #1a1d23; --line: #2a2f38; --accent: #6aa4f5;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
a { color: var(--accent); }
header { padding: 28px 20px 12px; max-width: 980px; margin: 0 auto; }
h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: -0.01em; }
.lede { margin: 0 0 4px; color: var(--muted); max-width: 62ch; }
nav { margin-top: 10px; font-size: 14px; }
.controls {
  position: sticky; top: 0; z-index: 5; background: var(--bg);
  border-bottom: 1px solid var(--line); padding: 12px 20px;
}
.controls-inner {
  max-width: 980px; margin: 0 auto;
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
}
#q { flex: 1 1 260px; min-width: 0; padding: 9px 12px;
     border: 1px solid var(--line); border-radius: 7px;
     background: var(--card); color: inherit; font: inherit; }
#group { padding: 9px 10px; border: 1px solid var(--line); border-radius: 7px;
        background: var(--card); color: inherit; font: inherit; }
#count { color: var(--muted); font-variant-numeric: tabular-nums; }
main { max-width: 980px; margin: 0 auto; padding: 18px 20px 60px; }
.entry {
  background: var(--card); border-radius: 9px; padding: 12px 16px;
  margin-bottom: 10px;
  content-visibility: auto; contain-intrinsic-size: auto 120px;
}
.entry h2 { margin: 0; font-size: 15px; display: flex; gap: 8px;
            align-items: baseline; flex-wrap: wrap; }
.entry .tag {
  font-size: 10px; letter-spacing: .05em; text-transform: uppercase;
  color: var(--muted); white-space: nowrap;
}
.entry .also { font-size: 12px; color: var(--muted); }
.entry p { margin: 6px 0 0; }
.entry code {
  display: block; white-space: pre-wrap; word-break: break-word;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 6px; padding: 7px 9px; font-size: 12.5px;
  margin-top: 6px;
}
.axis-h {
  margin: 26px 0 10px; font-size: 13px; letter-spacing: .06em;
  text-transform: uppercase; color: var(--muted);
}
/* Preview thumbnail on an entry, and the baseline card that opens a
   tiled axis. The entry is a flex row once it has art, so the text
   column keeps its own min-width: 0 and can still wrap. */
.entry.has-art {
  display: flex; gap: 14px; align-items: flex-start;
  /* The 120px guess above is for a text-only entry; a tiled one is taller,
     and an under-guess makes the scrollbar jump as content-visibility
     measures each entry for real. */
  contain-intrinsic-size: auto 170px;
}
.entry.has-art .body { flex: 1 1 auto; min-width: 0; }
.art {
  flex: 0 0 auto; width: 128px; height: 128px; border-radius: 7px;
  background: var(--bg) no-repeat center / cover; border: 1px solid var(--line);
}
.baseline {
  display: flex; gap: 14px; align-items: center;
  background: var(--card); border: 1px dashed var(--line);
  border-radius: 9px; padding: 12px 16px; margin-bottom: 10px;
}
.baseline p { margin: 0; color: var(--muted); max-width: 62ch; }
.baseline strong { color: var(--fg); }
.empty { padding: 60px 0; text-align: center; color: var(--muted); }
footer { max-width: 980px; margin: 0 auto; padding: 0 20px 40px;
         color: var(--muted); font-size: 13px; }
"""

_JS = """
const DATA = JSON.parse(document.getElementById("data").textContent);
const ASSETS = "__ASSET_PREFIX__";
const q = document.getElementById("q");
const groupSel = document.getElementById("group");
const countEl = document.getElementById("count");
const main = document.querySelector("main");

for (const [value, label] of DATA.groups) {
  groupSel.append(new Option(label, value));
}

function matches(e, needle) {
  if (!needle) return true;
  return e.search.toLowerCase().includes(needle);
}

/* Same sprite arithmetic as js/stylebook_gallery.js and the gallery page.
   The sprite index is keyed by *picker group*, and a modifier's group is
   its axis, so an axis atlas is reached with exactly the code a category
   atlas is. `rev` is the atlas content hash: the filename is stable, so
   without it a repack that changes a grid composites new offsets over a
   browser's cached old sheet and draws visibly wrong tiles. */
function applySprite(el, group, id) {
  const entry = DATA.sprites && DATA.sprites.categories
    && DATA.sprites.categories[group];
  const cell = entry && entry.tiles && entry.tiles[id];
  if (!cell || !entry.cols || !entry.rows) return false;
  const x = entry.cols > 1 ? (cell[0] / (entry.cols - 1)) * 100 : 0;
  const y = entry.rows > 1 ? (cell[1] / (entry.rows - 1)) * 100 : 0;
  const src = ASSETS + entry.atlas + (entry.rev ? "?v=" + entry.rev : "");
  el.style.backgroundImage = "url('" + src + "')";
  el.style.backgroundSize = entry.cols * 100 + "% " + entry.rows * 100 + "%";
  el.style.backgroundPosition = x + "% " + y + "%";
  return true;
}

/* The tile that says what all the others on this axis are a deviation
   from. A modifier tile is close to meaningless without it: "warmer than
   what?" is a fair question. Shown once per tiled axis, never filtered
   away, because it is not an entry. */
function baselineEl(group) {
  const box = document.createElement("div");
  box.className = "baseline";
  const art = document.createElement("div");
  art.className = "art";
  if (!applySprite(art, group, DATA.baselineId)) return null;
  const p = document.createElement("p");
  const strong = document.createElement("strong");
  strong.textContent = "No modifier. ";
  p.append(strong, document.createTextNode(
    "Every tile on this axis is this same render with only the modifier "
    + "changed."));
  box.append(art, p);
  return box;
}

function entryEl(e) {
  const div = document.createElement("article");
  div.className = "entry";
  /* Art first, then a text column, so the DOM order matches the reading
     order rather than relying on the flex direction to fix it. */
  let body = div;
  if (e.mid && DATA.previewAxes && DATA.previewAxes.includes(e.group)) {
    const art = document.createElement("div");
    art.className = "art";
    if (applySprite(art, e.group, e.mid)) {
      div.classList.add("has-art");
      div.append(art);
      body = document.createElement("div");
      body.className = "body";
      div.append(body);
    }
  }
  const h = document.createElement("h2");
  h.textContent = e.label;
  const tag = document.createElement("span");
  tag.className = "tag";
  tag.textContent = e.groupLabel;
  h.append(tag);
  body.append(h);
  if (e.also) {
    const also = document.createElement("div");
    also.className = "also";
    also.textContent = "also: " + e.also;
    body.append(also);
  }
  if (e.detail) {
    const p = document.createElement("p");
    p.textContent = e.detail;
    body.append(p);
  }
  for (const block of e.blocks || []) {
    const code = document.createElement("code");
    code.textContent = block.text;
    code.title = block.title;
    body.append(code);
  }
  return div;
}

function render() {
  const needle = q.value.trim().toLowerCase();
  const group = groupSel.value;
  const visible = DATA.entries.filter(e =>
    (!group || e.group === group) && matches(e, needle));
  countEl.textContent = visible.length + (visible.length === 1
    ? " entry" : " entries");
  main.replaceChildren();
  if (!visible.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "Nothing matches that.";
    main.append(p);
    return;
  }
  let lastGroup = null;
  const frag = document.createDocumentFragment();
  /* Modifiers arrive grouped by axis in data order (era stays
     chronological). Artists arrive pre-sorted flat, so their group never
     changes between neighbours and no heading ever renders. */
  for (const e of visible) {
    if (DATA.groupHeadings && e.group && e.group !== lastGroup) {
      const h = document.createElement("h2");
      h.className = "axis-h";
      h.textContent = e.groupLabel;
      frag.append(h);
      lastGroup = e.group;
      if (DATA.previewAxes && DATA.previewAxes.includes(e.group)) {
        const base = baselineEl(e.group);
        if (base) frag.append(base);
      }
    }
    frag.append(entryEl(e));
  }
  main.append(frag);
}

q.addEventListener("input", render);
groupSel.addEventListener("change", render);
render();
"""


def _embed(payload: dict) -> str:
    """Serialise payload for a <script type="application/json"> block.

    Identical escaping to build_gallery_page._embed -- see the rationale
    there about ``</script>`` closing the block early.
    """
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )


def _page(*, heading: str, title: str, lede: str, nav: str,
          placeholder: str, payload: dict) -> str:
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{lede}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%230f1115'/><rect x='5' y='5' width='10' height='10' rx='2' fill='%232b6fd4'/><rect x='17' y='5' width='10' height='10' rx='2' fill='%23e8543f'/><rect x='5' y='17' width='10' height='10' rx='2' fill='%23f0b429'/><rect x='17' y='17' width='10' height='10' rx='2' fill='%232f9e63'/></svg>">
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>{heading}</h1>
  <p class="lede">{lede}</p>
  <nav>{nav}</nav>
</header>

<div class="controls"><div class="controls-inner">
  <input id="q" type="search" placeholder="{placeholder}"
         autocomplete="off" spellcheck="false"
         aria-label="Search">
  <select id="group" aria-label="Filter"></select>
  <span id="count" aria-live="polite"></span>
</div></div>

<main></main>

<footer>Part of the <a
  href="https://github.com/EnragedAntelope/comfyui-stylebook">Stylebook</a>
node pack for ComfyUI. See also the
<a href="../gallery/">style gallery</a>.</footer>

<script id="data" type="application/json">{_embed(payload)}</script>
<script>{_JS.replace("__ASSET_PREFIX__", ASSET_PREFIX)}</script>
</body>
</html>
"""
    return html


def _artists_payload() -> dict:
    from data.artists import ARTIST_CATEGORIES, ARTIST_CATEGORY_LABELS, ARTISTS
    from data.ordering import label_sort_key

    labels = {c: ARTIST_CATEGORY_LABELS[c] for c in ARTIST_CATEGORIES}
    entries = []
    for rec in sorted(ARTISTS.values(),
                      key=lambda r: label_sort_key(r["label"])):
        cat = rec.get("category", "")
        entries.append({
            "label": rec["label"],
            "group": cat,
            "groupLabel": labels.get(cat, cat),
            "also": ", ".join(rec.get("aliases", [])),
            "detail": rec.get("descriptor", ""),
            # One haystack per entry keeps the client-side filter dumb.
            "search": " ".join([
                rec["label"], cat, labels.get(cat, ""),
                " ".join(rec.get("aliases", [])),
                rec.get("descriptor", ""),
            ]),
        })
    return {
        "groups": [["", "All"]] + [[c, labels[c]] for c in ARTIST_CATEGORIES],
        "entries": entries,
        # Flat A-Z list: interleaving category headings over an
        # alphabetically sorted pool would repeat each heading dozens of
        # times. The dropdown does that job instead.
        "groupHeadings": False,
    }


def _modifiers_payload() -> dict:
    from build_previews import BASELINE_ID, PREVIEW_AXES  # noqa: E402
    from generate_js_data import _preview_sprites  # noqa: E402

    from data.modifiers import AXES, MODIFIERS, MODIFIERS_BY_AXIS

    axis_labels = {
        "lighting": "Lighting", "color_grade": "Colour Grade",
        "era": "Era", "period_dress": "Period Dress",
        "finish": "Finish", "mood": "Mood",
    }
    entries = []
    for axis in AXES:
        for mid in MODIFIERS_BY_AXIS.get(axis, []):
            rec = MODIFIERS.get(mid)
            if not rec:
                continue
            blocks = []
            if rec.get("prose"):
                blocks.append({"title": "prose output", "text": rec["prose"]})
            if rec.get("tags"):
                blocks.append({"title": "tags output", "text": rec["tags"]})
            if rec.get("negative"):
                blocks.append({"title": "negative output",
                               "text": rec["negative"]})
            entries.append({
                "label": rec["label"],
                # The record id, which is what the atlas is keyed by. The
                # rest of the pack addresses a modifier by label, and a
                # label can be reworded.
                "mid": mid,
                "group": axis,
                "groupLabel": axis_labels.get(axis, axis),
                "also": ", ".join(rec.get("aliases", [])),
                "blocks": blocks,
                "search": " ".join([
                    rec["label"], axis_labels.get(axis, axis),
                    " ".join(rec.get("aliases", [])),
                    rec.get("prose", ""), rec.get("tags", ""),
                ]),
            })
    return {
        "groups": [["", "All"]] + [[a, axis_labels[a]] for a in AXES],
        "entries": entries,
        # Data order within each axis is meaningful (era reads
        # chronologically), so headings carry real information here.
        "groupHeadings": True,
        # Reshaped atlas coordinates, exactly as the gallery and the public
        # style gallery consume them. Empty until the tiles are rendered,
        # in which case every applySprite() call returns false and the page
        # renders as it did before tiles existed.
        "sprites": _preview_sprites(),
        "previewAxes": list(PREVIEW_AXES),
        "baselineId": BASELINE_ID,
    }


def generate_all() -> dict[str, str]:
    return {
        "artists": _page(
            heading="Stylebook artists",
            title="Stylebook — every artist, with its descriptor",
            lede="Every artist shipped with the Stylebook node pack for "
                 "ComfyUI, each with the written descriptor the node emits "
                 "so the look lands even when the model does not know the "
                 "name.",
            nav='<a href="../gallery/">Style gallery</a> · '
                '<a href="modifiers.html">Modifier reference</a>',
            placeholder="Search artists by name, movement, or what their "
                        "work looks like",
            payload=_artists_payload(),
        ),
        "modifiers": _page(
            heading="Stylebook modifiers",
            title="Stylebook — every modifier, verbatim",
            lede="Every lighting, colour-grade, era, period-dress, "
                 "finish and mood "
                 "modifier in the Stylebook node pack for ComfyUI, shown "
                 "as the exact prose, keyword and negative text the node "
                 "emits. The three purely visual axes also carry a "
                 "rendered tile, against one fixed base render.",
            nav='<a href="../gallery/">Style gallery</a> · '
                '<a href="artists.html">Artist reference</a>',
            placeholder="Search modifiers by name, alias or effect",
            payload=_modifiers_payload(),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the public artist and modifier reference pages."
    )
    parser.add_argument("--check", action="store_true",
                        help="Verify only; exit non-zero if stale.")
    args = parser.parse_args()

    expected = generate_all()

    if args.check:
        problems = []
        for key, target in TARGETS.items():
            if not target.is_file():
                problems.append(f"{target.relative_to(ROOT)} does not exist")
            elif target.read_text(encoding="utf-8") != expected[key]:
                problems.append(f"{target.relative_to(ROOT)} is stale")
        if problems:
            print("FAIL: " + "; ".join(problems) +
                  ". Run: python scripts/build_reference_pages.py")
            return 1
        print("PASS: reference pages are current.")
        return 0

    for key, target in TARGETS.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected[key], encoding="utf-8", newline="\n")
        print(f"Written: {target.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
