"""Dump node widget fixtures for the jsdom frontend tests.

Writes ``tests/frontend/fixtures/nodes.json``: one entry per Stylebook node,
listing its widgets in the exact order ``schema_options.WIDGET_ORDER`` says
ComfyUI serialises them, each with a ``name``/``type``/``value`` and, for the
few widgets the frontend actually narrows or reads by name (``mode``,
``axis``, ``modifier``), a full ``options`` list. ``style`` and ``artist``
get their default and a count instead of all 400+/650+ labels, which would
make the fixture large and brittle against ordinary data growth.

This is what lets ``tests/frontend/*.test.mjs`` build LiteGraph-shaped fake
nodes (via ``fake_node.mjs``) from the real Python schema, so a Python
rename shows up as a fixture diff and, if ``--check`` is wired into CI (it
is), fails the build before it ever reaches a saved workflow.

Same generated-file contract as ``scripts/generate_js_data.py``: write in
full, never hand-edit, verify with ``--check``.

Usage:
    python scripts/dump_frontend_fixtures.py            # write
    python scripts/dump_frontend_fixtures.py --check    # verify (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A maintainer's own local user_styles.json must not change what ships in
# this fixture. Set before any node/data import below.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

# Real-first, stub-fallback: the node modules only define their classes
# (StylebookStyle etc.) when `from comfy_api.latest import io` succeeds. On
# a machine with ComfyUI installed it genuinely does; everywhere else this
# registers the same stand-in the test suite uses. See
# tests/comfy_stub/comfy_api/latest/io.py for why the stub's shape matters
# and tests/__init__.py for the same pattern applied to the test runner.
try:
    import comfy_api.latest.io  # noqa: F401
except ImportError:
    _STUB_ROOT = ROOT / "tests" / "comfy_stub"
    if str(_STUB_ROOT) not in sys.path:
        sys.path.insert(0, str(_STUB_ROOT))

TARGET = ROOT / "tests" / "frontend" / "fixtures" / "nodes.json"

#: Widgets the frontend narrows or reads by name and therefore needs a real
#: options list in the fixture (see js/stylebook_gallery.js: updateModeVisibility
#: reads `mode`; narrowModifierOptions reads `axis` and rewrites `modifier`).
_FULL_OPTIONS_WIDGETS = {"mode", "axis", "modifier"}

#: Widgets whose option list is large and irrelevant to the frontend logic
#: under test; emit only the default value and how many options exist.
_COUNT_ONLY_WIDGETS = {"style", "artist"}


def generate() -> dict:
    from stylebook_nodes import schema_options as opt
    from stylebook_nodes.stylebook_artist import StylebookArtist
    from stylebook_nodes.stylebook_blend import StylebookBlend
    from stylebook_nodes.stylebook_modifier import StylebookModifier
    from stylebook_nodes.stylebook_sheet import StylebookSheet
    from stylebook_nodes.stylebook_style import StylebookStyle

    nodes = {
        "StylebookStyle": StylebookStyle,
        "StylebookArtist": StylebookArtist,
        "StylebookModifier": StylebookModifier,
        "StylebookSheet": StylebookSheet,
        "StylebookBlend": StylebookBlend,
    }

    out: dict[str, object] = {
        "__generated__": "scripts/dump_frontend_fixtures.py -- do not edit by hand",
    }

    for node_id, node in nodes.items():
        schema = node.define_schema()
        inputs_by_id = {inp.id: inp for inp in schema.inputs}
        widgets = []
        for name in opt.WIDGET_ORDER.get(node_id, []):
            if name == "control_after_generate":
                widgets.append({
                    "name": name,
                    "type": "combo",
                    "value": "randomize",
                    "options": ["fixed", "increment", "decrement", "randomize"],
                })
                continue
            inp = inputs_by_id[name]
            entry: dict[str, object] = {
                "name": name,
                "type": type(inp).__qualname__.split(".")[0].lower(),
                "value": getattr(inp, "default", None),
            }
            if name in _COUNT_ONLY_WIDGETS:
                entry["optionCount"] = len(getattr(inp, "options", None) or [])
            elif name in _FULL_OPTIONS_WIDGETS or getattr(inp, "options", None):
                options = getattr(inp, "options", None)
                if options:
                    entry["options"] = list(options)
            widgets.append(entry)
        out[node_id] = widgets

    return out


def _dumps(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump frontend node fixtures.")
    parser.add_argument("--check", action="store_true",
                        help="Verify only; exit non-zero if stale.")
    args = parser.parse_args()

    expected = _dumps(generate())

    if args.check:
        if not TARGET.is_file():
            print(f"FAIL: {TARGET} does not exist. "
                  f"Run: python scripts/dump_frontend_fixtures.py")
            return 1
        if TARGET.read_text(encoding="utf-8") != expected:
            print("FAIL: frontend fixtures are stale. "
                  "Run: python scripts/dump_frontend_fixtures.py")
            return 1
        print("PASS: frontend fixtures are current.")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Written: {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
