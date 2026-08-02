"""Build preview images for every style via ComfyUI's HTTP API.

Renders each style with one fixed subject prompt and one fixed seed.
Uses the Chroma text-to-image pipeline.

Usage:
  python scripts/build_previews.py          # render all
  python scripts/build_previews.py --only photography
  python scripts/build_previews.py --check  # verify
  python scripts/build_previews.py --build-atlas  # pack atlases
"""

from __future__ import annotations

import argparse, json, sys, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_MODEL = "Chroma\\Chroma1-HD.safetensors"
CLIP_NAME = "t5xxl_fp16.safetensors"
VAE_NAME = "ae.safetensors"
TILE_SIZE = 256
FIXED_SEED = 42
SUBJECT_PROMPT = "a single person standing in a neutral studio, front-facing, centered composition, even lighting"
NEGATIVE_PROMPT = "nsfw, nude, deformed, blurry, text, watermark"
STEPS = 26
CFG = 3.5
SAMPLER = "euler"
SCHEDULER = "beta"
WIDTH = 1024
HEIGHT = 1024


def queue_prompt(workflow: dict) -> str | None:
    try:
        data = json.dumps({"prompt": workflow, "client_id": "stylebook-preview-builder"}).encode("utf-8")
        req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("prompt_id")
    except Exception as exc:
        print(f"  Failed to queue: {exc}")
        return None


def get_history(prompt_id: str, timeout: int = 600) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5) as resp:
                history = json.loads(resp.read())
            entry = history.get(prompt_id)
            if entry is not None:
                return entry
        except Exception:
            pass
        time.sleep(3)
    return None


def fetch_image(filename: str, subfolder: str = "") -> bytes | None:
    try:
        params = f"filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type=output"
        with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}", timeout=30) as resp:
            return resp.read()
    except Exception as exc:
        print(f"  Failed to fetch {filename}: {exc}")
        return None


def build_workflow(style_prose: str) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": DEFAULT_MODEL, "weight_dtype": "default"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP_NAME, "type": "chroma", "device": "default"}},
        "4": {"class_type": "T5TokenizerOptions", "inputs": {"min_padding": 0, "min_length": 0, "clip": ["3", 0]}},
        "5": {"class_type": "ModelSamplingAuraFlow", "inputs": {"shift": 1, "model": ["1", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": f"{style_prose}, {SUBJECT_PROMPT}", "clip": ["4", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE_PROMPT, "clip": ["4", 0]}},
        "8": {"class_type": "CFGGuider", "inputs": {"cfg": CFG, "model": ["5", 0], "positive": ["6", 0], "negative": ["7", 0]}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": SAMPLER}},
        "10": {"class_type": "BasicScheduler", "inputs": {"scheduler": SCHEDULER, "steps": STEPS, "denoise": 1, "model": ["5", 0]}},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": FIXED_SEED}},
        "12": {"class_type": "EmptySD3LatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
        "13": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["11", 0], "guider": ["8", 0], "sampler": ["9", 0], "sigmas": ["10", 0], "latent_image": ["12", 0]}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["2", 0]}},
        "15": {"class_type": "SaveImage", "inputs": {"filename_prefix": "stylebook/", "images": ["14", 0]}},
    }


def render_style(style_id: str, style_prose: str, src_dir: Path, force: bool = False) -> bool:
    safe = style_id.replace("/", "_")
    png_path = src_dir / f"{safe}.png"
    if png_path.exists() and not force:
        return True
    print(f"  rendering: {style_id}")
    prompt_id = queue_prompt(build_workflow(style_prose))
    if not prompt_id:
        return False
    history = get_history(prompt_id)
    if not history:
        return False
    for node_output in history.get("outputs", {}).values():
        for img in node_output.get("images", []):
            data = fetch_image(img.get("filename", ""), img.get("subfolder", ""))
            if data:
                png_path.parent.mkdir(parents=True, exist_ok=True)
                png_path.write_bytes(data)
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    from data.styles import STYLES, CATEGORIES, get_style_ids
    src_dir = ROOT / "previews" / "src"

    if args.check:
        missing = sum(1 for sid in STYLES if not (src_dir / f"{sid.replace('/', '_')}.png").exists())
        print(f"{missing} preview(s) missing." if missing else "All previews present.")
        return 1 if missing else 0

    categories = [args.only] if args.only else list(CATEGORIES)
    success, fail = 0, 0
    for cat in categories:
        print(f"\nCategory: {cat}")
        for sid in get_style_ids(category=cat):
            rec = STYLES.get(sid)
            if not rec:
                continue
            prose = rec.get("prose") or rec.get("tags", "")
            if render_style(sid, prose, src_dir, args.force):
                success += 1
            else:
                fail += 1
    print(f"\nDone. {success} rendered, {fail} failed.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
