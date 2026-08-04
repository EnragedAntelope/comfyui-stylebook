"""Stylebook chain engine - merge, render, randomize.

Pure functions with no ComfyUI dependency, so they can be unit-tested
without a ComfyUI install. The node classes wrap these with V3
``io.ComfyNode`` schemas.

The chain protocol is a plain JSON string so any string socket can
connect to any other. Every node outputs both ``prompt`` and
``style_chain``, so the result can be tapped off any node in the chain.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any

try:
    from ..data.artists import ARTISTS, get_artist_ids
    from ..data.styles import STYLES, get_style_ids
except ImportError:  # pragma: no cover - standalone/test context
    from data.artists import ARTISTS, get_artist_ids
    from data.styles import STYLES, get_style_ids


# ---------------------------------------------------------------------------
# Chain protocol
# ---------------------------------------------------------------------------

#: The empty chain every node starts from.
EMPTY_CHAIN = '{"_meta":{},"style":null,"modifiers":[],"artists":[]}'

#: Fields under ``_meta`` and their inheritance behaviour.
_META_FIELDS: tuple[str, ...] = (
    "format",           # "prose" | "tags"
    "placement",        # "append" | "prepend"
    "strength",         # "subtle" | "normal" | "strong"
    "artist_detail",    # "full" | "names_lead" | "names_only" | "descriptor_only"
    "template",         # user-supplied prompt template, or ""
)

#: There is no "auto" anywhere in here any more. ``format`` had one that
#: claimed to pick prose when a style carried prose text, and every style
#: does, so it was always prose. ``placement`` had one that resolved
#: against the format, which was a real rule but an invisible one: the
#: widget said "auto" and the user had to read the tooltip to find out
#: what it would do. Two honest options beat three where one is a guess.
_META_DEFAULTS: dict[str, str] = {
    "format": "prose",
    "placement": "append",
    "strength": "normal",
    "artist_detail": "full",
    "template": "",
}

#: Chaining more artists than this muddies every descriptor.
ARTIST_WARN_THRESHOLD = 3

#: Hard cap on chained artists. Inclusive: the fifth is kept.
ARTIST_MAX = 5


def parse_chain(raw: str) -> dict[str, Any]:
    """Parse a chain JSON string, falling back to an empty chain."""
    if not raw or not raw.strip():
        return json.loads(EMPTY_CHAIN)
    try:
        chain = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return json.loads(EMPTY_CHAIN)
    if not isinstance(chain, dict):
        return json.loads(EMPTY_CHAIN)
    chain.setdefault("_meta", {})
    chain.setdefault("style", None)
    chain.setdefault("modifiers", [])
    chain.setdefault("artists", [])
    if not isinstance(chain["_meta"], dict):
        chain["_meta"] = {}
    if not isinstance(chain["modifiers"], list):
        chain["modifiers"] = []
    if not isinstance(chain["artists"], list):
        chain["artists"] = []
    return chain


def dump_chain(chain: dict[str, Any]) -> str:
    """Serialize a chain dict to a compact JSON string."""
    return json.dumps(chain, separators=(",", ":"), ensure_ascii=False)


def merge_chain(upstream: dict[str, Any], downstream: dict[str, Any]) -> dict[str, Any]:
    """Two-level merge, downstream winning on overlap.

    ``modifiers`` and ``artists`` concatenate (upstream first);
    ``style`` and ``_meta`` shallow-merge with downstream priority.
    """
    return {
        "_meta": {**upstream.get("_meta", {}), **downstream.get("_meta", {})},
        "style": (
            downstream.get("style")
            if downstream.get("style") is not None
            else upstream.get("style")
        ),
        "modifiers": upstream.get("modifiers", []) + downstream.get("modifiers", []),
        "artists": upstream.get("artists", []) + downstream.get("artists", []),
    }


def resolve_meta(
    chain: dict[str, Any],
    defaults: dict[str, str] | None = None,
) -> dict[str, str]:
    """Resolve ``_meta`` to concrete values, filling unset slots."""
    defaults = defaults or {}
    meta = chain.get("_meta", {})
    resolved: dict[str, str] = {}
    for field in _META_FIELDS:
        value = meta.get(field)
        if not value:
            value = defaults.get(field, _META_DEFAULTS.get(field, ""))
        resolved[field] = value
    return resolved


# ---------------------------------------------------------------------------
# Blocked axes
# ---------------------------------------------------------------------------

def get_blocked_axes(style: dict | None) -> set[str]:
    """Return the modifier axes this style suppresses."""
    if style is None:
        return set()
    blocks = style.get("blocks", [])
    return set(blocks) if isinstance(blocks, list) else set()


def filter_modifiers(
    modifiers: list[dict],
    blocked: set[str],
) -> tuple[list[dict], list[dict]]:
    """Split *modifiers* into (kept, dropped) by blocked axis.

    Returning the dropped ones lets the node tell the user why their
    modifier had no effect, instead of silently discarding it.
    """
    if not blocked:
        return list(modifiers), []
    kept, dropped = [], []
    for mod in modifiers:
        (dropped if mod.get("axis", "") in blocked else kept).append(mod)
    return kept, dropped


# ---------------------------------------------------------------------------
# Style / modifier rendering
# ---------------------------------------------------------------------------

def _split_items(text: str) -> list[str]:
    """Split a comma-separated tag string into trimmed, non-empty items."""
    return [item.strip() for item in text.split(",") if item.strip()]


def defining_term(style: dict | None) -> str:
    """Return the style's defining tag, which is always written first.

    ``strength="strong"`` restates this after the whole prompt is joined.
    Restating inside :func:`render_style_tags` would not survive, because
    joining deduplicates to stop a style, a modifier and an artist from
    repeating each other.
    """
    if not style:
        return ""
    items = _split_items(style.get("tags", ""))
    return items[0] if items else ""


def _lead_clause(text: str) -> str:
    """Return the opening portion of a descriptive string.

    Used by ``strength="subtle"``, which trims a style to its defining
    phrase rather than dropping it entirely. Most style prose is a single
    sentence of the form "Label: clause, clause, clause.", so falling back
    to the leading half of the clauses keeps subtle meaningful where there
    is no sentence break to cut at.
    """
    stripped = text.strip()
    for sep in (": ", "; "):
        _, found, tail = stripped.partition(sep)
        if found and tail:
            stripped = tail
            break

    match = re.search(r"(?<=[a-z0-9\"')])\.\s", stripped)
    if match:
        return stripped[:match.start() + 1].strip()

    clauses = [c.strip() for c in stripped.rstrip(".").split(",") if c.strip()]
    if len(clauses) > 1:
        keep = max(1, len(clauses) // 2)
        return ", ".join(clauses[:keep])
    return stripped


def render_style_tags(style: dict, strength: str = "normal") -> str:
    """Render a style as comma-separated tags.

    ``subtle`` keeps the leading half of the tag list, ``strong`` appends
    the style's own emphasis terms when it has them and otherwise repeats
    its defining term. This works for every style, including the ones
    that carry no ``emphasis`` or ``strength_tail`` field.
    """
    items = _split_items(style.get("tags", ""))
    if not items:
        return ""

    if strength == "subtle":
        keep = max(1, (len(items) + 1) // 2)
        return ", ".join(items[:keep])

    if strength == "strong":
        extra: list[str] = []
        for field in ("emphasis", "strength_tail"):
            value = style.get(field, "").strip()
            if value:
                extra.extend(_split_items(value))
        return ", ".join(_dedupe_preserving_order(items + extra))

    return ", ".join(items)


def render_style_prose(style: dict, strength: str = "normal") -> str:
    """Render a style as prose."""
    prose = style.get("prose", "").strip()
    if not prose:
        return ""
    if strength == "subtle":
        return _ensure_sentence(_lead_clause(prose))
    if strength == "strong":
        tail = style.get("strength_tail", "").strip()
        if tail:
            return _ensure_sentence(f"{prose.rstrip('.')}. {tail}")
    return _ensure_sentence(prose)


def render_modifier_tags(modifier: dict) -> str:
    """Render a modifier's tags form."""
    return modifier.get("tags", "").strip()


def render_modifier_prose(modifier: dict) -> str:
    """Render a modifier's prose form."""
    return modifier.get("prose", "").strip()


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _ensure_sentence(text: str) -> str:
    """Capitalize the first letter and guarantee terminal punctuation."""
    text = text.strip()
    if not text:
        return ""
    if text[0].islower():
        text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------

def render_artist(artist: dict, mode: str = "full") -> str:
    """Render one artist record according to *mode*."""
    label = artist.get("label", "").strip()
    descriptor = artist.get("descriptor", "").strip()

    if mode == "names_only":
        return label
    if mode == "descriptor_only":
        return descriptor
    if mode == "names_lead":
        if label and descriptor:
            first = descriptor.split(",")[0].strip()
            return f"{label}, {first}" if first else label
        return label or descriptor
    if label and descriptor:
        return f"{label}, {descriptor}"
    return label or descriptor


def build_artist_clause(artists: list[dict], mode: str) -> str:
    """Build the artist clause from a list of artist records.

    ``descriptor_only`` never emits the word "by", because there is no
    name to attribute to. Every other mode does.
    """
    rendered = [r for r in (render_artist(a, mode) for a in artists) if r]
    if not rendered:
        return ""
    if mode == "descriptor_only":
        return ", ".join(rendered)
    return "by " + ", ".join(rendered)


# ---------------------------------------------------------------------------
# Prompt renderer
# ---------------------------------------------------------------------------

#: Introduces the style block in prose. Without it, a style described as
#: a noun phrase reads as more scene content: "A View-Master stereo slide
#: with a cardboard mount holding a plastic film strip" put a View-Master
#: in the picture instead of rendering the picture as one. The connective
#: retags everything after it as a description of the medium.
STYLE_FRAME = "Rendered as"

#: Introduces the subject when the style block leads instead. Same job in
#: the other direction: it marks where the rendering description stops
#: and the thing being depicted starts.
SUBJECT_FRAME = "The image shows"


def _lower_opening(text: str) -> str:
    """Lower the first letter so *text* reads as a continuation.

    An acronym keeps its capitals: "HDR tone mapping" must not become
    "hDR". Everything else is lowered, including proper nouns, because
    case carries no meaning to a text encoder and the common opening by
    far is an article.
    """
    head, _, tail = text.partition(" ")
    if len(head) > 1 and head.isupper():
        return text
    return head[:1].lower() + head[1:] + (" " + tail if tail else "")


def _frame_style(text: str) -> str:
    """Attach the rendering connective to a style block."""
    text = text.strip()
    if not text:
        return ""
    return f"{STYLE_FRAME} {_lower_opening(text)}"


def _frame_subject(text: str) -> str:
    """Attach the subject connective to the user's prompt."""
    text = text.strip()
    if not text:
        return ""
    return _ensure_sentence(f"{SUBJECT_FRAME} {_lower_opening(text)}")


def _join_tags(parts: list[str]) -> str:
    items: list[str] = []
    for part in parts:
        items.extend(_split_items(part))
    return ", ".join(_dedupe_preserving_order(items))


def _join_prose(parts: list[str]) -> str:
    return " ".join(_ensure_sentence(p) for p in parts if p.strip())


def render_prompt(
    chain: dict[str, Any],
    meta: dict[str, str],
    user_prompt: str = "",
) -> str:
    """Render the full prompt from a resolved chain."""
    fmt = meta.get("format") or _META_DEFAULTS["format"]
    strength = meta.get("strength", "normal")
    artist_mode = meta.get("artist_detail", "full")
    template = meta.get("template", "")
    placement = meta.get("placement") or _META_DEFAULTS["placement"]

    style_rec = chain.get("style")
    modifiers = chain.get("modifiers", [])
    artists = chain.get("artists", [])

    parts: list[str] = []
    if style_rec:
        rendered = (
            render_style_tags(style_rec, strength)
            if fmt == "tags"
            else render_style_prose(style_rec, strength)
        )
        if rendered:
            parts.append(rendered)

    for mod in modifiers:
        rendered = (
            render_modifier_tags(mod) if fmt == "tags" else render_modifier_prose(mod)
        )
        if rendered:
            parts.append(rendered)

    artist_text = build_artist_clause(artists, artist_mode)
    if artist_text:
        parts.append(artist_text)

    if fmt == "tags":
        style_text = _join_tags(parts)
        # Restate the defining term after joining, so "strong" survives the
        # deduplication that keeps style, modifier and artist from echoing
        # each other. Without this, "strong" was identical to "normal" for
        # every style that ships no hand-written emphasis field.
        term = defining_term(style_rec)
        if strength == "strong" and style_text and term:
            style_text = f"{style_text}, {term}"
    else:
        style_text = _join_prose(parts)
    subject = user_prompt.strip()

    if template and "{style}" in template and "{prompt}" in template:
        result = template.replace("{style}", style_text).replace("{prompt}", subject)
    elif not style_text or not subject:
        # Nothing to separate, so no connective. A style block on its own
        # is the style, and a subject on its own is the subject.
        result = style_text or subject
    elif fmt == "tags":
        # A keyword list has no grammar to confuse, so it needs no frame.
        # Position is the only signal, and the leading tokens weigh most.
        result = (
            f"{subject}, {style_text}"
            if placement == "append"
            else f"{style_text}, {subject}"
        )
    elif placement == "append":
        result = f"{_ensure_sentence(subject)} {_frame_style(style_text)}"
    else:
        result = f"{_frame_style(style_text)} {_frame_subject(subject)}"

    return _tidy(result)


def _tidy(text: str) -> str:
    """Collapse whitespace and repair punctuation left by empty parts."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(,\s*){2,}", ", ", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text.strip(" ,")


def render_negative(chain: dict[str, Any]) -> str:
    """Build the negative prompt from the chain's style and modifiers."""
    parts: list[str] = []
    style = chain.get("style")
    if style and style.get("negative"):
        parts.append(style["negative"])
    for mod in chain.get("modifiers", []):
        if mod.get("negative"):
            parts.append(mod["negative"])
    return _join_tags(parts)


# ---------------------------------------------------------------------------
# Node-face readout
# ---------------------------------------------------------------------------
#
# The readout used to be the rendered prompt, truncated from the front at
# 300 characters. With the default placement="append" the user's subject
# leads, so every node in a chain showed the same opening of the user's own
# text and the style -- the only thing the node actually added -- was
# always past the cut. Worse, Random mode had no readout of what it picked
# at all: nothing on the node, nothing in the console.
#
# The fix is two lines: a short summary of what this node resolved (never
# truncated, so it survives Random mode), then detail with the user's
# subject collapsed to a literal marker (see readout_detail), so truncation
# spends its budget on what changed rather than on text the user already
# typed.

#: Above this many artists, the summary line stops naming them individually
#: and elides to a count -- the same point past which ARTIST_WARN_THRESHOLD
#: already says stacked descriptors start blending together in the
#: rendered prompt itself.
SUMMARY_ARTIST_THRESHOLD = ARTIST_WARN_THRESHOLD

#: Cap on the resolved-summary line. Short by construction (a style label,
#: up to a couple of artist names, up to five "Label (axis)" modifiers), but
#: truncate rather than let an unusual combination crowd out the detail
#: line entirely.
SUMMARY_LIMIT = 120


def resolved_summary(chain: dict[str, Any]) -> str:
    """One short line naming what a chain currently holds, e.g.
    ``"Cyanotype · Ansel Adams · Golden Hour (lighting)"``.

    This is what makes Random mode legible: previously the only way to
    learn what a Random pick resolved to was to read it out of the full
    rendered prompt, which is impossible when no user_prompt is connected
    and unreliable when one is (see the module docstring above this).
    """
    style = chain.get("style")
    artists = chain.get("artists", [])
    modifiers = chain.get("modifiers", [])

    parts: list[str] = []
    if style and style.get("label"):
        parts.append(style["label"])

    if len(artists) > SUMMARY_ARTIST_THRESHOLD:
        parts.append(f"{len(artists)} artists")
    else:
        parts.extend(a["label"] for a in artists if a.get("label"))

    parts.extend(
        f"{m.get('label', '?')} ({m.get('axis', '?')})" for m in modifiers
    )

    if not parts:
        return "(nothing applied yet)"

    summary = " · ".join(parts)
    if len(summary) > SUMMARY_LIMIT:
        summary = summary[:SUMMARY_LIMIT - 1].rstrip() + "…"
    return summary


def readout_detail(chain: dict[str, Any], meta: dict[str, str], user_prompt: str) -> str:
    """The readout's second line: style/artist/modifier text with the
    user's own subject collapsed to a literal ``[subject]`` marker.

    Rendering with an empty subject sidesteps render_prompt's framing
    connectives entirely (see its "not style_text or not subject" branch),
    leaving exactly the style/artist/modifier text with no half-formed
    sentence around it. That is also exactly what a reader needs here: the
    part of the prompt this node is actually responsible for.
    """
    style_only = render_prompt(chain, meta, "")
    if not user_prompt.strip():
        return style_only
    return f"[subject] {style_only}" if style_only else "[subject]"


# ---------------------------------------------------------------------------
# Pool filtering and selection
# ---------------------------------------------------------------------------

def filter_pool(
    category: str | None = None,
    tag_filter: str = "",
    style_map: dict[str, dict] | None = None,
) -> list[str]:
    """Return the sorted style ids matching *category* and *tag_filter*.

    ``tag_filter`` is comma-separated and every term must match (AND), so
    ``"bw, high-contrast"`` narrows to styles that are both. A term
    matches against the style's tags, prose, label and aliases. The old
    behaviour searched for the entire raw string as one substring, which
    meant any filter containing a comma matched nothing at all.
    """
    smap = style_map if style_map is not None else STYLES
    ids = get_style_ids(category=category) if category else list(smap)
    ids = [sid for sid in ids if sid in smap]

    terms = [t.strip().lower() for t in tag_filter.split(",") if t.strip()]
    if terms:
        matched = []
        for sid in ids:
            rec = smap[sid]
            haystack = " ".join([
                rec.get("tags", ""),
                rec.get("prose", ""),
                rec.get("label", ""),
                " ".join(rec.get("aliases", [])),
            ]).lower()
            if all(term in haystack for term in terms):
                matched.append(sid)
        ids = matched
    return sorted(ids)


def filter_artist_pool(
    category: str | None = None,
    tag_filter: str = "",
    artist_map: dict[str, dict] | None = None,
) -> list[str]:
    """Return the sorted artist ids matching *category* and *tag_filter*.

    Same contract as :func:`filter_pool`: comma-separated terms, every one
    must match, and a term matches against the descriptor, label, aliases
    and category. Searching the descriptor is the point, because it is how
    you find an artist by what their work looks like rather than by
    already knowing the name.
    """
    amap = artist_map if artist_map is not None else ARTISTS
    ids = get_artist_ids(category) if category else list(amap)
    ids = [aid for aid in ids if aid in amap]

    terms = [t.strip().lower() for t in tag_filter.split(",") if t.strip()]
    if terms:
        matched = []
        for aid in ids:
            rec = amap[aid]
            haystack = " ".join([
                rec.get("descriptor", ""),
                rec.get("label", ""),
                rec.get("category", ""),
                " ".join(rec.get("aliases", [])),
            ]).lower()
            if all(term in haystack for term in terms):
                matched.append(aid)
        ids = matched
    return sorted(ids)


def seeded_rng(seed: int) -> random.Random:
    """Return a ``random.Random`` seeded from *seed*."""
    return random.Random(seed)


def _score(seed: int, candidate: str) -> str:
    """Score one candidate for a seed. Stable across releases."""
    return hashlib.sha256(f"{seed}:{candidate}".encode("utf-8")).hexdigest()


def stable_choice(seed: int, candidates: list[str]) -> str | None:
    """Pick one candidate for *seed*, stably as the pool grows.

    Indexing a sorted list would be simpler, but it makes every saved
    workflow lie the moment the pack ships a new entry: inserting one
    artist alphabetically shifts every later index, so seed 7 silently
    starts producing something else and a workflow someone liked no
    longer reproduces.

    Scoring each candidate independently and taking the winner avoids
    that. Adding a new entry only changes the outcome for the seeds where
    the newcomer happens to score highest, which is roughly one seed in N
    rather than all of them. Removing an entry only affects the seeds it
    used to win.
    """
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: _score(seed, candidate))


def stable_sample(seed: int, candidates: list[str], count: int) -> list[str]:
    """Pick up to *count* distinct candidates, stably as the pool grows.

    Same reasoning as :func:`stable_choice`: ranking by per-candidate
    score means a new entry displaces at most one existing pick instead
    of reshuffling the whole sheet.
    """
    if not candidates or count <= 0:
        return []
    ranked = sorted(candidates, key=lambda candidate: _score(seed, candidate),
                    reverse=True)
    return ranked[:count]


def random_style_id(
    seed: int,
    category: str | None = None,
    tag_filter: str = "",
    style_map: dict[str, dict] | None = None,
    exclude: list[str] | None = None,
) -> str | None:
    """Pick a style id for *seed* from the filtered pool."""
    ids = filter_pool(category, tag_filter, style_map)
    if exclude:
        skip = set(exclude)
        ids = [sid for sid in ids if sid not in skip]
    return stable_choice(seed, ids)


def cycle_style_id(
    index: int,
    category: str | None = None,
    tag_filter: str = "",
    style_map: dict[str, dict] | None = None,
) -> str | None:
    """Return the style id at deterministic *index* within the pool."""
    ids = filter_pool(category, tag_filter, style_map)
    return ids[index % len(ids)] if ids else None


def random_artist_id(
    seed: int,
    category: str | None = None,
    tag_filter: str = "",
    artist_map: dict[str, dict] | None = None,
) -> str | None:
    """Pick an artist id for *seed* from the filtered pool."""
    return stable_choice(seed, filter_artist_pool(category, tag_filter, artist_map))


def cycle_artist_id(
    index: int,
    category: str | None = None,
    tag_filter: str = "",
    artist_map: dict[str, dict] | None = None,
) -> str | None:
    """Return the artist id at deterministic *index* within the pool."""
    ids = filter_artist_pool(category, tag_filter, artist_map)
    return ids[index % len(ids)] if ids else None


def sheet_style_ids(
    seed: int,
    count: int,
    category: str | None = None,
    tag_filter: str = "",
    style_map: dict[str, dict] | None = None,
) -> list[str]:
    """Return up to *count* distinct style ids for a style sheet."""
    return stable_sample(seed, filter_pool(category, tag_filter, style_map), count)
