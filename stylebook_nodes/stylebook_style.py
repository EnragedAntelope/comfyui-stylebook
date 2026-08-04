"""StylebookStyle node - the exclusive medium axis.

Pick a style, randomize within a filtered pool, or cycle
deterministically through that pool.
"""

from __future__ import annotations

try:
    from ..data.styles import STYLES, get_style
    from . import schema_options as opt
    from .node_support import report, send_resolved_event, show_readout
    from .stylebook_core import (
        cycle_style_id, dump_chain, filter_modifiers, get_blocked_axes,
        parse_chain, random_style_id, readout_detail, render_negative,
        render_prompt, resolve_meta, resolved_summary,
    )
except ImportError:  # pragma: no cover - standalone/test context
    from data.styles import STYLES, get_style
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.node_support import report, send_resolved_event, show_readout
    from stylebook_nodes.stylebook_core import (
        cycle_style_id, dump_chain, filter_modifiers, get_blocked_axes,
        parse_chain, random_style_id, readout_detail, render_negative,
        render_prompt, resolve_meta, resolved_summary,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


def build_style_chain(
    chain_json: str,
    style_label: str,
    mode: str,
    category: str,
    tag_filter: str,
    seed: int,
    cycle_index: int,
    meta_overrides: dict[str, str] | None = None,
) -> tuple[dict, list[str]]:
    """Resolve the style for this node and return ``(chain, warnings)``.

    Kept free of ComfyUI imports so the selection logic is unit-testable.
    """
    chain = parse_chain(chain_json)
    warnings: list[str] = []
    pool_category = opt.category_id(category)

    resolved_id: str | None = None
    if mode == opt.MODE_RANDOM:
        resolved_id = random_style_id(
            seed=seed,
            category=pool_category,
            tag_filter=tag_filter,
        )
    elif mode == opt.MODE_CYCLE:
        resolved_id = cycle_style_id(
            index=cycle_index,
            category=pool_category,
            tag_filter=tag_filter,
        )
    elif mode == opt.MODE_PICK and style_label and style_label != opt.NONE:
        record = get_style(style_label)
        if record is None:
            warnings.append(
                f"Style: no style named '{style_label}'. Nothing applied."
            )
        else:
            resolved_id = record["id"]

    if mode in (opt.MODE_RANDOM, opt.MODE_CYCLE) and resolved_id is None:
        warnings.append(
            f"Style: no style matches category '{category}' with tag_filter "
            f"'{tag_filter}'. Widen the filter or clear it."
        )

    if resolved_id:
        record = STYLES.get(resolved_id)
        if record:
            previous = chain.get("style")
            if previous is not None and previous.get("id") != record.get("id"):
                warnings.append(
                    f"Style: replacing '{previous.get('label', '?')}' with "
                    f"'{record['label']}'. Style is exclusive, so the "
                    f"downstream Style node wins."
                )
            chain["style"] = record

    if meta_overrides:
        for key, value in meta_overrides.items():
            if value:
                chain["_meta"][key] = value

    blocked = get_blocked_axes(chain.get("style"))
    kept, dropped = filter_modifiers(chain.get("modifiers", []), blocked)
    chain["modifiers"] = kept
    for mod in dropped:
        warnings.append(
            f"Style: '{chain['style'].get('label', '?')}' already fixes the "
            f"{mod.get('axis', '?')} axis, so the '{mod.get('label', '?')}' "
            f"modifier was dropped."
        )

    return chain, warnings


if _COMFY_AVAILABLE:

    class StylebookStyle(io.ComfyNode):
        """The primary style picker - the exclusive medium axis."""

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookStyle",
                display_name="Stylebook Style",
                category="conditioning/stylebook",
                description=(
                    "Pick, randomize or cycle a visual style across 12 "
                    "categories. Type your subject into user_prompt or "
                    "connect a text source; the style wraps around it. "
                    "Chain the style_chain output into Artist and Modifier."
                ),
                inputs=[
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        tooltip=(
                            "Optional. Connect an upstream Stylebook node's "
                            "style_chain output to build on it."
                        ),
                    ),
                    io.String.Input(
                        "user_prompt",
                        display_name="user_prompt",
                        multiline=True,
                        optional=True,
                        default="",
                        tooltip=(
                            "Your subject, for example 'a woman in a red coat "
                            "on a rainy street'. Type here or connect a text "
                            "source. Leave empty to output style text only."
                        ),
                    ),
                    io.Combo.Input(
                        "mode",
                        options=list(opt.MODES),
                        default=opt.DEFAULTS["mode"],
                        tooltip=(
                            "Random: a seeded pick from the filtered pool, "
                            "reproducible for a given seed. Pick: choose one "
                            "style yourself. Cycle: step through the pool by "
                            "index, which is how you sweep a whole category."
                        ),
                    ),
                    io.Combo.Input(
                        "style",
                        options=opt.style_options(),
                        default=opt.DEFAULTS["style"],
                        tooltip=(
                            "The style to apply in Pick mode. Use the Open "
                            "style gallery button to browse these with "
                            "preview images."
                        ),
                    ),
                    io.Combo.Input(
                        "category",
                        options=opt.category_options(),
                        default=opt.DEFAULTS["category"],
                        tooltip=(
                            "Narrows the pool that Random and Cycle draw "
                            "from. Has no effect in Pick mode."
                        ),
                    ),
                    io.String.Input(
                        "tag_filter",
                        default="",
                        tooltip=(
                            "Narrows Random and Cycle further. Comma-"
                            "separated, and every term must match, so "
                            "'ink, flat' finds styles that are both. Matches "
                            "against tags, prose, label and aliases."
                        ),
                    ),
                    io.Int.Input(
                        "seed",
                        default=0,
                        min=0,
                        max=0xFFFFFFFFFFFFFFFF,
                        control_after_generate=True,
                        tooltip=(
                            "Seed for Random mode. The same seed with the "
                            "same filter gives the same style, and keeps "
                            "giving it as the pack grows: seeds are scored "
                            "against each candidate rather than indexing a "
                            "list, so adding styles later re-rolls roughly "
                            "one seed in N instead of all of them."
                        ),
                    ),
                    io.Int.Input(
                        "cycle_index",
                        display_name="cycle index",
                        default=0,
                        min=0,
                        max=9999,
                        tooltip=(
                            "Which style to take in Cycle mode. 0 is the "
                            "first match and the index wraps at the end of "
                            "the pool. Unlike a seed, this is a position in "
                            "an alphabetical list, so adding styles to the "
                            "pack shifts what a given index returns. Use "
                            "Cycle to sweep, and Random to reproduce."
                        ),
                    ),
                    io.Combo.Input(
                        "format",
                        options=list(opt.FORMATS),
                        default=opt.DEFAULTS["format"],
                        tooltip=(
                            "How the style is written. prose is a plain "
                            "sentence describing the look. tags is a "
                            "comma-separated keyword list. If your model "
                            "responds better to keyword lists than to "
                            "sentences, choose tags. Every style ships both, "
                            "so switching costs nothing."
                        ),
                    ),
                    io.Combo.Input(
                        "strength",
                        options=list(opt.STRENGTHS),
                        default=opt.DEFAULTS["strength"],
                        tooltip=(
                            "How much style text to emit. subtle keeps only "
                            "the defining phrase, so your subject dominates. "
                            "normal is the full description. strong repeats "
                            "the defining term so the style pushes harder."
                        ),
                    ),
                    io.Combo.Input(
                        "placement",
                        options=list(opt.PLACEMENTS),
                        default=opt.DEFAULTS["placement"],
                        tooltip=(
                            "Where the style sits relative to your subject. "
                            "append puts your subject first and introduces "
                            "the style after it as a rendering instruction, "
                            "which is what you want with prose: a model "
                            "reading a sentence follows that sentence's "
                            "subject. prepend leads with the style, which is "
                            "what you want with tags, because a keyword list "
                            "weights its leading terms most."
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
            # Always re-execute: seed advances via control_after_generate.
            return float("nan")

        @classmethod
        def execute(
            cls,
            style_chain: str = "",
            user_prompt: str = "",
            mode: str = opt.DEFAULTS["mode"],
            style: str = opt.DEFAULTS["style"],
            category: str = opt.DEFAULTS["category"],
            tag_filter: str = "",
            seed: int = 0,
            cycle_index: int = 0,
            format: str = opt.DEFAULTS["format"],
            strength: str = opt.DEFAULTS["strength"],
            placement: str = opt.DEFAULTS["placement"],
        ) -> io.NodeOutput:
            meta_overrides = {
                "format": format,
                "strength": strength,
                "placement": placement,
            }

            chain, warnings = build_style_chain(
                chain_json=style_chain,
                style_label=style,
                mode=mode,
                category=category,
                tag_filter=tag_filter,
                seed=seed,
                cycle_index=cycle_index,
                meta_overrides=meta_overrides,
            )

            if user_prompt.strip():
                chain["_meta"]["user_prompt"] = user_prompt.strip()

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
            send_resolved_event(
                cls.hidden.unique_id,
                prompt,
                style=(chain.get("style") or {}).get("label"),
            )
            return io.NodeOutput(prompt, render_negative(chain), dump_chain(chain))
