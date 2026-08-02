"""Style data aggregator — imports all category files and merges them.

Each category file in data/styles/ defines a CATEGORY_STYLES dict.
This module imports them all, applies user additions from user_styles.json,
and exports a single STYLES dict + helper accessors.
"""

from __future__ import annotations

# Relative imports — works both inside ComfyUI and standalone with sys.path set.
from .photography import PHOTOGRAPHY_STYLES
from .illustration import ILLUSTRATION_STYLES
from .comics import COMICS_STYLES
# Future categories will be added here:
# from data.styles.film_cinema import FILM_CINEMA_STYLES
# from data.styles.painting import PAINTING_STYLES
# from data.styles.art_movements import ART_MOVEMENTS_STYLES
# from data.styles.anime_manga import ANIME_MANGA_STYLES
# from data.styles.three_d_digital import THREE_D_DIGITAL_STYLES
# from data.styles.print_graphic import PRINT_GRAPHIC_STYLES
# from data.styles.craft_material import CRAFT_MATERIAL_STYLES
# from data.styles.object_artifact import OBJECT_ARTIFACT_STYLES
# from data.styles.collage_mixed import COLLAGE_MIXED_STYLES

#: All shipped styles, keyed by id.
STYLES: dict[str, dict] = {}
STYLES.update(PHOTOGRAPHY_STYLES)
STYLES.update(ILLUSTRATION_STYLES)
STYLES.update(COMICS_STYLES)

# Merge user styles (survives git pull).
from ..user_data import apply_user_styles  # noqa: E402
apply_user_styles(STYLES)

#: Ordered list of category names.
CATEGORIES: tuple[str, ...] = (
    "photography", "illustration", "comics",
    # "film_cinema", "painting", "art_movements",
    # "anime_manga", "three_d_digital", "print_graphic",
    # "craft_material", "object_artifact", "collage_mixed",
)

#: Per-category ordered style id lists.
STYLES_BY_CATEGORY: dict[str, list[str]] = {}
for _sid, _rec in STYLES.items():
    _cat = _rec.get("category", "")
    STYLES_BY_CATEGORY.setdefault(_cat, []).append(_sid)


def get_style_ids(category: str | None = None, tag_filter: str | None = None) -> list[str]:
    """Return style ids, optionally filtered by category and/or tag substring.

    When *category* is ``None``, all categories are included. When
    *tag_filter* is given, only styles whose ``tags`` or ``prose``
    contains the substring (case-insensitive) are returned.
    """
    ids: list[str] = []
    filter_lower = tag_filter.lower().strip() if tag_filter else ""
    for sid, rec in STYLES.items():
        cat = rec.get("category", "")
        if category is not None and cat != category:
            continue
        if filter_lower:
            haystack = (rec.get("tags", "") + " " + rec.get("prose", "")).lower()
            if filter_lower not in haystack:
                continue
        ids.append(sid)
    return ids


def get_style(name_or_id: str) -> dict | None:
    """Return a style record by id or label (case-insensitive)."""
    name_lower = name_or_id.lower().strip()
    for sid, rec in STYLES.items():
        if sid.lower() == name_lower or rec.get("label", "").lower() == name_lower:
            return rec
    return None
