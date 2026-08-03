"""StylebookArtist node - additive, chainable artist selection.

Each Artist node adds one artist to the chain. Chain several to stack
influences. Capped at five, with a warning past three.

The widget layout mirrors the Style node exactly: mode first, then the
picker, then the pool filters, then the seed. The two nodes do the same
job on different axes, so making them look different was a cost with no
benefit.
"""

from __future__ import annotations

try:
    from ..data.artists import ARTISTS, get_artist
    from . import schema_options as opt
    from .node_support import report, show_readout
    from .stylebook_core import (
        ARTIST_MAX, ARTIST_WARN_THRESHOLD, cycle_artist_id, dump_chain,
        parse_chain, random_artist_id, render_negative, render_prompt,
        resolve_meta,
    )
except ImportError:  # pragma: no cover - standalone/test context
    from data.artists import ARTISTS, get_artist
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.node_support import report, show_readout
    from stylebook_nodes.stylebook_core import (
        ARTIST_MAX, ARTIST_WARN_THRESHOLD, cycle_artist_id, dump_chain,
        parse_chain, random_artist_id, render_negative, render_prompt,
        resolve_meta,
    )

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


def add_artist(
    chain_json: str,
    artist_label: str,
    mode: str,
    category: str,
    tag_filter: str,
    seed: int,
    cycle_index: int,
    artist_detail: str,
) -> tuple[dict, list[str]]:
    """Add one artist to the chain and return ``(chain, warnings)``.

    Kept free of ComfyUI imports so the selection logic is unit-testable.
    """
    chain = parse_chain(chain_json)
    warnings: list[str] = []
    pool_category = opt.artist_category_id(category)

    record: dict | None = None
    if mode in (opt.MODE_RANDOM, opt.MODE_CYCLE):
        resolved_id = (
            random_artist_id(
                seed=seed, category=pool_category, tag_filter=tag_filter
            )
            if mode == opt.MODE_RANDOM
            else cycle_artist_id(
                index=cycle_index, category=pool_category, tag_filter=tag_filter
            )
        )
        record = ARTISTS.get(resolved_id) if resolved_id else None
        if record is None:
            warnings.append(
                f"Artist: no artist matches category '{category}' with "
                f"tag_filter '{tag_filter}'. Widen the filter or clear it."
            )
    elif mode == opt.MODE_PICK and artist_label and artist_label != opt.NONE:
        record = get_artist(artist_label)
        if record is None:
            warnings.append(
                f"Artist: no artist named '{artist_label}'. Nothing applied."
            )

    if record is not None:
        artists = chain.get("artists", [])
        if len(artists) >= ARTIST_MAX:
            warnings.append(
                f"Artist: the chain already holds {ARTIST_MAX} artists, which "
                f"is the maximum. '{record['label']}' was not added."
            )
        else:
            artists.append(record)
            chain["artists"] = artists
            if len(artists) > ARTIST_WARN_THRESHOLD:
                warnings.append(
                    f"Artist: {len(artists)} artists chained. Descriptors "
                    f"start blending into each other past "
                    f"{ARTIST_WARN_THRESHOLD}. Switch artist_detail to "
                    f"'Names + lead descriptor' to keep them distinct."
                )

    chain["_meta"]["artist_detail"] = opt.ARTIST_DETAIL_MAP.get(
        artist_detail, "full"
    )

    return chain, warnings


if _COMFY_AVAILABLE:

    class StylebookArtist(io.ComfyNode):
        """Layer one artist onto the style chain."""

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookArtist",
                display_name="Stylebook Artist",
                category="conditioning/stylebook",
                description=(
                    "Layer one artist onto the style chain. Chain several "
                    "Artist nodes to stack influences. Every artist carries "
                    "a written descriptor, so the look still lands on models "
                    "that do not recognise the name."
                ),
                inputs=[
                    io.Custom(opt.CHAIN_TYPE).Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        tooltip=(
                            "Connect the style_chain output of the Style "
                            "node, or of another Artist node to stack."
                        ),
                    ),
                    io.Combo.Input(
                        "mode",
                        options=list(opt.MODES),
                        default=opt.DEFAULTS["artist_mode"],
                        tooltip=(
                            "Random: a seeded pick from the filtered pool. "
                            "Pick: choose one artist yourself. Cycle: step "
                            "through the pool by index, which is how you "
                            "sweep a category one artist at a time."
                        ),
                    ),
                    io.Combo.Input(
                        "artist",
                        options=opt.artist_options(),
                        default=opt.DEFAULTS["artist"],
                        tooltip=(
                            "The artist to layer in, in Pick mode. Use the "
                            "Open artist reference button to search by name, "
                            "by movement, or by what the work looks like."
                        ),
                    ),
                    io.Combo.Input(
                        "category",
                        options=opt.artist_category_options(),
                        default=opt.DEFAULTS["artist_category"],
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
                            "'ink, japanese' finds artists who are both. "
                            "Matches the descriptor, name, aliases and "
                            "category."
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
                            "same filter gives the same artist, and keeps "
                            "giving it as the pack grows: seeds are scored "
                            "against each candidate rather than indexing a "
                            "list, so adding artists later re-rolls roughly "
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
                            "Which artist to take in Cycle mode. 0 is the "
                            "first match and the index wraps at the end of "
                            "the pool. Unlike a seed, this is a position in "
                            "an alphabetical list, so adding artists to the "
                            "pack shifts what a given index returns. Use "
                            "Cycle to sweep, and Random to reproduce."
                        ),
                    ),
                    io.Combo.Input(
                        "artist_detail",
                        options=list(opt.ARTIST_DETAILS),
                        default=opt.DEFAULTS["artist_detail"],
                        tooltip=(
                            "How every artist in the chain is written. "
                            "Name + descriptor names the artist and describes "
                            "their work, and is the safe default. Descriptor "
                            "only drops the name and keeps the description, "
                            "which is what you want when your model does not "
                            "recognise the name. Names + lead descriptor "
                            "keeps stacked artists from blurring together. "
                            "Names only is the most compact."
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
            mode: str = opt.DEFAULTS["artist_mode"],
            artist: str = opt.DEFAULTS["artist"],
            category: str = opt.DEFAULTS["artist_category"],
            tag_filter: str = "",
            seed: int = 0,
            cycle_index: int = 0,
            artist_detail: str = opt.DEFAULTS["artist_detail"],
        ) -> io.NodeOutput:
            chain, warnings = add_artist(
                chain_json=style_chain,
                artist_label=artist,
                mode=mode,
                category=category,
                tag_filter=tag_filter,
                seed=seed,
                cycle_index=cycle_index,
                artist_detail=artist_detail,
            )
            report(warnings)

            meta = resolve_meta(chain)
            prompt = render_prompt(
                chain, meta, chain["_meta"].get("user_prompt", "")
            )
            show_readout(cls.hidden.unique_id, prompt, warnings)
            return io.NodeOutput(prompt, render_negative(chain), dump_chain(chain))
