"""StylebookModifier node - additive, one modifier per axis.

Add a lighting, colour grade, era, finish or mood tilt. Each node
targets one axis; a second modifier on the same axis replaces the first.
"""

from __future__ import annotations

try:
    from ..data.modifiers import AXES, MODIFIERS, MODIFIERS_BY_AXIS, get_modifier
    from . import schema_options as opt
    from .node_support import report, send_resolved_event, show_readout
    from .stylebook_core import (
        dump_chain, get_blocked_axes, parse_chain, readout_detail,
        render_negative, render_prompt, resolve_meta, resolved_summary,
        stable_choice,
    )
except ImportError:  # pragma: no cover - standalone/test context
    from data.modifiers import AXES, MODIFIERS, MODIFIERS_BY_AXIS, get_modifier
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.node_support import report, send_resolved_event, show_readout
    from stylebook_nodes.stylebook_core import (
        dump_chain, get_blocked_axes, parse_chain, readout_detail,
        render_negative, render_prompt, resolve_meta, resolved_summary,
        stable_choice,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


def apply_modifier(
    chain_json: str,
    axis: str,
    modifier_label: str,
    mode: str,
    seed: int,
    cycle_index: int = 0,
) -> tuple[dict, list[str]]:
    """Apply one modifier to the chain and return ``(chain, warnings)``."""
    chain = parse_chain(chain_json)
    warnings: list[str] = []

    axis_ids = sorted(MODIFIERS_BY_AXIS.get(axis, []))

    record = None
    if mode == opt.MODE_RANDOM:
        chosen = stable_choice(seed, axis_ids)
        record = MODIFIERS[chosen] if chosen else None
    elif mode == opt.MODE_CYCLE:
        chosen = axis_ids[cycle_index % len(axis_ids)] if axis_ids else None
        record = MODIFIERS[chosen] if chosen else None
    elif modifier_label and modifier_label != opt.OFF:
        record = get_modifier(modifier_label, axis)
        if record is None:
            # The dropdown carries every axis's modifiers so that changing
            # axis never leaves it holding an invalid value. Say plainly
            # which axis the chosen modifier actually belongs to.
            elsewhere = get_modifier(modifier_label)
            if elsewhere is not None:
                warnings.append(
                    f"Modifier: '{modifier_label}' belongs to the "
                    f"'{elsewhere['axis']}' axis, not '{axis}'. Set axis to "
                    f"'{elsewhere['axis']}' to use it."
                )
            else:
                warnings.append(f"Modifier: no modifier named '{modifier_label}'.")

    if record is not None:
        blocked = get_blocked_axes(chain.get("style"))
        if axis in blocked:
            style_label = (chain.get("style") or {}).get("label", "the style")
            warnings.append(
                f"Modifier: '{style_label}' already fixes the {axis} axis, "
                f"so '{record['label']}' would be overridden. Not applied."
            )
        else:
            modifiers = chain.get("modifiers", [])
            for index, existing in enumerate(modifiers):
                if existing.get("axis") == axis:
                    if existing.get("label") != record["label"]:
                        warnings.append(
                            f"Modifier: the {axis} axis already held "
                            f"'{existing.get('label', '?')}'. Replaced with "
                            f"'{record['label']}'."
                        )
                    modifiers[index] = record
                    break
            else:
                modifiers.append(record)
            chain["modifiers"] = modifiers

    return chain, warnings


if _COMFY_AVAILABLE:

    class StylebookModifier(io.ComfyNode):
        """Tilt the rendering on one axis."""

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookModifier",
                display_name="Stylebook Modifier",
                category="conditioning/stylebook",
                description=(
                    "Tilt the rendering on one axis: lighting, colour grade, "
                    "era, finish or mood. One modifier per axis; a second on "
                    "the same axis replaces the first. Defaults to Off."
                ),
                inputs=[
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        tooltip="Connect an upstream Stylebook style_chain output.",
                    ),
                    io.Combo.Input(
                        "axis",
                        options=opt.axis_options(),
                        default=opt.DEFAULTS["axis"],
                        tooltip=(
                            "Which rendering axis this node tilts. Each axis "
                            "holds exactly one modifier, so use one Modifier "
                            "node per axis you want to set."
                        ),
                    ),
                    # Mode sits above the widgets it swaps, so the control
                    # you just clicked never moves out from under the cursor.
                    io.Combo.Input(
                        "mode",
                        options=list(opt.MODES),
                        default=opt.DEFAULTS["modifier_mode"],
                        tooltip=(
                            "Pick: choose one modifier yourself, which is the "
                            "default because a modifier is a deliberate "
                            "finishing tilt. Random: a seeded pick from this "
                            "axis. Cycle: step through this axis by index."
                        ),
                    ),
                    io.Combo.Input(
                        "modifier",
                        options=opt.modifier_options(),
                        default=opt.DEFAULTS["modifier"],
                        tooltip=(
                            "The modifier to apply in Pick mode. The list "
                            "narrows to the selected axis. Off applies "
                            "nothing, which is what a fresh node does."
                        ),
                    ),
                    io.Int.Input(
                        "seed",
                        default=0,
                        min=0,
                        max=0xFFFFFFFFFFFFFFFF,
                        control_after_generate=True,
                        tooltip=(
                            "Seed for Random mode. The same seed on the same "
                            "axis gives the same modifier."
                        ),
                    ),
                    io.Int.Input(
                        "cycle_index",
                        display_name="cycle index",
                        default=0,
                        min=0,
                        max=9999,
                        tooltip=(
                            "Which modifier to take in Cycle mode. 0 is the "
                            "first on this axis and the index wraps at the "
                            "end. This is a list position, not a seed, so "
                            "adding modifiers to an axis shifts it. "
                            "Cycle mode steps the index automatically each run "
                            "(right-click the node to turn 'Auto-advance cycle' "
                            "off if you want to hold a fixed index)."
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
            axis: str = AXES[0],
            mode: str = opt.DEFAULTS["modifier_mode"],
            modifier: str = opt.OFF,
            seed: int = 0,
            cycle_index: int = 0,
        ) -> io.NodeOutput:
            chain, warnings = apply_modifier(
                chain_json=style_chain,
                axis=axis,
                modifier_label=modifier,
                mode=mode,
                seed=seed,
                cycle_index=cycle_index,
            )
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
            on_axis = next(
                (m for m in chain.get("modifiers", []) if m.get("axis") == axis),
                None,
            )
            send_resolved_event(
                cls.hidden.unique_id,
                prompt,
                modifier=on_axis["label"] if on_axis else None,
                axis=axis,
                cycle_pool_size=len(MODIFIERS_BY_AXIS.get(axis, [])),
            )
            return io.NodeOutput(prompt, render_negative(chain), dump_chain(chain))
