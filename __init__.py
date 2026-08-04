"""comfyui-stylebook - V3 custom node pack entrypoint.

Five nodes:

* ``StylebookStyle`` - the exclusive medium axis, across 12 categories.
* ``StylebookArtist`` - additive and chainable. Stack several to blend
  influences.
* ``StylebookModifier`` - one modifier per axis (lighting, color_grade,
  era, finish, mood).
* ``StylebookBlend`` - blend two styles at a ratio.
* ``StylebookSheet`` - one subject rendered across many styles as a batch.

The first three share one widget layout: a ``mode`` of Pick, Random or
Cycle, then the picker, then the filters that narrow what Random and
Cycle draw from. They do the same job on different axes, so looking
different was a cost with no benefit.

They pass state along a ``style_chain`` socket carrying its own type,
``STYLEBOOK_CHAIN``. It used to be a STRING, which meant the ``prompt``
output connected happily to a chain input and then parsed as an empty
chain.

Discovery uses the ComfyUI V3 ``comfy_entrypoint`` mechanism. Frontend
assets live in ``./js`` and are served via ``WEB_DIRECTORY``.

Imports here are strictly package-relative. An earlier revision inserted
the pack root onto ``sys.path`` so that ``import data`` would resolve,
which put a module named ``data`` in the global namespace where any
other custom node pack doing the same thing would collide with it.
"""

from comfy_api.latest import ComfyExtension, io

from .stylebook_nodes.stylebook_artist import StylebookArtist
from .stylebook_nodes.stylebook_blend import StylebookBlend
from .stylebook_nodes.stylebook_modifier import StylebookModifier
from .stylebook_nodes.stylebook_sheet import StylebookSheet
from .stylebook_nodes.stylebook_style import StylebookStyle

try:
    from .stylebook_nodes import routes  # noqa: F401
except ImportError:  # pragma: no cover - no server/aiohttp in the test env
    pass

#: Where ComfyUI finds this pack's frontend assets.
WEB_DIRECTORY = "./js"

__all__ = ["comfy_entrypoint", "WEB_DIRECTORY"]


class StylebookExtension(ComfyExtension):
    """Registers the Stylebook node pack with ComfyUI."""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            StylebookStyle,
            StylebookArtist,
            StylebookModifier,
            StylebookBlend,
            StylebookSheet,
        ]


async def comfy_entrypoint() -> StylebookExtension:
    return StylebookExtension()
