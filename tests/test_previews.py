"""Contract tests for the preview pipeline that need no GPU.

``scripts/build_previews.py`` is the only thing that renders, but three of
its decisions are load-bearing outside itself: which modifier axes get
tiles (mirrored in the frontend), what a modifier's synthetic render
record looks like, and the fact that adding modifier tiles must not have
invalidated the 600-plus style tiles already in the manifest.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

import build_previews  # noqa: E402


class PreviewedAxesTests(unittest.TestCase):
    """Every axis gets tiles, and that is now an equality rather than a
    mirror.

    Until 0.15.0 this class bound a *list* in ``build_previews`` to a
    matching list in ``js/stylebook_gallery.js``, because three axes had
    tiles and three did not. Both lists are gone: the frontend no longer
    needs to know which axes have pictures, since all of them do. What is
    left is the stronger statement -- adding a seventh axis without
    rendering it fails here, instead of silently shipping a picture-less
    tab and the per-axis layout switch that used to paper over one.
    """

    def test_every_axis_gets_preview_tiles(self):
        from data.modifiers import AXES

        self.assertEqual(build_previews.PREVIEW_AXES, tuple(AXES))

    def test_the_frontend_no_longer_declares_its_own_axis_list(self):
        # A leftover PREVIEWED_AXES would be a second source of truth that
        # nothing keeps current -- worse than the mirror it replaced.
        source = (ROOT / "js" / "stylebook_gallery.js").read_text(
            encoding="utf-8"
        )
        self.assertIsNone(
            re.search(r"const PREVIEWED_AXES\b", source),
            "js/stylebook_gallery.js still declares PREVIEWED_AXES; every "
            "axis has tiles, so the frontend must not branch on the axis",
        )

    def test_the_reference_page_needs_no_axis_list_either(self):
        import build_reference_pages

        payload = build_reference_pages._modifiers_payload()
        self.assertNotIn(
            "previewAxes",
            payload,
            "the modifier page must not carry a previewAxes list: every "
            "entry attempts a sprite and degrades to text if it has none",
        )
        self.assertEqual(payload["baselineId"], build_previews.BASELINE_ID)


class ModifierRecordTests(unittest.TestCase):
    """The synthetic record handed to the renderer."""

    def test_a_modifier_record_is_namespaced_away_from_style_ids(self):
        from data.styles import STYLES

        for mid, record in build_previews.modifier_targets():
            self.assertTrue(record["id"].startswith("mod/"), record["id"])
            self.assertNotIn(record["id"], STYLES)

    def test_every_previewed_modifier_has_exactly_one_target(self):
        from data.modifiers import MODIFIERS_BY_AXIS

        expected = 1  # the baseline
        for axis in build_previews.PREVIEW_AXES:
            expected += len(MODIFIERS_BY_AXIS.get(axis, []))
        targets = build_previews.modifier_targets()
        self.assertEqual(len(targets), expected)
        self.assertEqual(len(dict(targets)), expected, "duplicate target id")

    def test_the_baseline_carries_the_base_style_and_no_modifier(self):
        record = build_previews.baseline_record()
        self.assertEqual(record["prose"], build_previews.MODIFIER_BASE_STYLE)
        self.assertEqual(record["subject"], build_previews.MODIFIER_SUBJECT)
        # It must differ from every real modifier tile, or the "what is
        # this a deviation from" tile is a duplicate of one of them.
        others = {
            build_previews.tile_hash(rec, "model")
            for mid, rec in build_previews.modifier_targets()
            if mid != build_previews.BASELINE_ID
        }
        self.assertNotIn(build_previews.tile_hash(record, "model"), others)

    def test_a_modifier_tile_shows_the_base_style_then_the_modifier(self):
        from data.modifiers import MODIFIERS, MODIFIERS_BY_AXIS

        mid = MODIFIERS_BY_AXIS[build_previews.PREVIEW_AXES[0]][0]
        record = build_previews.modifier_record(mid, MODIFIERS[mid])
        self.assertTrue(
            record["prose"].startswith(build_previews.MODIFIER_BASE_STYLE)
        )
        self.assertIn(MODIFIERS[mid]["prose"], record["prose"])

    def test_a_style_record_still_resolves_its_subject_the_old_way(self):
        """The subject override exists only for synthetic records; a real
        style must be unaffected, or every tile in the pack re-renders."""
        from data.styles import STYLES

        for sid, rec in STYLES.items():
            self.assertNotIn("subject", rec, sid)


class ManifestCompatibilityTests(unittest.TestCase):
    """Adding modifier tiles must not have re-rendered the pack.

    ``load_manifest()`` throws away a manifest whose ``version`` it does
    not recognise. Bumping it for the new section would have discarded
    every style tile hash and quietly queued 600-plus renders.
    """

    def test_the_committed_manifest_is_still_readable(self):
        raw = json.loads(
            build_previews.MANIFEST.read_text(encoding="utf-8")
        )
        self.assertEqual(raw.get("version"), build_previews.MANIFEST_VERSION)
        self.assertTrue(build_previews.load_manifest().get("tiles"))

    def test_an_id_shared_by_a_style_and_a_modifier_cannot_collide(self):
        """`chiaroscuro` is both a style id and a lighting modifier id.

        That is allowed, and it is exactly why the two live in separate
        manifest sections and separate source directories. What must never
        happen is one render overwriting the other's PNG, or one atlas
        entry shadowing the other's.
        """
        from data.modifiers import MODIFIERS
        from data.styles import STYLES

        shared = set(STYLES) & set(MODIFIERS)
        self.assertTrue(shared, "expected at least one shared id to test with")
        for rid in shared:
            style_png = build_previews.SRC_DIR / f"{rid}.png"
            mod_png = build_previews.MOD_SRC_DIR / f"{rid}.png"
            self.assertNotEqual(style_png, mod_png)
        # And the two sections are addressed separately in the manifest.
        manifest = build_previews.load_manifest()
        self.assertIsNot(
            manifest.get("tiles"), manifest.get("modifier_tiles")
        )


if __name__ == "__main__":
    unittest.main()
