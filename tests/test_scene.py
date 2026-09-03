"""The `scene` field, and the two lists that must agree about it.

A style describes how an image is rendered. A handful are defined by
*where* the image is instead - Liminal Space without a transitional
interior is not liminal space - and those declare `scene`, which the
gallery turns into a badge so the user knows before rendering that their
subject is about to be relocated.

`scripts/build_previews.py` independently knows which styles are places,
because a preview of one has to render the place rather than the category's
stock person. Two lists that must stay in step, bound here.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from data.styles import STYLES  # noqa: E402


class SceneFieldTests(unittest.TestCase):
    def test_scene_is_a_short_lowercase_noun_phrase(self):
        """It is rendered as "Places your subject in <scene>"."""
        for sid, rec in STYLES.items():
            scene = rec.get("scene")
            if scene is None:
                continue
            with self.subTest(style=sid):
                self.assertIsInstance(scene, str)
                self.assertTrue(scene.strip(), "scene must not be blank")
                self.assertLessEqual(len(scene.split()), 12)
                self.assertFalse(
                    scene.endswith("."),
                    "scene is a phrase, not a sentence",
                )

    def test_some_styles_declare_a_scene(self):
        """A zero here means the field was dropped, not that the pack is clean."""
        declared = [sid for sid, rec in STYLES.items() if rec.get("scene")]
        self.assertGreater(len(declared), 10)

    def test_scene_is_the_exception(self):
        """Most styles must remain rendering-only.

        If this ever trips, the field has become a dumping ground and the
        badge has stopped carrying information.
        """
        declared = [sid for sid, rec in STYLES.items() if rec.get("scene")]
        self.assertLess(len(declared), len(STYLES) // 4)


class DepictsFieldTests(unittest.TestCase):
    """The `depicts` field, `scene`'s sibling.

    `scene` answers *where this style puts your subject*; `depicts`
    answers *what this style puts in the frame whatever your subject is*.
    Fashion Photography is not relocating you, but it is definitely
    dressing you. Same contract as `scene`, because it is the same kind of
    thing: a badge caption a human reads in a tooltip.
    """

    def test_depicts_is_a_short_lowercase_noun_phrase(self):
        """It is rendered as "Adds <depicts> to the frame"."""
        for sid, rec in STYLES.items():
            depicts = rec.get("depicts")
            if depicts is None:
                continue
            with self.subTest(style=sid):
                self.assertIsInstance(depicts, str)
                self.assertTrue(depicts.strip(), "depicts must not be blank")
                self.assertLessEqual(len(depicts.split()), 12)
                self.assertFalse(
                    depicts.endswith("."),
                    "depicts is a phrase, not a sentence",
                )

    def test_some_styles_declare_depicts(self):
        """A zero here means the field was dropped, not that the pack is clean."""
        declared = [sid for sid, rec in STYLES.items() if rec.get("depicts")]
        self.assertGreater(len(declared), 10)

    def test_depicts_is_the_exception(self):
        """Most styles must remain rendering-only.

        The failure mode this guards is specific: `depicts` is an escape
        from a hot validator rule, so the cheapest way to silence that
        rule is to declare the field instead of fixing the record. If this
        trips, the field has become a dumping ground and the badge has
        stopped carrying information.
        """
        declared = [sid for sid, rec in STYLES.items() if rec.get("depicts")]
        self.assertLess(len(declared), len(STYLES) // 8)

    def test_no_style_declares_an_empty_depicts(self):
        """A blank declaration must not buy an exemption.

        `_check_entity_content` tests `.strip()`, so `"depicts": ""` fails
        the rule rather than passing it. Asserted here too because the
        quiet version of this bug -- a declared-but-empty field that
        silences a check and renders no badge -- is invisible otherwise.
        """
        for sid, rec in STYLES.items():
            if "depicts" in rec:
                with self.subTest(style=sid):
                    self.assertTrue(rec["depicts"].strip())


class PreviewSubjectAgreementTests(unittest.TestCase):
    """Every place-style the preview builder knows about must declare `scene`.

    The builder's override table is what taught us this category of style
    exists at all; before `scene`, that knowledge lived in one comment in
    one build script and never reached the user.
    """

    def test_place_overrides_declare_scene(self):
        import build_previews

        # The overrides that exist because the *subject is a place*. The
        # rest of STYLE_SUBJECT is design objects and simulation set-ups,
        # where the category already tells the user what they are getting.
        place_styles = ("liminal_space", "googie", "metaphysical_art",
                        "vaporwave", "nabis", "intimism")

        for sid in place_styles:
            with self.subTest(style=sid):
                self.assertIn(
                    sid, build_previews.STYLE_SUBJECT,
                    "still expected to need a preview subject override",
                )
                self.assertTrue(
                    STYLES[sid].get("scene"),
                    f"{sid} renders a place in its preview but does not "
                    f"declare `scene`, so the gallery cannot warn the user",
                )


if __name__ == "__main__":
    unittest.main()
