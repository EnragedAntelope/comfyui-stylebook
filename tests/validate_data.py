"""Static integrity checks for the Stylebook data layer.

Run directly (``python tests/validate_data.py``) for a human-readable
report, or import :func:`validate` from the unit tests.
Exits non-zero on any failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A maintainer's own local user_styles.json must not change what this
# validator checks. Set before the `data` import directly below.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

from data.styles import STYLES, CATEGORIES, CATEGORY_LABELS
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

    # --- category display names ---
    for category in CATEGORIES:
        label = CATEGORY_LABELS.get(category)
        if not label:
            errors.append(f"category '{category}': no display name in CATEGORY_LABELS")
        elif "_" in label:
            errors.append(
                f"category '{category}': display name {label!r} still looks "
                f"like an id"
            )
    for category in CATEGORY_LABELS:
        if category not in CATEGORIES:
            errors.append(f"CATEGORY_LABELS has unknown category '{category}'")
    duplicate_names = [
        name for name in set(CATEGORY_LABELS.values())
        if list(CATEGORY_LABELS.values()).count(name) > 1
    ]
    for name in sorted(duplicate_names):
        errors.append(f"two categories share the display name {name!r}")

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

    # --- duplicate labels ---
    # Dict keys are unique by construction, so checking ids proves nothing.
    # Duplicate *labels* are the real hazard: they make a combo dropdown
    # ambiguous, and label-to-record lookup silently returns whichever
    # entry happens to come first.
    errors.extend(_check_duplicate_labels("style", STYLES))
    errors.extend(_check_duplicate_labels("artist", ARTISTS))
    errors.extend(_check_duplicate_labels("modifier", MODIFIERS))

    # --- reserved sentinels ---
    # A record labelled "Random", "None" or "Off" would be unreachable:
    # the node treats those values as control words, not selections.
    for kind, coll in (("style", STYLES), ("artist", ARTISTS), ("modifier", MODIFIERS)):
        for rid, rec in coll.items():
            if rec.get("label", "").strip() in _SENTINELS:
                errors.append(
                    f"{kind} '{rid}': label '{rec['label']}' collides with a "
                    f"reserved sentinel {sorted(_SENTINELS)}"
                )

    # --- text encoding ---
    errors.extend(_check_encoding("style", STYLES))
    errors.extend(_check_encoding("artist", ARTISTS))
    errors.extend(_check_encoding("modifier", MODIFIERS))

    # --- negation, in both directions ---
    errors.extend(_check_negation("style", STYLES))
    errors.extend(_check_negation("modifier", MODIFIERS))

    return errors


def _check_duplicate_labels(kind: str, coll: dict[str, dict]) -> list[str]:
    """Report any label claimed by more than one record."""
    by_label: dict[str, list[str]] = {}
    for rid, rec in coll.items():
        label = rec.get("label", "").strip()
        if label:
            by_label.setdefault(label, []).append(rid)
    return [
        f"duplicate {kind} label {label!r} claimed by {sorted(ids)}"
        for label, ids in sorted(by_label.items())
        if len(ids) > 1
    ]


#: Opens a negated clause. Matched at the start of a comma-separated
#: clause, so "no longer align" is caught but "piano keys" is not.
_NEGATORS = ("no ", "without ", "lacking ", "absent ", "free of ", "never ")

#: Negations allowed in positive text because they name a process or an
#: intent rather than anything the model could render. "Painted without
#: hesitation" describes the painter, not the painting.
_PROCESS_NEGATIONS = (
    "without hesitation", "without jury", "without seeing the others",
    "without metaphor", "without ideological burden", "without restraint",
    "without obvious artifice", "without a camera present",
)


def _check_negation(kind: str, coll: dict[str, dict]) -> list[str]:
    """Reject negated clauses in `negative`, and bare ones in positive text.

    Both directions are the same defect. A text encoder handles negation
    poorly, so the phrase lands as the thing it was meant to exclude.

    In `negative`, which is fed straight to a negative prompt, "no wax"
    suppresses wax. Candle Making shipped excluding "no wax, no wick, no
    flame, no glow, no translucency" - every defining feature it has.

    In `tags` and `prose` the same phrase gives the model the thing you
    did not want. Say what is there instead: "unshaded interiors" rather
    than "no shading".
    """
    errors: list[str] = []
    for rid, rec in coll.items():
        for clause in rec.get("negative", "").split(","):
            stripped = clause.strip().lower()
            if any(stripped.startswith(n) for n in _NEGATORS):
                errors.append(
                    f"{kind} '{rid}': negative clause '{clause.strip()}' is "
                    f"itself negated, so it excludes the opposite of what it "
                    f"means. State the exclusion affirmatively or drop it."
                )
        for field in ("tags", "prose"):
            text = rec.get(field, "")
            lowered = text.lower()
            if any(allowed in lowered for allowed in _PROCESS_NEGATIONS):
                continue
            # "never" is dropped here on purpose. In a negative clause it
            # opens a real exclusion, but in positive prose it is almost
            # always narrative - "a palette that could never be planned",
            # "the hand never looks at the paper" - and flagging those
            # would train people to ignore this check.
            for negator in (n for n in _NEGATORS if n != "never "):
                index = lowered.find(" " + negator)
                if index == -1 and not lowered.startswith(negator):
                    continue
                start = max(0, index - 20)
                errors.append(
                    f"{kind} '{rid}': {field} contains a negation near "
                    f"'{text[start:index + 40].strip()}'. Positive text must "
                    f"say what is there, not what is missing."
                )
                break
    return errors


def _check_encoding(kind: str, coll: dict[str, dict]) -> list[str]:
    """Report text that looks double-encoded (mojibake).

    A run of UTF-8 bytes decoded as latin-1 and re-encoded leaves a
    telltale lead character in U+00C2..U+00C3 followed by a character in
    U+0080..U+00BF. Real text in this pack never produces that pair, so
    any match means the source file was written through a bad codec.
    """
    errors: list[str] = []
    for rid, rec in coll.items():
        for field, raw in rec.items():
            # Aliases are a list of strings and are exactly where this
            # last bit: European Album's alias read "bande dessin?e", so
            # the style answered a search for neither spelling. Scanning
            # only str fields would have missed it.
            if isinstance(raw, (list, tuple)):
                value = " ".join(v for v in raw if isinstance(v, str))
            elif isinstance(raw, str):
                value = raw
            else:
                continue
            if not value:
                continue
            # U+FFFD is a character that was already lost: something read
            # the file as the wrong codec and substituted the replacement
            # glyph. "bande dessinee" shipped for a while as "bande
            # dessin�e", which searches for neither spelling.
            index = value.find("�")
            if index != -1:
                errors.append(
                    f"{kind} '{rid}': field '{field}' holds a replacement "
                    f"character, so text was lost to a bad codec, near "
                    f"{value[max(0, index - 12):index + 12]!r}"
                )
                break
            for i, ch in enumerate(value[:-1]):
                if 0xC2 <= ord(ch) <= 0xC3 and 0x80 <= ord(value[i + 1]) <= 0xBF:
                    errors.append(
                        f"{kind} '{rid}': field '{field}' looks double-encoded "
                        f"near {value[max(0, i - 8):i + 8]!r}"
                    )
                    break
            else:
                continue
            break
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
