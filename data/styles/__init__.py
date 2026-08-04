"""Style data aggregator - imports all category files and merges them.

Each category file in data/styles/ defines a CATEGORY_STYLES dict.
This module imports them all, applies user additions from user_styles.json,
and exports a single STYLES dict + helper accessors.
"""

from __future__ import annotations

# Relative imports - works both inside ComfyUI and standalone with sys.path set.
from .photography import PHOTOGRAPHY_STYLES
from .illustration import ILLUSTRATION_STYLES
from .comics import COMICS_STYLES
from .film_cinema import FILM_CINEMA_STYLES
from .painting import PAINTING_STYLES
from .art_movements import ART_MOVEMENTS_STYLES
from .anime_manga import ANIME_MANGA_STYLES
from .three_d_digital import THREE_D_DIGITAL_STYLES
from .print_graphic import PRINT_GRAPHIC_STYLES
from .craft_material import CRAFT_MATERIAL_STYLES
from .object_artifact import OBJECT_ARTIFACT_STYLES
from .collage_mixed import COLLAGE_MIXED_STYLES

#: All shipped styles, keyed by id.
STYLES: dict[str, dict] = {}
STYLES.update(PHOTOGRAPHY_STYLES)
STYLES.update(ILLUSTRATION_STYLES)
STYLES.update(COMICS_STYLES)
STYLES.update(FILM_CINEMA_STYLES)
STYLES.update(PAINTING_STYLES)
STYLES.update(ART_MOVEMENTS_STYLES)
STYLES.update(ANIME_MANGA_STYLES)
STYLES.update(THREE_D_DIGITAL_STYLES)
STYLES.update(PRINT_GRAPHIC_STYLES)
STYLES.update(OBJECT_ARTIFACT_STYLES)
STYLES.update(CRAFT_MATERIAL_STYLES)
STYLES.update(COLLAGE_MIXED_STYLES)
# Merge user styles (survives git pull).
from ..user_data import apply_user_styles  # noqa: E402
apply_user_styles(STYLES)

#: Ordered list of category names.
CATEGORIES: tuple[str, ...] = (
    "photography", "illustration", "comics",
    "film_cinema", "painting", "art_movements",
    "anime_manga", "three_d_digital", "print_graphic", "object_artifact",
    "craft_material", "collage_mixed",
)
#: Human-facing category names.
#:
#: Deriving these by title-casing the id gives "Three D Digital", which
#: nobody writes. Ids stay snake_case for the data layer; this is what a
#: person should ever see.
CATEGORY_LABELS: dict[str, str] = {
    "photography": "Photography",
    "illustration": "Illustration",
    "comics": "Comics",
    "film_cinema": "Film & Cinema",
    "painting": "Painting",
    "art_movements": "Art Movements",
    "anime_manga": "Anime & Manga",
    "three_d_digital": "3D & Digital",
    "print_graphic": "Print & Graphic",
    "object_artifact": "Object & Artifact",
    "craft_material": "Craft & Material",
    "collage_mixed": "Collage & Mixed",
}

#: Per-category ordered style id lists.
STYLES_BY_CATEGORY: dict[str, list[str]] = {}
for _sid, _rec in STYLES.items():
    _cat = _rec.get("category", "")
    STYLES_BY_CATEGORY.setdefault(_cat, []).append(_sid)


def get_style_ids(category: str | None = None) -> list[str]:
    """Return style ids, optionally filtered by category.

    When *category* is ``None``, all categories are included.

    Tag filtering deliberately does not live here. It used to, as a second
    implementation with different (and once-buggy) semantics from
    ``stylebook_core.filter_pool``: this one matched the whole raw string
    as a single substring, so any filter containing a comma matched
    nothing -- the exact bug already fixed once in ``filter_pool``, which
    splits on commas and requires every term to match. Rather than
    reimplement that fix a second time, the parameter was removed. There
    is exactly one tag-filter implementation in this pack:
    ``stylebook_core.filter_pool``.
    """
    if category is None:
        return list(STYLES)
    return [sid for sid, rec in STYLES.items() if rec.get("category") == category]


#: Exact lookup keys: every id and every label, lowercased. Built once,
#: because resolving a list of names would otherwise scan every record
#: once per name.
_STYLES_BY_NAME: dict[str, str] = {}
for _sid, _rec in STYLES.items():
    _STYLES_BY_NAME[_sid.lower()] = _sid
    _STYLES_BY_NAME.setdefault(_rec.get("label", "").lower().strip(), _sid)

#: Alias to the ids claiming it. A list rather than a single id because
#: aliases are not unique: "diorama" is claimed by both Tilt-Shift and
#: Museum Diorama, and "overhead" by both Aerial and Overhead God's Eye.
#: Guessing between them would be worse than saying so.
_STYLES_BY_ALIAS: dict[str, list[str]] = {}
for _sid, _rec in STYLES.items():
    for _alias in _rec.get("aliases", []):
        _STYLES_BY_ALIAS.setdefault(_alias.lower().strip(), []).append(_sid)


def get_style(name_or_id: str) -> dict | None:
    """Return a style record by id or label (case-insensitive).

    Deliberately strict: no alias matching. This backs the dropdown,
    where the value always came from the option list, and a widget that
    silently resolved a near-miss would hide a real mismatch.
    """
    sid = _STYLES_BY_NAME.get(name_or_id.lower().strip())
    return STYLES[sid] if sid else None


def resolve_style_name(name: str) -> tuple[dict | None, list[str]]:
    """Resolve a hand-typed style name, returning ``(record, candidates)``.

    Used where a human typed the name rather than picking it, so an alias
    has to work: "Ukiyo-e" is a term people know, and it is an alias of
    Woodblock Print rather than a label of its own.

    Resolution order matters, because 12 aliases collide with a real
    label somewhere else in the pack and 6 are claimed by two styles:

    1. An exact id or label wins outright. "Deep Focus" is both a label
       and somebody else's alias, and the label is what you meant.
    2. An alias claimed by exactly one style resolves to it.
    3. An alias claimed by several resolves to nothing, and the
       candidates come back so the caller can name them. Picking one
       would be a coin flip presented as an answer.
    """
    key = name.lower().strip()
    record = get_style(key)
    if record is not None:
        return record, []

    ids = _STYLES_BY_ALIAS.get(key, [])
    if len(ids) == 1:
        return STYLES[ids[0]], []
    return None, sorted(STYLES[sid]["label"] for sid in ids)
