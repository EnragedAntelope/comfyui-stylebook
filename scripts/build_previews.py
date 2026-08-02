"""Build preview images for every style via ComfyUI's HTTP API.

Renders each style with one fixed subject prompt and one fixed seed,
varying only the style text. Comparability across tiles is the point.

Behaviour:
- Uses the *prose* form of each style.
- Resumable: skips styles whose source PNG already exists in previews/src/.
- Outputs: full-size PNGs -> previews/src/ (gitignored)
          packed per-category WebP atlas -> previews/<category>.webp
          tile coords + provenance -> previews/index.json

Flags:
  --only <category>   Render only one category
  --force             Re-render even if PNG exists
  --check             Verify all styles have preview PNGs (exit non-zero if missing)
  --model <path>       Override the preview model (default: Chroma1-HD)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ComfyUI defaults.
COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_MODEL = "Chroma\\Chroma1-HD.safetensors"
TILE_SIZE = 256
FIXED_SEED = 42
SUBJECT_PROMPT = (
    "a single person standing in a neutral studio, "
    "front-facing, centered composition, even lighting"
)
NEGATIVE_PROMPT = "nsfw, nude, deformed, blurry, text, watermark"
STEPS = 30
CFG = 4.0
SAMPLER = "euler"
SCHEDULER = "normal"
WIDTH = 1024
HEIGHT = 1024


def queue_prompt(workflow: dict) -> str | None:
    """Submit a workflow to ComfyUI. Returns prompt_id or None."""
    try:
        data = json.dumps({"prompt": workflow, "client_id": "stylebook-preview-builder"}).encode("utf-8")
        req = urllib.request.Request(
            f"{COMFYUI_URL}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        return result.get("prompt_id")
    except Exception as exc:
        print(f"  Failed to queue: {exc}")
        return None


def get_history(prompt_id: str, timeout: int = 600) -> dict | None:
    """Poll /history until the prompt finishes. Returns the history entry."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = f"{COMFYUI_URL}/history/{prompt_id}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                history = json.loads(resp.read())
            entry = history.get(prompt_id)
            if entry is not None:
                return entry
        except Exception:
            pass
        time.sleep(2)
    return None


def fetch_image(filename: str, subfolder: str = "") -> bytes | None:
    """Download a rendered image from ComfyUI's output directory."""
    try:
        params = f"filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type=output"
        url = f"{COMFYUI_URL}/view?{params}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except Exception as exc:
        print(f"  Failed to fetch {filename}: {exc}")
        return None


def build_workflow(style_prose: str, model_path: str = DEFAULT_MODEL) -> dict:
    """Build a ComfyUI API-format workflow for a style preview render."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": model_path},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": f"{style_prose}, {SUBJECT_PROMPT}",
                "clip": ["1", 1],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": NEGATIVE_PROMPT,
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": WIDTH,
                "height": HEIGHT,
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": FIXED_SEED,
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": SAMPLER,
                "scheduler": SCHEDULER,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "stylebook/",
                "images": ["6", 0],
            },
        },
    }


def render_style(
    style_id: str,
    style_prose: str,
    src_dir: Path,
    model_path: str,
    force: bool = False,
) -> bool:
    """Render one style. Returns True on success."""
    safe_name = style_id.replace("/", "_")
    png_path = src_dir / f"{safe_name}.png"

    if png_path.exists() and not force:
        print(f"  skip (exists): {style_id}")
        return True

    print(f"  rendering: {style_id}")
    workflow = build_workflow(style_prose, model_path)
    prompt_id = queue_prompt(workflow)
    if not prompt_id:
        return False

    print(f"    queued {prompt_id}, waiting...")
    history = get_history(prompt_id)
    if not history:
        print(f"    timeout waiting for {prompt_id}")
        return False

    # Find the SaveImage output.
    outputs = history.get("outputs", {})
    for node_id, node_output in outputs.items():
        images = node_output.get("images", [])
        for img in images:
            filename = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            data = fetch_image(filename, subfolder)
            if data:
                png_path.parent.mkdir(parents=True, exist_ok=True)
                png_path.write_bytes(data)
                print(f"    saved: {png_path.name}")
                return True

    print(f"    no image in output for {prompt_id}")
    return False


def build_atlas(category: str, style_ids: list[str], src_dir: Path, atlas_dir: Path) -> dict:
    """Pack preview tiles for one category into a WebP sprite atlas.

    Returns tile metadata: {style_id: {x, y, w, h}}.
    Returns empty dict if Pillow is not available or no PNGs exist.
    """
    try:
        from PIL import Image  # noqa: F401 — Pillow ships with ComfyUI
    except ImportError:
        print(f"  Pillow not available, skipping atlas for {category}")
        return {}

    tiles: list[tuple[str, Image.Image]] = []
    for sid in style_ids:
        safe = sid.replace("/", "_")
        png = src_dir / f"{safe}.png"
        if png.exists():
            try:
                img = Image.open(png).convert("RGB")
                img.thumbnail((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
                tiles.append((sid, img))
            except Exception:
                pass

    if not tiles:
        return {}

    # Arrange tiles in a grid.
    import math
    cols = max(1, int(math.ceil(math.sqrt(len(tiles)))))
    rows = max(1, int(math.ceil(len(tiles) / cols)))
    atlas_w = cols * TILE_SIZE
    atlas_h = rows * TILE_SIZE

    atlas = Image.new("RGB", (atlas_w, atlas_h), (30, 30, 50))
    coords: dict[str, dict] = {}

    for i, (sid, img) in enumerate(tiles):
        col = i % cols
        row = i // cols
        x = col * TILE_SIZE
        y = row * TILE_SIZE
        atlas.paste(img, (x, y))
        coords[sid] = {"x": x, "y": y, "w": TILE_SIZE, "h": TILE_SIZE}

    atlas_path = atlas_dir / f"{category}.webp"
    atlas.save(atlas_path, "WEBP", quality=85)
    print(f"  atlas: {atlas_path} ({len(tiles)} tiles, {cols}x{rows})")
    return coords


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Stylebook preview images.")
    parser.add_argument("--only", type=str, help="Render only this category.")
    parser.add_argument("--force", action="store_true", help="Re-render all, overwriting existing PNGs.")
    parser.add_argument("--check", action="store_true", help="Check for missing previews (exit non-zero).")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model path for rendering.")
    parser.add_argument("--build-atlas", action="store_true", help="Build sprite atlases from existing PNGs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from data.styles import STYLES, CATEGORIES, get_style_ids

    src_dir = ROOT / "previews" / "src"
    atlas_dir = ROOT / "previews"

    if args.check:
        missing = 0
        for sid, rec in STYLES.items():
            safe = sid.replace("/", "_")
            if not (src_dir / f"{safe}.png").exists():
                print(f"  MISSING: {sid}")
                missing += 1
        if missing:
            print(f"\n{missing} preview(s) missing.")
            return 1
        print("All previews present.")
        return 0

    if args.build_atlas:
        index: dict[str, dict] = {}
        for cat in CATEGORIES:
            ids = get_style_ids(category=cat)
            tiles = build_atlas(cat, ids, src_dir, atlas_dir)
            if tiles:
                index[cat] = {"atlas": f"{cat}.webp", "tiles": tiles}
        # Write index.json.
        index_path = atlas_dir / "index.json"
        index_path.write_text(
            json.dumps({
                "version": 1,
                "model": args.model,
                "subject": SUBJECT_PROMPT,
                "seed": FIXED_SEED,
                "steps": STEPS,
                "cfg": CFG,
                "sampler": SAMPLER,
                "scheduler": SCHEDULER,
                "resolution": f"{WIDTH}x{HEIGHT}",
                "categories": index,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Index written: {index_path}")
        return 0

    # Render mode.
    categories = [args.only] if args.only else list(CATEGORIES)
    success = 0
    fail = 0
    for cat in categories:
        print(f"\nCategory: {cat}")
        ids = get_style_ids(category=cat)
        for sid in ids:
            rec = STYLES.get(sid)
            if not rec:
                continue
            prose = rec.get("prose", "")
            if not prose:
                prose = rec.get("tags", "")
            ok = render_style(sid, prose, src_dir, args.model, args.force)
            if ok:
                success += 1
            else:
                fail += 1

    print(f"\nDone. {success} rendered, {fail} failed.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
