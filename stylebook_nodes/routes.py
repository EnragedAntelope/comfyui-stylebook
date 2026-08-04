"""A read-only HTTP route exposing what a local user_styles.json added.

Registered onto the shared PromptServer instance's routes at import time --
the standard way a ComfyUI custom node pack adds an endpoint. Imported from
``__init__.py`` inside ``try/except ImportError`` so the pack, and the test
suite, still load fine without ``server``/``aiohttp`` present.

No parameters and no filesystem access at request time: this serialises
records already resident in process memory from the merge that ran at
import time (see ``data/user_data.py``), so there is no path-traversal or
injection surface to worry about. The payload shape itself lives in
``user_data_payload.py``, which has no ComfyUI import and is what
``tests/test_user_data.py`` actually exercises.
"""

from __future__ import annotations

from aiohttp import web
from server import PromptServer

from ..data.artists import ARTISTS
from ..data.modifiers import MODIFIERS
from ..data.styles import STYLES
from ..data.user_data import (
    USER_ADDED_ARTISTS, USER_ADDED_MODIFIERS, USER_ADDED_STYLES,
)
from .user_data_payload import build_user_data_payload


@PromptServer.instance.routes.get("/stylebook/user_data")
async def get_user_data(request: web.Request) -> web.Response:
    """The gallery's "Yours" tab data. See ``build_user_data_payload``."""
    return web.json_response(build_user_data_payload(
        styles=STYLES,
        artists=ARTISTS,
        modifiers=MODIFIERS,
        added_styles=USER_ADDED_STYLES,
        added_artists=USER_ADDED_ARTISTS,
        added_modifiers=USER_ADDED_MODIFIERS,
    ))
