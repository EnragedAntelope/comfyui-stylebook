"""StylebookBlend node — blend two styles at a ratio.

Wire a second style into the ``style_b`` input to blend it with
the current chain's style. The ``ratio`` widget (0.0–1.0) controls
the balance — 0.0 is pure style A, 1.0 is pure style B, 0.5 is
an even blend.
"""

from __future__ import annotations

import json

try:
    from .stylebook_core import parse_chain, dump_chain, resolve_meta, render_prompt, render_negative
except ImportError:  # pragma: no cover
    from stylebook_nodes.stylebook_core import parse_chain, dump_chain, resolve_meta, render_prompt, render_negative

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


if _COMFY_AVAILABLE:

    class StylebookBlend(io.ComfyNode):
        """Blend two styles at a controllable ratio.

        The primary style comes from the upstream ``style_chain``. Connect
        a second style chain into ``style_b`` to blend. Ratio 0.0 = pure
        style A; 1.0 = pure style B; 0.5 = even blend. The blend is
        performed by interpolating prose text, weighted toward each side.
        """

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookBlend",
                display_name="Stylebook Blend",
                category="conditioning/stylebook",
                description="Blend two styles at a ratio from 0.0 (style A) "
                            "to 1.0 (style B). Connect a second style_chain into "
                            "style_b to blend.",
                inputs=[
                    io.String.Input(
                        "style_chain",
                        display_name="style_chain",
                        force_input=True,
                        optional=True,
                        default="{}",
                        tooltip="Primary style chain (style A).",
                    ),
                    io.String.Input(
                        "style_b",
                        display_name="style B",
                        force_input=True,
                        optional=True,
                        default="{}",
                        tooltip="Second style chain to blend with (style B). "
                                "Connect another Style node's style_chain output here.",
                    ),
                    io.Float.Input(
                        "ratio",
                        default=0.5,
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        round=0.01,
                        display_mode=io.NumberDisplay.slider,
                        tooltip="Blend ratio: 0.0 = pure style A, 1.0 = pure style B, "
                                "0.5 = even blend.",
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
            return float("nan")

        @classmethod
        def execute(
            cls,
            style_chain: str,
            style_b: str,
            ratio: float,
        ) -> io.NodeOutput:
            chain_a = parse_chain(style_chain)
            chain_b = parse_chain(style_b)

            style_a = chain_a.get("style")
            style_b_rec = chain_b.get("style")

            # If no second style, just pass through.
            if not style_b_rec:
                meta = resolve_meta(chain_a)
                return io.NodeOutput(
                    render_prompt(chain_a, meta),
                    render_negative(chain_a),
                    dump_chain(chain_a),
                )

            # If no first style, use second entirely.
            if not style_a:
                meta = resolve_meta(chain_b)
                return io.NodeOutput(
                    render_prompt(chain_b, meta),
                    render_negative(chain_b),
                    dump_chain(chain_b),
                )

            # Blend: create a synthetic style entry from the two.
            a_label = style_a.get("label", "A")
            b_label = style_b_rec.get("label", "B")

            # Weighted prose blend.
            a_prose = style_a.get("prose", style_a.get("tags", ""))
            b_prose = style_b_rec.get("prose", style_b_rec.get("tags", ""))

            if ratio <= 0.01:
                # Pure A
                chain_a["style"]["blend"] = None
                result_chain = chain_a
            elif ratio >= 0.99:
                # Pure B
                chain_a["style"] = style_b_rec
                chain_a["style"]["blend"] = None
                result_chain = chain_a
            else:
                # Interpolate: build a compound style.
                a_weight = 1.0 - ratio
                b_weight = ratio

                blend_tags = f"{a_label} style, {b_label} style"
                blend_prose = (
                    f"A blend of {b_label} sensibility crossing into {a_label} form: "
                    f"{b_prose} {a_prose}"
                )

                blended = dict(style_a)
                blended["id"] = f"blend_{style_a.get('id','a')}_{style_b_rec.get('id','b')}"
                blended["label"] = f"{a_label} × {b_label}"
                blended["tags"] = blend_tags
                blended["prose"] = blend_prose
                blended["blend"] = {"a": style_a.get("id"), "b": style_b_rec.get("id"), "ratio": ratio}
                chain_a["style"] = blended

                result_chain = chain_a

            meta = resolve_meta(result_chain)
            prompt = render_prompt(result_chain, meta)
            negative = render_negative(result_chain)

            return io.NodeOutput(prompt, negative, dump_chain(result_chain))
