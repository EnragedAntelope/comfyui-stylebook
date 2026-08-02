"""Optional user-supplied styles (survive ``git pull``).

Drop a ``user_styles.json`` in the pack root to add styles, artists, or
modifiers without editing the source - so updates won't clobber them.

The file is parsed as plain JSON - no code is executed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Default location of the user file: the pack root.
USER_STYLES_PATH = Path(__file__).resolve().parents[1] / "user_styles.json"

#: What the user file added, recorded as it merges.
USER_ADDED_STYLES: set[str] = set()
USER_ADDED_ARTISTS: set[str] = set()
USER_ADDED_MODIFIERS: set[str] = set()


def _clean_strings(value: Any) -> list[str]:
    """Return usable, sentinel-free strings from a JSON list (else [])."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v]


def _load_section(section: str, path: Path | None = None) -> dict[str, Any]:
    """Return the ``section`` dict of the user JSON, or {} on any problem."""
    path = path or USER_STYLES_PATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"[Stylebook] Ignoring {path.name}: {exc}")
        return {}
    block = data.get(section) if isinstance(data, dict) else None
    return block if isinstance(block, dict) else {}


def apply_user_styles(
    styles: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``styles`` section of ``user_styles.json`` in place.

    Each entry is a full style record (same shape as built-ins). A user
    entry whose id matches a built-in overrides it. Returns the count.
    """
    path = path or USER_STYLES_PATH
    added = 0
    for style_id, record in _load_section("styles", path).items():
        if not isinstance(style_id, str) or not style_id or not isinstance(record, dict):
            continue
        if "label" not in record or "category" not in record:
            continue
        styles[style_id] = record
        USER_ADDED_STYLES.add(style_id)
        added += 1
    if added:
        print(f"[Stylebook] Loaded {added} custom style(s) from {path.name}.")
    return added


def apply_user_artists(
    artists: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``artists`` section of ``user_styles.json`` in place."""
    path = path or USER_STYLES_PATH
    added = 0
    for artist_id, record in _load_section("artists", path).items():
        if not isinstance(artist_id, str) or not artist_id or not isinstance(record, dict):
            continue
        if "label" not in record:
            continue
        artists[artist_id] = record
        USER_ADDED_ARTISTS.add(artist_id)
        added += 1
    if added:
        print(f"[Stylebook] Loaded {added} custom artist(s) from {path.name}.")
    return added


def apply_user_modifiers(
    modifiers: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``modifiers`` section of ``user_styles.json`` in place."""
    path = path or USER_STYLES_PATH
    added = 0
    for mod_id, record in _load_section("modifiers", path).items():
        if not isinstance(mod_id, str) or not mod_id or not isinstance(record, dict):
            continue
        if "label" not in record or "axis" not in record:
            continue
        modifiers[mod_id] = record
        USER_ADDED_MODIFIERS.add(mod_id)
        added += 1
    if added:
        print(f"[Stylebook] Loaded {added} custom modifier(s) from {path.name}.")
    return added
