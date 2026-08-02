"""StylebookModifier node — additive, one per sub-axis.

Add a lighting, colour grade, era, finish, or mood tilt.
Each modifier node targets one axis; a second modifier on the
same axis replaces the first (with a warning).
"""

from __future__ import annotations

try:
    from ..data.modifiers import MODIFIERS, AXES, MODIFIERS_BY_AXIS
    from .stylebook_core import parse_chain, dump_chain, merge_chain, resolve_meta, render_prompt, render_negative
except ImportError:  # pragma: no cover
    from data.modifiers import MODIFIERS, AXES, MODIFIERS_BY_AXIS
    from stylebook_nodes.stylebook_core import parse_chain, dump_chain, merge_chain, resolve_meta, render_prompt, render_negative

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


_MOD_OFF = "Off"
_MOD_RANDOM = "Random"


def _modifier_options(axis: str) -> list[str]:
    ids = MODIFIERS_BY_AXIS.get(axis, [])
    names = [MODIFIERS[mid]["label"] for mid in ids if mid in MODIFIERS]
    return [_MOD_RANDOM, _MOD_OFF] + sorted(names)


if _COMFY_AVAILABLE:

    class StylebookModifier(io.ComfyNode):
        """Add a rendering modifier on one axis.

        Five axes: lighting, color_grade, era, finish, mood. Each modifier
        node targets exactly one axis. A second modifier on the same axis
        replaces the first. Defaults to Off on every axis — no modifier is
        applied unless you enable one.
        """

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookModifier",
                display_name="Stylebook Modifier",
                category="conditioning/stylebook",
                description="Tilt the rendering on one axis: lighting, colour grade, "
                            "era, finish, or mood. One per axis — stacking another on the "
                            "same axis replaces the first. Defaults to Off.",
                inputs=[
                    io.String.Input(
                        "style_chain",
                        display_name="style_chain",
                        force_input=True,
                        optional=True,
                        default="{}",
                        tooltip="Connect an upstream Stylebook node's style_chain output.",
                    ),
                    io.Combo.Input(
                        "axis",
                        options=list(AXES),
                        default=AXES[0],
                        tooltip="Which rendering axis this modifier tilts. "
                                "Each axis can hold exactly one modifier.",
                    ),
                    io.Combo.Input(
                        "modifier",
                        options=_modifier_options(AXES[0]),
                        default=_MOD_OFF,
                        tooltip="The modifier to apply on this axis. 'Off' applies no modifier. "
                                "'Random' picks from the axis pool.",
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
            axis: str,
            modifier: str,
            style_chain: str = "{}",
        ) -> io.NodeOutput:
            chain = parse_chain(style_chain)
            warnings: list[str] = []

            if modifier and modifier not in (_MOD_OFF, _MOD_RANDOM):
                mod_rec = None
                for mid, mrec in MODIFIERS.items():
                    if mrec.get("label") == modifier and mrec.get("axis") == axis:
                        mod_rec = mrec
                        break

                if mod_rec:
                    # Check if this axis already has a modifier.
                    existing = chain.get("modifiers", [])
                    for i, ex in enumerate(existing):
                        if ex.get("axis") == axis:
                            warnings.append(
                                f"Modifier: {axis} already has '{ex.get('label', '?')}' "
                                f"— replacing with '{mod_rec['label']}'."
                            )
                            existing[i] = mod_rec
                            break
                    else:
                        existing.append(mod_rec)
                    chain["modifiers"] = existing
                else:
                    warnings.append(f"Modifier: unknown '{modifier}' on axis '{axis}'.")

            for w in warnings:
                print(f"[Stylebook] {w}")

            meta = resolve_meta(chain)
            prompt = render_prompt(chain, meta, chain.get("_meta", {}).get("user_prompt", ""))
            negative = render_negative(chain)

            return io.NodeOutput(prompt, negative, dump_chain(chain))
