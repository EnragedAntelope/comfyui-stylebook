"""HTTP-level test for ``/stylebook/user_data``.

``routes.py`` imports ``aiohttp`` and ComfyUI's ``server`` at module load,
and neither is a dependency of this pack -- that is why the payload logic
lives in ``user_data_payload.py``, which ``test_user_data.py`` covers on
its own. What stayed untested until now was the wiring this file adds:
that a GET handler actually gets registered at the right path and returns
the payload as JSON.

``routes.py`` addresses its sibling data modules relatively
(``from ..data.styles import ...``), exactly as the pack root does when
ComfyUI loads it. So the test imports it the same way: inside a synthetic
parent package whose ``__path__`` points at the repo root. That exercises
the real import shape rather than a test-only absolute fallback, and it
means the ``..data`` modules resolve fresh under the patched environment.

Neither stub pretends to be aiohttp beyond what routes.py touches. The
route table records its registrations instead of serving anything; the
response stand-in just captures what ``json_response`` was handed. If
routes.py ever grows a second endpoint or starts reading the request,
these stubs fail loudly rather than silently passing.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Synthetic top-level package name for the pack under test.
PKG = "_stylebook_under_test"


class _FakeRouteTable:
    """Stands in for aiohttp.web.RouteTableDef: records registrations."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, str, object]] = []

    def get(self, path: str):
        def register(handler):
            self.routes.append(("GET", path, handler))
            return handler

        return register


class _FakeJsonResponse:
    def __init__(self, payload: dict) -> None:
        self.status = 200
        self.body = payload


@contextmanager
def _stubbed_aiohttp():
    route_table = _FakeRouteTable()

    web = types.SimpleNamespace(
        RouteTableDef=_FakeRouteTable,
        Request=type("Request", (), {}),
        json_response=lambda payload: _FakeJsonResponse(payload),
    )
    server_module = types.SimpleNamespace(
        PromptServer=types.SimpleNamespace(
            instance=types.SimpleNamespace(routes=route_table),
        ),
    )

    pkg = types.ModuleType(PKG)
    pkg.__path__ = [str(ROOT)]
    created = [PKG]
    saved_pkg = sys.modules.get(PKG)
    sys.modules[PKG] = pkg

    with mock.patch.dict(
        sys.modules,
        {"aiohttp": mock.Mock(web=web), "server": server_module},
    ):
        try:
            yield route_table, importlib.import_module(
                f"{PKG}.stylebook_nodes.routes"
            )
        finally:
            # Drop everything the synthetic import created, including the
            # ..data modules it pulled in under this namespace.
            for name in list(sys.modules):
                if name == PKG or name.startswith(f"{PKG}."):
                    del sys.modules[name]
                    created.append(name)
            if saved_pkg is not None:
                sys.modules[PKG] = saved_pkg


class UserDataRouteTests(unittest.TestCase):
    """The route registers once, at the documented path, and serves JSON."""

    def test_route_registers_and_serves_payload(self):
        # A maintainer's local user_styles.json must not decide what this
        # asserts; build scripts set the same guard for the same reason.
        env = {k: v for k, v in os.environ.items()
               if k != "STYLEBOOK_USER_STYLES"}
        env["STYLEBOOK_IGNORE_USER_STYLES"] = "1"
        with mock.patch.dict(os.environ, env, clear=True):
            with _stubbed_aiohttp() as (route_table, routes_module):

                registered = [
                    (method, path, handler)
                    for method, path, handler in route_table.routes
                    if path == "/stylebook/user_data"
                ]
                self.assertEqual(len(registered), 1)
                method, _, handler = registered[0]
                self.assertEqual(method, "GET")

                response = asyncio.run(handler(mock.Mock()))
                self.assertEqual(response.status, 200)

                # Expected payload built from the SAME modules the handler
                # closed over -- the ones imported under the synthetic
                # package -- so the assertion cannot drift from what the
                # route actually read.
                data_styles = importlib.import_module(f"{PKG}.data.styles")
                data_artists = importlib.import_module(f"{PKG}.data.artists")
                data_modifiers = importlib.import_module(
                    f"{PKG}.data.modifiers"
                )
                data_user = importlib.import_module(f"{PKG}.data.user_data")
                payload_mod = importlib.import_module(
                    f"{PKG}.stylebook_nodes.user_data_payload"
                )
                expected = payload_mod.build_user_data_payload(
                    styles=data_styles.STYLES,
                    artists=data_artists.ARTISTS,
                    modifiers=data_modifiers.MODIFIERS,
                    added_styles=data_user.USER_ADDED_STYLES,
                    added_artists=data_user.USER_ADDED_ARTISTS,
                    added_modifiers=data_user.USER_ADDED_MODIFIERS,
                )
                self.assertEqual(response.body, expected)
                # The three keys are the contract the gallery tab reads.
                self.assertEqual(set(expected), {"styles", "artists",
                                                 "modifiers"})
                json.dumps(response.body)  # must stay JSON-serialisable
                self.assertIsNotNone(routes_module)


if __name__ == "__main__":
    unittest.main()
