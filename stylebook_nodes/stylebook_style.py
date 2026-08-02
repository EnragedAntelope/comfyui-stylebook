"""StylebookStyle node — the exclusive medium axis.

Pick a style, randomize within a filtered pool, cycle
deterministically through a pool, or batch-emit a style sheet.
"""

from __future__ import annotations

import json

# Dual import: package-relative inside ComfyUI, absolute for tests.
try:
    from ..data.styles import STYLES, get_style_ids, get_style
    from ..data.modifiers import MODIFIERS
    from .stylebook_core import (
        parse_chain, dump_chain, merge_chain, resolve_meta,
        render_prompt, render_negative, get_blocked_axes,
        filter_modifiers, seeded_rng, random_style_id,
        cycle_style_id,
    )
except ImportError:  # pragma: no cover — standalone/test context
    from data.styles import STYLES, get_style_ids, get_style
    from data.modifiers import MODIFIERS
    from stylebook_nodes.stylebook_core import (
        parse_chain, dump_chain, merge_chain, resolve_meta,
        render_prompt, render_negative, get_blocked_axes,
        filter_modifiers, seeded_rng, random_style_id,
        cycle_style_id,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pure engine helpers
# ---------------------------------------------------------------------------

#: Sentinel for the mode combo.
_MODE_PICK = "Pick"
_MODE_RANDOM = "Random"
_MODE_CYCLE = "Cycle"
_MODE_SHEET = "Sheet"

#: Style sentinel.
_STYLE_NONE = "None"
_STYLE_RANDOM = "Random"

#: Format options.
_FMT_TAGS = "tags"
_FMT_PROSE = "prose"
_FMT_AUTO = "auto"

#: Strength options.
_STRENGTH_SUBTLE = "subtle"
_STRENGTH_NORMAL = "normal"
_STRENGTH_STRONG = "strong"

#: Placement options.
_PLACEMENT_PREPEND = "prepend"
_PLACEMENT_APPEND = "append"

#: Category options (built from the data).
def _category_options() -> list[str]:
    from data.styles import CATEGORIES  # noqa: E402
    return [_STYLE_NONE] + list(CATEGORIES)


def build_style_chain(
    chain_json: str,
    style_id: str,
    mode: str,
    category: str,
    tag_filter: str,
    seed: int,
    cycle_index: int,
    sheet_count: int,
    meta_overrides: dict[str, str] | None,
) -> dict:
    """Resolve the style chain for the Style node and return
    ``(chain, warnings, sheet_chains)``.
    """
    chain = parse_chain(chain_json)
    warnings: list[str] = []
    sheet_chains: list[dict] = []

    rng = seeded_rng(seed)

    # Determine the actual style id based on mode.
    resolved_id: str | None = None

    if mode == _MODE_RANDOM:
        resolved_id = random_style_id(
            rng=rng,
            category=category if category != _STYLE_NONE else None,
            tag_filter=tag_filter,
        )
    elif mode == _MODE_CYCLE:
        resolved_id = cycle_style_id(
            index=cycle_index,
            category=category if category != _STYLE_NONE else None,
            tag_filter=tag_filter,
        )
    elif mode == _MODE_SHEET:
        ids = get_style_ids(
            category=category if category != _STYLE_NONE else None,
            tag_filter=tag_filter,
        )
        rng.shuffle(ids)
        ids = ids[:sheet_count]
        for sid in ids:
            sc = dict(chain)  # shallow copy
            sc["style"] = STYLES.get(sid)
            sheet_chains.append(sc)
        if ids:
            resolved_id = ids[0]  # primary output uses first style
    elif mode == _MODE_PICK:
        if style_id == _STYLE_RANDOM:
            resolved_id = random_style_id(
                rng=rng,
                category=category if category != _STYLE_NONE else None,
                tag_filter=tag_filter,
            )
        elif style_id != _STYLE_NONE:
            resolved_id = style_id
        # else: resolved_id stays None (no style)

    # Apply the style.
    if resolved_id:
        rec = STYLES.get(resolved_id)
        if rec:
            if chain.get("style") is not None and chain["style"] != rec:
                old_label = chain["style"].get("label", chain["style"].get("id", "unknown"))
                warnings.append(
                    f"Style Picker: replacing style '{old_label}' with "
                    f"'{rec.get('label', resolved_id)}' (Style is exclusive — "
                    f"the second Style Picker wins.)"
                )
            chain["style"] = rec

    # Apply meta overrides.
    if meta_overrides:
        chain.setdefault("_meta", {})
        for key, value in meta_overrides.items():
            if value and value != "inherit":
                chain["_meta"][key] = value

    # Blocked axes.
    blocked = get_blocked_axes(chain.get("style"))
    chain["modifiers"] = filter_modifiers(chain.get("modifiers", []), blocked)

    return chain, warnings, sheet_chains


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

if _COMFY_AVAILABLE:

    class StylebookStyle(io.ComfyNode):
        """The primary style picker — exclusive medium axis.

        Pick a style from a category dropdown, randomize within a filter,
        cycle through a pool deterministically, or emit a batch style-sheet.
        Connects to any downstream Stylebook node (Artist, Modifier, Blend)
        or directly to a CLIPTextEncode node.

        The user_prompt input accepts your subject description. Leave it
        empty to output style text only — connect it to a CLIPTextEncode
        and add your prompt afterwards. Or type your subject here and
        the style will be prepended (or appended) to it.
        """

        @classmethod
        def define_schema(cls) -> io.Schema:
            categories = _category_options()
            style_names = [_STYLE_RANDOM] + sorted(
                rec["label"] for rec in STYLES.values()
            )

            return io.Schema(
                node_id="StylebookStyle",
                display_name="Stylebook Style",
                category="conditioning/stylebook",
                description="Pick, randomize, cycle, or batch-sheet a visual style from "
                            "12 categories. Type your subject in user_prompt or connect a "
                            "text source — the style wraps around it.",
                inputs=[
                    io.String.Input(
                        "style_chain",
                        display_name="style_chain",
                        force_input=True,
                        optional=True,
                        default="{}",
                        tooltip="Connect an upstream Stylebook node's style_chain output here.",
                    ),
                    io.String.Input(
                        "user_prompt",
                        display_name="user_prompt",
                        force_input=True,
                        multiline=True,
                        optional=True,
                        default="",
                        tooltip="Your subject description. The rendered style text will be "
                                "prepended or appended to this. Leave empty to output just "
                                "the style text. Connect a text source or type directly.",
                    ),
                    io.Combo.Input(
                        "mode",
                        options=[_MODE_PICK, _MODE_RANDOM, _MODE_CYCLE, _MODE_SHEET],
                        default=_MODE_PICK,
                        tooltip="Pick: choose a style from the dropdown. Random: seeded random pick "
                                "within the filtered pool. Cycle: deterministic index through the pool. "
                                "Sheet: emit N styles as a batch.",
                    ),
                    io.Combo.Input(
                        "style",
                        options=style_names,
                        default=_STYLE_RANDOM,
                        tooltip="The style to apply. 'Random' draws from the category+tag_filter pool. "
                                "Visible only in Pick mode.",
                    ),
                    io.Combo.Input(
                        "category",
                        options=categories,
                        default=_STYLE_NONE,
                        tooltip="Restrict Random/Cycle/Sheet to this category. None means all "
                                "categories. Does not affect the picked style. Example: set to "
                                "'photography' to cycle through photography styles only.",
                    ),
                    io.String.Input(
                        "tag_filter",
                        default="",
                        tooltip="Narrows Random/Cycle/Sheet to styles matching these "
                                "comma-separated tags. Leave empty to use the whole category. "
                                "Example: 'bw, high-contrast'.",
                    ),
                    io.Int.Input(
                        "seed",
                        default=0,
                        min=0,
                        max=0xFFFFFFFFFFFFFFFF,
                        control_after_generate="randomize",
                        tooltip="Seed for Random and Sheet modes. Same seed + same filter = "
                                "same result, always reproducible.",
                    ),
                    io.Int.Input(
                        "cycle_index",
                        display_name="cycle index",
                        default=0,
                        min=0,
                        max=9999,
                        tooltip="0-based index into the filtered pool for Cycle mode. "
                                "Index 0 = first match, 1 = second, wraps around.",
                    ),
                    io.Int.Input(
                        "sheet_count",
                        display_name="sheet count",
                        default=4,
                        min=2,
                        max=16,
                        tooltip="Number of styles to emit in Sheet mode.",
                    ),
                    io.Combo.Input(
                        "format",
                        options=["inherit", _FMT_AUTO, _FMT_TAGS, _FMT_PROSE],
                        default="inherit",
                        tooltip="Output format. 'inherit' uses upstream setting. 'auto' picks "
                                "prose when available, tags otherwise. Tags: comma-separated "
                                "keywords. Prose: natural language paragraph.",
                    ),
                    io.Combo.Input(
                        "strength",
                        options=["inherit", _STRENGTH_SUBTLE, _STRENGTH_NORMAL, _STRENGTH_STRONG],
                        default="inherit",
                        tooltip="How strongly the style is applied. Strong repeats emphasis "
                                "keywords (tags) or appends the strength tail (prose).",
                    ),
                    io.Combo.Input(
                        "placement",
                        options=["inherit", _PLACEMENT_PREPEND, _PLACEMENT_APPEND],
                        default="inherit",
                        tooltip="Where the style text goes relative to your prompt. "
                                "Prepend: style first, then your prompt. Append: your prompt first.",
                    ),
                ],
                outputs=[
                    io.String.Output(display_name="prompt"),
                    io.String.Output(display_name="negative"),
                    io.String.Output(display_name="style_chain"),
                ],
            )

        @classmethod
        def fingerprint_inputs(cls, **kwargs) -> float:
            return float("nan")  # always re-execute (seed advances control_after_generate)

        @classmethod
        def execute(
            cls,
            style_chain: str = "{}",
            user_prompt: str = "",
            mode: str = "Pick",
            style: str = "Random",
            category: str = "None",
            tag_filter: str = "",
            seed: int = 0,
            cycle_index: int = 0,
            sheet_count: int = 4,
            format: str = "inherit",
            strength: str = "inherit",
            placement: str = "inherit",
        ) -> io.NodeOutput:
            meta_overrides = {}
            if format != "inherit":
                meta_overrides["format"] = format
            if strength != "inherit":
                meta_overrides["strength"] = strength
            if placement != "inherit":
                meta_overrides["placement"] = placement

            # Resolve style id from label if in Pick mode.
            style_id = style
            if mode == _MODE_PICK and style not in (_STYLE_RANDOM, _STYLE_NONE):
                rec = get_style(style)
                style_id = rec["id"] if rec else _STYLE_NONE

            chain, warnings, sheet_chains = build_style_chain(
                chain_json=style_chain,
                style_id=style_id,
                mode=mode,
                category=category,
                tag_filter=tag_filter,
                seed=seed,
                cycle_index=cycle_index,
                sheet_count=sheet_count,
                meta_overrides=meta_overrides,
            )

            # Store the user prompt in the chain so downstream nodes can use it.
            if user_prompt.strip():
                chain.setdefault("_meta", {})
                chain["_meta"]["user_prompt"] = user_prompt.strip()

            for w in warnings:
                print(f"[Stylebook] {w}")

            meta = resolve_meta(chain)
            prompt = render_prompt(chain, meta, meta.get("user_prompt", ""))

            return io.NodeOutput(prompt, render_negative(chain), dump_chain(chain))
