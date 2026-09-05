"""Static integrity checks for the Stylebook data layer.

Run directly (``python tests/validate_data.py``) for a human-readable
report, or import :func:`validate` from the unit tests.
Exits non-zero on any failure.
"""

from __future__ import annotations

import os
import re
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
_EXPECTED_AXES = {"lighting", "color_grade", "era", "period_dress",
                  "finish", "mood"}

#: Reserved sentinel values that must not appear in data.
_SENTINELS = {"Random", "None", "Off"}

#: Primitive facet vocabulary for Rule 4 validation.
_PRIMITIVE_VOCAB: dict[str, set[str]] = {
    "color_palette": {
        "flat", "duotone", "monochrome", "grayscale", "black and white",
        "sepia", "pastel", "neon", "saturated", "desaturated", "warm",
        "cool", "amber", "magenta", "cyan", "ochre", "cobalt", "crimson",
        "gold", "silver", "bone", "rust", "oxblood", "slate", "mauve",
        "pearl", "ultramarine", "viridian", "umber", "sienna",
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
        "distressed", "aged", "chipped", "cracked",
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
    # --- scene content ---
    # A style describes rendering. Naming a place renders that place.
    errors.extend(_check_scene_content(STYLES))
    errors.extend(_check_scene_content(MODIFIERS, "modifier"))
    errors.extend(_check_scene_field(STYLES))

    # --- entity content ---
    # A modifier tilts the rendering. Naming a wig renders a head to wear
    # it. Hot on both now: a style's escape is the declared `depicts`
    # field, which 0.12.0 lacked and which is why it could only report.
    errors.extend(_check_entity_content(MODIFIERS))
    errors.extend(_check_entity_content(STYLES, "style"))
    errors.extend(_check_depicts_field(STYLES))
    errors.extend(_check_modifier_alias_content(MODIFIERS))

    # --- a style named after somebody must be findable as an artist ---
    errors.extend(_check_person_styles(STYLES, ARTISTS))
    errors.extend(_check_undeclared_namesakes(STYLES, ARTISTS))

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
    errors.extend(_check_negation("artist", ARTISTS, ("descriptor",)))

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


def _check_negation(
    kind: str,
    coll: dict[str, dict],
    positive_fields: tuple[str, ...] = ("tags", "prose"),
) -> list[str]:
    """Reject negated clauses in `negative`, and bare ones in positive text.

    Both directions are the same defect. A text encoder handles negation
    poorly, so the phrase lands as the thing it was meant to exclude.

    In `negative`, which is fed straight to a negative prompt, "no wax"
    suppresses wax. Candle Making shipped excluding "no wax, no wick, no
    flame, no glow, no translucency" - every defining feature it has.

    In `tags` and `prose` the same phrase gives the model the thing you
    did not want. Say what is there instead: "unshaded interiors" rather
    than "no shading".

    ``positive_fields`` exists because an artist record spells its
    positive text ``descriptor`` rather than ``tags``/``prose``, and that
    text is concatenated straight into the prompt by
    ``stylebook_core.render_artist``. Leaving artists out of this check
    is how Candida Hofer shipped "endless bookshelves without a single
    figure" - a descriptor whose whole point is the absence of people,
    asking a text encoder for a figure.
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
        for field in positive_fields:
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


#: Place, weather and landscape nouns that a *rendering* style has no
#: business naming. Deliberately narrow and hand-verified against every
#: style in the pack, because the obvious wide version is mostly false
#: positives: "paper" is a substrate, "hand" is hand-pulled, "plate" is a
#: printing plate, "field" is depth of field, "face" is a coin face and
#: "plane" is the picture plane. A narrow gate that is always right beats
#: a broad one that trains a maintainer to skim past it. This catches a
#: regression of a known defect class; it is not an oracle, and adding a
#: style still needs the judgement described in ARCHITECTURE.md.
_SCENE_NOUNS = (
    # Interiors and transitional places
    "corridor", "hallway", "stairwell", "staircase", "escalator",
    "carpet", "ceiling tile", "drop ceiling", "cockpit", "jazz club",
    # Exteriors and settlements
    "alley", "piazza", "plaza", "courtyard", "arcaded", "roadside",
    "castle", "cathedral", "skyscraper", "cityscape", "city street",
    "street background", "street at night", "megacity", "space colony",
    # Weather and ground conditions
    # "rain-slick" as well as "rain-slicked": the bare form is what
    # Neon Noir actually shipped, and the inflected one did not match it.
    "rain-soaked", "rain-slick", "rain-slicked", "wet street", "wet mud",
    # Landscape features. "wheat" is not here on its own: the only match
    # in the pack is "wheat-pasted", which is an adhesive.
    "tall grass", "wheat field", "wilderness", "meadow", "mountain vista",
    "river vista", "forest",
    # Sky
    "milky way", "star field", "star trails",
    # Props that caused real contamination once already
    "trenchcoat", "cherry blossom", "water droplet crown",
    "bullet through", "insect scale",
    # Rooms and grounds the era axis leaked past this list in 0.11.0:
    # edwardian said "a soft garden light", _1920s "a smoky room",
    # practical_glow "lit by what is in the room".
    # "room" catches the idioms too - "breathing room", "leaving room for
    # a title" - and that is on purpose: a text encoder has no idiom, so
    # "leaving room for a title" is a request for a room. All four style
    # hits were reworded rather than exempted.
    # "interior" is deliberately NOT here. Half its hits in the pack are
    # the geometric sense - "unshaded interiors", "large open white
    # interiors", "washed interior shading", "every interior a single
    # flat tone" - which is correct rendering vocabulary. A gate that is
    # always right beats one a maintainer learns to skim past.
    "garden", "parlour", "parlor", "room",
    # Water, added in 0.14.0. The modifier preview tiles were the first
    # time anybody could see that "lit through water" on the *lighting*
    # axis floods the room and shrinks the subject to a distant figure.
    # A place-in-a-liquid is a place. Counted across the whole corpus
    # before being added: every term here was clean except "underwater"
    # (Underwater Photography, which now declares `scene`, and the
    # caustics modifier, reworded in the same commit).
    # NOT added, and each for a measured reason: "sky" (25 records, and
    # "soft box sky" is ordinary lighting vocabulary), "window" (12, and
    # `_PRIMITIVE_VOCAB` lists "window light" as a lighting primitive),
    # "stage" (7, mostly "staged"), "river" (Hudson River School), and
    # bare "pool" -- Stage Spotlight ships "hard pool of light".
    "underwater", "under water", "submerged", "submersion", "immersed",
    "swimming pool", "aquarium", "seabed", "ocean floor", "lagoon",
    "through water",
)

#: Styles that name a term above for a reason unrelated to scene content.
#: Every entry needs a written reason - an exemption without one is how a
#: check quietly stops meaning anything.
_SCENE_EXEMPT: dict[str, str] = {
    "long_exposure": "star trails are an exposure artefact, not sky content",
    "terrarium_miniature_garden": "a miniature garden is the craft artefact "
                                  "the subject is rendered as, not a setting "
                                  "it is placed in",
}


#: Things a modifier must never *add* to the picture: bodies, garments,
#: hairpieces, furniture, light fixtures, appliances. Its companion rule
#: to ``_SCENE_NOUNS``, and the same shape of defect - ``_SCENE_NOUNS``
#: lists *places*, and the era axis walked straight through the gap
#: because a wig is not a place.
#:
#: 11 of the 20 era modifiers enumerated garments, furniture and light
#: fixtures as free-standing nouns, so a subject that was not wearing a
#: wig got one, and a subject nowhere near a parlour got gaslit drapery.
#: A text encoder cannot render a frock coat without shoulders, so it
#: invents the shoulders.
#:
#: The rule an era modifier now follows: **name the light's behaviour,
#: never its fixture**, and more generally convert every entity noun into
#: an attribute of whatever is already in frame. Colour temperature,
#: direction, softness, falloff, contrast ratio, surface finish and
#: ornament density cannot be instantiated as separate objects, because
#: they are not objects.
#:
#: Stated honestly: this cannot be driven to zero. A text encoder attends
#: to every token and "gilt" will gild things. The testable bar is
#: narrower - a modifier must never add an *entity*.
#:
#: Narrow and hand-verified, like ``_SCENE_NOUNS``. Deliberately absent:
#: "drape" (the fall of cloth - Cloth Simulation and Knitwear both use it
#: correctly), "uniform" (``\b`` matches inside "uniform-weight", which is
#: line vocabulary), "hose" and bare "suit" (too many innocent senses),
#: "panel" and "screen" (picture plane, screen printing, screentone).
_ENTITY_NOUNS = (
    # Worn
    "wig", "hairpiece", "toupee", "caul", "hairstyle",
    "gown", "dress", "doublet", "corset", "corsetry", "crinoline",
    "pannier", "petticoat", "bodice", "frock coat", "waistcoat",
    "collar", "sleeve", "skirt", "trouser", "tailoring",
    "hat", "bonnet", "cloche", "plumed hat",
    "shoe", "boot", "glove", "cravat", "necktie", "apron",
    "tunic", "robe", "cape", "cloak", "costume", "wardrobe",
    "clothing", "garment", "outfit", "jewellery", "jewelry", "brooch",
    "mannequin",
    # Furniture and soft furnishing
    "furniture", "chair", "armchair", "sofa", "settee", "table", "desk",
    "bookcase", "cabinet", "sideboard", "stool",
    "drapery", "curtain", "upholstery", "cushion",
    # Light fixtures
    "lamp", "lantern", "chandelier", "candelabra", "sconce",
    "light fixture", "fixture", "bulb", "lightbulb", "streetlight",
    "candlestick", "candle",
    # Appliances
    "monitor", "appliance", "television", "loudspeaker",
)

#: Axes exempt from ``_ENTITY_NOUNS`` by definition. ``period_dress``
#: exists precisely to put wardrobe in the picture; running the rule over
#: it would flag every record it ships.
_ENTITY_EXEMPT_AXES = frozenset({"period_dress"})

#: Style categories exempt from ``_ENTITY_NOUNS`` by definition. Both mean
#: "the subject is rendered *as* the thing", so naming the thing is the
#: whole record: Candle Making, Furniture Design Render, Vinyl Record
#: Sleeve. ``ARCHITECTURE.md`` already argues these two categories out of
#: the ``scene`` rule for exactly this reason, and the gallery's category
#: chip already tells the user. A second signal for a case that has one is
#: surface area with no information.
_ENTITY_EXEMPT_CATEGORIES = frozenset({"object_artifact", "craft_material"})

#: Modifiers that name an entity term for an unrelated reason, mapped to
#: that reason. Same contract as ``_SCENE_EXEMPT``: an exemption without a
#: written reason is how a check quietly stops meaning anything.
_ENTITY_EXEMPT: dict[str, str] = {}


def _check_entity_content(
    coll: dict[str, dict],
    kind: str = "modifier",
) -> list[str]:
    """Reject entity nouns a record has not declared.

    A modifier tilts one axis of the rendering. It is never the reason a
    body, a garment, a chair or a lamp is in the frame, and on Randomize
    it is applied to subjects its author never pictured. There is no
    escape hatch: a modifier that needs one is written wrong.

    A style is different, and 0.12.0 could only report on styles for want
    of a way to say so. A style may legitimately *be* the object. The
    escape is the optional ``depicts`` field -- exactly parallel to
    ``scene``, and a declaration on the record rather than an exemption in
    this file. That distinction is the whole design:

    * an exemption id is never checked against a live record, so it rots
      into a lie the moment the style is renamed or dropped;
    * an exemption is invisible to the user, while ``depicts`` becomes a
      gallery badge that says what is about to appear in their frame;
    * and an agent that writes a costume clause writes its own exemption
      sentence thirty seconds later, so a private list gates nothing.

    ``depicts`` costs a declaration the user can see. That is the point.
    """
    errors: list[str] = []
    is_style = kind == "style"
    for rid, rec in coll.items():
        if rid in _ENTITY_EXEMPT:
            continue
        if is_style:
            if rec.get("depicts", "").strip():
                continue
            if rec.get("category") in _ENTITY_EXEMPT_CATEGORIES:
                continue
        else:
            if rec.get("axis") in _ENTITY_EXEMPT_AXES:
                continue
            if "depicts" in rec:
                # Nothing reads `depicts` off a modifier - the gallery
                # badges styles only - so declaring one here buys no
                # exemption and silently does nothing. Say so rather than
                # honour it. Same contract as `scene`.
                errors.append(
                    f"{kind} '{rid}': declares a 'depicts', which only a "
                    f"style may do. A modifier tilts one axis of the "
                    f"rendering and is never the reason an object is in "
                    f"the picture."
                )
        blob = f"{rec.get('tags', '')} {rec.get('prose', '')}".lower()
        for noun in _ENTITY_NOUNS:
            # Same matcher as _check_scene_content, for the same reasons:
            # word boundaries so "alley" does not match "gallery", and a
            # trailing `s?` so a plural is not silently missed.
            if re.search(rf"\b{re.escape(noun)}s?\b", blob):
                if is_style:
                    errors.append(
                        f"style '{rid}': names the entity '{noun}' but "
                        f"declares no 'depicts'. Either cut it (a style "
                        f"describes rendering, not what is in the picture) "
                        f"or, if the style genuinely puts that object in "
                        f"every frame, declare `depicts` so the gallery can "
                        f"warn the user."
                    )
                else:
                    errors.append(
                        f"{kind} '{rid}': names the entity '{noun}'. A "
                        f"modifier tilts the rendering and must not add an "
                        f"object to the picture - a text encoder cannot draw "
                        f"that without inventing whatever wears or holds it. "
                        f"Say what it does to the colour, light, surface or "
                        f"finish of what is already there instead."
                    )
                break
    return errors


def _check_depicts_field(coll: dict[str, dict]) -> list[str]:
    """`depicts` must be a short affirmative phrase when present.

    Same contract as `_check_scene_field`, because it is the same kind of
    thing: a badge caption, read by a human in a tooltip.
    """
    errors: list[str] = []
    for sid, rec in coll.items():
        if "depicts" not in rec:
            continue
        depicts = rec["depicts"]
        if not isinstance(depicts, str) or not depicts.strip():
            errors.append(
                f"style '{sid}': 'depicts' must be a non-empty string, or be "
                f"omitted entirely"
            )
            continue
        if _word_count(depicts) > 12:
            errors.append(
                f"style '{sid}': 'depicts' has {_word_count(depicts)} words; "
                f"it is a badge caption, keep it under 12"
            )
        if depicts[:1].isupper() and not depicts.startswith(("A ", "An ", "The ")):
            errors.append(
                f"style '{sid}': 'depicts' reads {depicts!r}; write it "
                f"lower-case as a noun phrase so it reads naturally after "
                f"'adds'"
            )
    return errors


def depicts_concentration(coll: dict[str, dict]) -> str:
    """One informational line: which category holds most of the `depicts`
    declarations, and what share of them.

    Never an error. `depicts` is an escape from a rule that is *hot* on
    styles, so the cheapest way to silence the rule is to declare the
    field instead of fixing the record -- and a single category taking
    most of the declarations is the shape a dumping ground takes long
    before the overall share ceiling in test_scene.DepictsFieldTests is
    anywhere near hit. Failing on it would block legitimate work
    (`anime_manga` costume styles genuinely do add costume); printing it
    keeps the signal visible without a memory hand-off.
    """
    declared = [rec.get("category", "?") for rec in coll.values()
                if rec.get("depicts")]
    if not declared:
        return "  Styles declaring `depicts`: 0"
    counts: dict[str, int] = {}
    for category in declared:
        counts[category] = counts.get(category, 0) + 1
    top, count = max(sorted(counts.items()), key=lambda kv: kv[1])
    share = round(100 * count / len(declared))
    return (f"  Styles declaring `depicts`: {len(declared)} "
            f"(top category {top}: {count}, {share}% of all declarations)")



#: Style labels that share a word with an artist label without being named
#: after that person, mapped to the reason. Same contract as
#: ``_SCENE_EXEMPT``: an exemption without a written reason is how a check
#: quietly stops meaning anything.
_NAMESAKE_EXEMPT: dict[str, str] = {
    "cctv_still": "'still' is a frame grab, not the painter Clyfford Still",
    "still_life_drawing": "'still' as in still life, not Clyfford Still",
    "model_kit_sprue": "'model' as in a scale model kit, not the "
                       "photographer Lisette Model",
}


def _check_person_styles(
    styles: dict[str, dict],
    artists: dict[str, dict],
) -> list[str]:
    """Every person a style is named after must have an artist record.

    The declaration lives on the style record itself, as the optional
    `namesake` field, rather than in a map inside this file. Three things
    read it: this check, the picker tooltip and the public gallery, which
    both show "Named for ..." so the connection is visible before the
    render rather than only to a maintainer.

    Naming a style after somebody is a promise the Artist picker has to
    keep. Finding "Akira Kurosawa Rain" in the style gallery and then
    getting nothing back for "Kurosawa" in the artist search is the pack
    contradicting itself.

    Styles named only for a work, a studio or a movement -- Cowboy Bebop,
    Evangelion, Studio Ghibli, Superflat -- carry no `namesake` by design:
    no person is named on the tile, so nothing is promised.
    """
    errors: list[str] = []
    labels = {
        rec.get("label", "").strip().lower()
        for rec in artists.values()
        if isinstance(rec.get("label"), str)
    }
    for sid, rec in sorted(styles.items()):
        namesake = rec.get("namesake", "")
        if not namesake:
            continue
        if not isinstance(namesake, str) or not namesake.strip():
            errors.append(f"style '{sid}': namesake must be a non-empty string")
        elif namesake.strip().lower() not in labels:
            errors.append(
                f"style '{sid}' is named after {namesake}, who has no "
                f"artist record. A style named after somebody has to be "
                f"findable in the Artist picker under that name."
            )
    return errors


def _name_words(label: str) -> set[str]:
    """Words in a label long enough to be somebody's name.

    Five characters, because four admits "Ross", "Wood", "Lee" and "Ray",
    every one of which collides with a style word ("Wood Engraving",
    "Ray Traced Render") while naming nobody the style is about.
    """
    cleaned = re.sub(r"\(.*?\)", " ", label)
    return {
        word.lower()
        for word in re.split(r"[^A-Za-z]+", cleaned)
        if len(word) >= 5
    }


def _check_undeclared_namesakes(
    styles: dict[str, dict],
    artists: dict[str, dict],
) -> list[str]:
    """Catch a style that names a shipped artist and forgot to say so.

    The old hand-maintained map caught a *broken* promise -- a declared
    namesake with no artist record -- but never a *missing* one: a new
    person-named style simply had to remember to add its own line, and
    nothing noticed when it did not.

    This closes the common half of that gap. When a style label shares a
    name-length word with an artist label, one of two things is true: the
    style is named after that person and must declare `namesake`, or the
    collision is a coincidence and belongs in ``_NAMESAKE_EXEMPT`` with a
    reason.

    It is honestly partial, and the remaining hole is worth stating: an
    adjectival label ("Sirkian Melodrama", "Hitchcockian") shares no whole
    word with "Douglas Sirk" or "Alfred Hitchcock", so only the author can
    declare those. What it does catch is the case that actually recurs --
    a style named for somebody the pack already ships.
    """
    errors: list[str] = []
    artist_words: dict[str, str] = {}
    for rec in artists.values():
        label = rec.get("label", "")
        if not isinstance(label, str):
            continue
        for word in _name_words(label):
            artist_words.setdefault(word, label)

    for sid, rec in sorted(styles.items()):
        if rec.get("namesake") or sid in _NAMESAKE_EXEMPT:
            continue
        label = rec.get("label", "")
        if not isinstance(label, str):
            continue
        hit = sorted(_name_words(label) & set(artist_words))
        if hit:
            who = ", ".join(artist_words[word] for word in hit)
            errors.append(
                f"style '{sid}' ({label}) shares a name with a shipped "
                f"artist ({who}) but declares no 'namesake'. Either add "
                f"namesake so the Artist picker keeps the promise the tile "
                f"makes, or record why it is a coincidence in "
                f"_NAMESAKE_EXEMPT."
            )
    return errors


def _check_scene_content(coll: dict[str, dict], kind: str = "style") -> list[str]:
    """Reject scene content in a record that has not declared a `scene`.

    A style describes how the image is rendered. Naming a place puts that
    place in the picture whatever the user asked for: Macro Photography
    once listed "dew drops" and rendered them onto every subject.

    A style whose identity *is* a place declares it in `scene` instead -
    Liminal Space without a transitional interior is not liminal space -
    and the gallery badges it so the choice is visible before the render.

    Modifiers get the same treatment, and get no `scene` escape hatch: a
    modifier tilts one axis of the rendering and is never the reason a
    place is in the picture. This ran on styles only for a while, and in
    that gap the Neon Noir lighting modifier shipped "rain-slick streets"
    in its tags - a wet street added to every image it touched, on an
    axis the user chose for its colour.
    """
    errors: list[str] = []
    for sid, rec in coll.items():
        if kind == "style":
            if rec.get("scene", "").strip() or sid in _SCENE_EXEMPT:
                continue
        elif "scene" in rec:
            # Nothing reads `scene` off a modifier - the gallery badges
            # styles only - so declaring one here buys no exemption and
            # silently does nothing. Say so rather than honour it.
            errors.append(
                f"{kind} '{sid}': declares a 'scene', which only a style "
                f"may do. A modifier tilts one axis of the rendering and "
                f"is never the reason a place is in the picture."
            )
        blob = f"{rec.get('tags', '')} {rec.get('prose', '')}".lower()
        for noun in _SCENE_NOUNS:
            # Word boundaries, not substrings. A plain `in` test matched
            # "alley" inside "gallery" and "wheat" inside "wheat-pasted",
            # which is exactly the kind of confident wrong answer that
            # makes a maintainer stop believing a checker.
            # Trailing `s?` because the first boundary-anchored version
            # silently stopped matching "wet streets" and "city streets"
            # and quietly shrank the report.
            if re.search(rf"\b{re.escape(noun)}s?\b", blob):
                errors.append(
                    f"{kind} '{sid}': names the scene element '{noun}' but "
                    f"declares no 'scene'. Either cut it (a {kind} describes "
                    f"rendering, not what is in the picture) or, if the "
                    f"style is defined by that setting, declare `scene` so "
                    f"the gallery can warn the user."
                )
                break
    return errors


def _check_modifier_alias_content(coll: dict[str, dict]) -> list[str]:
    """A modifier's aliases must not advertise a place or an object.

    Aliases never reach the encoder -- they are search terms -- so this is
    not about what gets rendered. It is about what the record *is*. When
    0.12.0 cut "rain-slick streets" out of Neon Noir's tags it left the
    alias "neon street" behind, and when the same pass cleaned the era
    records it left "submerged" and "pool light" on Underwater Caustics.
    Both records went on quietly delivering the scene anyway, and the
    surviving alias was the only visible evidence. Nobody looked, because
    nothing checked.

    So: an alias naming a scene or an entity means either the alias is
    wrong or the record is. Both need a human. Hot on modifiers only --
    a style may legitimately be named for a place, and declares `scene`.
    """
    errors: list[str] = []
    for mid, rec in coll.items():
        aliases = rec.get("aliases", []) or []
        blob = " | ".join(str(a) for a in aliases).lower()
        if not blob:
            continue
        for label, nouns in (("scene element", _SCENE_NOUNS),
                             ("entity", _ENTITY_NOUNS)):
            if rec.get("axis") in _ENTITY_EXEMPT_AXES and label == "entity":
                continue
            for noun in nouns:
                if re.search(rf"\b{re.escape(noun)}s?\b", blob):
                    errors.append(
                        f"modifier '{mid}': the alias list names the "
                        f"{label} '{noun}'. A modifier tilts one axis of "
                        f"the rendering; an alias promising a place or an "
                        f"object means either the alias is wrong or the "
                        f"record is. Aliases are search terms and never "
                        f"reach the prompt, so fixing the alias alone is "
                        f"only half an answer -- read the prose too."
                    )
                    break
    return errors


def _check_scene_field(coll: dict[str, dict]) -> list[str]:
    """`scene` must be a short affirmative phrase when present."""
    errors: list[str] = []
    for sid, rec in coll.items():
        if "scene" not in rec:
            continue
        scene = rec["scene"]
        if not isinstance(scene, str) or not scene.strip():
            errors.append(
                f"style '{sid}': 'scene' must be a non-empty string, or be "
                f"omitted entirely"
            )
            continue
        if _word_count(scene) > 12:
            errors.append(
                f"style '{sid}': 'scene' has {_word_count(scene)} words; it "
                f"is a badge caption, keep it under 12"
            )
        if scene[:1].isupper() and not scene.startswith(("A ", "An ", "The ")):
            errors.append(
                f"style '{sid}': 'scene' reads {scene!r}; write it lower-case "
                f"as a noun phrase so it reads naturally after 'places your "
                f"subject in'"
            )
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
    # The entity rule is hot on styles now, so there is nothing left to
    # report: a style that names an entity either declares `depicts` or
    # fails above. What is worth printing is how many carry the
    # declaration, because a number climbing towards the share ceiling in
    # test_scene.DepictsFieldTests means the field is becoming a dumping
    # ground and the badge is losing its meaning.
    print(depicts_concentration(STYLES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
