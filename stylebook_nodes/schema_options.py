"""Option lists, sentinels and defaults shared by every node schema.

This module imports no ComfyUI code on purpose. The node classes build
their schemas from it, and the test suite validates every dropdown from
it, so option/default drift is caught in CI on a runner that has no
ComfyUI installed.

A "sentinel" here is a dropdown entry that is a control word rather than
a selection: ``None`` means apply nothing, ``Off`` disables an axis.
The data layer forbids any record from claiming one of these labels
(see ``tests/validate_data.py``), so a sentinel can never be ambiguous.
"""

from __future__ import annotations

try:
    from ..data.ordering import label_sort_key
    from ..data.styles import STYLES, CATEGORIES, CATEGORY_LABELS
    from ..data.modifiers import MODIFIERS, AXES, MODIFIERS_BY_AXIS
    from ..data.artists import ARTISTS, ARTIST_CATEGORIES, ARTIST_CATEGORY_LABELS
except ImportError:  # pragma: no cover - standalone/test context
    from data.ordering import label_sort_key
    from data.styles import STYLES, CATEGORIES, CATEGORY_LABELS
    from data.modifiers import MODIFIERS, AXES, MODIFIERS_BY_AXIS
    from data.artists import ARTISTS, ARTIST_CATEGORIES, ARTIST_CATEGORY_LABELS


#: The socket type carried by every ``style_chain`` input and output.
#:
#: This used to be a plain STRING, on the reasoning that a chain is JSON
#: and any string socket should be able to reach any other. In practice
#: that reasoning was backwards. Every node emits three strings, so
#: wiring `prompt` into a `style_chain` input connected happily and then
#: parsed as an empty chain, which is exactly how the Blend node came to
#: report "nothing connected to style B" while looking connected. A
#: distinct type makes the mistake impossible instead of merely
#: reportable. `prompt` and `negative` stay STRING and still reach any
#: text socket in ComfyUI.
CHAIN_TYPE = "STYLEBOOK_CHAIN"


# ---------------------------------------------------------------------------
# Sentinels
# ---------------------------------------------------------------------------

#: Apply no style / no artist.
NONE = "None"

#: Apply no modifier on this axis.
OFF = "Off"

#: Every category, i.e. do not narrow the pool. Spelled out rather than
#: reusing "None", which reads as "no category" and confused the point.
CATEGORY_ALL = "All categories"

#: Same idea on the artist side, worded for what it lists.
ARTIST_CATEGORY_ALL = "All artists"

#: Labels no record may claim. Mirrored by the data validator.
SENTINELS: frozenset[str] = frozenset({NONE, OFF, "Random"})


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

MODE_PICK = "Pick"
MODE_RANDOM = "Random"
MODE_CYCLE = "Cycle"

#: Selection modes, shared by the Style and Artist nodes so the two read
#: identically. "Sheet" used to live here; it is now its own node because
#: it emits a list, not a single prompt.
#:
#: The Artist node used to carry a `randomize` boolean instead. A boolean
#: could not express Cycle at all, and it made two nodes that do the same
#: job look like they do different jobs.
MODES: tuple[str, ...] = (MODE_PICK, MODE_RANDOM, MODE_CYCLE)


# ---------------------------------------------------------------------------
# Rendering meta
# ---------------------------------------------------------------------------

FMT_PROSE = "prose"
FMT_TAGS = "tags"

#: How the style is written into the prompt.
#:
#: There used to be an "auto" option that chose prose when a style had
#: prose text. Every style has prose text, so it was always prose while
#: pretending to be a decision. Two honest options are better than three
#: where one is a fiction.
FORMATS: tuple[str, ...] = (FMT_PROSE, FMT_TAGS)

STRENGTH_SUBTLE = "subtle"
STRENGTH_NORMAL = "normal"
STRENGTH_STRONG = "strong"
STRENGTHS: tuple[str, ...] = (STRENGTH_SUBTLE, STRENGTH_NORMAL, STRENGTH_STRONG)

PLACEMENT_APPEND = "append"
PLACEMENT_PREPEND = "prepend"

#: Where the style sits relative to the subject.
#:
#: There used to be an "auto" here that resolved against the format. The
#: rule it applied was correct, but a widget reading "auto" tells the user
#: nothing about what their prompt will look like, and they had to open a
#: tooltip to find out. The rule is now stated in the tooltip as advice
#: and the widget says what it does.
#:
#: append leads: with a subject present, a model reading a sentence
#: follows that sentence's subject, and our style blocks are paragraphs.
#: Leading with a paragraph about film grain and naming the subject last
#: is the most common way to get the style honoured and the subject
#: ignored. Keyword lists are the other way round, which is why the
#: tooltip points tags users at prepend.
PLACEMENTS: tuple[str, ...] = (PLACEMENT_APPEND, PLACEMENT_PREPEND)

#: UI label -> internal artist rendering mode.
ARTIST_DETAIL_MAP: dict[str, str] = {
    "Name + descriptor": "full",
    "Names + lead descriptor": "names_lead",
    "Names only": "names_only",
    "Descriptor only": "descriptor_only",
}
ARTIST_DETAILS: tuple[str, ...] = tuple(ARTIST_DETAIL_MAP)

#: Maximum artists a chain will carry. The cap is inclusive: the fifth
#: artist is kept, the sixth is refused.
ARTIST_MAX = 5

#: Chaining more than this many artists muddies every descriptor.
ARTIST_WARN_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Option builders
# ---------------------------------------------------------------------------

def style_options() -> list[str]:
    """Labels for the style dropdown, with ``None`` first.

    "Random" is deliberately absent. It used to sit in this list and
    silently resolved to no style at all, which made a freshly dropped
    node a no-op. Randomising is what ``mode`` is for.

    Ordered by :func:`~data.ordering.label_sort_key`, the same rule the
    gallery uses, so the dropdown and the picker agree on where an
    accented or number-leading name belongs.
    """
    return [NONE] + sorted(
        (rec["label"] for rec in STYLES.values()), key=label_sort_key
    )


def category_options() -> list[str]:
    """Category names for the pool filter, widest option first.

    These are display labels, not ids. The node resolves the chosen label
    back to an id with :func:`category_id`, so the data layer never sees
    a display string and nobody has to read "three_d_digital".
    """
    return [CATEGORY_ALL] + [CATEGORY_LABELS[c] for c in CATEGORIES]


#: Display label -> category id, built once.
_CATEGORY_BY_LABEL: dict[str, str] = {
    name: cid for cid, name in CATEGORY_LABELS.items()
}


def category_id(label: str) -> str | None:
    """Resolve a category display label to its id.

    ``None`` means do not narrow the pool, which is what "All categories"
    and an unrecognised label both mean.
    """
    if label == CATEGORY_ALL:
        return None
    return _CATEGORY_BY_LABEL.get(label)


def artist_options() -> list[str]:
    """Labels for the artist dropdown, with ``None`` first.

    Same ordering rule as :func:`style_options`. A bare ``sorted()`` here
    stranded "Élisabeth Vigée Le Brun" at the very end of the list, after
    "Zhang Xiaogang", because É outranks Z by code point.
    """
    return [NONE] + sorted(
        (rec["label"] for rec in ARTISTS.values()), key=label_sort_key
    )


def artist_category_options() -> list[str]:
    """Artist category names for the pool filter, widest option first."""
    return [ARTIST_CATEGORY_ALL] + [
        ARTIST_CATEGORY_LABELS[c] for c in ARTIST_CATEGORIES
    ]


#: Display label -> artist category id, built once.
_ARTIST_CATEGORY_BY_LABEL: dict[str, str] = {
    ARTIST_CATEGORY_LABELS[c]: c for c in ARTIST_CATEGORIES
}


def artist_category_id(label: str) -> str | None:
    """Resolve an artist category display label to its id.

    ``None`` means do not narrow the pool, which is what "All artists"
    and an unrecognised label both mean.
    """
    if label == ARTIST_CATEGORY_ALL:
        return None
    return _ARTIST_CATEGORY_BY_LABEL.get(label)


def axis_options() -> list[str]:
    """The modifier axes."""
    return list(AXES)


def modifier_options(axis: str | None = None) -> list[str]:
    """Modifier labels for *axis*, with ``Off`` first.

    With no *axis*, returns every modifier on every axis. The Modifier
    node ships the full list so that changing ``axis`` never leaves the
    widget holding a value outside its own options, which fails ComfyUI's
    prompt validation. The frontend narrows the visible entries per axis,
    and ``execute`` resolves the pair, so an axis/modifier mismatch is
    reported rather than silently applied.
    """
    if axis is None:
        ids = [mid for axis_ids in MODIFIERS_BY_AXIS.values() for mid in axis_ids]
    else:
        ids = list(MODIFIERS_BY_AXIS.get(axis, []))
    # Data order, not alphabetical: era reads chronologically, so sorting
    # here would drop 1920s in between Ancient Classical and Edwardian.
    # Styles and artists do sort, by data.ordering.label_sort_key. This
    # axis is the one deliberate exemption, and the gallery's
    # modifierItems() matches it.
    seen: set[str] = set()
    labels: list[str] = []
    for mid in ids:
        label = MODIFIERS.get(mid, {}).get("label")
        if label and label not in seen:
            seen.add(label)
            labels.append(label)
    return [OFF] + labels


def modifier_options_by_axis() -> dict[str, list[str]]:
    """Per-axis modifier labels, for the frontend to narrow the dropdown."""
    return {axis: modifier_options(axis) for axis in AXES}


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

#: Widget order per node, as the frontend actually serialises it into
#: ``widgets_values``. Two rules matter and neither is obvious from
#: ``define_schema``:
#:
#:   - a seed with ``control_after_generate`` contributes two entries,
#:     value then control;
#:   - a multiline string is a DOM-backed widget and sorts after every
#:     plain one, whatever position it holds in the schema. That is why
#:     ``user_prompt`` trails on Style, and why both text boxes trail on
#:     Sheet.
#:
#: These were read off a live node with ``serialize()``, not inferred. This
#: is the single source of truth: ``tests/test_engine.py`` checks the shipped
#: example workflows against it, and ``tests/test_schemas.py`` checks it is
#: still derivable from the live ``define_schema()`` output under the two
#: rules above, so a schema change that forgets to update this dict fails on
#: the Python side *and* on the JS fixture generated from it
#: (``scripts/dump_frontend_fixtures.py``) before it ever reaches a saved
#: workflow.
WIDGET_ORDER: dict[str, list[str]] = {
    "StylebookStyle": ["mode", "style", "category", "tag_filter", "seed",
                       "control_after_generate", "cycle_index", "format",
                       "strength", "placement", "user_prompt"],
    "StylebookArtist": ["mode", "artist", "category", "tag_filter", "seed",
                        "control_after_generate", "cycle_index",
                        "artist_detail"],
    "StylebookModifier": ["axis", "mode", "modifier", "seed",
                          "control_after_generate", "cycle_index"],
    "StylebookSheet": ["count", "category", "tag_filter", "seed",
                       "control_after_generate", "user_prompt", "styles"],
    "StylebookBlend": ["ratio"],
}


#: Widget defaults, kept here so the tests can assert every default is a
#: member of its own option list.
DEFAULTS: dict[str, str] = {
    # A freshly dropped node produces output immediately. Both pickers
    # default to Random for the same reason: a node that renders nothing
    # until you configure it looks broken rather than empty.
    "mode": MODE_RANDOM,
    "style": NONE,
    "category": CATEGORY_ALL,
    "format": FMT_PROSE,
    "strength": STRENGTH_NORMAL,
    "placement": PLACEMENT_APPEND,
    "artist_mode": MODE_RANDOM,
    # The one deliberate exception. Style and Artist add the thing you
    # dropped the node for, so Random is a useful starting point. A
    # Modifier that applied a random lighting the moment it landed would
    # be changing your image without being asked; Off is a real member of
    # its option list, not an empty selection.
    "modifier_mode": MODE_PICK,
    "artist": NONE,
    "artist_category": ARTIST_CATEGORY_ALL,
    "artist_detail": "Name + descriptor",
    "axis": AXES[0],
    "modifier": OFF,
}
