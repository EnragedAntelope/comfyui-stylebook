"""Static integrity checks for the Stylebook data layer.

Run directly (``python tests/validate_data.py``) for a human-readable
report, or import :func:`validate` from the unit tests.
Exits non-zero on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.styles import STYLES, CATEGORIES
from data.modifiers import MODIFIERS, AXES, MODIFIERS_BY_AXIS
from data.artists import ARTISTS


#: Minimum style count per category at v0.1.0.
_MIN_STYLES_PER_CATEGORY = 8

#: Minimum total styles.
_MIN_TOTAL_STYLES = 25

#: Expected modifier axes.
_EXPECTED_AXES = {"lighting", "color_grade", "era", "finish", "mood"}

#: Reserved sentinel values that must not appear in data.
_SENTINELS = {"Random", "None", "Off"}

#: Primitive facet vocabulary for Rule 4 validation.
_PRIMITIVE_VOCAB: dict[str, set[str]] = {
    "color_palette": {
        "flat", "duotone", "monochrome", "grayscale", "black and white",
        "sepia", "pastel", "neon", "saturated", "desaturated", "warm",
        "cool", "amber", "magenta", "cyan", "ochre", "cobalt", "crimson",
        "gold", "silver", "bone", "rust", "oxblood", "slate", "mauve",
        "pearl", "ultramarine", "viridian", "umber", "sienna", "ochre",
        "lilac", "rose", "teal", "orange", "violet", "purple", "green",
        "blue", "red", "yellow", "white", "black", "grey", "brown",
        "pink", "lavender", "beige", "turquoise", "indigo", "emerald",
        "ruby", "sapphire", "jade", "ivory", "ebony", "charcoal",
        "pigment", "palette", "tone", "hue", "shade", "tint",
        "colour", "color", "colored", "coloured", "colourful", "colorful",
        "luminous", "glowing", "bright", "dark", "light", "deep",
        "vivid", "muted", "subdued", "rich", "bold",
    },
    "line_edge": {
        "outline", "contour", "line", "lines", "linework", "ink",
        "stroke", "hatching", "cross-hatching", "crosshatching",
        "silhouette", "edge", "edges", "wireframe", "sketch",
        "uniform-weight", "variable", "thick", "thin", "fine",
        "bold", "rough", "scratchy", "clean", "crisp", "sharp",
        "soft", "jagged", "angular", "curved", "flowing", "organic",
        "geometric", "graphic", "mechanical", "calligraphic",
        "halftone", "ben-day", "screentone", "dotted", "dashed",
        "negative space",
    },
    "texture_surface": {
        "grain", "film grain", "noise", "paper texture", "canvas",
        "impasto", "brushstroke", "brushwork", "wash", "glaze",
        "matte", "glossy", "metallic", "rough", "smooth", "polished",
        "velvety", "powdery", "gritty", "dusty", "weathered",
        "distressed", "aged", "weathered", "chipped", "cracked",
        "peeling", "worn", "faded", "bleached", "stained",
        "transparent", "translucent", "opaque", "reflective",
        "wet", "dry", "slick", "texture", "surface", "finish",
        "rendering", "render", "shading", "gradient",
    },
    "lighting": {
        "diffuse", "soft", "hard", "harsh", "direct", "indirect",
        "ambient", "atmospheric", "volumetric", "god rays",
        "backlight", "rim light", "keylight", "fill light",
        "dramatic", "high-contrast", "low-key", "high-key",
        "chiaroscuro", "silhouette", "cast shadow", "shadow",
        "shadows", "highlight", "highlights", "catchlight",
        "golden hour", "window light", "natural light", "available light",
        "flash", "strobe", "neon", "gaslight", "candlelight",
        "moonlight", "twilight", "overcast", "diffused",
        "bloom", "glow", "flare", "lens flare", "haze",
        "beam", "ray", "sunbeam", "spotlight",
    },
    "composition_format": {
        "composition", "frame", "framing", "perspective",
        "symmetrical", "asymmetrical", "centered", "off-center",
        "rule of thirds", "foreground", "background", "midground",
        "depth of field", "shallow focus", "deep focus",
        "bokeh", "wide", "close-up", "macro", "aerial",
        "top-down", "low angle", "high angle", "eye level",
        "dutch angle", "tilt", "panoramic", "square format",
        "letterbox", "widescreen", "portrait orientation",
        "landscape orientation", "vertical", "horizontal",
        "dynamic", "static", "balanced", "tension",
        "cropped", "full frame", "tight", "loose",
    },
}

#: Terms that are jargon unless accompanied by primitive vocabulary.
_JARGON_TERMS: set[str] = {
    "ligne claire", "chiaroscuro", "sfumato", "tenebrism",
    "pointillism", "divisionism", "fauvism", "cubism",
    "surrealism", "dada", "bauhaus", "constructivism",
    "abstract expressionism", "pop art", "minimalism",
    "hyperrealism", "photorealism",
}


def _word_count(text: str) -> int:
    return len(text.split())


def _facet_hits(text: str) -> int:
    """Count how many of the 5 primitive facets are hit in *text*."""
    text_lower = text.lower()
    hits = 0
    for vocab in _PRIMITIVE_VOCAB.values():
        if any(term in text_lower for term in vocab):
            hits += 1
    return hits


def validate() -> list[str]:
    """Return a list of error strings; empty means the data layer is valid."""
    errors: list[str] = []

    # --- style counts ---
    if len(STYLES) < _MIN_TOTAL_STYLES:
        errors.append(f"STYLES has {len(STYLES)} entries; need >= {_MIN_TOTAL_STYLES}")

    category_counts: dict[str, int] = {}
    for cat in CATEGORIES:
        category_counts[cat] = 0
    for sid, rec in STYLES.items():
        cat = rec.get("category", "")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    for cat, count in category_counts.items():
        if count < _MIN_STYLES_PER_CATEGORY:
            errors.append(f"category '{cat}': {count} styles; need >= {_MIN_STYLES_PER_CATEGORY}")

    # --- per-style validation ---
    for sid, rec in STYLES.items():
        # Required fields.
        for field in ("id", "label", "category", "tags", "prose", "preview"):
            if field not in rec:
                errors.append(f"style '{sid}': missing '{field}'")

        # id must match key.
        if rec.get("id") != sid:
            errors.append(f"style '{sid}': id field '{rec.get('id')}' does not match key")

        # category must be valid.
        cat = rec.get("category", "")
        if cat not in CATEGORIES:
            errors.append(f"style '{sid}': unknown category '{cat}'")

        # Rule 4: description must stand alone (≥3 facets, ≥15 prose words).
        tags = rec.get("tags", "")
        prose = rec.get("prose", "")

        if not tags.strip():
            errors.append(f"style '{sid}': empty tags")
        if not prose.strip():
            errors.append(f"style '{sid}': empty prose")

        # Check prose word count.
        if _word_count(prose) < 15:
            errors.append(f"style '{sid}': prose has {_word_count(prose)} words (need >= 15)")

        # Check facet coverage.
        tag_hits = _facet_hits(tags)
        prose_hits = _facet_hits(prose)
        combined_hits = max(tag_hits, prose_hits)
        if combined_hits < 3:
            errors.append(f"style '{sid}': only {combined_hits}/5 primitive facets covered (need >= 3)")

        # blocks must name real axes.
        for axis in rec.get("blocks", []):
            if axis not in _EXPECTED_AXES:
                errors.append(f"style '{sid}': blocks unknown axis '{axis}'")

    # --- modifier validation ---
    if set(AXES) != _EXPECTED_AXES:
        errors.append(f"AXES mismatch: {set(AXES)} != {_EXPECTED_AXES}")

    for mid, rec in MODIFIERS.items():
        for field in ("label", "axis", "tags", "prose"):
            if field not in rec:
                errors.append(f"modifier '{mid}': missing '{field}'")
        axis = rec.get("axis", "")
        if axis not in _EXPECTED_AXES:
            errors.append(f"modifier '{mid}': unknown axis '{axis}'")
        if not rec.get("tags", "").strip():
            errors.append(f"modifier '{mid}': empty tags")
        if not rec.get("prose", "").strip():
            errors.append(f"modifier '{mid}': empty prose")

    # Check modifier counts per axis.
    for axis in _EXPECTED_AXES:
        count = len(MODIFIERS_BY_AXIS.get(axis, []))
        if count < 2:
            errors.append(f"axis '{axis}': only {count} modifiers (need >= 2)")

    # --- artist validation ---
    for aid, rec in ARTISTS.items():
        for field in ("label", "category", "descriptor"):
            if field not in rec:
                errors.append(f"artist '{aid}': missing '{field}'")
        desc = rec.get("descriptor", "")
        wc = _word_count(desc)
        if wc < 8:
            errors.append(f"artist '{aid}': descriptor has {wc} words (need >= 8)")
        if wc > 30:
            errors.append(f"artist '{aid}': descriptor has {wc} words (should be <= 25, got > 30)")

    # --- duplicate check ---
    seen_ids: set[str] = set()
    for sid in STYLES:
        if sid.lower().strip() in seen_ids:
            errors.append(f"Duplicate style id: {sid}")
        seen_ids.add(sid.lower().strip())

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("VALIDATION PASSED")
    print(f"  Styles:     {len(STYLES)}")
    print(f"  Categories: {len(CATEGORIES)}")
    print(f"  Modifiers:  {len(MODIFIERS)}")
    print(f"  Artists:    {len(ARTISTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
