"""The ordering rule, and the doc claims that depend on counting the data.

Every case here is a regression: each one shipped, visibly, before
``data/ordering.py`` existed.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

# A maintainer's own user_styles.json must not reach these assertions: it
# would inflate the counts the doc guard compares against and mask real
# drift. Set before `data` is imported, since data/user_data.py reads it
# once at merge time -- same reason scripts/generate_js_data.py does it.
os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

from data.artists import ARTISTS  # noqa: E402
from data.ordering import label_sort_key  # noqa: E402
from data.styles import STYLES  # noqa: E402
from stylebook_nodes.schema_options import (  # noqa: E402
    NONE,
    OFF,
    artist_options,
    modifier_options,
    style_options,
)

ROOT = Path(__file__).resolve().parents[1]


class LabelSortKeyTests(unittest.TestCase):
    """The rule itself, independent of any option list."""

    def test_accents_rank_with_their_unaccented_letter(self):
        # É is U+00C9, which a code-point sort puts after every ASCII
        # letter -- the reason "Élisabeth Vigée Le Brun" was the last
        # entry in the artist dropdown.
        names = ["Zorach", "Élisabeth Vigée Le Brun", "Anguissola"]
        self.assertEqual(
            sorted(names, key=label_sort_key),
            ["Anguissola", "Élisabeth Vigée Le Brun", "Zorach"],
        )

    def test_digit_runs_compare_as_numbers(self):
        names = ["16-Bit Pixel Art", "8-Bit Pixel Art", "90s Cel Anime", "35mm"]
        self.assertEqual(
            sorted(names, key=label_sort_key),
            ["8-Bit Pixel Art", "16-Bit Pixel Art", "35mm", "90s Cel Anime"],
        )

    def test_digits_rank_before_letters(self):
        self.assertLess(label_sort_key("3D Matte Painting"),
                        label_sort_key("Abstract Expressionism"))

    def test_case_is_ignored(self):
        names = ["banana", "Apple", "Cherry"]
        self.assertEqual(sorted(names, key=label_sort_key),
                         ["Apple", "banana", "Cherry"])

    def test_labels_that_fold_alike_still_order_deterministically(self):
        # "Naive Art" and "Naïve Art" fold to the same key. Without the
        # raw-label tiebreak the result would depend on input order.
        pair = ["Naïve Art", "Naive Art"]
        self.assertEqual(sorted(pair, key=label_sort_key),
                         sorted(list(reversed(pair)), key=label_sort_key))

    def test_key_never_compares_int_against_str(self):
        # Digit and text runs are both 3-tuples for this reason; mixing
        # bare ints and strs would raise rather than sort oddly.
        sorted(("3D", "Alpha", "16-Bit", "9 Lives"), key=label_sort_key)


class StyleOptionOrderTests(unittest.TestCase):

    def setUp(self):
        self.options = style_options()

    def test_sentinel_stays_first(self):
        self.assertEqual(self.options[0], NONE)

    def test_dropdown_actually_applies_the_rule(self):
        body = self.options[1:]
        self.assertEqual(body, sorted(body, key=label_sort_key))

    def test_numeric_labels_read_naturally(self):
        numeric = [label for label in self.options if label[:1].isdigit()]
        self.assertEqual(numeric, [
            "1-Bit Monochrome",
            "3D Matte Painting",
            "8-Bit Pixel Art",
            "16-Bit Pixel Art",
            "35mm Slide Mount",
            "90s Cel Anime",
        ])

    def test_accented_style_sits_where_a_reader_expects(self):
        index = self.options.index("Naïve Art")
        self.assertEqual(self.options[index - 1], "Nabis")
        self.assertEqual(self.options[index + 1], "Naoki Urasawa (Monster)")


class ArtistOptionOrderTests(unittest.TestCase):

    def setUp(self):
        self.options = artist_options()

    def test_sentinel_stays_first(self):
        self.assertEqual(self.options[0], NONE)

    def test_dropdown_actually_applies_the_rule(self):
        body = self.options[1:]
        self.assertEqual(body, sorted(body, key=label_sort_key))

    def test_accented_artist_is_not_stranded_at_the_end(self):
        # The whole point. This name used to sort after "Zhang Xiaogang".
        self.assertNotEqual(self.options[-1], "Élisabeth Vigée Le Brun")
        index = self.options.index("Élisabeth Vigée Le Brun")
        self.assertTrue(
            self.options[index - 1].lower().startswith("el"),
            f"expected an E-name before it, got {self.options[index - 1]!r}",
        )


class ModifierOrderTests(unittest.TestCase):
    """The one deliberate exemption."""

    def test_era_axis_stays_chronological(self):
        era = modifier_options("era")
        self.assertEqual(era[0], OFF)
        body = era[1:]
        self.assertNotEqual(
            body, sorted(body, key=label_sort_key),
            "the era axis is chronological on purpose; sorting it would "
            "drag every decade to the top of the list",
        )


class DocCountClaimTests(unittest.TestCase):
    """Every "N+" claim in a shipped doc must still be true.

    Truth only -- there is deliberately no upper bound. A claim of "450+"
    against 600 styles is stale, not broken, and an upper bound would turn
    every content addition into a doc chore. This catches the case that
    actually matters: a claim that has become a lie.
    """

    CLAIM = re.compile(r"(\d+)\+\s*(?:visual\s+)?(styles|artists)", re.IGNORECASE)

    FILES = ("README.md", "AGENTS.md", "pyproject.toml")

    def test_claims_are_still_true(self):
        actual = {"styles": len(STYLES), "artists": len(ARTISTS)}
        found = 0
        for name in self.FILES:
            text = (ROOT / name).read_text(encoding="utf-8")
            for claimed, noun in self.CLAIM.findall(text):
                found += 1
                self.assertLessEqual(
                    int(claimed), actual[noun.lower()],
                    f"{name} claims {claimed}+ {noun.lower()} but the pack "
                    f"ships {actual[noun.lower()]}",
                )
        self.assertGreater(found, 0, "no count claims found -- has the regex rotted?")


if __name__ == "__main__":
    unittest.main()
