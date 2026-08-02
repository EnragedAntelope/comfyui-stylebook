"""comfyui-stylebook — V3 custom node pack entrypoint.

Exposes four nodes:

* ``StylebookStyle`` — the exclusive medium axis. Pick, randomize,
  cycle, or batch-sheet a visual style from 12 categories.
* ``StylebookArtist`` — additive, chainable artist selection. Stack
  multiple to blend influences.
* ``StylebookModifier`` — additive, one per sub-axis (lighting,
  color_grade, era, finish, mood).
* ``StylebookBlend`` — blend two styles at a controllable ratio.

Discovery uses the ComfyUI V3 ``comfy_entrypoint`` mechanism. Frontend
widgets live in ``./js`` and are served via ``WEB_DIRECTORY``.
"""

from comfy_api.latest import ComfyExtension, io

# Package-relative inside ComfyUI; absolute fallback for tests.
try:
    from .nodes.stylebook_style import StylebookStyle
    from .nodes.stylebook_artist import StylebookArtist
    from .nodes.stylebook_modifier import StylebookModifier
    from .nodes.stylebook_blend import StylebookBlend
except ImportError:  # pragma: no cover
    from nodes.stylebook_style import StylebookStyle
    from nodes.stylebook_artist import StylebookArtist
    from nodes.stylebook_modifier import StylebookModifier
    from nodes.stylebook_blend import StylebookBlend

#: Tells ComfyUI where to find this pack's frontend JavaScript.
WEB_DIRECTORY = "./js"

__all__ = ["comfy_entrypoint", "WEB_DIRECTORY"]


class StylebookExtension(ComfyExtension):
    """Registers the Stylebook node pack with ComfyUI."""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [StylebookStyle, StylebookArtist, StylebookModifier, StylebookBlend]


async def comfy_entrypoint() -> StylebookExtension:
    return StylebookExtension()
