"""StylebookArtist node — additive, chainable artist selection.

Each Artist node adds one artist to the chain. Chain multiple
to stack artists (Rembrandt × Picasso). Capped at 5, warns above 3.
"""

from __future__ import annotations

try:
    from ..data.artists import ARTISTS
    from .stylebook_core import parse_chain, dump_chain, merge_chain, resolve_meta, render_prompt, render_negative
except ImportError:  # pragma: no cover
    from data.artists import ARTISTS
    from stylebook_nodes.stylebook_core import parse_chain, dump_chain, merge_chain, resolve_meta, render_prompt, render_negative

try:
    from comfy_api.latest import io  # type: ignore[import-not-found]
    _COMFY_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _COMFY_AVAILABLE = False


#: Sentinel for the name_handling combo.
_NAME_HANDLING_FULL = "Name + descriptor"
_NAME_HANDLING_NAMES_LEAD = "Names + lead descriptor"
_NAME_HANDLING_NAMES_ONLY = "Names only"
_NAME_HANDLING_DESCRIPTOR_ONLY = "Descriptor only"

#: Map UI labels to chain meta values.
_NAME_HANDLING_MAP = {
    _NAME_HANDLING_FULL: "full",
    _NAME_HANDLING_NAMES_LEAD: "names_lead",
    _NAME_HANDLING_NAMES_ONLY: "names_only",
    _NAME_HANDLING_DESCRIPTOR_ONLY: "descriptor_only",
}

#: Artist sentinel.
_ARTIST_NONE = "None"
_ARTIST_RANDOM = "Random"

#: Max artists before hard cap.
_ARTIST_MAX = 5
_ARTIST_WARN = 3

#: Artist detail modes.
_ARTIST_FULL = "full"
_ARTIST_NAMES_ONLY = "names_only"
_ARTIST_DESCRIPTOR_ONLY = "descriptor_only"
_ARTIST_NAMES_LEAD = "names_lead"


def _artist_options() -> list[str]:
    names = sorted(a["label"] for a in ARTISTS.values())
    return [_ARTIST_RANDOM, _ARTIST_NONE] + names


if _COMFY_AVAILABLE:

    class StylebookArtist(io.ComfyNode):
        """Add an artist to the rendering chain.

        Each Artist node stacks one artist. Chain multiple to blend
        influences (e.g. Rembrandt x Picasso). Every artist carries a
        hand-written descriptor so the style reads on any model,
        even ones that don't know the name.
        """

        @classmethod
        def define_schema(cls) -> io.Schema:
            return io.Schema(
                node_id="StylebookArtist",
                display_name="Stylebook Artist",
                category="conditioning/stylebook",
                description="Layer one artist onto the style chain. Chain multiple Artist "
                            "nodes to stack influences. Every artist has a descriptor "
                            "that works even on models that don't know the name.",
                inputs=[
                    io.String.Input(
                        "style_chain",
                        display_name="style_chain",
                        optional=True,
                        default="{}",
                        tooltip="Connect an upstream Stylebook node's style_chain output.",
                    ),
                    io.Combo.Input(
                        "artist",
                        options=_artist_options(),
                        default=_ARTIST_RANDOM,
                        tooltip="The artist to layer in. 'Random' draws from the full pool.",
                    ),
                    io.Combo.Input(
                        "name_handling",
                        options=[
                            _NAME_HANDLING_FULL,
                            _NAME_HANDLING_NAMES_LEAD,
                            _NAME_HANDLING_NAMES_ONLY,
                            _NAME_HANDLING_DESCRIPTOR_ONLY,
                        ],
                        default=_NAME_HANDLING_FULL,
                        tooltip="How to render this artist. 'Name + descriptor' works on "
                                "all models. 'Descriptor only' is best for recaption models "
                                "(Flux, Z-Image, Krea) where artist names are stripped from "
                                "training data and have no effect.",
                    ),
                    io.Combo.Input(
                        "artist_detail",
                        options=["inherit", _NAME_HANDLING_FULL, _NAME_HANDLING_NAMES_LEAD, _NAME_HANDLING_NAMES_ONLY, _NAME_HANDLING_DESCRIPTOR_ONLY],
                        default="inherit",
                        tooltip="Override how ALL stacked artists are rendered. "
                                "'inherit' uses the upstream setting.",
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
            artist: str,
            name_handling: str,
            artist_detail: str,
        ) -> io.NodeOutput:
            chain = parse_chain(style_chain)
            warnings: list[str] = []

            # Determine effective name_handling mode.
            # artist_detail overrides name_handling when not "inherit".
            mode_key = artist_detail if artist_detail != "inherit" else name_handling
            mode = _NAME_HANDLING_MAP.get(mode_key, "full")

            # Apply artist_detail override to meta.
            meta_overrides: dict[str, str] = {}
            if artist_detail != "inherit":
                meta_overrides["artist_detail"] = _NAME_HANDLING_MAP.get(artist_detail, "full")

            # Find and add the artist.
            if artist and artist not in (_ARTIST_NONE, _ARTIST_RANDOM):
                artist_rec = ARTISTS.get(artist)
                if artist_rec is None:
                    # Try by label.
                    for aid, arec in ARTISTS.items():
                        if arec.get("label") == artist:
                            artist_rec = arec
                            break
                if artist_rec:
                    artists = chain.get("artists", [])
                    artists.append(artist_rec)
                    chain["artists"] = artists

                    n = len(artists)
                    if n >= _ARTIST_MAX:
                        warnings.append(
                            f"Artist node: {n} artists chained (max {_ARTIST_MAX}). "
                            f"'{artist_rec.get('label', artist)}' was dropped."
                        )
                        artists.pop()
                    elif n > _ARTIST_WARN:
                        warnings.append(
                            f"Artist node: {n} artists chained. "
                            f"Descriptors may get muddy above 3. "
                            f"Try 'Names + lead descriptor' mode."
                        )
                else:
                    warnings.append(f"Artist node: unknown artist '{artist}'.")

            # Apply meta.
            chain.setdefault("_meta", {})
            for k, v in meta_overrides.items():
                if v:
                    chain["_meta"][k] = v

            for w in warnings:
                print(f"[Stylebook] {w}")

            meta = resolve_meta(chain)
            prompt = render_prompt(chain, meta)
            negative = render_negative(chain)

            return io.NodeOutput(prompt, negative, dump_chain(chain))
