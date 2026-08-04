"""Schema tests for the real (or stubbed) V3 node classes.

``tests/__init__.py`` registers a stand-in for ``comfy_api.latest.io`` before
this module is ever imported, if the real package is not on the path. See
that file for why the ordering matters. On a machine with ComfyUI installed
these assertions run against the genuine API; everywhere else, against the
stub in ``tests/comfy_stub/``.

This used to be ``NodeSchemaTests`` in ``test_engine.py``, gated by
``raise unittest.SkipTest("ComfyUI not installed")`` in its own
``setUpClass`` -- which meant it had never once run in CI, since CI has no
ComfyUI. Moving the stub-registration to package level removes the need for
that skip entirely.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stylebook_nodes import schema_options as opt  # noqa: E402
from stylebook_nodes.stylebook_artist import StylebookArtist  # noqa: E402
from stylebook_nodes.stylebook_blend import StylebookBlend  # noqa: E402
from stylebook_nodes.stylebook_modifier import StylebookModifier  # noqa: E402
from stylebook_nodes.stylebook_sheet import StylebookSheet  # noqa: E402
from stylebook_nodes.stylebook_style import StylebookStyle  # noqa: E402

NODES = [StylebookStyle, StylebookArtist, StylebookModifier,
         StylebookBlend, StylebookSheet]

#: Nodes that show a readout on their face and therefore must declare
#: io.Hidden.unique_id, the id send_progress_text/send_sync target.
READOUT_NODES = [StylebookStyle, StylebookArtist, StylebookModifier,
                  StylebookBlend, StylebookSheet]

#: Widgets whose DOM/multiline placement makes them sort after every plain
#: widget regardless of schema position -- see schema_options.WIDGET_ORDER.
_TRAILING_MULTILINE = {"user_prompt", "styles"}


class NodeSchemaTests(unittest.TestCase):
    """Structural assertions every node schema must satisfy."""

    def test_every_combo_default_is_in_its_options(self):
        for node in NODES:
            for inp in node.define_schema().inputs:
                options = getattr(inp, "options", None)
                if options is None:
                    continue
                values = getattr(options, "values", options)
                default = getattr(inp, "default", None)
                if values and default is not None:
                    self.assertIn(default, values,
                                  f"{node.__name__}.{inp.id} default not in options")

    def test_every_input_has_a_tooltip(self):
        for node in NODES:
            for inp in node.define_schema().inputs:
                self.assertTrue(getattr(inp, "tooltip", ""),
                                f"{node.__name__}.{inp.id} has no tooltip")

    def test_input_ids_are_unique_per_node(self):
        for node in NODES:
            ids = [inp.id for inp in node.define_schema().inputs]
            self.assertEqual(len(ids), len(set(ids)), f"{node.__name__} dup input")

    def test_node_ids_are_unique(self):
        ids = [n.define_schema().node_id for n in NODES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_readout_nodes_declare_hidden_unique_id(self):
        """A node that calls show_readout needs io.Hidden.unique_id declared,
        or PromptServer has no node id to attach the readout text to."""
        for node in READOUT_NODES:
            schema = node.define_schema()
            self.assertIn("UNIQUE_ID", [h.value for h in schema.hidden],
                          f"{node.__name__} does not declare Hidden.unique_id")


class WidgetOrderDerivationTests(unittest.TestCase):
    """schema_options.WIDGET_ORDER must still match the live schema.

    Two rules turn a schema's input list into serialised widget order (see
    the comment on WIDGET_ORDER): a seed with control_after_generate
    contributes two entries, and a handful of DOM-backed multiline widgets
    always sort last. This test derives an order from define_schema() under
    those two rules and checks it against the hand-verified constant, so a
    schema change that forgets to update WIDGET_ORDER fails here instead of
    silently drifting from what ComfyUI will actually serialize.
    """

    def _derive(self, node) -> list[str]:
        schema = node.define_schema()
        plain, trailing, seed_name = [], [], None
        for inp in schema.inputs:
            # Only WidgetInput subclasses (Combo/String/Int/Float) put an
            # entry in widgets_values. A socket-only Input, such as the
            # style_chain Custom() type, has no `default` attribute at all
            # in the real API -- that structural gap, not a name list, is
            # what distinguishes a widget from a link-only input here.
            if not hasattr(inp, "default"):
                continue
            if inp.id in _TRAILING_MULTILINE:
                trailing.append(inp.id)
            else:
                plain.append(inp.id)
                if getattr(inp, "control_after_generate", None):
                    seed_name = inp.id
        if seed_name:
            index = plain.index(seed_name)
            plain.insert(index + 1, "control_after_generate")
        return plain + trailing

    def test_widget_order_matches_define_schema(self):
        for node in NODES:
            name = node.define_schema().node_id
            expected = opt.WIDGET_ORDER.get(name)
            if expected is None:
                continue
            with self.subTest(name):
                self.assertEqual(self._derive(node), expected)


if __name__ == "__main__":
    unittest.main()
