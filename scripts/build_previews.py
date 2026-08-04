"""Build and pack the style gallery preview thumbnails.

The gallery shows one rendered thumbnail per style. Keeping 400-plus of
those honest by hand is not possible, so the build is content-addressed:
every tile records a hash of the exact inputs that produced it, and a
tile whose inputs have changed is rebuilt.

    python scripts/build_previews.py --check      # what is stale or missing
    python scripts/build_previews.py --build      # render only those
    python scripts/build_previews.py --build --all       # force everything
    python scripts/build_previews.py --build --only craft_material
    python scripts/build_previews.py --pack       # repack atlases only
    python scripts/build_previews.py --style <id> # redo one bad tile
    python scripts/build_previews.py --contact-sheet   # labelled review sheets

``--check`` is the CI gate. It needs no GPU and no ComfyUI: it compares
the manifest against the data layer and fails when they have drifted, so
adding or editing a style tells you its thumbnail is now a lie.

Rendering needs a running ComfyUI. Point at it with --url, and pick the
checkpoint with --model (defaults to the first Chroma model it finds).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A maintainer's own local user_styles.json must never make --check
# machine-dependent or reach a rendered preview. Set before any `data`
# import below, since data/user_data.py reads this once at merge time.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

SRC_DIR = ROOT / "previews" / "src"
OUT_DIR = ROOT / "js" / "previews"
MANIFEST = ROOT / "previews" / "manifest.json"

DEFAULT_URL = "http://127.0.0.1:8188"
TILE_SIZE = 256

# Render settings. Changing any of these invalidates every tile, which is
# the point: the manifest hash covers them.
RENDER = {
    "seed": 42,
    "steps": 26,
    "cfg": 3.5,
    "sampler": "euler",
    "scheduler": "beta",
    "width": 1024,
    "height": 1024,
}

# A style is only legible when the subject suits it. Rendering a postage
# stamp, a cereal box or a cross-stitch sampler as "a person in a studio"
# shows the subject, not the style. The subject is part of the tile hash,
# so changing one of these re-renders exactly that category.
CATEGORY_SUBJECT = {
    "photography": "a fully clothed person standing in a plain studio, "
                   "front-facing, centred, waist-up",
    "film_cinema": "a fully clothed person standing in a plain interior, "
                   "front-facing, centred, waist-up",
    "illustration": "a fully clothed person standing, front-facing, centred, "
                    "waist-up",
    "painting": "a fully clothed person seated by a window with a bowl of "
                "fruit on the table beside them",
    "art_movements": "a fully clothed person seated beside a table holding a "
                     "vase of flowers",
    "anime_manga": "a fully clothed character standing, front-facing, "
                   "centred, waist-up",
    "comics": "a fully clothed character standing in a city street, "
              "front-facing, centred",
    "three_d_digital": "a single rendered figure standing on a plain ground "
                       "plane, three-quarter view",
    "print_graphic": "a printed poster of a mountain and a bird, centred on "
                     "a plain background",
    "object_artifact": "a mountain and a flying bird as the pictured subject",
    "craft_material": "a mountain and a flying bird as the worked motif",
    "collage_mixed": "a mountain and a flying bird as the composed subject",
}

FALLBACK_SUBJECT = "a mountain and a flying bird, centred composition"

# A handful of styles are about a technique or a design discipline rather
# than a look, and the category subject cannot show them. A concept-car
# render needs a car; an ambient occlusion pass needs geometry with
# crevices to occlude. The subject is part of the tile hash, so adding an
# entry here re-renders exactly that one tile.
STYLE_SUBJECT = {
    # Design disciplines: the subject IS the designed object.
    "automotive_design_concept": "a sleek concept car, three-quarter view",
    "furniture_design_render": "a moulded lounge chair, three-quarter view",
    "product_design_render": "a cordless electric kettle on a plain surface",
    "industrial_design_sketch": "a cordless power drill, three-quarter view",
    "packaging_label_design_mockup": "a cylindrical coffee tin with a label",
    "jewelry_design_board": "a pendant necklace and two rings",
    "sneaker_trainer_design": "a running shoe, three-quarter view",
    "watch_horology_face": "a wristwatch face seen straight on",
    # Techniques that need geometry, motion or material to be visible.
    "ambient_occlusion_pass": "a cluster of stacked blocks and columns",
    "zbrush_sculpt_render": "a detailed creature bust on a turntable",
    "soft_body_dynamics": "a rubber ball squashing flat as it hits the ground",
    "rigid_body_dynamics": "a stone column shattering into tumbling fragments",
    "cloth_simulation": "a length of fabric draped over an invisible form",
    "fluid_simulation": "water splashing upward in a crown shape",
    "particle_hair_fur": "a shaggy long-haired animal",
    "displacement_mapping": "a stone wall with deep carved relief",
    "photogrammetry_scan": "a weathered stone statue scanned from all sides",
    # Not a hand: hands are the one subject image models reliably deform,
    # and a preview whose main feature is an extra finger teaches nothing
    # about the style.
    "subsurface_scattering": "a backlit marble bust and a translucent wax candle",
    "hdri_environment_lighting": "a chrome sphere and a matte sphere side by side",
}

# Applied on top of each style's own negative, never instead of it. The
# old builder discarded the per-style negative entirely, which is why
# styles defined by what they exclude (ligne claire's "no hatching")
# rendered as their own opposite.
BASE_NEGATIVE = "nsfw, nude, text, watermark, signature, deformed, blurry"

MANIFEST_VERSION = 2


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def subject_for(category: str, style_id: str = "") -> str:
    """The subject to render this style against.

    A per-style override wins, then the category subject, then a generic
    fallback.
    """
    if style_id and style_id in STYLE_SUBJECT:
        return STYLE_SUBJECT[style_id]
    return CATEGORY_SUBJECT.get(category, FALLBACK_SUBJECT)


def tile_hash(style: dict, model: str) -> str:
    """Hash every input that affects how this tile looks."""
    payload = json.dumps(
        {
            "prose": style.get("prose", ""),
            "tags": style.get("tags", ""),
            "negative": style.get("negative", ""),
            "subject": subject_for(style.get("category", ""), style.get("id", "")),
            "model": model,
            "render": RENDER,
            "tile": TILE_SIZE,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {"version": MANIFEST_VERSION, "model": "", "tiles": {}}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except ValueError:
        return {"version": MANIFEST_VERSION, "model": "", "tiles": {}}
    if data.get("version") != MANIFEST_VERSION:
        return {"version": MANIFEST_VERSION, "model": "", "tiles": {}}
    return data


def save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def survey(model: str) -> tuple[list[str], list[str], list[str]]:
    """Return (missing, stale, orphan) style ids against the manifest.

    Two different questions get asked here, and only one of them can be
    answered on a fresh checkout:

    * Does the manifest know about this style, and does its hash still
      match the style text? That is the real gate. It catches the case
      this pipeline exists for: somebody edited a style and did not
      re-render its tile.
    * Is the full-size source render still on disk? That only matters on
      a machine that has rendered before, because ``previews/src`` is
      gitignored and never reaches a clone.

    Testing the second unconditionally made ``--check`` report all 433
    styles as missing on any fresh checkout, which is why CI had never
    once passed. When the source directory is absent entirely, the
    manifest is the only truth available and is trusted.
    """
    from data.styles import STYLES

    manifest = load_manifest()
    recorded = manifest.get("tiles", {})
    effective_model = model or manifest.get("model", "")
    have_sources = SRC_DIR.is_dir()

    missing, stale = [], []
    for sid, rec in STYLES.items():
        entry = recorded.get(sid)
        if entry is None:
            missing.append(sid)
        elif have_sources and not (SRC_DIR / f"{sid}.png").is_file():
            missing.append(sid)
        elif entry.get("hash") != tile_hash(rec, effective_model):
            stale.append(sid)

    orphan = [sid for sid in recorded if sid not in STYLES]
    return sorted(missing), sorted(stale), sorted(orphan)


# ---------------------------------------------------------------------------
# ComfyUI HTTP client
# ---------------------------------------------------------------------------

class ComfyClient:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def _get(self, path: str, timeout: int = 10) -> bytes:
        with urllib.request.urlopen(self.url + path, timeout=timeout) as response:
            return response.read()

    def reachable(self) -> bool:
        try:
            self._get("/system_stats", timeout=5)
            return True
        except (urllib.error.URLError, OSError):
            return False

    def unet_names(self) -> list[str]:
        try:
            info = json.loads(self._get("/object_info/UNETLoader"))
        except (urllib.error.URLError, OSError, ValueError):
            return []
        try:
            return list(info["UNETLoader"]["input"]["required"]["unet_name"][0])
        except (KeyError, IndexError, TypeError):
            return []

    def queue(self, workflow: dict) -> str | None:
        body = json.dumps(
            {"prompt": workflow, "client_id": "stylebook-preview-builder"}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url + "/prompt", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read()).get("prompt_id")
        except urllib.error.HTTPError as error:
            print(f"    queue rejected: {error.read()[:300].decode('utf-8', 'replace')}")
        except (urllib.error.URLError, OSError, ValueError) as error:
            print(f"    queue failed: {error}")
        return None

    def wait(self, prompt_id: str, timeout: int = 600) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                history = json.loads(self._get(f"/history/{prompt_id}", timeout=10))
                entry = history.get(prompt_id)
                if entry is not None:
                    return entry
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(2)
        return None

    def image(self, filename: str, subfolder: str = "") -> bytes | None:
        query = urllib.parse.urlencode(
            {"filename": filename, "subfolder": subfolder, "type": "output"}
        )
        try:
            return self._get(f"/view?{query}", timeout=60)
        except (urllib.error.URLError, OSError) as error:
            print(f"    fetch failed for {filename}: {error}")
            return None


def build_workflow(positive: str, negative: str, model: str,
                   style_id: str = "preview") -> dict:
    """A Chroma text-to-image graph, matching the node's own prose output."""
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": model, "weight_dtype": "default"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "t5xxl_fp16.safetensors",
                         "type": "chroma", "device": "default"}},
        "4": {"class_type": "T5TokenizerOptions",
              "inputs": {"min_padding": 0, "min_length": 0, "clip": ["3", 0]}},
        "5": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"shift": 1, "model": ["1", 0]}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": positive, "clip": ["4", 0]}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": ["4", 0]}},
        "8": {"class_type": "CFGGuider",
              "inputs": {"cfg": RENDER["cfg"], "model": ["5", 0],
                         "positive": ["6", 0], "negative": ["7", 0]}},
        "9": {"class_type": "KSamplerSelect",
              "inputs": {"sampler_name": RENDER["sampler"]}},
        "10": {"class_type": "BasicScheduler",
               "inputs": {"scheduler": RENDER["scheduler"],
                          "steps": RENDER["steps"], "denoise": 1,
                          "model": ["5", 0]}},
        "11": {"class_type": "RandomNoise",
               "inputs": {"noise_seed": RENDER["seed"]}},
        "12": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": RENDER["width"],
                          "height": RENDER["height"], "batch_size": 1}},
        "13": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["11", 0], "guider": ["8", 0],
                          "sampler": ["9", 0], "sigmas": ["10", 0],
                          "latent_image": ["12", 0]}},
        "14": {"class_type": "VAEDecode",
               "inputs": {"samples": ["13", 0], "vae": ["2", 0]}},
        # Name the file after the style. The old prefix produced
        # stylebook_preview_00119_.png, which cannot be traced back to a
        # style without counting render order.
        "15": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": f"stylebook/{style_id}",
                          "images": ["14", 0]}},
    }


def render_one(client: ComfyClient, style: dict, model: str) -> bool:
    """Render one style's preview into previews/src. Returns success."""
    subject = subject_for(style.get("category", ""), style.get("id", ""))
    # Match the node's own prose output: subject first, style as a
    # trailing rendering clause. A tile that does not represent what the
    # node emits is worse than no tile.
    positive = f"{subject}. {style.get('prose', '')}".strip()
    negative = ", ".join(
        part for part in (style.get("negative", ""), BASE_NEGATIVE) if part
    )

    prompt_id = client.queue(
        build_workflow(positive, negative, model, style["id"])
    )
    if not prompt_id:
        return False
    history = client.wait(prompt_id)
    if not history:
        print("    timed out waiting for the render")
        return False

    for output in history.get("outputs", {}).values():
        for image in output.get("images", []):
            data = client.image(image.get("filename", ""), image.get("subfolder", ""))
            if data:
                SRC_DIR.mkdir(parents=True, exist_ok=True)
                (SRC_DIR / f"{style['id']}.png").write_bytes(data)
                return True
    print("    render produced no image")
    return False


# ---------------------------------------------------------------------------
# Atlas packing
# ---------------------------------------------------------------------------

def pack_atlases() -> int:
    """Pack per-category sprite sheets and write the gallery index.

    This is the step the old script documented but never implemented, so
    the committed atlases could not be reproduced from the repository.
    """
    try:
        from PIL import Image
    except ImportError:
        print("Packing needs Pillow. Install it with: pip install Pillow")
        print("(Pillow is a build-time tool only. The node pack itself "
              "still has no runtime dependencies.)")
        return 1

    import math

    from data.styles import CATEGORIES, STYLES

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = {
        "version": 1,
        "model": load_manifest().get("model", ""),
        "tile": TILE_SIZE,
        "categories": {},
    }

    for category in CATEGORIES:
        ids = sorted(sid for sid, rec in STYLES.items()
                     if rec.get("category") == category)
        present = [sid for sid in ids if (SRC_DIR / f"{sid}.png").is_file()]
        if not present:
            print(f"  {category}: no source renders, skipped")
            continue

        columns = math.ceil(math.sqrt(len(present)))
        rows = math.ceil(len(present) / columns)
        sheet = Image.new(
            "RGB", (columns * TILE_SIZE, rows * TILE_SIZE), (18, 18, 18)
        )

        tiles = {}
        for position, sid in enumerate(present):
            column, row = position % columns, position // columns
            with Image.open(SRC_DIR / f"{sid}.png") as source:
                thumb = source.convert("RGB").resize(
                    (TILE_SIZE, TILE_SIZE), Image.LANCZOS
                )
            sheet.paste(thumb, (column * TILE_SIZE, row * TILE_SIZE))
            tiles[sid] = {"x": column * TILE_SIZE, "y": row * TILE_SIZE,
                          "w": TILE_SIZE, "h": TILE_SIZE}

        atlas_name = f"{category}.webp"
        sheet.save(OUT_DIR / atlas_name, "WEBP", quality=82, method=6)
        index["categories"][category] = {"atlas": atlas_name, "tiles": tiles}
        size_kb = (OUT_DIR / atlas_name).stat().st_size // 1024
        print(f"  {category}: {len(present)} tiles, "
              f"{columns}x{rows}, {size_kb} KB")

    (OUT_DIR / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\nWrote {OUT_DIR / 'index.json'}")
    print("Now run: python scripts/generate_js_data.py")
    return 0



# ---------------------------------------------------------------------------
# Review sheets
# ---------------------------------------------------------------------------

def build_contact_sheets(only: str | None = None) -> int:
    """Write labelled review sheets to previews/review.

    Reviewing 433 thumbnails one file at a time is impractical for a
    person and expensive for a model. One labelled sheet per category
    puts every tile in that category side by side with its style id
    underneath, so a wrong or ugly render is obvious at a glance and the
    id needed to redo it is right there:

        python scripts/build_previews.py --style <id>
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Review sheets need Pillow. Install it with: pip install Pillow")
        return 1

    import math

    from data.styles import CATEGORIES, STYLES

    review_dir = ROOT / "previews" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    cell, label_h, pad = 220, 26, 6
    categories = [only] if only else list(CATEGORIES)
    written = 0

    for category in categories:
        ids = sorted(sid for sid, rec in STYLES.items()
                     if rec.get("category") == category)
        present = [sid for sid in ids if (SRC_DIR / f"{sid}.png").is_file()]
        if not present:
            print(f"  {category}: no renders yet, skipped")
            continue

        columns = min(6, len(present))
        rows = math.ceil(len(present) / columns)
        sheet = Image.new(
            "RGB",
            (columns * (cell + pad) + pad, rows * (cell + label_h + pad) + pad),
            (24, 24, 24),
        )
        draw = ImageDraw.Draw(sheet)

        for position, sid in enumerate(present):
            column, row = position % columns, position // columns
            x = pad + column * (cell + pad)
            y = pad + row * (cell + label_h + pad)
            with Image.open(SRC_DIR / f"{sid}.png") as source:
                sheet.paste(source.convert("RGB").resize((cell, cell),
                                                         Image.LANCZOS), (x, y))
            # The id, not the label: it is what --style takes.
            text = sid if len(sid) <= 30 else sid[:29] + "~"
            draw.text((x + 2, y + cell + 6), text, fill=(200, 200, 200))

        out = review_dir / f"{category}.jpg"
        sheet.save(out, "JPEG", quality=76, optimize=True)
        size_kb = out.stat().st_size // 1024
        print(f"  {category}: {len(present)} tiles -> {out.name} ({size_kb} KB)")
        written += 1

    print(f"\nWrote {written} review sheet(s) to previews/review")
    print("Redo any single tile with: "
          "python scripts/build_previews.py --style <id>")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def resolve_model(client: ComfyClient, requested: str) -> str | None:
    names = client.unet_names()
    if requested:
        if requested in names:
            return requested
        matches = [n for n in names if requested.lower() in n.lower()]
        if len(matches) == 1:
            return matches[0]
        print(f"Model {requested!r} not found. Available: {names[:10]}")
        return None
    # Prefer the shortest match, which is the base checkpoint. Picking the
    # first match instead grabs merges like "Chroma1-HD-<something>-Hyper-
    # Flash-Turbo", and a Turbo merge needs far fewer steps and a much
    # lower CFG than RENDER specifies, so every tile would come out wrong
    # while still looking plausible enough to miss.
    chroma = sorted((n for n in names if "chroma1-hd" in n.lower()), key=len)
    if chroma:
        return chroma[0]
    print(f"No Chroma model found. Pass --model. Available: {names[:10]}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Report stale/missing tiles and exit non-zero.")
    parser.add_argument("--build", action="store_true",
                        help="Render stale and missing tiles.")
    parser.add_argument("--pack", action="store_true",
                        help="Repack atlases from previews/src.")
    parser.add_argument("--all", action="store_true",
                        help="With --build, re-render every style.")
    parser.add_argument("--only", metavar="CATEGORY",
                        help="Restrict to one category.")
    parser.add_argument("--style", metavar="ID", action="append", default=[],
                        help="Render just this style id. Repeatable. "
                             "Use when one tile came out wrong.")
    parser.add_argument("--contact-sheet", action="store_true",
                        help="Write labelled review sheets to previews/review.")
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"ComfyUI address (default {DEFAULT_URL}).")
    parser.add_argument("--model", default="",
                        help="UNet filename or a substring of one.")
    args = parser.parse_args()

    if not (args.check or args.build or args.pack or args.contact_sheet):
        args.check = True
    if args.style:
        args.build = True
        args.check = False

    from data.styles import STYLES

    if args.check:
        missing, stale, orphan = survey(args.model)
        if args.only:
            keep = lambda ids: [  # noqa: E731
                s for s in ids if STYLES.get(s, {}).get("category") == args.only
            ]
            missing, stale = keep(missing), keep(stale)
        print(f"Styles: {len(STYLES)}")
        print(f"  missing tiles: {len(missing)}")
        print(f"  stale tiles:   {len(stale)}")
        print(f"  orphan tiles:  {len(orphan)}")
        for label, ids in (("missing", missing), ("stale", stale)):
            for sid in ids[:15]:
                print(f"    {label}: {sid}")
            if len(ids) > 15:
                print(f"    ... and {len(ids) - 15} more {label}")
        if missing or stale:
            print("\nRun: python scripts/build_previews.py --build")
            return 1
        print("\nAll preview tiles are current.")
        return 0

    if args.contact_sheet and not args.build:
        return build_contact_sheets(args.only)

    if args.build:
        client = ComfyClient(args.url)
        if not client.reachable():
            print(f"No ComfyUI at {args.url}. Start it, or pass --url.")
            return 1
        model = resolve_model(client, args.model)
        if not model:
            return 1
        print(f"Rendering against {model} at {args.url}\n")

        if args.style:
            unknown = [s for s in args.style if s not in STYLES]
            if unknown:
                print(f"Unknown style id(s): {unknown}")
                return 1
            targets = sorted(args.style)
        elif args.all:
            targets = sorted(STYLES)
        else:
            missing, stale, _ = survey(model)
            targets = sorted(set(missing) | set(stale))
        if args.only:
            targets = [s for s in targets
                       if STYLES.get(s, {}).get("category") == args.only]

        if not targets:
            print("Nothing to render; every tile is current.")
        else:
            manifest = load_manifest()
            manifest["model"] = model
            tiles = manifest.setdefault("tiles", {})
            done = failed = 0
            for position, sid in enumerate(targets, 1):
                style = STYLES[sid]
                print(f"[{position}/{len(targets)}] {sid} ({style['category']})")
                if render_one(client, style, model):
                    tiles[sid] = {"hash": tile_hash(style, model)}
                    done += 1
                else:
                    failed += 1
                # Save as we go: a long unattended run must survive a stop.
                save_manifest(manifest)
            print(f"\nRendered {done}, failed {failed}.")
            if failed:
                return 1
        result = pack_atlases()
        if args.contact_sheet:
            build_contact_sheets(args.only)
        return result

    return pack_atlases()


if __name__ == "__main__":
    sys.exit(main())
