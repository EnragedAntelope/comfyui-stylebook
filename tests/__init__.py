"""comfyui-stylebook tests package.

Registers a stand-in for ``comfy_api.latest.io`` when the real package is not
importable, *before* any test module gets a chance to import
``stylebook_nodes.*``. That ordering matters: every node module does
``try: from comfy_api.latest import io / except ImportError`` at its own
top level and only defines its node class when that import succeeds. Once a
module has executed once, Python caches it in ``sys.modules`` and will not
re-run its top level, so registering the stub any later than this — say,
inside ``tests/test_schemas.py`` itself, after ``tests/test_engine.py`` has
already imported ``stylebook_nodes.stylebook_style`` and found no
``comfy_api`` on the path — would be too late to make the node classes exist
in that already-cached module.

This only actually runs first if ``tests`` is imported as a genuine
subpackage of the repo root, i.e. ``unittest discover`` is invoked with
``-t .`` (see the exact command in every test-running script and workflow in
this repo). Without ``-t .``, ``unittest discover -s tests`` treats ``tests``
as an implicit top-level directory and imports its ``test_*.py`` files as
bare top-level modules (``test_engine``, not ``tests.test_engine``) without
running this ``__init__.py`` first at all -- confirmed empirically, not
merely inferred from the docs. Python's import system, in contrast,
*guarantees* a package's ``__init__.py`` runs before any of its submodules
whenever the dotted form is used, which ``-t .`` is what forces.

Real-first: on a machine with ComfyUI installed (this repo's own dev
machine), ``comfy_api.latest.io`` is genuinely importable and this stub is
never put on ``sys.path`` at all — every assertion downstream runs against
the real API. The stub exists only to cover a runner, such as CI, that has
neither.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import comfy_api.latest.io  # noqa: F401
except ImportError:
    _STUB_ROOT = Path(__file__).resolve().parent / "comfy_stub"
    if str(_STUB_ROOT) not in sys.path:
        sys.path.insert(0, str(_STUB_ROOT))
