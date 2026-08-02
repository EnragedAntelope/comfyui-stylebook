"""Unit tests for the Stylebook chain engine.

Pure-stdlib ``unittest`` so it runs without ComfyUI installed:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stylebook_nodes.stylebook_core import (
    parse_chain, dump_chain, merge_chain, resolve_meta,
    render_prompt, render_negative, get_blocked_axes,
    filter_modifiers, EMPTY_CHAIN, seeded_rng,
)
from stylebook_nodes.stylebook_style import build_style_chain
from tests.validate_data import validate


class DataLayerTests(unittest.TestCase):
    def test_data_layer_valid(self):
        self.assertEqual(validate(), [])


class ParseChainTests(unittest.TestCase):
    def test_empty_string_returns_empty_chain(self):
        chain = parse_chain("")
        self.assertEqual(chain, json.loads(EMPTY_CHAIN))

    def test_none_returns_empty_chain(self):
        chain = parse_chain(None)  # type: ignore[arg-type]
        self.assertEqual(chain, json.loads(EMPTY_CHAIN))

    def test_invalid_json_returns_empty_chain(self):
        chain = parse_chain("not json")
        self.assertEqual(chain, json.loads(EMPTY_CHAIN))

    def test_valid_chain_preserved(self):
        chain = parse_chain('{"_meta":{"format":"tags"},"style":null,"modifiers":[],"artists":[]}')
        self.assertEqual(chain["_meta"]["format"], "tags")

    def test_missing_keys_filled(self):
        chain = parse_chain('{"_meta":{}}')
        self.assertIn("style", chain)
        self.assertIn("modifiers", chain)
        self.assertIn("artists", chain)


class MergeChainTests(unittest.TestCase):
    def test_downstream_wins(self):
        upstream = json.loads('{"_meta":{"format":"tags"},"style":{"id":"a"},"modifiers":[],"artists":[]}')
        downstream = json.loads('{"_meta":{"format":"prose"},"style":{"id":"b"},"modifiers":[],"artists":[]}')
        merged = merge_chain(upstream, downstream)
        self.assertEqual(merged["_meta"]["format"], "prose")
        self.assertEqual(merged["style"]["id"], "b")

    def test_upstream_preserved_when_downstream_null(self):
        upstream = json.loads('{"_meta":{"format":"tags"},"style":{"id":"a"},"modifiers":[],"artists":[]}')
        downstream = json.loads('{"_meta":{},"style":null,"modifiers":[],"artists":[]}')
        merged = merge_chain(upstream, downstream)
        self.assertEqual(merged["style"]["id"], "a")

    def test_modifiers_concatenated(self):
        upstream = json.loads('{"_meta":{},"style":null,"modifiers":[{"axis":"lighting","id":"a"}],"artists":[]}')
        downstream = json.loads('{"_meta":{},"style":null,"modifiers":[{"axis":"era","id":"b"}],"artists":[]}')
        merged = merge_chain(upstream, downstream)
        self.assertEqual(len(merged["modifiers"]), 2)

    def test_artists_appended(self):
        upstream = json.loads('{"_meta":{},"style":null,"modifiers":[],"artists":[{"label":"A"}]}')
        downstream = json.loads('{"_meta":{},"style":null,"modifiers":[],"artists":[{"label":"B"}]}')
        merged = merge_chain(upstream, downstream)
        self.assertEqual(len(merged["artists"]), 2)
        self.assertEqual(merged["artists"][0]["label"], "A")
        self.assertEqual(merged["artists"][1]["label"], "B")


class ResolveMetaTests(unittest.TestCase):
    def test_inherit_falls_back_to_defaults(self):
        chain = json.loads('{"_meta":{},"style":null,"modifiers":[],"artists":[]}')
        meta = resolve_meta(chain)
        self.assertEqual(meta["format"], "auto")
        self.assertEqual(meta["placement"], "prepend")

    def test_explicit_values_preserved(self):
        chain = json.loads('{"_meta":{"format":"tags","placement":"append"},"style":null,"modifiers":[],"artists":[]}')
        meta = resolve_meta(chain)
        self.assertEqual(meta["format"], "tags")
        self.assertEqual(meta["placement"], "append")


class RenderPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = {"format": "tags", "placement": "prepend", "strength": "normal",
                    "artist_detail": "full", "template": ""}

    def test_no_style_no_modifiers_returns_user_prompt(self):
        chain = json.loads(EMPTY_CHAIN)
        result = render_prompt(chain, self.meta, "a cat")
        self.assertEqual(result, "a cat")

    def test_style_tags_prepended(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"id": "test", "label": "Test", "tags": "test style, tag words"}
        result = render_prompt(chain, self.meta, "a cat")
        self.assertIn("test style", result)
        self.assertIn("a cat", result)
        self.assertTrue(result.startswith("test style"))

    def test_prose_format_renders_prose(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"id": "test", "label": "Test", "tags": "t1",
                          "prose": "A test rendering with enough descriptive words."}
        meta = dict(self.meta, format="prose")
        result = render_prompt(chain, meta, "a cat")
        self.assertIn("test rendering", result.lower())

    def test_negative_rendered(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"id": "test", "label": "Test", "tags": "test",
                          "negative": "bad stuff, noise"}
        result = render_negative(chain)
        self.assertIn("bad stuff", result)


class BlockedAxesTests(unittest.TestCase):
    def test_empty_blocks(self):
        style = {"id": "test", "blocks": []}
        self.assertEqual(get_blocked_axes(style), set())

    def test_blocks_returned(self):
        style = {"id": "test", "blocks": ["color_grade"]}
        self.assertEqual(get_blocked_axes(style), {"color_grade"})

    def test_none_style(self):
        self.assertEqual(get_blocked_axes(None), set())

    def test_filter_modifiers_removes_blocked(self):
        modifiers = [
            {"axis": "lighting", "id": "a"},
            {"axis": "color_grade", "id": "b"},
        ]
        blocked = {"color_grade"}
        result = filter_modifiers(modifiers, blocked)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["axis"], "lighting")


class ReproducibilityTests(unittest.TestCase):
    def test_seeded_rng_consistent(self):
        rng1 = seeded_rng(42)
        rng2 = seeded_rng(42)
        self.assertEqual(rng1.random(), rng2.random())

    def test_same_seed_same_prompt(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"id": "test", "label": "Test", "tags": "test style words",
                          "prose": "A test rendering with enough description."}
        meta = {"format": "tags", "placement": "prepend", "strength": "normal",
                "artist_detail": "full", "template": ""}
        a = render_prompt(chain, meta, "cat")
        b = render_prompt(chain, meta, "cat")
        self.assertEqual(a, b)


class RoundTripTests(unittest.TestCase):
    def test_dump_parse_roundtrip(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["_meta"]["format"] = "tags"
        chain["style"] = {"id": "test", "label": "Test"}
        dumped = dump_chain(chain)
        re_parsed = parse_chain(dumped)
        self.assertEqual(re_parsed["_meta"]["format"], "tags")
        self.assertEqual(re_parsed["style"]["id"], "test")


class SchemaValidationTests(unittest.TestCase):
    """Verify node schemas match what ComfyUI's prompt validator checks.

    These catch the class of bug where a widget default or saved value
    is not in the options list, which fails prompt validation silently.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from comfy_api.latest import io  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("ComfyUI not available")
        from stylebook_nodes.stylebook_style import StylebookStyle
        from stylebook_nodes.stylebook_artist import StylebookArtist
        from stylebook_nodes.stylebook_blend import StylebookBlend
        cls.style_node = StylebookStyle
        cls.artist_node = StylebookArtist
        cls.modifier_node = StylebookModifier
        cls.blend_node = StylebookBlend

    def _get_schema_inputs(self, node_cls):
        schema = node_cls.define_schema()
        return {inp.id: inp for inp in schema.inputs}

    def test_style_node_style_dropdown_has_random(self):
        """'Random' must be in the style dropdown for saved workflow compat."""
        inputs = self._get_schema_inputs(self.style_node)
        style_input = inputs.get("style")
        self.assertIsNotNone(style_input, "style input missing")
        options = getattr(style_input, "options", None)
        if hasattr(options, "values"):
            options = options.values
        self.assertIn("Random", options,
                      "'Random' missing from style dropdown -- saved workflows will fail")

    def test_style_node_defaults_in_options(self):
        """Every combo widget default must be in its options list."""
        inputs = self._get_schema_inputs(self.style_node)
        combo_inputs = {name: inp for name, inp in inputs.items()
                        if hasattr(inp, "options")}
        for name, inp in combo_inputs.items():
            options = getattr(inp, "options", None)
            if hasattr(options, "values"):
                options = options.values
            if not options:
                continue
            default = getattr(inp, "default", None)
            if default is not None:
                self.assertIn(default, options,
                              f"style node '{name}' default '{default}' not in options")

    def test_artist_node_defaults_in_options(self):
        inputs = self._get_schema_inputs(self.artist_node)
        combo_inputs = {name: inp for name, inp in inputs.items()
                        if hasattr(inp, "options")}
        for name, inp in combo_inputs.items():
            options = getattr(inp, "options", None)
            if hasattr(options, "values"):
                options = options.values
            if not options:
                continue
            default = getattr(inp, "default", None)
            if default is not None:
                self.assertIn(default, options,
                              f"artist node '{name}' default '{default}' not in options")

    def test_modifier_node_defaults_in_options(self):
        inputs = self._get_schema_inputs(self.modifier_node)
        combo_inputs = {name: inp for name, inp in inputs.items()
                        if hasattr(inp, "options")}
        for name, inp in combo_inputs.items():
            options = getattr(inp, "options", None)
            if hasattr(options, "values"):
                options = options.values
            if not options:
                continue
            default = getattr(inp, "default", None)
            if default is not None:
                self.assertIn(default, options,
                              f"modifier node '{name}' default '{default}' not in options")

    def test_blend_node_defaults_in_options(self):
        inputs = self._get_schema_inputs(self.blend_node)
        combo_inputs = {name: inp for name, inp in inputs.items()
                        if hasattr(inp, "options")}
        for name, inp in combo_inputs.items():
            options = getattr(inp, "options", None)
            if hasattr(options, "values"):
                options = options.values
            if not options:
                continue
            default = getattr(inp, "default", None)
            if default is not None:
                self.assertIn(default, options,
                              f"blend node '{name}' default '{default}' not in options")


if __name__ == "__main__":
    unittest.main()
