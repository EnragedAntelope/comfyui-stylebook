"""Generate frontend JavaScript data from Python data modules.

Regenerates the generated-data blocks in js/stylebook_widgets.js.
Run with ``--check`` to verify (CI gate).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def generate() -> str:
    """Return the generated JavaScript data block as a string."""
    from data.styles import STYLES, CATEGORIES
    from data.modifiers import MODIFIERS, MODIFIERS_BY_AXIS
    from data.artists import ARTISTS

    lines: list[str] = []

    # Style data.
    lines.append("// >>> GENERATED DATA — do not edit by hand. Regenerate: python scripts/generate_js_data.py >>>")
    lines.append(f"const CATEGORIES = {list(CATEGORIES)};")
    lines.append("")
    lines.append(f"const STYLE_COUNT = {len(STYLES)};")
    lines.append("")

    # Style labels and ids by category.
    for cat in CATEGORIES:
        ids = [sid for sid, rec in STYLES.items() if rec.get("category") == cat]
        labels = [STYLES[sid]["label"] for sid in ids]
        cat_key = cat.upper().replace(" ", "_")
        lines.append(f"const STYLE_LABELS_{cat_key} = {labels};")
        lines.append(f"const STYLE_IDS_{cat_key} = {ids};")
        lines.append("")

    # All labels for the style dropdown.
    all_labels = sorted(rec["label"] for rec in STYLES.values())
    lines.append(f"const ALL_STYLE_LABELS = {all_labels};")
    lines.append("")

    # Modifier data.
    axes_list = list(MODIFIERS_BY_AXIS.keys())
    lines.append(f"const MODIFIER_AXES = {axes_list};")
    for axis, mod_ids in MODIFIERS_BY_AXIS.items():
        labels = [MODIFIERS[mid]["label"] for mid in mod_ids if mid in MODIFIERS]
        axis_key = axis.upper()
        lines.append(f"const MODIFIER_LABELS_{axis_key} = {labels};")
    lines.append("")

    # Artist data.
    artist_labels = sorted(a["label"] for a in ARTISTS.values())
    lines.append(f"const ARTIST_LABELS = {artist_labels};")
    lines.append(f"const ARTIST_COUNT = {len(ARTISTS)};")
    lines.append("")
    lines.append("// <<< GENERATED DATA <<<")

    return "\n".join(lines) + "\n"


def check_file(target: Path) -> tuple[bool, str]:
    """Return (ok, diff_msg) comparing generated content against *target*."""
    expected = generate()
    if not target.is_file():
        return False, f"File {target} does not exist."
    actual = target.read_text(encoding="utf-8")

    # Extract the generated block from the actual file.
    import re
    match = re.search(r"// >>> GENERATED DATA >>>.*?// <<< GENERATED DATA <<<", actual, re.DOTALL)
    if not match:
        # Fallback: compare whole file (for standalone generated-data files).
        if actual.strip() != expected.strip():
            return False, "Generated data block differs from expected. Run: python scripts/generate_js_data.py"
        return True, "OK (standalone generated data match)"
    actual_block = match.group(0)

    if actual_block.strip() != expected.strip():
        return False, "Generated data block differs. Run: python scripts/generate_js_data.py"
    return True, "OK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate frontend JS data.")
    parser.add_argument("--check", action="store_true", help="Check only, exit non-zero if stale.")
    args = parser.parse_args()

    target = ROOT / "js" / "stylebook_widgets.js"

    if args.check:
        ok, msg = check_file(target)
        if not ok:
            print(f"FAIL: {msg}")
            return 1
        print("PASS: Generated JS data is current.")
    else:
        content = generate()
        target.write_text(content, encoding="utf-8")
        print(f"Written: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
