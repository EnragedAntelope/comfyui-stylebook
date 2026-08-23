"""StylebookBlend node - blend two styles at a ratio.

Wire a second style chain into ``style_b`` to blend it with the current
chain's style. ``ratio`` runs 0.0 (pure A) to 1.0 (pure B).
"""

from __future__ import annotations

try:
    from . import schema_options as opt
    from .node_support import report, send_resolved_event, show_readout
    from .stylebook_core import (
        _split_items, dump_chain, parse_chain, readout_detail,
        render_negative, render_prompt, resolve_meta, resolved_summary,
    )
except ImportError:  # pragma: no cover - standalone/test context
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.node_support import report, send_resolved_event, show_readout
    from stylebook_nodes.stylebook_core import (
        _split_items, dump_chain, parse_chain, readout_detail,
        render_negative, render_prompt, resolve_meta, resolved_summary,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


#: Blend splits tag strings exactly as the renderer does. This was a
#: second copy of the same three lines; two implementations of "split a
#: tag string" is one more than the pack should have.
_items = _split_items


def _take(items: list[str], share: float) -> list[str]:
    """Take a leading share of *items*, always keeping at least one.

    Tag strings are written defining-term-first, so the leading slice is
    the part that carries the style.
    """
    if not items:
        return []
    count = max(1, round(len(items) * share))
    return items[:min(count, len(items))]


def blend_styles(style_a: dict, style_b: dict, ratio: float) -> dict:
    """Return a synthetic style record interpolating *style_a* and *style_b*.

    The ratio genuinely changes the output at every value, rather than
    only at the endpoints:

    * it sets how many tag items each side contributes, so 0.25 gives a
      mostly-A tag list and 0.75 a mostly-B one;
    * it decides which style leads the prose sentence, because whichever
      style is named first dominates how a prose model reads the result.
    """
    # NaN survives min/max untouched -- every comparison against it is
    # False -- and then round(NaN) raises ValueError deep inside _take.
    # The widget's own min/max keeps this off the normal path; a chain
    # carrying a hand-written value does not.
    if ratio != ratio:
        ratio = 0.5
    ratio = min(1.0, max(0.0, float(ratio)))
    a_label = style_a.get("label", "A")
    b_label = style_b.get("label", "B")

    a_items = _take(_items(style_a.get("tags", "")), 1.0 - ratio)
    b_items = _take(_items(style_b.get("tags", "")), ratio)

    if ratio >= 0.5:
        lead, follow = b_label, a_label
        lead_prose = style_b.get("prose", "")
        follow_prose = style_a.get("prose", "")
        tag_items = b_items + a_items
    else:
        lead, follow = a_label, b_label
        lead_prose = style_a.get("prose", "")
        follow_prose = style_b.get("prose", "")
        tag_items = a_items + b_items

    seen: set[str] = set()
    merged_tags: list[str] = []
    for item in tag_items:
        if item.lower() not in seen:
            seen.add(item.lower())
            merged_tags.append(item)

    blended = dict(style_a)
    blended["id"] = f"blend_{style_a.get('id', 'a')}_{style_b.get('id', 'b')}"
    blended["label"] = f"{a_label} x {b_label}"
    blended["tags"] = ", ".join(merged_tags)
    blended["prose"] = (
        f"{lead_prose.rstrip('.')}, carrying the character of {follow}: "
        f"{follow_prose.rstrip('.')}."
    ).strip()
    blended["negative"] = ", ".join(
        _items(style_a.get("negative", "")) + _items(style_b.get("negative", ""))
    )
    blended["blocks"] = sorted(
        set(style_a.get("blocks", [])) & set(style_b.get("blocks", []))
    )
    blended["blend"] = {
        "a": style_a.get("id"),
        "b": style_b.get("id"),
        "ratio": round(ratio, 3),
        "lead": lead,
    }
    return blended


def build_blend_chain(
    chain_json_a: str,
    chain_json_b: str,
    ratio: float,
) -> tuple[dict, list[str]]:
    """Blend two chains and return ``(chain, warnings)``."""
    chain_a = parse_chain(chain_json_a)
    chain_b = parse_chain(chain_json_b)
    style_a = chain_a.get("style")
    style_b = chain_b.get("style")
    warnings: list[str] = []

    if style_a is None and style_b is None:
        warnings.append("Blend: neither input carries a style. Passing through.")
        return chain_a, warnings
    if style_b is None:
        warnings.append(
            "Blend: nothing connected to style B, so there is nothing to "
            "blend with. Passing style A through unchanged."
        )
        return chain_a, warnings
    if style_a is None:
        warnings.append("Blend: no style on the A input. Using style B alone.")
        chain_a["style"] = style_b
        return chain_a, warnings

    if ratio <= 0.001:
        chain_a["style"] = style_a
    elif ratio >= 0.999:
        chain_a["style"] = style_b
    else:
        chain_a["style"] = blend_styles(style_a, style_b, ratio)

    # Artists and modifiers from the B branch would otherwise be lost.
    # The comment said "and modifiers" for a while before the code did.
    for artist in chain_b.get("artists", []):
        if artist not in chain_a.get("artists", []):
            chain_a.setdefault("artists", []).append(artist)

    # One modifier per axis still holds across a blend, and the A branch
    # is the primary chain, so an axis A already occupies stays with A.
    merged = chain_a.setdefault("modifiers", [])
    occupied = {mod.get("axis") for mod in merged}
    for mod in chain_b.get("modifiers", []):
        axis = mod.get("axis")
        if axis in occupied:
            warnings.append(
                f"Blend: both branches set the {axis} axis. Keeping A's "
                f"modifier and dropping B's '{mod.get('label', '?')}'."
            )
            continue
        occupied.add(axis)
        merged.append(mod)

    return chain_a, warnings


if _COMFY_AVAILABLE:

    class StylebookBlend(io.ComfyNode):
        """Blend two styles at a controllable ratio."""

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookBlend",
                display_name="Stylebook Blend",
                category="conditioning/stylebook",
                description=(
                    "Blend two styles into one description. Feed one Style "
                    "node's style_chain into style_chain and another into "
                    "style B, then set the ratio: 0.0 is pure A, 1.0 is pure "
                    "B. This is a blend of the two written descriptions, not "
                    "of two images: the ratio sets how much of each style's "
                    "keyword list survives and which of the two leads the "
                    "sentence. Leading is what decides the result, so the "
                    "biggest change happens as the ratio crosses 0.5."
                ),
                inputs=[
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        tooltip="The primary style chain, style A.",
                    ),
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_b",
                        display_name="style B",
                        optional=True,
                        tooltip=(
                            "The second style chain. Connect another Style "
                            "node's style_chain output here, which is its "
                            "third output, not prompt. Without it there is "
                            "nothing to blend and A passes through."
                        ),
                    ),
                    io.Float.Input(
                        "ratio",
                        default=0.5,
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        round=0.01,
                        display_mode=io.NumberDisplay.slider,
                        tooltip=(
                            "0.0 is pure style A, 1.0 is pure style B. In "
                            "between, the ratio sets how much of each "
                            "style's description survives, and which of the "
                            "two leads the result."
                        ),
                    ),
                ],
                outputs=[
                    io.String.Output(display_name="prompt"),
                    io.String.Output(display_name="negative"),
                    io.Custom(opt.CHAIN_TYPE).Output(display_name="style_chain"),
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
            style_b: str = "",
            ratio: float = 0.5,
        ) -> io.NodeOutput:
            chain, warnings = build_blend_chain(style_chain, style_b, ratio)
            report(warnings)

            meta = resolve_meta(chain)
            subject = chain["_meta"].get("user_prompt", "")
            prompt = render_prompt(chain, meta, subject)
            show_readout(
                cls.hidden.unique_id,
                resolved_summary(chain),
                readout_detail(chain, meta, subject),
                warnings,
            )
            # No style/artist/modifier/axis: a blend's style is a synthetic
            # merged record, not a single named pick a Pin menu item could
            # write back to a widget (Blend has no Pin item -- see
            # js/stylebook_readout.js). Copy resolved prompt still works
            # off `prompt` alone.
            send_resolved_event(cls.hidden.unique_id, prompt)
            return io.NodeOutput(prompt, render_negative(chain), dump_chain(chain))
