"""StylebookSheet node - one subject rendered across many styles.

Emits a genuine list of prompts, one per style, so a batched sampler
produces a contact sheet of the same subject in N different looks.

This used to be a mode on the Style node that joined every prompt into
one string with separators, which nothing downstream could consume.
"""

from __future__ import annotations

try:
    from ..data.styles import STYLES, resolve_style_name
    from . import schema_options as opt
    from .node_support import report, send_resolved_event, show_readout
    from .stylebook_core import (
        parse_chain, render_negative, render_prompt, resolve_meta,
        sheet_style_ids,
    )
except ImportError:  # pragma: no cover - standalone/test context
    from data.styles import STYLES, resolve_style_name
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.node_support import report, send_resolved_event, show_readout
    from stylebook_nodes.stylebook_core import (
        parse_chain, render_negative, render_prompt, resolve_meta,
        sheet_style_ids,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


def parse_style_list(text: str) -> list[str]:
    """Split the ``styles`` box into labels.

    Accepts one label per line or a comma-separated list, because both are
    natural to type and there is no reason to insist on one. Blank entries
    and duplicates are dropped, the original order is kept, and the order
    is what the sheet renders in.
    """
    items: list[str] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        for raw in line.split(","):
            label = raw.strip()
            if not label or label.lower() in seen:
                continue
            seen.add(label.lower())
            items.append(label)
    return items


def resolve_style_list(labels: list[str]) -> tuple[list[str], list[str]]:
    """Resolve chosen labels to style ids, returning ``(ids, warnings)``.

    Aliases resolve too, because this box is hand-typeable and "Ukiyo-e"
    is a term people know: it is an alias of Woodblock Print rather than
    a label. An alias claimed by two styles is reported with both names
    instead of being guessed at.
    """
    ids: list[str] = []
    warnings: list[str] = []
    for label in labels:
        record, candidates = resolve_style_name(label)
        if record is None:
            if candidates:
                warnings.append(
                    f"Sheet: '{label}' is an alias of more than one style "
                    f"({', '.join(candidates)}). Skipped. Name the one you "
                    f"want, or pick it from the gallery."
                )
            else:
                warnings.append(
                    f"Sheet: no style named '{label}'. Skipped. Use the "
                    f"Choose styles button to fill this in from the gallery."
                )
            continue
        ids.append(record["id"])
    return ids, warnings


def build_sheet(
    chain_json: str,
    user_prompt: str,
    styles: str,
    count: int,
    category: str,
    tag_filter: str,
    seed: int,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return ``(prompts, negatives, labels, warnings)`` for the sheet.

    A non-empty ``styles`` list is an explicit choice and wins outright:
    the pool filters and the count are for when you have not chosen, and
    silently trimming or padding a list somebody typed out would be worse
    than ignoring the widgets they did not use.
    """
    base = parse_chain(chain_json)
    warnings: list[str] = []
    pool_category = opt.category_id(category)

    subject = user_prompt.strip() or base["_meta"].get("user_prompt", "")

    chosen = parse_style_list(styles)
    if chosen:
        ids, warnings = resolve_style_list(chosen)
        if not ids:
            warnings.append(
                "Sheet: none of the chosen styles could be resolved, so "
                "nothing was emitted."
            )
            return [], [], [], warnings
        return _render_sheet(base, subject, ids, warnings)

    ids = sheet_style_ids(
        seed=seed,
        count=count,
        category=pool_category,
        tag_filter=tag_filter,
    )

    if not ids:
        warnings.append(
            f"Sheet: no style matches category '{category}' with tag_filter "
            f"'{tag_filter}'. Widen the filter or clear it."
        )
        return [], [], [], warnings

    if len(ids) < count:
        warnings.append(
            f"Sheet: only {len(ids)} styles match the filter, fewer than the "
            f"{count} requested. Emitting {len(ids)}."
        )
    return _render_sheet(base, subject, ids, warnings)


def _render_sheet(
    base: dict,
    subject: str,
    ids: list[str],
    warnings: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Render one prompt per style id, sharing the base chain."""

    prompts: list[str] = []
    negatives: list[str] = []
    labels: list[str] = []
    for style_id in ids:
        record = STYLES.get(style_id)
        if record is None:
            continue
        chain = {
            "_meta": dict(base.get("_meta", {})),
            "style": record,
            "modifiers": list(base.get("modifiers", [])),
            "artists": list(base.get("artists", [])),
        }
        meta = resolve_meta(chain)
        prompts.append(render_prompt(chain, meta, subject))
        negatives.append(render_negative(chain))
        labels.append(record["label"])

    return prompts, negatives, labels, warnings


if _COMFY_AVAILABLE:

    class StylebookSheet(io.ComfyNode):
        """Render one subject across N styles as a batch."""

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookSheet",
                display_name="Stylebook Sheet",
                category="conditioning/stylebook",
                description=(
                    "Emit one prompt per style so a single subject renders "
                    "across many looks at once. Choose the styles yourself "
                    "with the gallery button, or leave the list empty and "
                    "let a seeded draw fill it. The outputs are lists: wire "
                    "prompt into a CLIPTextEncode and every entry runs as "
                    "its own image in the batch."
                ),
                inputs=[
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        tooltip=(
                            "Optional. Artists and modifiers on this chain "
                            "apply to every style in the sheet. Any style on "
                            "it is replaced by the sheet's own picks."
                        ),
                    ),
                    io.String.Input(
                        "user_prompt",
                        display_name="user_prompt",
                        multiline=True,
                        optional=True,
                        default="",
                        tooltip=(
                            "The one subject that every style in the sheet "
                            "renders."
                        ),
                    ),
                    io.String.Input(
                        "styles",
                        multiline=True,
                        optional=True,
                        default="",
                        tooltip=(
                            "The exact styles to render, one per line or "
                            "comma-separated, in the order you want them. "
                            "Click Choose styles to fill this in from the "
                            "gallery. While this box has anything in it, it "
                            "wins: count, category and tag_filter are "
                            "ignored, because a list you typed out should "
                            "not be silently trimmed."
                        ),
                    ),
                    io.Int.Input(
                        "count",
                        default=4,
                        min=2,
                        max=32,
                        tooltip=(
                            "How many styles to draw when the styles box is "
                            "empty. Each becomes one image in the batch, so "
                            "raise it with your VRAM in mind."
                        ),
                    ),
                    io.Combo.Input(
                        "category",
                        options=opt.category_options(),
                        default=opt.DEFAULTS["category"],
                        tooltip=(
                            "Restrict the seeded draw to one category. No "
                            "effect while the styles box has entries."
                        ),
                    ),
                    io.String.Input(
                        "tag_filter",
                        default="",
                        tooltip=(
                            "Comma-separated; every term must match. Matches "
                            "tags, prose, label and aliases. No effect while "
                            "the styles box has entries."
                        ),
                    ),
                    io.Int.Input(
                        "seed",
                        default=0,
                        min=0,
                        max=0xFFFFFFFFFFFFFFFF,
                        control_after_generate=True,
                        tooltip=(
                            "Which styles get drawn when the styles box is "
                            "empty. The same seed and filter always produce "
                            "the same sheet."
                        ),
                    ),
                ],
                outputs=[
                    io.String.Output(display_name="prompt", is_output_list=True),
                    io.String.Output(display_name="negative", is_output_list=True),
                    io.String.Output(display_name="style_names", is_output_list=True),
                ],
                hidden=[io.Hidden.unique_id],
            )

        @classmethod
        def fingerprint_inputs(cls, **kwargs) -> float:
            return float("nan")

        @classmethod
        def execute(
            cls,
            style_chain: str = "",
            user_prompt: str = "",
            styles: str = "",
            count: int = 4,
            category: str = opt.DEFAULTS["category"],
            tag_filter: str = "",
            seed: int = 0,
        ) -> io.NodeOutput:
            prompts, negatives, labels, warnings = build_sheet(
                chain_json=style_chain,
                user_prompt=user_prompt,
                styles=styles,
                count=count,
                category=category,
                tag_filter=tag_filter,
                seed=seed,
            )
            report(warnings)
            summary = (f"{len(prompts)} styles: " + ", ".join(labels)
                       if prompts else "no styles matched the filter")
            show_readout(cls.hidden.unique_id, summary, warnings=warnings)
            # One prompt per line: currently the only way to read every
            # entry without wiring a preview node onto a list output, and
            # exactly what "Copy resolved prompt" puts on the clipboard.
            # No style/artist/modifier: Sheet resolves N styles, not one,
            # so it has no Pin menu item -- see js/stylebook_readout.js.
            send_resolved_event(cls.hidden.unique_id, "\n".join(prompts))
            return io.NodeOutput(prompts, negatives, labels)
