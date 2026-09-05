"""Unit tests for data/user_data.py -- the optional user_styles.json merge.

This module had zero tests before this revision, despite being the one
place in the pack that parses content someone else wrote. Every test here
writes to a tempfile and passes ``path=`` explicitly; none of them ever
touch the real pack-root user_styles.json.

    python -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.modifiers import AXES  # noqa: E402
from data.user_data import (  # noqa: E402
    _AXES, apply_user_artists, apply_user_modifiers, apply_user_styles,
    validate_user_record,
)
from stylebook_nodes.user_data_payload import build_user_data_payload  # noqa: E402

# A minimal built-in pool each test merges against, standing in for the
# real STYLES/ARTISTS/MODIFIERS dicts so a test never depends on -- or
# risks perturbing -- the pack's actual data.
BUILTIN_STYLES = {
    "cyanotype": {"label": "Cyanotype", "category": "photography"},
    "risograph": {"label": "Risograph", "category": "print_graphic"},
}
BUILTIN_ARTISTS = {
    "ansel_adams": {"label": "Ansel Adams", "category": "photography"},
}
BUILTIN_MODIFIERS = {
    "golden_hour": {"label": "Golden Hour", "axis": "lighting"},
}


class TempUserFile:
    """A user_styles.json in a throwaway directory, for one test."""

    def __init__(self, payload):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "user_styles.json"
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def __enter__(self):
        return self.path

    def __exit__(self, *exc):
        self._dir.cleanup()


def _not_ignoring():
    """apply_user_* short-circuits when STYLEBOOK_IGNORE_USER_STYLES is
    set, and the test runner sets it globally (see tests/validate_data.py)
    so the suite never depends on the machine's own user_styles.json. Every
    test in this file needs it cleared."""
    return patch.dict("os.environ", {"STYLEBOOK_IGNORE_USER_STYLES": ""})


class ApplyUserStylesTests(unittest.TestCase):
    def test_a_valid_style_merges(self):
        payload = {"styles": {"my_style": {
            "label": "My Style", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 1)
        self.assertIn("my_style", styles)
        self.assertEqual(styles["my_style"]["label"], "My Style")

    def test_missing_file_is_a_silent_no_op(self):
        with _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=Path("/does/not/exist.json"))
        self.assertEqual(added, 0)
        self.assertEqual(styles, BUILTIN_STYLES)

    def test_malformed_json_is_ignored_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user_styles.json"
            path.write_text("{not valid json", encoding="utf-8")
            with _not_ignoring():
                styles = dict(BUILTIN_STYLES)
                added = apply_user_styles(styles, path=path)  # must not raise
        self.assertEqual(added, 0)

    def test_override_of_a_built_in_id_works(self):
        payload = {"styles": {"cyanotype": {
            "label": "Cyanotype (mine)", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            apply_user_styles(styles, path=path)
        self.assertEqual(styles["cyanotype"]["label"], "Cyanotype (mine)")

    def test_override_of_a_built_in_id_keeping_its_label_works(self):
        """The test above renames the entry, which is what hid this: the
        obvious way to override a built-in is to keep its name and change
        the text underneath. The label-collision check counted the record
        being replaced as a collision, so that rejected the override and
        said "duplicates an existing style" about the very style it was
        replacing. Only a rename got through."""
        payload = {"styles": {"cyanotype": {
            "label": "Cyanotype", "category": "photography",
            "prose": "My own take on it.", "tags": "cyan, blueprint",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 1)
        self.assertEqual(styles["cyanotype"]["prose"], "My own take on it.")

    def test_a_duplicate_label_under_a_new_id_is_still_rejected(self):
        """The override fix must not open the gate to two records sharing
        a dropdown entry, which is the reason the check exists."""
        payload = {"styles": {"my_own_cyanotype": {
            "label": "Cyanotype", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 0)
        self.assertNotIn("my_own_cyanotype", styles)

    def test_two_user_entries_claiming_one_label_still_collide(self):
        """Recomputing the in-use labels per record reads the live dict,
        so an entry merged earlier in the same file is still counted."""
        payload = {"styles": {
            "first": {"label": "Twin", "category": "photography"},
            "second": {"label": "Twin", "category": "photography"},
        }}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 1)

    def test_a_style_missing_id_gets_it_set_to_its_own_json_key(self):
        """Real bug, caught by hand in a browser, not by any test until
        this one: stylebook_style.py and stylebook_sheet.py both read
        record["id"] directly (exactly like every built-in style), so a
        user style that omits it -- easy to do, since it looks redundant
        with the JSON key -- raised KeyError: 'id' at execute() time in
        Pick mode, with no validation message pointing at the cause."""
        payload = {"styles": {"my_style": {
            "label": "My Style", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            apply_user_styles(styles, path=path)
        self.assertEqual(styles["my_style"]["id"], "my_style")

    def test_a_style_with_a_mismatched_id_is_corrected_to_its_json_key(self):
        payload = {"styles": {"my_style": {
            "id": "something_else", "label": "My Style", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            apply_user_styles(styles, path=path)
        self.assertEqual(styles["my_style"]["id"], "my_style")

    def test_user_added_styles_is_populated(self):
        payload = {"styles": {"tracked_id": {
            "label": "Tracked", "category": "photography",
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            apply_user_styles(styles, path=path)
        import data.user_data as user_data
        self.assertIn("tracked_id", user_data.USER_ADDED_STYLES)

    def test_the_ignore_flag_suppresses_a_merge(self):
        payload = {"styles": {"my_style": {
            "label": "My Style", "category": "photography",
        }}}
        with TempUserFile(payload) as path:
            with patch.dict("os.environ", {"STYLEBOOK_IGNORE_USER_STYLES": "1"}):
                styles = dict(BUILTIN_STYLES)
                added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 0)
        self.assertEqual(styles, BUILTIN_STYLES)


class BlocksAxisTests(unittest.TestCase):
    """`blocks` fails silently when it is wrong.

    A typo passes a bare list-of-strings check and then blocks nothing:
    the user's modifier keeps applying, the style never says why, and no
    console line points at the file.
    """

    def test_the_mirrored_axes_match_the_real_ones(self):
        """data/user_data.py cannot import data/modifiers.py (that module
        imports it back), so the axis list is mirrored. This is the bind
        that stops the copy drifting from the original."""
        self.assertEqual(_AXES, frozenset(AXES))

    def test_a_valid_axis_merges(self):
        payload = {"styles": {"mine": {
            "label": "Mine", "category": "photography",
            "blocks": ["color_grade"],
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            self.assertEqual(apply_user_styles(styles, path=path), 1)
        self.assertEqual(styles["mine"]["blocks"], ["color_grade"])

    def test_an_unknown_axis_is_rejected_by_name(self):
        payload = {"styles": {"mine": {
            "label": "Mine", "category": "photography",
            "blocks": ["color_grading"],
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            self.assertEqual(apply_user_styles(styles, path=path), 0)
        self.assertNotIn("mine", styles)

    def test_one_bad_axis_rejects_the_whole_record(self):
        payload = {"styles": {"mine": {
            "label": "Mine", "category": "photography",
            "blocks": ["lighting", "colour_grade"],
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            self.assertEqual(apply_user_styles(styles, path=path), 0)

    def test_an_empty_blocks_list_is_fine(self):
        payload = {"styles": {"mine": {
            "label": "Mine", "category": "photography", "blocks": [],
        }}}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            self.assertEqual(apply_user_styles(styles, path=path), 1)

    def test_the_reason_names_the_field_and_the_known_axes(self):
        reason = validate_user_record(
            "style",
            {"label": "Mine", "category": "photography", "blocks": ["nope"]},
            existing_labels=set(),
            list_fields=("blocks",),
            axis_list_field="blocks",
        )
        self.assertIn("blocks", reason)
        self.assertIn("nope", reason)
        self.assertIn("color_grade", reason)


class RejectionTests(unittest.TestCase):
    """Each style-record rejection rule, exercised through apply_user_styles
    so the test proves the whole path, not just validate_user_record()."""

    def _try(self, record):
        with TempUserFile({"styles": {"x": record}}) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        return added, styles

    def test_sentinel_label_is_rejected(self):
        added, styles = self._try({"label": "Random", "category": "photography"})
        self.assertEqual(added, 0)
        self.assertNotIn("x", styles)

    def test_unknown_category_is_rejected(self):
        added, styles = self._try({"label": "Odd One", "category": "not_a_real_category"})
        self.assertEqual(added, 0)

    def test_duplicate_label_against_a_built_in_is_rejected(self):
        added, styles = self._try({"label": "Cyanotype", "category": "photography"})
        self.assertEqual(added, 0)

    def test_duplicate_label_against_an_earlier_user_entry_is_rejected(self):
        payload = {"styles": {
            "a": {"label": "Twin", "category": "photography"},
            "b": {"label": "Twin", "category": "photography"},
        }}
        with TempUserFile(payload) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 1, "exactly one of the two identically-labeled entries should land")

    def test_non_string_tags_is_rejected(self):
        added, styles = self._try({
            "label": "Odd", "category": "photography", "tags": ["not", "a", "string"],
        })
        self.assertEqual(added, 0)

    def test_non_list_aliases_is_rejected(self):
        added, styles = self._try({
            "label": "Odd", "category": "photography", "aliases": "not-a-list",
        })
        self.assertEqual(added, 0)

    def test_aliases_with_a_non_string_entry_is_rejected(self):
        added, styles = self._try({
            "label": "Odd", "category": "photography", "aliases": ["fine", 3],
        })
        self.assertEqual(added, 0)

    def test_missing_required_field_is_rejected(self):
        added, styles = self._try({"label": "No Category"})
        self.assertEqual(added, 0)

    def test_non_dict_entry_is_rejected(self):
        with TempUserFile({"styles": {"x": "just a string"}}) as path, _not_ignoring():
            styles = dict(BUILTIN_STYLES)
            added = apply_user_styles(styles, path=path)
        self.assertEqual(added, 0)


class ApplyUserArtistsTests(unittest.TestCase):
    def test_a_valid_artist_merges(self):
        payload = {"artists": {"my_artist": {"label": "My Artist", "descriptor": "..."}}}
        with TempUserFile(payload) as path, _not_ignoring():
            artists = dict(BUILTIN_ARTISTS)
            added = apply_user_artists(artists, path=path)
        self.assertEqual(added, 1)

    def test_unknown_artist_category_is_rejected(self):
        payload = {"artists": {"x": {"label": "X", "category": "not_a_category"}}}
        with TempUserFile(payload) as path, _not_ignoring():
            artists = dict(BUILTIN_ARTISTS)
            added = apply_user_artists(artists, path=path)
        self.assertEqual(added, 0)


class ApplyUserModifiersTests(unittest.TestCase):
    def test_a_valid_modifier_merges(self):
        payload = {"modifiers": {"my_mod": {"label": "My Mod", "axis": "lighting"}}}
        with TempUserFile(payload) as path, _not_ignoring():
            modifiers = dict(BUILTIN_MODIFIERS)
            added = apply_user_modifiers(modifiers, path=path)
        self.assertEqual(added, 1)

    def test_unknown_axis_is_rejected(self):
        payload = {"modifiers": {"x": {"label": "X", "axis": "not_a_real_axis"}}}
        with TempUserFile(payload) as path, _not_ignoring():
            modifiers = dict(BUILTIN_MODIFIERS)
            added = apply_user_modifiers(modifiers, path=path)
        self.assertEqual(added, 0)

    def test_off_as_a_modifier_label_is_rejected(self):
        payload = {"modifiers": {"x": {"label": "Off", "axis": "lighting"}}}
        with TempUserFile(payload) as path, _not_ignoring():
            modifiers = dict(BUILTIN_MODIFIERS)
            added = apply_user_modifiers(modifiers, path=path)
        self.assertEqual(added, 0)


class ValidateUserRecordTests(unittest.TestCase):
    """Direct tests of the shared validator, for cases awkward to reach
    through a whole apply_user_* call (a non-dict record's exact message,
    the None sentinel specifically)."""

    def test_none_sentinel_is_rejected(self):
        reason = validate_user_record(
            "style", {"label": "None", "category": "photography"},
            existing_labels=set(), category_field="category",
            known_categories={"photography"},
        )
        self.assertIsNotNone(reason)
        self.assertIn("reserved", reason)

    def test_a_valid_record_returns_none(self):
        reason = validate_user_record(
            "style", {"label": "Fine", "category": "photography"},
            existing_labels=set(), category_field="category",
            known_categories={"photography"},
        )
        self.assertIsNone(reason)


class BuildUserDataPayloadTests(unittest.TestCase):
    """The /stylebook/user_data route's payload shape, tested framework-free
    -- this is the part of routes.py that has real logic in it."""

    def test_empty_when_nothing_was_added(self):
        payload = build_user_data_payload(
            styles=BUILTIN_STYLES, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles=set(), added_artists=set(), added_modifiers=set(),
        )
        self.assertEqual(payload, {"styles": [], "artists": [], "modifiers": []})

    def test_a_custom_style_entry_carries_label_category_and_detail(self):
        styles = dict(BUILTIN_STYLES)
        styles["my_style"] = {
            "label": "My Style", "category": "photography", "prose": "a hand-written look.",
        }
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"my_style"}, added_artists=set(), added_modifiers=set(),
        )
        self.assertEqual(payload["styles"], [{
            "id": "my_style", "label": "My Style", "category": "photography",
            "detail": "a hand-written look.",
            "scene": "", "depicts": "", "aliases": [],
        }])

    def test_a_custom_style_passes_scene_depicts_and_aliases_to_the_gallery(self):
        styles = dict(BUILTIN_STYLES)
        styles["my_style"] = {
            "label": "My Style", "category": "photography", "prose": "a look.",
            "scene": "an empty corridor", "depicts": "a brass telescope",
            "aliases": ["my alias", "another"],
        }
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"my_style"}, added_artists=set(), added_modifiers=set(),
        )
        entry = payload["styles"][0]
        self.assertEqual(entry["scene"], "an empty corridor")
        self.assertEqual(entry["depicts"], "a brass telescope")
        self.assertEqual(entry["aliases"], ["my alias", "another"])

    def test_namesake_is_deliberately_not_passed_through(self):
        # It promises a matching artist record exists, which the validator
        # enforces for built-ins and cannot for a user file.
        styles = dict(BUILTIN_STYLES)
        styles["my_style"] = {
            "label": "My Style", "category": "photography", "namesake": "Nobody At All",
        }
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"my_style"}, added_artists=set(), added_modifiers=set(),
        )
        self.assertNotIn("namesake", payload["styles"][0])

    def test_aliases_default_to_an_empty_list_when_absent(self):
        styles = dict(BUILTIN_STYLES)
        styles["my_style"] = {"label": "My Style", "category": "photography"}
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"my_style"}, added_artists=set(), added_modifiers=set(),
        )
        self.assertEqual(payload["styles"][0]["aliases"], [])

    def test_artist_and_modifier_entries_keep_the_four_field_shape(self):
        artists = dict(BUILTIN_ARTISTS)
        artists["mine"] = {"label": "Mine", "category": "photography", "descriptor": "d"}
        modifiers = dict(BUILTIN_MODIFIERS)
        modifiers["my_mod"] = {"label": "My Mod", "axis": "lighting", "prose": "p"}
        payload = build_user_data_payload(
            styles=BUILTIN_STYLES, artists=artists, modifiers=modifiers,
            added_styles=set(), added_artists={"mine"}, added_modifiers={"my_mod"},
        )
        for entry in payload["artists"] + payload["modifiers"]:
            self.assertEqual(sorted(entry), ["category", "detail", "id", "label"])

    def test_detail_falls_back_to_tags_when_prose_is_absent(self):
        styles = dict(BUILTIN_STYLES)
        styles["my_style"] = {"label": "My Style", "category": "photography", "tags": "grainy, warm"}
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"my_style"}, added_artists=set(), added_modifiers=set(),
        )
        self.assertEqual(payload["styles"][0]["detail"], "grainy, warm")

    def test_modifier_entry_uses_axis_as_its_category_field(self):
        modifiers = dict(BUILTIN_MODIFIERS)
        modifiers["my_mod"] = {"label": "My Mod", "axis": "era", "tags": "1970s"}
        payload = build_user_data_payload(
            styles=BUILTIN_STYLES, artists=BUILTIN_ARTISTS, modifiers=modifiers,
            added_styles=set(), added_artists=set(), added_modifiers={"my_mod"},
        )
        self.assertEqual(payload["modifiers"][0]["category"], "era")

    def test_entries_are_sorted_by_id_for_a_stable_response(self):
        styles = dict(BUILTIN_STYLES)
        styles["zzz"] = {"label": "Z", "category": "photography"}
        styles["aaa"] = {"label": "A", "category": "photography"}
        payload = build_user_data_payload(
            styles=styles, artists=BUILTIN_ARTISTS, modifiers=BUILTIN_MODIFIERS,
            added_styles={"zzz", "aaa"}, added_artists=set(), added_modifiers=set(),
        )
        self.assertEqual([e["id"] for e in payload["styles"]], ["aaa", "zzz"])


if __name__ == "__main__":
    unittest.main()
