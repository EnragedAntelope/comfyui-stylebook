"""Pure payload builder for the ``/stylebook/user_data`` route.

Kept apart from ``routes.py`` for the same reason ``stylebook_core.py`` is
kept apart from ``node_support.py``: this has no ComfyUI/aiohttp import, so
it stays testable on a runner without either installed.
"""

from __future__ import annotations


def _entry(record_id: str, records: dict, detail_fields: tuple[str, ...],
           category_field: str,
           passthrough_fields: tuple[str, ...] = (),
           list_fields: tuple[str, ...] = ()) -> dict:
    """One payload row.

    ``passthrough_fields`` are optional string fields copied straight through
    so a custom record can show what a built-in shows -- the gallery reads
    ``scene`` and ``depicts`` off the entry and badges them, and never saw
    either before. ``list_fields`` are the same idea for fields that are
    lists (``aliases``), which need a list default rather than "".

    ``namesake`` is deliberately not passed through: it promises a matching
    artist record exists, which the validator enforces for built-ins and
    cannot for a user file. See docs/custom-styles.md.
    """
    rec = records.get(record_id, {})
    detail = ""
    for field in detail_fields:
        detail = rec.get(field, "")
        if detail:
            break
    entry = {
        "id": record_id,
        "label": rec.get("label", record_id),
        "category": rec.get(category_field, ""),
        "detail": detail,
    }
    for field in passthrough_fields:
        entry[field] = rec.get(field, "")
    for field in list_fields:
        value = rec.get(field)
        entry[field] = list(value) if isinstance(value, (list, tuple)) else []
    return entry


def build_user_data_payload(
    *,
    styles: dict,
    artists: dict,
    modifiers: dict,
    added_styles: set,
    added_artists: set,
    added_modifiers: set,
) -> dict:
    """The gallery's "Yours" tab data: what a local user_styles.json
    added, across all three sections, empty where nothing was added.

    Sorted by id, so the response (and therefore the tab's tile order) is
    stable across requests rather than depending on dict iteration order.
    """
    return {
        "styles": [
            _entry(sid, styles, ("prose", "tags"), "category",
                   passthrough_fields=("scene", "depicts"),
                   list_fields=("aliases",))
            for sid in sorted(added_styles)
        ],
        "artists": [
            _entry(aid, artists, ("descriptor",), "category")
            for aid in sorted(added_artists)
        ],
        "modifiers": [
            _entry(mid, modifiers, ("prose", "tags"), "axis")
            for mid in sorted(added_modifiers)
        ],
    }
