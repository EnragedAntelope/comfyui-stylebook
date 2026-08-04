"""Pure payload builder for the ``/stylebook/user_data`` route.

Kept apart from ``routes.py`` for the same reason ``stylebook_core.py`` is
kept apart from ``node_support.py``: this has no ComfyUI/aiohttp import, so
it stays testable on a runner without either installed.
"""

from __future__ import annotations


def _entry(record_id: str, records: dict, detail_fields: tuple[str, ...],
           category_field: str) -> dict:
    rec = records.get(record_id, {})
    detail = ""
    for field in detail_fields:
        detail = rec.get(field, "")
        if detail:
            break
    return {
        "id": record_id,
        "label": rec.get("label", record_id),
        "category": rec.get(category_field, ""),
        "detail": detail,
    }


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
            _entry(sid, styles, ("prose", "tags"), "category")
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
