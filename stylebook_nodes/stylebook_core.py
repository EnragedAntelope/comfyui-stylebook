"""Stylebook chain engine — merge, render, randomize.

Pure functions with no ComfyUI dependency, so they can be
unit-tested without a ComfyUI install. The node classes in
``nodes/`` wrap these with V3 ``io.ComfyNode`` schemas.

The chain protocol is a plain JSON string so any socket can
connect to any socket. Every node outputs both ``prompt`` and
``style_chain``, so the result can be tapped off any node.
"""

from __future__ import annotations

import json
import random
from typing import Any

# Dual import for data access — package-relative inside ComfyUI, absolute for tests.
try:
    from ..data.styles import STYLES, get_style_ids  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from data.styles import STYLES, get_style_ids  # noqa: E402


# ---------------------------------------------------------------------------
# Chain protocol
# ---------------------------------------------------------------------------

#: The empty chain every node starts from.
EMPTY_CHAIN = '{"_meta":{},"style":null,"modifiers":[],"artists":[]}'

#: Fields under ``_meta`` and their inheritance behaviour.
_META_FIELDS: tuple[str, ...] = (
    "format",           # "tags" | "prose" | "auto"
    "placement",        # "prepend" | "append"
    "strength",         # "subtle" | "normal" | "strong"
    "artist_detail",    # "full" | "names_lead" | "names_only"
    "template",         # user-supplied prompt template or null
)

#: How many artists before the node warns.
ARTIST_WARN_THRESHOLD = 3

#: Maximum number of chained artist nodes.
ARTIST_MAX = 5

#: Strength multipliers for the emphasis keyword.
STRENGTH_MULTIPLIERS: dict[str, float] = {
    "subtle": 0.75,
    "normal": 1.0,
    "strong": 1.25,
}


# ---------------------------------------------------------------------------
# Chain merge
# ---------------------------------------------------------------------------

def parse_chain(raw: str) -> dict[str, Any]:
    """Parse a chain JSON string, falling back to an empty chain on failure."""
    if not raw or not raw.strip():
        return json.loads(EMPTY_CHAIN)
    try:
        chain = json.loads(raw)
        if not isinstance(chain, dict):
            return json.loads(EMPTY_CHAIN)
        # Ensure expected keys exist.
        chain.setdefault("_meta", {})
        chain.setdefault("style", None)
        chain.setdefault("modifiers", [])
        chain.setdefault("artists", [])
        return chain
    except (json.JSONDecodeError, TypeError):
        return json.loads(EMPTY_CHAIN)


def dump_chain(chain: dict[str, Any]) -> str:
    """Serialize a chain dict to a compact JSON string."""
    return json.dumps(chain, separators=(",", ":"), ensure_ascii=False)


def merge_chain(upstream: dict[str, Any], downstream: dict[str, Any]) -> dict[str, Any]:
    """Two-level merge: downstream wins on overlap. The ``modifiers`` and
    ``artists`` lists are concatenated (upstream first, downstream appended);
    ``style`` and ``_meta`` are shallow-merged with downstream priority.
    """
    merged: dict[str, Any] = {
        "_meta": {**upstream.get("_meta", {}), **downstream.get("_meta", {})},
        "style": downstream.get("style") if downstream.get("style") is not None else upstream.get("style"),
        "modifiers": upstream.get("modifiers", []) + downstream.get("modifiers", []),
        "artists": upstream.get("artists", []) + downstream.get("artists", []),
    }
    return merged


def resolve_meta(chain: dict[str, Any], defaults: dict[str, str] | None = None) -> dict[str, str]:
    """Resolve ``_meta`` to concrete values, filling ``"inherit"`` slots
    from *defaults* (or from hard-coded fallback values).
    """
    defaults = defaults or {}
    meta = chain.get("_meta", {})
    resolved: dict[str, str] = {}
    for field in _META_FIELDS:
        value = meta.get(field, "inherit")
        if value == "inherit" or value is None:
            value = defaults.get(field, _META_DEFAULTS.get(field, "auto"))
        resolved[field] = value
    return resolved


_META_DEFAULTS: dict[str, str] = {
    "format": "auto",
    "placement": "prepend",
    "strength": "normal",
    "artist_detail": "full",
    "template": "",
}


# ---------------------------------------------------------------------------
# Blocked axes
# ---------------------------------------------------------------------------

def get_blocked_axes(style: dict | None) -> set[str]:
    """Return the modifier axes this style suppresses."""
    if style is None:
        return set()
    return set(style.get("blocks", []))


def filter_modifiers(modifiers: list[dict], blocked: set[str]) -> list[dict]:
    """Return modifiers whose axis is NOT in *blocked*."""
    if not blocked:
        return modifiers
    return [m for m in modifiers if m.get("axis", "") not in blocked]


# ---------------------------------------------------------------------------
# Prompt renderer
# ---------------------------------------------------------------------------

def _join_non_empty(parts: list[str], sep: str = ", ") -> str:
    """Join non-empty strings, stripping whitespace."""
    return sep.join(p for p in parts if p.strip())


def render_style_tags(style: dict, strength: float = 1.0) -> str:
    """Render a style as comma-separated tags, with optional emphasis."""
    tags = style.get("tags", "")
    if not tags:
        return ""
    if strength > 1.0:
        emphasis = style.get("emphasis", "")
        if emphasis:
            tags = f"{tags}, {emphasis}"
        tail = style.get("strength_tail", "")
        if tail:
            tags = f"{tags}, {tail}"
    return tags


def render_style_prose(style: dict, strength: float = 1.0) -> str:
    """Render a style as prose, with optional strength tail."""
    prose = style.get("prose", "")
    if not prose:
        return ""
    if strength > 1.0:
        tail = style.get("strength_tail", "")
        if tail:
            prose = f"{prose} {tail}."
    return prose


def render_artist(artist: dict, mode: str = "full") -> str:
    """Render a single artist record according to *mode*.

    Modes:
    - ``"full"`` — name + descriptor (default)
    - ``"names_only"`` — name only
    - ``"descriptor_only"`` — descriptor only
    - ``"names_lead"`` — name + lead descriptor only
    """
    label = artist.get("label", "")
    descriptor = artist.get("descriptor", "")

    if mode == "names_only":
        return label
    if mode == "descriptor_only":
        return descriptor
    if mode == "names_lead":
        if label and descriptor:
            # Take only the first sentence of the descriptor.
            first_sent = descriptor.split(".")[0].strip()
            return f"{label}, {first_sent}" if first_sent else label
        return label or descriptor

    # mode == "full"
    parts = []
    if label:
        parts.append(label)
    if descriptor:
        parts.append(descriptor)
    return ", ".join(parts)


def render_modifier_tags(modifier: dict) -> str:
    """Render a modifier's tags form."""
    return modifier.get("tags", "")


def render_modifier_prose(modifier: dict) -> str:
    """Render a modifier's prose form."""
    return modifier.get("prose", "")


def _build_artist_clause(artists: list[dict], mode: str) -> str:
    """Build the artist clause from a list of artist records."""
    n = len(artists)
    if n == 0:
        return ""
    if mode == "names_only" or (mode == "names_lead" and n <= 2):
        parts = [render_artist(a, mode) for a in artists]
        return ", ".join(parts) if parts else ""
    # Multiple artists with descriptors: render individually and join.
    rendered = []
    for a in artists:
        r = render_artist(a, mode)
        if r:
            rendered.append(r)
    if mode == "names_lead" and n > 2:
        # Names only for stacking beyond 2.
        return "by " + ", ".join(a.get("label", "") for a in artists if a.get("label"))
    return "by " + ", ".join(rendered) if rendered else ""


def render_prompt(
    chain: dict[str, Any],
    meta: dict[str, str],
    user_prompt: str = "",
) -> str:
    """Render the full prompt from a resolved chain.

    The *user_prompt* is the user's own prompt text that the style
    text wraps around (prepended or appended based on meta.placement).
    """
    fmt = meta.get("format", "auto")
    placement = meta.get("placement", "prepend")
    strength_name = meta.get("strength", "normal")
    strength = STRENGTH_MULTIPLIERS.get(strength_name, 1.0)
    artist_mode = meta.get("artist_detail", "full")
    template = meta.get("template", "")

    style_rec = chain.get("style")
    modifiers = chain.get("modifiers", [])
    artists = chain.get("artists", [])

    # Auto-detect format: use prose if any prose text exists, else tags.
    if fmt == "auto":
        has_prose = bool(style_rec and style_rec.get("prose"))
        if not has_prose:
            has_prose = any(m.get("prose") for m in modifiers)
        fmt = "prose" if has_prose else "tags"

    # Build style text.
    parts: list[str] = []

    if style_rec:
        if fmt == "tags":
            s = render_style_tags(style_rec, strength)
        else:
            s = render_style_prose(style_rec, strength)
        if s:
            parts.append(s)

    # Modifiers.
    for mod in modifiers:
        if fmt == "tags":
            m = render_modifier_tags(mod)
        else:
            m = render_modifier_prose(mod)
        if m:
            parts.append(m)

    # Artists.
    artist_text = _build_artist_clause(artists, artist_mode)
    if artist_text:
        parts.append(artist_text)

    style_text = ", ".join(parts) if fmt == "tags" else " ".join(parts)

    # Apply template or default wrapping.
    if template and "{style}" in template and "{prompt}" in template:
        result = template.replace("{style}", style_text).replace("{prompt}", user_prompt.strip())
    elif placement == "append":
        if user_prompt.strip() and style_text:
            sep = ", " if fmt == "tags" else " "
            result = f"{user_prompt.strip()}{sep}{style_text}"
        else:
            result = user_prompt.strip() or style_text
    else:
        # prepend
        if style_text and user_prompt.strip():
            sep = ", " if fmt == "tags" else " "
            result = f"{style_text}{sep}{user_prompt.strip()}"
        else:
            result = style_text or user_prompt.strip()

    # Clean up double commas, extra spaces.
    while ", ," in result:
        result = result.replace(", ,", ",")
    result = " ".join(result.split())

    return result


def render_negative(chain: dict[str, Any]) -> str:
    """Build the negative prompt from the chain's style and modifiers."""
    parts: list[str] = []
    style = chain.get("style")
    if style:
        neg = style.get("negative", "")
        if neg:
            parts.append(neg)
    for mod in chain.get("modifiers", []):
        neg = mod.get("negative", "")
        if neg:
            parts.append(neg)
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# RNG helpers
# ---------------------------------------------------------------------------

def seeded_rng(seed: int) -> random.Random:
    """Return a ``random.Random`` instance seeded from *seed*."""
    return random.Random(seed)


def random_style_id(
    rng: random.Random,
    category: str | None = None,
    tag_filter: str | None = None,
    style_ids: list[str] | None = None,
    style_map: dict[str, dict] | None = None,
    exclude: list[str] | None = None,
) -> str | None:
    """Pick a random style id from the optional filtered pool.

    Falls back to the global STYLES if *style_ids*/*style_map* are not given.
    """
    smap = style_map or STYLES
    if style_ids is None:
        ids = get_style_ids(category=category, tag_filter=tag_filter)
        ids = [i for i in ids if i in smap]
    else:
        ids = [i for i in style_ids if i in smap]
        if category is not None:
            ids = [i for i in ids if smap[i].get("category") == category]
        if tag_filter:
            tf = tag_filter.lower().strip()
            ids = [i for i in ids if tf in (smap[i].get("tags", "") + " " + smap[i].get("prose", "")).lower()]
    if exclude:
        ids = [i for i in ids if i not in exclude]
    return rng.choice(ids) if ids else None


def cycle_style_id(
    index: int,
    category: str | None = None,
    tag_filter: str | None = None,
    style_map: dict[str, dict] | None = None,
) -> str | None:
    """Return the style id at deterministic *index* within the filter pool."""
    smap = style_map or STYLES
    smap = style_map or STYLES
    ids = get_style_ids(category=category, tag_filter=tag_filter)
    ids = [i for i in ids if i in smap]
    if not ids:
        return None
    return ids[index % len(ids)]


# ---------------------------------------------------------------------------
# Strength modifiers
# ---------------------------------------------------------------------------

def strength_adjust(text: str, multiplier: float) -> str:
    """Apply emphasis by repeating the text (for tags format) or no-op (for prose).

    For tags format: if multiplier > 1.0, the text is repeated.
    For prose: the strength tail is already baked into the render.
    """
    return text  # strength is handled at render time via emphasis/strength_tail
