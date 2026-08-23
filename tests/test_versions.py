"""The release stamps behind the gallery's "New" tab and newest-first sort.

`scripts/stamp_versions.py --check` is the CI gate; these are the
properties that gate depends on, plus the two places the stamp has to
agree with something outside `data/versions.py`.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("STYLEBOOK_IGNORE_USER_STYLES", "1")

from data.artists import ARTISTS  # noqa: E402
from data.modifiers import MODIFIERS  # noqa: E402
from data.styles import STYLES  # noqa: E402
from data.versions import ADDED_IN, RELEASES  # noqa: E402

SHIPPED = {"styles": STYLES, "artists": ARTISTS, "modifiers": MODIFIERS}


def _pyproject_version() -> str:
    match = re.search(
        r'(?m)^version\s*=\s*"([^"]+)"',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    return match.group(1) if match else ""


class ReleaseStampTests(unittest.TestCase):
    """Every entry knows which release it arrived in."""

    def test_every_shipped_entry_is_stamped(self):
        """An unstamped entry sorts as if it had always been there.

        That is the quiet failure this replaces: the "New" tab would
        simply not list a style somebody had just added, and nothing
        anywhere would say so.
        """
        for kind, collection in SHIPPED.items():
            missing = sorted(set(collection) - set(ADDED_IN[kind]))
            with self.subTest(kind):
                self.assertEqual(
                    missing, [],
                    "run: python scripts/stamp_versions.py --stamp",
                )

    def test_no_stamp_outlives_the_entry_it_names(self):
        for kind, collection in SHIPPED.items():
            stale = sorted(set(ADDED_IN[kind]) - set(collection))
            with self.subTest(kind):
                self.assertEqual(stale, [])

    def test_every_stamp_names_a_known_release(self):
        used = {version for kind in ADDED_IN for version in ADDED_IN[kind].values()}
        self.assertEqual(sorted(used - set(RELEASES)), [])

    def test_releases_are_unique_and_ordered_oldest_first(self):
        self.assertEqual(len(RELEASES), len(set(RELEASES)))
        # Position in RELEASES is what the gallery ranks on, so the order
        # is load-bearing: "0.10.0" sorts before "0.9.0" as a string, and
        # ranking on the list index is how that is sidestepped rather than
        # writing a semver comparator in JavaScript.
        as_tuples = [tuple(int(part) for part in v.split(".")) for v in RELEASES]
        self.assertEqual(as_tuples, sorted(as_tuples))

    def test_this_version_is_a_known_release(self):
        """A release that adds nothing still has to be listed once it is
        the current one, or the "New" tab would name a version the rank
        table has never heard of."""
        version = _pyproject_version()
        self.assertTrue(version, "no version in pyproject.toml")
        self.assertIn(version, RELEASES)

    def test_the_generated_frontend_agrees_with_pyproject(self):
        generated = (ROOT / "js" / "stylebook_data.js").read_text(encoding="utf-8")
        match = re.search(r'CURRENT_VERSION = "([^"]+)"', generated)
        self.assertIsNotNone(match, "CURRENT_VERSION missing from the generated data")
        self.assertEqual(match.group(1), _pyproject_version())


class LazyCorpusTests(unittest.TestCase):
    """The corpus stays out of ComfyUI's extension glob.

    ComfyUI imports every ``.js`` under a pack's web directory at app
    start. A 300 KB one is a tax on every ComfyUI user, including the ones
    with no Stylebook node on the canvas, so the corpus is a ``.json``
    the gallery fetches when a picker first opens.
    """

    #: Generous: the eager module is a few kilobytes. This is a tripwire
    #: for the corpus coming back, not a byte budget.
    MAX_EAGER_BYTES = 32 * 1024

    def test_the_eagerly_imported_module_stays_small(self):
        size = (ROOT / "js" / "stylebook_data.js").stat().st_size
        self.assertLess(
            size, self.MAX_EAGER_BYTES,
            f"js/stylebook_data.js is {size} bytes; the corpus belongs in "
            f"stylebook_data.json, which ComfyUI's *.js glob does not match",
        )

    def test_the_corpus_ships_as_json(self):
        corpus = ROOT / "js" / "stylebook_data.json"
        self.assertTrue(corpus.is_file())
        self.assertGreater(corpus.stat().st_size, 100 * 1024)

    def test_no_other_javascript_file_is_oversized(self):
        """Every .js in js/ is parsed at app start, generated or not."""
        for path in sorted((ROOT / "js").glob("*.js")):
            with self.subTest(path.name):
                self.assertLess(path.stat().st_size, 128 * 1024)


if __name__ == "__main__":
    unittest.main()
