"""Build the public style gallery at docs/gallery/index.html.

The pack's whole pitch is "look at it before you commit", and until now
the only way to look was to install it first. This renders every shipped
style to a single static page that GitHub Pages serves straight off
``main``, so the gallery is browsable from the README.

It reuses what already exists rather than inventing a second pipeline:
the WebP atlases in ``js/previews/``, and the sprite arithmetic in
``generate_js_data._preview_sprites`` -- percentage background-size is
measured against the element rather than the image, so an atlas ``cols``
tiles wide is addressed in grid units. Duplicating that maths is exactly
how the page and the in-app gallery would drift apart.

The page also shows each style's prose, keywords and negative, which the
in-app gallery deliberately does not: shipping 460-odd prose blocks would
roughly double the frontend payload every ComfyUI user downloads, but on
a page somebody chose to open it is the most useful thing there is.

Usage:
    python scripts/build_gallery_page.py            # write
    python scripts/build_gallery_page.py --check    # verify (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A maintainer's own local user_styles.json must never reach a published
# page. Set before `data` is imported, since data/user_data.py reads it
# once at merge time.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

TARGET = ROOT / "docs" / "gallery" / "index.html"

#: Where the atlases sit relative to the built page.
#:
#: This only works because Pages is configured to serve the repository
#: ROOT, not ``/docs``. With ``/docs`` as the source, Pages publishes that
#: folder *as the site root*, so this path escapes above it and every
#: atlas 404s -- which is exactly what shipped the first time. Serving the
#: root instead keeps the committed atlases reachable and duplicates
#: nothing; the alternative was a second 4.4 MB copy under docs/.
#:
#: To verify locally you must reproduce the deployed layout, and a plain
#: ``python -m http.server`` from the repo root does NOT: it serves the
#: page at /docs/gallery/ with the repo above it, which is the one
#: arrangement in which a wrong prefix still works. Check the live URL, or
#: serve the repo under a path prefix that matches Pages.
ASSET_PREFIX = "../../js/previews/"



def _current_version() -> str:
    """This build's version, read out of pyproject.toml.

    A regex rather than tomllib, which arrived in 3.11 while the pack floor
    is 3.10 -- and CI actually runs 3.10.
    """
    match = re.search(
        r'(?m)^version\s*=\s*"([^"]+)"',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    return match.group(1) if match else ""


def _payload() -> dict:
    from generate_js_data import _preview_sprites  # noqa: E402

    from data.artists import ARTISTS
    from data.ordering import label_sort_key
    from data.styles import CATEGORIES, CATEGORY_LABELS, STYLES
    from data.versions import ADDED_IN, RELEASES

    version = _current_version()
    styles = sorted(STYLES.values(), key=lambda rec: label_sort_key(rec["label"]))
    return {
        "categoryLabels": {c: CATEGORY_LABELS[c] for c in CATEGORIES},
        "categories": list(CATEGORIES),
        "artistCount": len(ARTISTS),
        "version": version,
        "releases": list(RELEASES),
        "sprites": _preview_sprites(),
        "styles": [
            {
                "id": rec["id"],
                "label": rec["label"],
                "category": rec.get("category", ""),
                "aliases": list(rec.get("aliases", [])),
                "scene": rec.get("scene", ""),
                "added": ADDED_IN["styles"].get(rec["id"], ""),
                "namesake": rec.get("namesake", ""),
                "prose": rec.get("prose", ""),
                "tags": rec.get("tags", ""),
                "negative": rec.get("negative", ""),
            }
            for rec in styles
        ],
    }


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stylebook — every style, with a preview</title>
<meta name="description" content="Browse all __STYLE_COUNT__ visual styles in the Stylebook node pack for ComfyUI. Every one ships a rendered preview, a written description, a keyword list and a matching negative prompt.">
<!-- Inline SVG, so the page stops requesting /favicon.ico from the site root
     and 404ing. Four swatches on a dark rounded tile: reads as a palette at
     16px and holds up against both light and dark browser chrome. `#` is
     percent-encoded because it would otherwise open a URI fragment. -->
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%230f1115'/><rect x='5' y='5' width='10' height='10' rx='2' fill='%232b6fd4'/><rect x='17' y='5' width='10' height='10' rx='2' fill='%23e8543f'/><rect x='5' y='17' width='10' height='10' rx='2' fill='%23f0b429'/><rect x='17' y='17' width='10' height='10' rx='2' fill='%232f9e63'/></svg>">
<style>
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #14161a; --muted: #5c6470;
  --card: #f4f5f7; --line: #dfe3e8; --accent: #2b6fd4;
  --tile: 168px; --label: 38px; --cat: 15px;
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
header { padding: 28px 20px 12px; max-width: 1180px; margin: 0 auto; }
h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: -0.01em; }
.lede { margin: 0 0 4px; color: var(--muted); max-width: 62ch; }
.controls {
  position: sticky; top: 0; z-index: 5; background: var(--bg);
  border-bottom: 1px solid var(--line); padding: 12px 20px;
}
.controls-inner {
  max-width: 1180px; margin: 0 auto;
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
}
#q {
  flex: 1 1 260px; min-width: 0; padding: 9px 12px;
  border: 1px solid var(--line); border-radius: 7px;
  background: var(--card); color: inherit; font: inherit;
}
#cat { padding: 9px 10px; border: 1px solid var(--line); border-radius: 7px;
       background: var(--card); color: inherit; font: inherit; }
#count { color: var(--muted); font-variant-numeric: tabular-nums; }
main { max-width: 1180px; margin: 0 auto; padding: 18px 20px 60px; }
#grid {
  display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(var(--tile), 1fr));
}
.tile {
  border: 2px solid transparent; border-radius: 9px; background: var(--card);
  overflow: hidden; cursor: pointer; padding: 0; color: inherit;
  font: inherit; text-align: center; display: flex; flex-direction: column;
}
.tile:hover, .tile:focus-visible { border-color: var(--accent); outline: none; }
/* Skip layout and paint for tiles scrolled out of view. Six hundred of
   them rebuild on every keystroke; virtualising the grid would mean
   owning scroll position and the result count by hand to reproduce what
   the browser already does in two declarations. The intrinsic size has
   to match what a tile actually occupies or the scrollbar jumps. */
.tile {
  content-visibility: auto;
  contain-intrinsic-size: auto var(--tile)
    auto calc(var(--tile) + var(--label) + var(--cat));
}
.art {
  position: relative;
  width: 100%; aspect-ratio: 1; background-repeat: no-repeat;
  background-color: rgba(127,127,127,.12);
}
/* Own colours, not theme variables: it sits on an arbitrary photograph
   and has to stay legible on every one of them. */
.scene {
  position: absolute; left: 4px; bottom: 4px; padding: 1px 5px;
  border-radius: 3px; background: rgba(12,12,12,.72); color: #f2f2f2;
  font-size: 9px; font-weight: 600; line-height: 1.4; letter-spacing: .06em;
  text-transform: uppercase;
}
/* Opposite corner from .scene so the two never collide. */
.newbadge {
  position: absolute; right: 4px; top: 4px; padding: 1px 5px;
  border-radius: 3px; background: var(--accent); color: #fff;
  font-size: 9px; font-weight: 700; line-height: 1.4; letter-spacing: .06em;
  text-transform: uppercase;
}
.name { padding: 6px 6px 0; font-size: 12px; font-weight: 600; line-height: 1.25; }
.cat {
  padding: 2px 6px 7px; font-size: 10px; letter-spacing: .04em;
  text-transform: uppercase; color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.empty { padding: 60px 0; text-align: center; color: var(--muted); }
dialog {
  border: 1px solid var(--line); border-radius: 12px; padding: 0;
  background: var(--bg); color: var(--fg);
  width: min(680px, 92vw); max-height: 88vh;
}
dialog::backdrop { background: rgba(0,0,0,.55); }
.sheet { padding: 20px 22px 22px; }
.sheet h2 { margin: 0 0 2px; font-size: 20px; }
.sheet .where { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
.sheet .art { max-width: 260px; border-radius: 8px; margin-bottom: 16px; }
.field { margin-bottom: 14px; }
.field h3 {
  margin: 0 0 4px; font-size: 11px; letter-spacing: .05em;
  text-transform: uppercase; color: var(--muted);
}
.field p { margin: 0; }
.field code {
  display: block; white-space: pre-wrap; word-break: break-word;
  background: var(--card); border: 1px solid var(--line);
  border-radius: 6px; padding: 8px 10px; font-size: 12.5px;
}
.close {
  position: sticky; top: 0; float: right; margin: 10px 12px 0 0;
  border: 1px solid var(--line); border-radius: 7px; background: var(--card);
  color: inherit; font: inherit; padding: 5px 12px; cursor: pointer;
}
footer { max-width: 1180px; margin: 0 auto; padding: 0 20px 40px; color: var(--muted); font-size: 13px; }
</style>
</head>
<body>
<header>
  <h1>Stylebook</h1>
  <p class="lede">Every one of the __STYLE_COUNT__ visual styles in the
  <a href="https://github.com/EnragedAntelope/comfyui-stylebook">Stylebook</a>
  node pack for ComfyUI, each with the preview it ships. Click any tile for the
  exact prose, keywords and negative prompt the node emits.</p>
  <p class="lede">The pack also ships __ARTIST_COUNT__ artists with written
  descriptors, and modifiers for lighting, colour, era, finish and mood.</p>
</header>

<div class="controls"><div class="controls-inner">
  <input id="q" type="search" placeholder="Search styles by name, alias, category or description" autocomplete="off" spellcheck="false" aria-label="Search styles">
  <select id="cat" aria-label="Filter by category"></select>
  <select id="sort" aria-label="Sort order">
    <option value="az">A-Z</option>
    <option value="new">Newest first</option>
  </select>
  <span id="count" aria-live="polite"></span>
</div></div>

<main><div id="grid"></div></main>

<footer>
  Previews rendered against <span id="model"></span> at a fixed seed, one subject per
  category, so tiles are comparable with each other.
</footer>

<dialog id="sheet"><button class="close" type="button">Close</button><div class="sheet"></div></dialog>

<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const ASSETS = "__ASSET_PREFIX__";
const grid = document.getElementById("grid");
const q = document.getElementById("q");
const catSel = document.getElementById("cat");
const sortSel = document.getElementById("sort");
const countEl = document.getElementById("count");

/* Rank by position in the release list rather than by comparing version
   strings: "0.10.0" sorts before "0.9.0" as text. */
const RANK = new Map((DATA.releases || []).map((v, i) => [v, i]));
const isNew = s => Boolean(DATA.version) && s.added === DATA.version;
const sheet = document.getElementById("sheet");

/* The manifest stores the checkpoint exactly as ComfyUI names it, which
   on Windows is a backslashed subfolder path with a .safetensors suffix.
   That is build provenance, not something to publish verbatim. */
document.getElementById("model").textContent =
  ((DATA.sprites && DATA.sprites.model) || "")
    .split(/[\\\\/]/).pop().replace(/\\.(safetensors|ckpt|sft)$/i, "")
  || "a fixed checkpoint";

catSel.append(new Option("All categories", ""));
/* Offered first, and only when this release actually added something --
   a filter that is always there and sometimes empty teaches you to
   ignore it. */
if (DATA.styles.some(isNew)) {
  catSel.append(new Option("New in " + DATA.version, "__new__"));
}
for (const c of DATA.categories) catSel.append(new Option(DATA.categoryLabels[c] || c, c));

/* Same sprite arithmetic as js/stylebook_gallery.js: percentage
   background-size resolves against the element, not the image, so an
   atlas `cols` tiles wide scaled to cols*100% makes each cell exactly one
   tile wide at any element size. Position then interpolates across the
   remaining cells, which is why it divides by cols - 1. */
function applySprite(el, category, id) {
  const entry = DATA.sprites && DATA.sprites.categories && DATA.sprites.categories[category];
  const cell = entry && entry.tiles && entry.tiles[id];
  if (!cell || !entry.cols || !entry.rows) return false;
  const x = entry.cols > 1 ? (cell[0] / (entry.cols - 1)) * 100 : 0;
  const y = entry.rows > 1 ? (cell[1] / (entry.rows - 1)) * 100 : 0;
  el.style.backgroundImage = "url('" + ASSETS + entry.atlas + "')";
  el.style.backgroundSize = entry.cols * 100 + "% " + entry.rows * 100 + "%";
  el.style.backgroundPosition = x + "% " + y + "%";
  return true;
}

const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });

function matches(s, needle) {
  if (!needle) return true;
  return (s.label + " " + s.id + " " + s.aliases.join(" ") + " " + s.scene +
          " " + (DATA.categoryLabels[s.category] || "") + " " + s.prose +
          " " + s.tags)
         .toLowerCase().includes(needle);
}

function render() {
  const needle = q.value.trim().toLowerCase();
  const cat = catSel.value;
  const inScope = s => !cat || (cat === "__new__" ? isNew(s) : s.category === cat);
  const visible = DATA.styles.filter(s => inScope(s) && matches(s, needle));
  if (sortSel.value === "new") {
    visible.sort((a, b) => {
      const ra = RANK.has(a.added) ? RANK.get(a.added) : -1;
      const rb = RANK.has(b.added) ? RANK.get(b.added) : -1;
      return rb - ra || collator.compare(a.label, b.label);
    });
  }
  countEl.textContent = visible.length + (visible.length === 1 ? " style" : " styles");
  grid.replaceChildren();
  if (!visible.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = "Nothing matches that.";
    grid.append(p);
    return;
  }
  const frag = document.createDocumentFragment();
  for (const s of visible) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "tile";
    const art = document.createElement("div");
    art.className = "art";
    applySprite(art, s.category, s.id);
    /* Overlaid on the art, so it costs no row height. */
    const tips = [];
    if (s.scene) {
      const b = document.createElement("span");
      b.className = "scene";
      b.textContent = "scene";
      art.append(b);
      tips.push("Places your subject in " + s.scene + ".");
    }
    if (isNew(s)) {
      const n = document.createElement("span");
      n.className = "newbadge";
      n.textContent = "new";
      art.append(n);
      tips.push("New in " + DATA.version + ".");
    }
    if (s.namesake) tips.push("Named for " + s.namesake + ".");
    if (tips.length) tile.title = tips.join(" ");
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = s.label;
    tile.append(art, name);
    /* The category caption only earns its place when the filter is not
       already showing one category -- same rule as the in-app gallery. */
    if (!cat) {
      const c = document.createElement("div");
      c.className = "cat";
      c.textContent = DATA.categoryLabels[s.category] || s.category;
      tile.append(c);
    }
    tile.addEventListener("click", () => open(s));
    frag.append(tile);
  }
  grid.append(frag);
}

function field(title, text, mono) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  const h = document.createElement("h3");
  h.textContent = title;
  const body = document.createElement(mono ? "code" : "p");
  body.textContent = text;
  wrap.append(h, body);
  return wrap;
}

function open(s) {
  const body = sheet.querySelector(".sheet");
  body.replaceChildren();
  const h = document.createElement("h2");
  h.textContent = s.label;
  const where = document.createElement("div");
  where.className = "where";
  where.textContent = (DATA.categoryLabels[s.category] || s.category) +
    (s.added ? " \\u00b7 added in " + s.added : "") +
    (s.namesake ? " \\u00b7 named for " + s.namesake : "") +
    (s.aliases.length ? " \\u00b7 also: " + s.aliases.join(", ") : "");
  const art = document.createElement("div");
  art.className = "art";
  applySprite(art, s.category, s.id);
  body.append(h, where, art);
  if (s.scene) {
    body.append(field("Sets the scene",
      "This style places your subject in " + s.scene +
      ". Most styles only change how your subject is rendered; this one " +
      "also decides where it is.", false));
  }
  if (s.prose) body.append(field("Prose", s.prose, true));
  if (s.tags) body.append(field("Keywords", s.tags, true));
  if (s.negative) body.append(field("Negative prompt", s.negative, true));
  sheet.showModal();
}

sheet.querySelector(".close").addEventListener("click", () => sheet.close());
q.addEventListener("input", render);
catSel.addEventListener("change", render);
sortSel.addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def _embed(payload: dict) -> str:
    """Serialise the payload for a ``<script type="application/json">`` block.

    ``json.dumps`` escapes nothing HTML cares about, so a style whose text
    ever contained ``</script>`` would close the block early and the rest
    of the page would be parsed as markup. No shipped style does today;
    that is a property of the current data, not of the code, and one
    ASCII-art or HTML-themed entry is all it takes. ``<`` and ``&`` are
    escaped as JSON string escapes, which JSON.parse decodes right back,
    so the value the page reads is byte-identical either way.
    """
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )


def generate() -> str:
    payload = _payload()
    return (
        TEMPLATE
        .replace("__PAYLOAD__", _embed(payload))
        .replace("__STYLE_COUNT__", str(len(payload["styles"])))
        .replace("__ARTIST_COUNT__", str(payload["artistCount"]))
        .replace("__ASSET_PREFIX__", ASSET_PREFIX)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public style gallery page.")
    parser.add_argument("--check", action="store_true",
                        help="Verify only; exit non-zero if stale.")
    args = parser.parse_args()

    expected = generate()

    if args.check:
        if not TARGET.is_file():
            print(f"FAIL: {TARGET.relative_to(ROOT)} does not exist. "
                  f"Run: python scripts/build_gallery_page.py")
            return 1
        if TARGET.read_text(encoding="utf-8") != expected:
            print("FAIL: the public gallery page is stale. "
                  "Run: python scripts/build_gallery_page.py")
            return 1
        print("PASS: the public gallery page is current.")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Written: {TARGET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
