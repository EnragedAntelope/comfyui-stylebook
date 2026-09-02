"""Optional user-supplied styles (survive ``git pull``).

Drop a ``user_styles.json`` in the pack root to add styles, artists, or
modifiers without editing the source - so updates won't clobber them. See
``docs/custom-styles.md`` for the full field reference.

The file is parsed as plain JSON - no code is executed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

#: Default location of the user file: the pack root, unless overridden so the
#: file can live outside the pack and survive a Manager reinstall.
USER_STYLES_PATH = Path(
    os.environ.get("STYLEBOOK_USER_STYLES")
    or (Path(__file__).resolve().parents[1] / "user_styles.json")
)

#: When set, every ``apply_user_*`` below is a no-op, regardless of whether
#: a user file exists. The build/check scripts (generate_js_data.py,
#: dump_frontend_fixtures.py, build_previews.py, validate_data.py) set this
#: before importing ``data`` so a maintainer's own local user_styles.json can
#: never be baked into a shipped artifact or make ``--check`` machine-
#: dependent. See ARCHITECTURE.md for the incident this closes.
_IGNORE_ENV_VAR = "STYLEBOOK_IGNORE_USER_STYLES"

#: Labels no record may claim, mirrored from stylebook_nodes.schema_options
#: rather than imported from it: that module imports the data layer, and
#: the data layer's styles/artists/modifiers packages import this module at
#: their own top level, so importing stylebook_nodes here would be a real
#: import cycle, not just a style preference.
_SENTINELS = frozenset({"None", "Off", "Random"})

#: The modifier axes a style may name in ``blocks``. Mirrored from
#: ``data.modifiers.AXES`` for the same reason ``_SENTINELS`` is mirrored:
#: ``data/modifiers.py`` imports this module at its own top level, so
#: importing it back here would be a real cycle. A cross-check test binds
#: the two (``tests/test_user_data.py``), so they cannot drift.
#:
#: Worth checking at all because ``blocks`` fails silently. A typo like
#: "color_grading" passes a bare list-of-strings check, then blocks
#: nothing: the user's modifier keeps applying, the style never says why,
#: and there is no console line anywhere to look at.
_AXES = frozenset({"lighting", "color_grade", "era", "period_dress",
                   "finish", "mood"})

#: What the user file added, recorded as it merges.
USER_ADDED_STYLES: set[str] = set()
USER_ADDED_ARTISTS: set[str] = set()
USER_ADDED_MODIFIERS: set[str] = set()


def _ignoring_user_styles() -> bool:
    return os.environ.get(_IGNORE_ENV_VAR, "") not in ("", "0")


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


def _existing_labels(
    records: dict[str, dict],
    exclude_id: str | None = None,
) -> set[str]:
    """Lower-cased labels already in use, built-in or already merged.

    ``exclude_id`` drops one record's own label from the set. Overriding
    a built-in by reusing its id is documented behaviour
    (``docs/custom-styles.md``), and the obvious way to do it is to keep
    the built-in's label and change the text underneath. Counting the
    record being replaced as a collision rejected exactly that, so the
    only override that worked was one that also renamed the entry - and
    the console said "duplicates an existing style" about the very style
    it was replacing.
    """
    return {
        rec["label"].strip().lower()
        for record_id, rec in records.items()
        if record_id != exclude_id
        and isinstance(rec.get("label"), str)
        and rec["label"].strip()
    }


def _known_values(records: dict[str, dict], field: str) -> set[str]:
    """Values *field* actually takes among built-ins, e.g. every category
    a shipped style uses. Read off the live built-in data rather than a
    hardcoded list, so this never drifts from the pack it is validating
    against -- and because importing the canonical CATEGORIES/AXES tuples
    from their owning modules here would be the same import cycle
    ``_SENTINELS`` above is avoiding."""
    return {rec[field] for rec in records.values() if rec.get(field)}


def validate_user_record(
    kind: str,
    record: Any,
    *,
    existing_labels: set[str],
    required_fields: tuple[str, ...] = ("label",),
    string_fields: tuple[str, ...] = (),
    list_fields: tuple[str, ...] = (),
    axis_list_field: str | None = None,
    category_field: str | None = None,
    known_categories: set[str] | None = None,
) -> str | None:
    """Return a rejection reason for *record*, or ``None`` if it is usable.

    Checked in the order a user is most likely to hit it: wrong shape,
    a required field missing, a reserved label, a field of the wrong
    type, an unrecognised category/axis, then a label collision -- each
    one a real failure mode this used to hit late and far from the cause
    (a sentinel label produced two identical-looking dropdown entries; a
    non-string ``tags`` value raised inside ``_split_items`` at render
    time with a traceback that named neither the file nor the record).
    """
    if not isinstance(record, dict):
        return f"a {kind} entry must be a JSON object"

    for field in required_fields:
        if field not in record:
            return f"missing required field '{field}'"

    label = record.get("label")
    if not isinstance(label, str) or not label.strip():
        return "'label' must be non-empty text"
    label = label.strip()
    if label in _SENTINELS:
        return f"label '{label}' is reserved (None, Off and Random are not usable names)"

    for field in string_fields:
        if field in record and not isinstance(record[field], str):
            return f"'{field}' must be text, not {type(record[field]).__name__}"

    for field in list_fields:
        if field in record:
            value = record[field]
            if not isinstance(value, list):
                return f"'{field}' must be a list of text, not {type(value).__name__}"
            if not all(isinstance(v, str) for v in value):
                return f"'{field}' must be a list of text; it has a non-text entry"

    if axis_list_field:
        for axis in record.get(axis_list_field, []):
            if axis not in _AXES:
                return (
                    f"'{axis_list_field}' names '{axis}', which is not a "
                    f"modifier axis (known: {', '.join(sorted(_AXES))})"
                )

    if category_field and known_categories is not None:
        category = record.get(category_field)
        if category and category not in known_categories:
            return (
                f"{category_field} '{category}' is not one the pack ships "
                f"(known: {', '.join(sorted(known_categories))})"
            )

    if label.lower() in existing_labels:
        return f"label '{label}' duplicates an existing {kind}"

    return None


def apply_user_styles(
    styles: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``styles`` section of ``user_styles.json`` in place.

    Each entry is a full style record (same shape as built-ins). A user
    entry whose id matches a built-in overrides it. Returns the count.
    """
    if _ignoring_user_styles():
        return 0
    path = path or USER_STYLES_PATH
    known_categories = _known_values(styles, "category")
    added = 0
    rejected = 0
    for style_id, record in _load_section("styles", path).items():
        if not isinstance(style_id, str) or not style_id:
            continue
        reason = validate_user_record(
            "style",
            record,
            existing_labels=_existing_labels(styles, exclude_id=style_id),
            required_fields=("label", "category"),
            string_fields=("label", "tags", "prose", "negative", "preview",
                           "scene"),
            list_fields=("aliases", "blocks"),
            axis_list_field="blocks",
            category_field="category",
            known_categories=known_categories,
        )
        if reason:
            print(f"[Stylebook] Ignoring style '{style_id}' in {path.name}: {reason}")
            rejected += 1
            continue
        # A style record must carry a self-referencing "id" matching its
        # own dict key -- stylebook_style.py and stylebook_sheet.py both
        # read record["id"] directly, the same way every built-in style
        # does. The JSON key already is that id, so set it here rather
        # than asking the user to duplicate it (and silently drop a
        # mismatch): omitting it used to raise ``KeyError: 'id'`` deep
        # inside execute(), far from a user_styles.json that looked fine.
        record["id"] = style_id
        styles[style_id] = record
        USER_ADDED_STYLES.add(style_id)
        added += 1
    _report(path, "style", added, rejected)
    return added


def apply_user_artists(
    artists: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``artists`` section of ``user_styles.json`` in place."""
    if _ignoring_user_styles():
        return 0
    path = path or USER_STYLES_PATH
    known_categories = _known_values(artists, "category")
    added = 0
    rejected = 0
    for artist_id, record in _load_section("artists", path).items():
        if not isinstance(artist_id, str) or not artist_id:
            continue
        reason = validate_user_record(
            "artist",
            record,
            existing_labels=_existing_labels(artists, exclude_id=artist_id),
            required_fields=("label",),
            string_fields=("label", "descriptor", "category"),
            list_fields=("aliases",),
            category_field="category",
            known_categories=known_categories,
        )
        if reason:
            print(f"[Stylebook] Ignoring artist '{artist_id}' in {path.name}: {reason}")
            rejected += 1
            continue
        artists[artist_id] = record
        USER_ADDED_ARTISTS.add(artist_id)
        added += 1
    _report(path, "artist", added, rejected)
    return added


def apply_user_modifiers(
    modifiers: dict[str, dict],
    path: Path | None = None,
) -> int:
    """Merge the ``modifiers`` section of ``user_styles.json`` in place."""
    if _ignoring_user_styles():
        return 0
    path = path or USER_STYLES_PATH
    known_axes = _known_values(modifiers, "axis")
    added = 0
    rejected = 0
    for mod_id, record in _load_section("modifiers", path).items():
        if not isinstance(mod_id, str) or not mod_id:
            continue
        reason = validate_user_record(
            "modifier",
            record,
            existing_labels=_existing_labels(modifiers, exclude_id=mod_id),
            required_fields=("label", "axis"),
            string_fields=("label", "tags", "prose", "negative"),
            list_fields=("aliases",),
            category_field="axis",
            known_categories=known_axes,
        )
        if reason:
            print(f"[Stylebook] Ignoring modifier '{mod_id}' in {path.name}: {reason}")
            rejected += 1
            continue
        modifiers[mod_id] = record
        USER_ADDED_MODIFIERS.add(mod_id)
        added += 1
    _report(path, "modifier", added, rejected)
    return added


def _report(path: Path, kind: str, added: int, rejected: int) -> None:
    if not added and not rejected:
        return
    parts = [f"Loaded {added} custom {kind}(s) from {path.name}."]
    if rejected:
        parts.append(f"Rejected {rejected} (see above).")
    print(f"[Stylebook] {' '.join(parts)}")
