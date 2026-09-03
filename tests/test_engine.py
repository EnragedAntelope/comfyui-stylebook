"""Unit tests for the Stylebook chain engine.

Pure-stdlib ``unittest`` so it runs without ComfyUI installed:

    python -m unittest discover -s tests -t . -v

The ``-t .`` matters: it makes ``tests`` a genuine subpackage of the repo
root rather than an implicit top-level directory, which is what guarantees
``tests/__init__.py`` (and the comfy_api stub it registers) runs before any
test_*.py file in this directory. See that file for why.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.artists import ARTISTS, get_artist, get_artist_ids  # noqa: E402
from data.modifiers import MODIFIERS, MODIFIERS_BY_AXIS, get_modifier  # noqa: E402
from data.styles import CATEGORIES, CATEGORY_LABELS, STYLES, get_style_ids  # noqa: E402
from stylebook_nodes import schema_options as opt  # noqa: E402
from stylebook_nodes.stylebook_artist import add_artist  # noqa: E402
from stylebook_nodes.stylebook_blend import blend_styles, build_blend_chain  # noqa: E402
from stylebook_nodes.stylebook_core import (  # noqa: E402
    EMPTY_CHAIN, build_artist_clause, cycle_style_id, dump_chain, filter_modifiers,
    filter_pool, get_blocked_axes, merge_chain, parse_chain, random_style_id,
    readout_detail, render_negative, render_prompt, render_style_prose,
    render_style_tags, resolve_meta, resolved_summary, sheet_style_ids,
    stable_choice, stable_sample,
)
from stylebook_nodes.stylebook_modifier import apply_modifier  # noqa: E402
from stylebook_nodes.stylebook_sheet import (  # noqa: E402
    build_sheet, parse_style_list,
)
from stylebook_nodes.stylebook_style import build_style_chain  # noqa: E402
from tests.validate_data import (  # noqa: E402
    _ENTITY_EXEMPT, _ENTITY_EXEMPT_CATEGORIES, _ENTITY_NOUNS,
    _NAMESAKE_EXEMPT, _SCENE_EXEMPT,
    _check_encoding, _check_entity_content, _check_negation,
    _check_person_styles, _check_undeclared_namesakes, validate,
)

TAG_META = {"format": "tags", "placement": "prepend", "strength": "normal",
            "artist_detail": "full", "template": ""}
PROSE_META = dict(TAG_META, format="prose", placement="append")


class DataLayerTests(unittest.TestCase):
    def test_data_layer_valid(self):
        self.assertEqual(validate(), [])

    def test_every_style_id_matches_its_key(self):
        for sid, rec in STYLES.items():
            self.assertEqual(rec["id"], sid)

    def test_get_artist_by_label_and_id(self):
        aid, rec = next(iter(ARTISTS.items()))
        self.assertIs(get_artist(aid), rec)
        self.assertIs(get_artist(rec["label"]), rec)
        self.assertIs(get_artist(rec["label"].upper()), rec)
        self.assertIsNone(get_artist("no such artist"))

    def test_get_modifier_respects_axis(self):
        rec = MODIFIERS["golden_hour"]
        self.assertIs(get_modifier("Golden Hour", "lighting"), rec)
        self.assertIsNone(get_modifier("Golden Hour", "mood"))

    def test_get_style_ids_and_get_artist_ids_take_the_same_parameters(self):
        """There is exactly one tag-filter implementation in this pack
        (stylebook_core.filter_pool). get_style_ids used to carry a second,
        buggier one (whole-string matching, so any filter with a comma
        matched nothing); it was removed rather than fixed twice. This
        pins the two id-lookup functions to the same, category-only
        signature so a tag_filter parameter cannot quietly reappear on
        either one."""
        self.assertEqual(
            inspect.signature(get_style_ids), inspect.signature(get_artist_ids),
        )

    def test_get_style_ids_filters_by_category(self):
        photography_ids = get_style_ids(category="photography")
        self.assertTrue(photography_ids)
        for sid in photography_ids:
            self.assertEqual(STYLES[sid]["category"], "photography")
        self.assertEqual(get_style_ids(), list(STYLES))


class NegationGuardTests(unittest.TestCase):
    """The data validator must reject negation in both directions.

    A guard that matches nothing passes forever while checking nothing,
    so these feed it known-bad records and require a complaint.
    """

    def _errors(self, record: dict) -> list[str]:
        return _check_negation("style", {"probe": record})

    BASE = {"label": "Probe", "tags": "flat colour", "prose": "Flat colour.",
            "negative": "photographic"}

    def test_clean_record_passes(self):
        self.assertEqual(self._errors(dict(self.BASE)), [])

    def test_negated_clause_in_the_negative_field_is_rejected(self):
        """Candle Making shipped excluding 'no wax'. Fed to a negative
        prompt that suppresses wax, which is the whole style."""
        errors = self._errors(dict(self.BASE, negative="digital, no wax"))
        self.assertTrue(any("itself negated" in e for e in errors))

    def test_bare_negation_in_tags_is_rejected(self):
        errors = self._errors(dict(self.BASE, tags="pure contour, no shading"))
        self.assertTrue(any("say what is there" in e for e in errors))

    def test_bare_negation_in_prose_is_rejected(self):
        errors = self._errors(dict(self.BASE, prose="Drawn without colour."))
        self.assertTrue(any("say what is there" in e for e in errors))

    def test_process_negations_are_allowed(self):
        """These name how the work was made, not any property of the
        image, so rewriting them would be churn."""
        errors = self._errors(
            dict(self.BASE, prose="Laid down in one pass without hesitation.")
        )
        self.assertEqual(errors, [])

    def test_narrative_never_is_allowed_in_positive_text(self):
        """'a palette that could never be planned' is English, not a
        property the model would render."""
        errors = self._errors(
            dict(self.BASE, prose="A palette that could never be planned.")
        )
        self.assertEqual(errors, [])

    def test_an_artist_descriptor_is_checked_too(self):
        """An artist's positive text is spelled `descriptor`, and it goes
        straight into the prompt via render_artist. Candida Hofer shipped
        "endless bookshelves without a single figure" - a descriptor whose
        whole point is the absence of people, asking for a figure."""
        errors = _check_negation(
            "artist",
            {"probe": {"label": "Probe",
                       "descriptor": "wide interiors without a single figure"}},
            ("descriptor",),
        )
        self.assertTrue(any("say what is there" in e for e in errors))

    def test_the_shipped_data_is_clean(self):
        self.assertEqual(_check_negation("style", STYLES), [])
        self.assertEqual(_check_negation("modifier", MODIFIERS), [])
        self.assertEqual(_check_negation("artist", ARTISTS, ("descriptor",)), [])


class PersonNamedStyleTests(unittest.TestCase):
    """A style named after somebody must be findable as an artist.

    Fifteen were not: a user who found "Akira Kurosawa Rain" in the style
    gallery and then searched the Artist picker for "Kurosawa" got
    nothing back.
    """

    def test_the_shipped_data_is_clean(self):
        self.assertEqual(_check_person_styles(STYLES, ARTISTS), [])

    def test_a_missing_artist_record_is_reported(self):
        thinned = {aid: rec for aid, rec in ARTISTS.items()
                   if rec.get("label") != "Akira Kurosawa"}
        errors = _check_person_styles(STYLES, thinned)
        self.assertTrue(any("Akira Kurosawa" in e for e in errors))

    def test_the_declaration_lives_on_the_style_record(self):
        """The map used to live in the test file, where a maintainer
        adding a style never saw it. It is data now, so the field is
        written beside the prose it belongs to."""
        self.assertEqual(STYLES["kurosawa"]["namesake"], "Akira Kurosawa")

    def test_a_style_named_for_a_shipped_artist_must_declare_it(self):
        """The gap the old map could not close: a *missing* entry.

        A style is named after somebody the pack already ships, and
        nobody remembers to say so.
        """
        undeclared = dict(STYLES)
        stripped = dict(undeclared["kurosawa"])
        stripped.pop("namesake")
        undeclared["kurosawa"] = stripped
        errors = _check_undeclared_namesakes(undeclared, ARTISTS)
        self.assertTrue(any("kurosawa" in e for e in errors), errors)

    def test_the_shipped_data_declares_or_exempts_every_collision(self):
        self.assertEqual(_check_undeclared_namesakes(STYLES, ARTISTS), [])

    def test_every_exemption_carries_a_written_reason(self):
        """An exemption without a reason is how a check quietly stops
        meaning anything -- the same contract as _SCENE_EXEMPT."""
        for sid, reason in _NAMESAKE_EXEMPT.items():
            with self.subTest(sid):
                self.assertIn(sid, STYLES)
                self.assertTrue(reason.strip())


class EntityContentTests(unittest.TestCase):
    """A modifier tilts the rendering; it must not add an object.

    11 of the 20 era modifiers enumerated garments, furniture and light
    fixtures as free-standing nouns, so Randomize on `era` put wigs on
    mannequins and gaslit drapery around subjects that were neither.
    _SCENE_NOUNS could not catch it: it lists places, and a wig is not a
    place.
    """

    def test_a_garment_in_a_modifier_is_rejected(self):
        bad = {"probe": {"label": "P", "axis": "era",
                         "tags": "powdered wigs and embroidered frock coats",
                         "prose": "P."}}
        errors = _check_entity_content(bad)
        self.assertTrue(any("wig" in e for e in errors), errors)

    def test_a_light_fixture_in_a_modifier_is_rejected(self):
        """The catch that sharpened the rule: a *fixture* is an entity, a
        light's *behaviour* is not. "gaslight casting a warm amber glow"
        can put a gas lamp in the frame; "low amber light falling off fast
        into deep shadow" cannot, because falloff is not an object."""
        bad = {"probe": {"label": "P", "axis": "era",
                         "tags": "oil lamp ambiance over velvet drapes",
                         "prose": "P."}}
        errors = _check_entity_content(bad)
        self.assertTrue(errors, errors)

    def test_light_behaviour_is_not_an_entity(self):
        ok = {"probe": {"label": "P", "axis": "era",
                        "tags": "low amber light falling off fast into deep "
                                "shadow with barely any fill, a sepia-leaning "
                                "palette, densely ornamented hand-finished "
                                "surfaces darkened with age",
                        "prose": "P."}}
        self.assertEqual(_check_entity_content(ok), [])

    def test_period_dress_is_exempt_by_definition(self):
        """It is the one axis whose job *is* entities. Splitting it off
        era is what makes the era fix non-lossy."""
        bad = {"probe": {"label": "P", "axis": "period_dress",
                         "tags": "powdered wig and embroidered frock coat",
                         "prose": "P."}}
        self.assertEqual(_check_entity_content(bad), [])

    def test_the_shipped_modifiers_name_no_entity(self):
        self.assertEqual(_check_entity_content(MODIFIERS), [])

    def test_every_entity_exemption_carries_a_written_reason(self):
        for mid, reason in _ENTITY_EXEMPT.items():
            with self.subTest(mid):
                self.assertIn(mid, MODIFIERS)
                self.assertTrue(reason.strip())

    def test_every_scene_exemption_carries_a_written_reason(self):
        """_SCENE_EXEMPT had this contract in its comment and nothing
        checked it."""
        for sid, reason in _SCENE_EXEMPT.items():
            with self.subTest(sid):
                self.assertIn(sid, STYLES)
                self.assertTrue(reason.strip())

    def test_the_noun_list_uses_word_boundaries(self):
        """Substring matching lies in both directions: it once matched
        "alley" inside *gallery*. The matcher is shared with
        _check_scene_content, so this pins the shared behaviour."""
        ok = {"probe": {"label": "P", "axis": "finish",
                        "tags": "uniform-weight contour and screentone",
                        "prose": "P."}}
        self.assertEqual(_check_entity_content(ok), [])

    def test_the_noun_list_still_matches_plurals(self):
        """Adding \\b once silently stopped matching plurals and quietly
        shrank the report. A shrinking report looks like progress."""
        for singular in ("wig", "chair", "lamp"):
            with self.subTest(singular):
                bad = {"probe": {"label": "P", "axis": "era",
                                 "tags": f"a row of {singular}s",
                                 "prose": "P."}}
                self.assertTrue(_check_entity_content(bad))

    def test_no_noun_is_listed_twice(self):
        self.assertEqual(len(_ENTITY_NOUNS), len(set(_ENTITY_NOUNS)))


class StyleEntityContentTests(unittest.TestCase):
    """The styles half of the entity rule, hot since 0.13.0.

    0.12.0 could only *report* on styles -- it printed a count of 39 and
    offered no way to act on it -- because a style may legitimately be the
    object. The escape is the declared `depicts` field rather than an
    exemption map in this file, for three reasons the map cannot fix:
    nothing checks that an exemption id still points at a live record, an
    exemption is invisible to the user, and an agent that writes a costume
    clause writes its own exemption sentence thirty seconds later.
    """

    def test_a_style_naming_an_entity_without_depicts_is_rejected(self):
        bad = {"probe": {"label": "P", "category": "painting",
                         "tags": "a velvet armchair beside a lamp",
                         "prose": "P."}}
        errors = _check_entity_content(bad, "style")
        self.assertTrue(any("armchair" in e for e in errors), errors)
        self.assertTrue(any("depicts" in e for e in errors), errors)

    def test_declaring_depicts_clears_it(self):
        ok = {"probe": {"label": "P", "category": "painting",
                        "depicts": "an armchair and a lamp",
                        "tags": "a velvet armchair beside a lamp",
                        "prose": "P."}}
        self.assertEqual(_check_entity_content(ok, "style"), [])

    def test_a_blank_depicts_buys_no_exemption(self):
        """The quiet failure this guards: a declared-but-empty field that
        silences the rule and renders no badge, so the user is told
        nothing and the check reports nothing."""
        for blank in ("", "   "):
            with self.subTest(repr(blank)):
                bad = {"probe": {"label": "P", "category": "painting",
                                 "depicts": blank,
                                 "tags": "a velvet armchair",
                                 "prose": "P."}}
                self.assertTrue(_check_entity_content(bad, "style"))

    def test_the_container_categories_are_exempt_by_definition(self):
        """Both mean "the subject is rendered *as* the thing", so naming
        the thing is the whole record. ARCHITECTURE.md already argues them
        out of the `scene` rule on the same grounds, and the gallery's
        category chip already tells the user."""
        for category in _ENTITY_EXEMPT_CATEGORIES:
            with self.subTest(category):
                bad = {"probe": {"label": "P", "category": category,
                                 "tags": "a hand-poured candle in a mould",
                                 "prose": "P."}}
                self.assertEqual(_check_entity_content(bad, "style"), [])

    def test_a_modifier_may_not_declare_depicts(self):
        """Nothing reads `depicts` off a modifier, so honouring one would
        be a silent exemption. Same contract `scene` already carries."""
        bad = {"probe": {"label": "P", "axis": "mood", "depicts": "a chair",
                         "tags": "warm and calm", "prose": "P."}}
        errors = _check_entity_content(bad, "modifier")
        self.assertTrue(any("only a style may do" in e for e in errors), errors)

    def test_the_shipped_styles_pass_the_hot_rule(self):
        self.assertEqual(_check_entity_content(STYLES, "style"), [])

    def test_every_exempt_category_is_a_real_category(self):
        """The failure an exemption *map* has and this does not: an entry
        that no longer points at anything. Categories are few and stable,
        so pin them."""
        from data.styles import CATEGORIES
        for category in _ENTITY_EXEMPT_CATEGORIES:
            with self.subTest(category):
                self.assertIn(category, CATEGORIES)


class EncodingGuardTests(unittest.TestCase):
    """A replacement character means text was already lost."""

    def test_a_replacement_character_in_an_alias_is_rejected(self):
        """Where this one actually was. European Album's alias read
        "bande dessin?e", so the style answered a search for neither
        spelling, and aliases are a list rather than a plain string."""
        bad = {"probe": {"label": "P", "aliases": ["bande dessin�e"],
                         "tags": "t", "prose": "P."}}
        errors = _check_encoding("style", bad)
        self.assertTrue(any("replacement character" in e for e in errors))

    def test_a_replacement_character_in_a_text_field_is_rejected(self):
        bad = {"probe": {"label": "P", "tags": "bande dessin�e"}}
        errors = _check_encoding("style", bad)
        self.assertTrue(any("replacement character" in e for e in errors))

    def test_clean_text_passes(self):
        good = {"probe": {"label": "P", "tags": "bande dessinee"}}
        self.assertEqual(_check_encoding("style", good), [])

    def test_the_shipped_data_is_clean(self):
        self.assertEqual(_check_encoding("style", STYLES), [])
        self.assertEqual(_check_encoding("artist", ARTISTS), [])
        self.assertEqual(_check_encoding("modifier", MODIFIERS), [])


class ParseChainTests(unittest.TestCase):
    def test_empty_string_returns_empty_chain(self):
        self.assertEqual(parse_chain(""), json.loads(EMPTY_CHAIN))

    def test_none_returns_empty_chain(self):
        self.assertEqual(parse_chain(None), json.loads(EMPTY_CHAIN))  # type: ignore[arg-type]

    def test_invalid_json_returns_empty_chain(self):
        self.assertEqual(parse_chain("not json"), json.loads(EMPTY_CHAIN))

    def test_non_dict_json_returns_empty_chain(self):
        self.assertEqual(parse_chain("[1,2,3]"), json.loads(EMPTY_CHAIN))

    def test_wrong_typed_fields_are_repaired(self):
        chain = parse_chain('{"_meta":"nope","modifiers":"nope","artists":5}')
        self.assertEqual(chain["_meta"], {})
        self.assertEqual(chain["modifiers"], [])
        self.assertEqual(chain["artists"], [])

    def test_roundtrip(self):
        chain = parse_chain(EMPTY_CHAIN)
        chain["_meta"]["format"] = "tags"
        chain["style"] = {"id": "t", "label": "T"}
        again = parse_chain(dump_chain(chain))
        self.assertEqual(again["_meta"]["format"], "tags")
        self.assertEqual(again["style"]["id"], "t")


class MergeChainTests(unittest.TestCase):
    def test_downstream_wins_and_lists_concatenate(self):
        up = json.loads('{"_meta":{"format":"tags"},"style":{"id":"a"},'
                        '"modifiers":[{"axis":"lighting"}],"artists":[{"label":"A"}]}')
        down = json.loads('{"_meta":{"format":"prose"},"style":{"id":"b"},'
                          '"modifiers":[{"axis":"era"}],"artists":[{"label":"B"}]}')
        merged = merge_chain(up, down)
        self.assertEqual(merged["_meta"]["format"], "prose")
        self.assertEqual(merged["style"]["id"], "b")
        self.assertEqual(len(merged["modifiers"]), 2)
        self.assertEqual([a["label"] for a in merged["artists"]], ["A", "B"])

    def test_upstream_style_survives_null_downstream(self):
        up = json.loads('{"_meta":{},"style":{"id":"a"},"modifiers":[],"artists":[]}')
        down = json.loads(EMPTY_CHAIN)
        self.assertEqual(merge_chain(up, down)["style"]["id"], "a")


class StrengthTests(unittest.TestCase):
    """Strength must work for every style, not only the few that ship
    an ``emphasis`` or ``strength_tail`` field."""

    PLAIN = {"id": "p", "label": "P", "tags": "one, two, three, four",
             "prose": "A first clause here. A second clause here."}

    def test_subtle_trims_tags(self):
        self.assertEqual(render_style_tags(self.PLAIN, "subtle"), "one, two")

    def test_normal_keeps_all_tags(self):
        self.assertEqual(render_style_tags(self.PLAIN, "normal"),
                         "one, two, three, four")

    def test_strong_uses_emphasis_when_present(self):
        rec = dict(self.PLAIN, emphasis="extra, more")
        self.assertIn("extra", render_style_tags(rec, "strong"))

    def test_subtle_prose_keeps_only_lead_clause(self):
        out = render_style_prose(self.PLAIN, "subtle")
        self.assertIn("first clause", out)
        self.assertNotIn("second clause", out)

    def _rendered(self, rec, strength, fmt="tags"):
        chain = parse_chain("")
        chain["style"] = rec
        meta = dict(TAG_META if fmt == "tags" else PROSE_META, strength=strength)
        return render_prompt(chain, meta, "a cat")

    def test_strong_restates_the_defining_term_in_the_final_prompt(self):
        """The join deduplicates, so a restatement added inside the style
        renderer would be stripped again before it reached the output."""
        out = self._rendered(self.PLAIN, "strong")
        self.assertEqual(out.count("one"), 2)

    def test_every_shipped_style_changes_under_strength_end_to_end(self):
        """Regression: strength was a no-op for 399 of 468 styles, because
        it depended on emphasis/strength_tail fields almost none of them had."""
        same_strong, same_subtle = [], []
        for sid, rec in STYLES.items():
            normal = self._rendered(rec, "normal")
            if self._rendered(rec, "strong") == normal:
                same_strong.append(sid)
            if self._rendered(rec, "subtle") == normal:
                same_subtle.append(sid)
        self.assertEqual(same_strong, [], "strong did nothing for these")
        self.assertEqual(same_subtle, [], "subtle did nothing for these")

    def test_every_shipped_style_changes_under_strength_in_prose(self):
        same = [
            sid for sid, rec in STYLES.items()
            if self._rendered(rec, "subtle", "prose")
            == self._rendered(rec, "normal", "prose")
        ]
        self.assertEqual(same, [])


class TagFilterTests(unittest.TestCase):
    """The filter is comma-separated AND, matching tags/prose/label/aliases."""

    def test_single_term_matches(self):
        ids = filter_pool(tag_filter="cyanotype")
        self.assertIn("cyanotype", ids)

    def test_comma_separated_terms_are_anded(self):
        """Regression: a filter containing a comma used to match nothing,
        because the whole raw string was searched as one substring."""
        both = filter_pool(tag_filter="ink, flat")
        self.assertTrue(both)
        for sid in both:
            rec = STYLES[sid]
            haystack = (rec["tags"] + rec["prose"] + rec["label"]
                        + " ".join(rec["aliases"])).lower()
            self.assertIn("ink", haystack)
            self.assertIn("flat", haystack)

    def test_and_is_narrower_than_either_term(self):
        a = set(filter_pool(tag_filter="ink"))
        b = set(filter_pool(tag_filter="flat"))
        both = set(filter_pool(tag_filter="ink, flat"))
        self.assertEqual(both, a & b)

    def test_alias_is_searchable(self):
        """Aliases folded in from merged styles must stay findable."""
        self.assertIn("otome_game", filter_pool(tag_filter="reverse harem"))

    def test_impossible_filter_returns_empty(self):
        self.assertEqual(filter_pool(tag_filter="zzzznotathing"), [])

    def test_category_narrows_pool(self):
        ids = filter_pool(category="comics")
        self.assertTrue(ids)
        for sid in ids:
            self.assertEqual(STYLES[sid]["category"], "comics")


class StableSelectionTests(unittest.TestCase):
    """Adding an entry must not silently change what existing seeds mean.

    Indexing a sorted pool would reshuffle every seed the moment one new
    style or artist shipped, quietly breaking every saved workflow.
    """

    POOL = [f"item_{i:03d}" for i in range(200)]

    def test_same_seed_same_pick(self):
        self.assertEqual(stable_choice(7, self.POOL), stable_choice(7, self.POOL))

    def test_different_seeds_differ(self):
        picks = {stable_choice(s, self.POOL) for s in range(40)}
        self.assertGreater(len(picks), 25)

    def test_pick_is_order_independent(self):
        """A pool listed in another order must give the same answer."""
        shuffled = list(reversed(self.POOL))
        for seed in range(20):
            self.assertEqual(stable_choice(seed, self.POOL),
                             stable_choice(seed, shuffled))

    def test_adding_an_entry_disturbs_almost_no_seeds(self):
        grown = self.POOL + ["item_new"]
        changed = sum(1 for s in range(400)
                      if stable_choice(s, self.POOL) != stable_choice(s, grown))
        # Roughly 1 seed in len(pool). Index-based selection would change
        # about half of them, since every later index shifts by one.
        self.assertLess(changed, 20, f"{changed}/400 seeds changed")

    def test_removing_an_entry_only_affects_seeds_it_won(self):
        victim = stable_choice(3, self.POOL)
        smaller = [i for i in self.POOL if i != victim]
        changed = [s for s in range(400)
                   if stable_choice(s, self.POOL) != stable_choice(s, smaller)]
        for seed in changed:
            self.assertEqual(stable_choice(seed, self.POOL), victim)

    def test_sample_is_stable_and_distinct(self):
        picked = stable_sample(11, self.POOL, 8)
        self.assertEqual(len(picked), 8)
        self.assertEqual(len(set(picked)), 8)
        self.assertEqual(picked, stable_sample(11, self.POOL, 8))

    def test_sample_grows_gracefully(self):
        grown = self.POOL + ["item_new"]
        before = stable_sample(5, self.POOL, 10)
        after = stable_sample(5, grown, 10)
        self.assertGreaterEqual(len(set(before) & set(after)), 9)

    def test_empty_pool(self):
        self.assertIsNone(stable_choice(1, []))
        self.assertEqual(stable_sample(1, [], 5), [])


class SelectionTests(unittest.TestCase):
    def test_random_is_reproducible_for_a_seed(self):
        a = random_style_id(42)
        b = random_style_id(42)
        self.assertEqual(a, b)
        self.assertIsNotNone(a)

    def test_random_respects_category(self):
        sid = random_style_id(7, category="painting")
        self.assertEqual(STYLES[sid]["category"], "painting")

    def test_random_returns_none_on_empty_pool(self):
        self.assertIsNone(random_style_id(1, tag_filter="zzzznope"))

    def test_cycle_is_deterministic_and_wraps(self):
        pool = filter_pool(category="comics")
        self.assertEqual(cycle_style_id(0, category="comics"), pool[0])
        self.assertEqual(cycle_style_id(len(pool), category="comics"), pool[0])

    def test_sheet_returns_distinct_ids(self):
        ids = sheet_style_ids(3, 8)
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)

    def test_sheet_caps_at_pool_size(self):
        ids = sheet_style_ids(3, 999, category="comics")
        self.assertEqual(len(ids), len(filter_pool(category="comics")))


class RenderPromptTests(unittest.TestCase):
    # The prose deliberately opens on a noun phrase, the way every shipped
    # style does. That shape is the whole reason the rendering frame
    # exists: without a connective, "A test slide with ..." reads as more
    # scene content and the model draws the slide.
    STYLE = {"id": "t", "label": "T", "tags": "test style, tag words",
             "prose": "A test slide with enough descriptive words here.",
             "negative": "bad stuff, noise"}

    def test_no_style_returns_subject(self):
        self.assertEqual(render_prompt(parse_chain(""), TAG_META, "a cat"), "a cat")

    def test_no_subject_returns_style_only(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        self.assertEqual(render_prompt(chain, TAG_META, ""), "test style, tag words")

    def test_tags_prepend_subject(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(chain, TAG_META, "a cat")
        self.assertEqual(result, "test style, tag words, a cat")

    def test_prose_appends_after_subject(self):
        """Prose models follow the subject of the sentence, so the subject
        leads and the style trails as a rendering clause."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(chain, PROSE_META, "a cat on a wall")
        self.assertTrue(result.startswith("A cat on a wall."))
        self.assertIn("Rendered as a test slide", result)

    def test_prose_frames_the_style_so_it_is_not_read_as_scene_content(self):
        """The defect this frame exists for.

        A style whose prose opens on a noun phrase, appended bare, reads as
        another thing in the picture. Chaining a subject description into a
        View-Master style put a View-Master in the image instead of
        rendering the image as one.
        """
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(chain, PROSE_META, "a cat on a wall")
        self.assertNotIn("wall. A test slide", result)
        self.assertIn("Rendered as", result)

    def test_prose_prepend_frames_both_halves(self):
        """Leading with the style needs the boundary marked from the other
        side, or the subject reads as part of the style description."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(
            chain, dict(PROSE_META, placement="prepend"), "a cat on a wall"
        )
        self.assertTrue(result.startswith("Rendered as a test slide"))
        self.assertIn("The image shows a cat on a wall.", result)

    def test_a_framed_opening_reads_as_a_continuation(self):
        """Regression: "The image shows A 43-year-old man" - the article
        kept its capital because the check tested the first two
        characters, and "A " counts as uppercase."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(
            chain, dict(PROSE_META, placement="prepend"),
            "A 43-year-old man in a coat",
        )
        self.assertIn("The image shows a 43-year-old man", result)

    def test_a_users_ellipsis_survives_tidying(self):
        """_tidy collapses the ". ." an empty part leaves behind. A bare
        two-dot pattern also ate the user's own "a cat... at night"."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(chain, PROSE_META, "a cat... at night")
        self.assertIn("A cat... at night", result)

    def test_an_acronym_keeps_its_capitals_when_framed(self):
        """Lowering the opening must not turn HDR into hDR."""
        chain = parse_chain("")
        chain["style"] = dict(self.STYLE, prose="HDR tone mapping throughout.")
        result = render_prompt(chain, PROSE_META, "a cat")
        self.assertIn("Rendered as HDR tone mapping", result)

    def test_a_style_alone_carries_no_frame(self):
        """With no subject there is no boundary to mark, and a bare
        "Rendered as ..." fragment is not a sentence."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        result = render_prompt(chain, PROSE_META, "")
        self.assertNotIn("Rendered as", result)
        self.assertTrue(result.startswith("A test slide"))

    def test_an_artist_alone_reads_as_rendered_by(self):
        """An Artist node with no Style upstream is a plain, supported
        setup, and the artist clause opens with "by". The generic
        connective produced "Rendered as by Ansel Adams"."""
        chain = parse_chain("")
        chain["artists"] = [{"label": "Ansel Adams", "descriptor": "crisp"}]
        for placement in ("append", "prepend"):
            with self.subTest(placement):
                result = render_prompt(
                    chain, dict(PROSE_META, placement=placement), "a cat"
                )
                self.assertIn("Rendered by Ansel Adams", result)
                self.assertNotIn("Rendered as by", result)

    def test_a_style_still_takes_the_full_connective_alongside_an_artist(self):
        """The 'by' special case must fire only when the artist clause is
        the whole block, not whenever a chain happens to hold an artist."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        chain["artists"] = [{"label": "Ansel Adams", "descriptor": "crisp"}]
        result = render_prompt(chain, PROSE_META, "a cat")
        self.assertIn("Rendered as a test slide", result)
        self.assertIn("By Ansel Adams", result)

    def test_tags_carry_no_frame_in_either_direction(self):
        """A keyword list has no grammar to confuse, so a connective would
        only be tokens spent on nothing."""
        chain = parse_chain("")
        chain["style"] = self.STYLE
        for placement in ("append", "prepend"):
            with self.subTest(placement):
                result = render_prompt(
                    chain, dict(TAG_META, placement=placement), "a cat"
                )
                self.assertNotIn("Rendered as", result)
                self.assertNotIn("The image shows", result)

    def test_placement_decides_which_half_leads(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        tags_prepend = render_prompt(
            chain, dict(TAG_META, placement="prepend"), "a cat")
        prose_append = render_prompt(
            chain, dict(PROSE_META, placement="append"), "a cat")
        self.assertTrue(tags_prepend.startswith("test style"))
        self.assertTrue(prose_append.startswith("A cat."))

    def test_no_double_commas_or_stray_punctuation(self):
        chain = parse_chain("")
        chain["style"] = dict(self.STYLE, tags="a, , b")
        result = render_prompt(chain, TAG_META, "cat")
        self.assertNotIn(", ,", result)
        self.assertNotIn("  ", result)

    def test_tag_output_has_no_duplicate_items(self):
        chain = parse_chain("")
        chain["style"] = dict(self.STYLE, tags="ink, flat, ink")
        self.assertEqual(render_prompt(chain, TAG_META, ""), "ink, flat")

    def test_template_overrides_placement(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        meta = dict(TAG_META, template="{prompt} || {style}")
        self.assertEqual(render_prompt(chain, meta, "cat"),
                         "cat || test style, tag words")

    def test_negative_collects_style_and_modifiers(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        chain["modifiers"] = [{"axis": "mood", "negative": "cheerful"}]
        result = render_negative(chain)
        self.assertIn("bad stuff", result)
        self.assertIn("cheerful", result)

    def test_render_is_deterministic(self):
        chain = parse_chain("")
        chain["style"] = self.STYLE
        self.assertEqual(render_prompt(chain, TAG_META, "cat"),
                         render_prompt(chain, TAG_META, "cat"))


class ArtistClauseTests(unittest.TestCase):
    ARTISTS = [{"label": "A One", "descriptor": "thick paint, dark ground"},
               {"label": "B Two", "descriptor": "thin line, pale wash"}]

    def test_full_mode_attributes_by_name(self):
        out = build_artist_clause(self.ARTISTS, "full")
        self.assertTrue(out.startswith("by A One"))
        self.assertIn("B Two", out)

    def test_names_only(self):
        self.assertEqual(build_artist_clause(self.ARTISTS, "names_only"),
                         "by A One, B Two")

    def test_descriptor_only_omits_the_word_by(self):
        """There is no name to attribute to, so 'by' would be nonsense."""
        out = build_artist_clause(self.ARTISTS, "descriptor_only")
        self.assertFalse(out.startswith("by "))
        self.assertIn("thick paint", out)
        self.assertNotIn("A One", out)

    def test_names_lead_keeps_only_the_first_descriptor_clause(self):
        out = build_artist_clause(self.ARTISTS[:1], "names_lead")
        self.assertIn("thick paint", out)
        self.assertNotIn("dark ground", out)

    def test_empty_list_yields_nothing(self):
        self.assertEqual(build_artist_clause([], "full"), "")


class BlockedAxesTests(unittest.TestCase):
    def test_none_style_blocks_nothing(self):
        self.assertEqual(get_blocked_axes(None), set())

    def test_blocks_are_returned(self):
        self.assertEqual(get_blocked_axes({"blocks": ["color_grade"]}),
                         {"color_grade"})

    def test_filter_splits_kept_from_dropped(self):
        mods = [{"axis": "lighting"}, {"axis": "color_grade"}]
        kept, dropped = filter_modifiers(mods, {"color_grade"})
        self.assertEqual([m["axis"] for m in kept], ["lighting"])
        self.assertEqual([m["axis"] for m in dropped], ["color_grade"])

    def test_no_blocks_keeps_everything(self):
        mods = [{"axis": "lighting"}]
        kept, dropped = filter_modifiers(mods, set())
        self.assertEqual(kept, mods)
        self.assertEqual(dropped, [])


class ReadoutTests(unittest.TestCase):
    """resolved_summary and readout_detail back the node-face readout.

    The bug these close: the old single-line readout truncated the
    rendered prompt from the front, so with a subject connected every node
    in a chain showed the same opening of the user's own text, and in
    Random mode there was no readout at all -- nothing named what got
    picked.
    """

    def test_empty_chain_says_nothing_applied(self):
        chain = json.loads(EMPTY_CHAIN)
        self.assertEqual(resolved_summary(chain), "(nothing applied yet)")

    def test_style_only(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"label": "Cyanotype"}
        self.assertEqual(resolved_summary(chain), "Cyanotype")

    def test_style_artist_and_modifier_join_with_middle_dot(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"label": "Cyanotype"}
        chain["artists"] = [{"label": "Ansel Adams"}]
        chain["modifiers"] = [{"label": "Golden Hour", "axis": "lighting"}]
        self.assertEqual(
            resolved_summary(chain),
            "Cyanotype · Ansel Adams · Golden Hour (lighting)",
        )

    def test_artists_at_the_warn_threshold_are_still_named(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["artists"] = [{"label": "A"}, {"label": "B"}, {"label": "C"}]
        self.assertEqual(resolved_summary(chain), "A · B · C")

    def test_artists_past_the_warn_threshold_elide_to_a_count(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["artists"] = [{"label": n} for n in "ABCD"]
        self.assertEqual(resolved_summary(chain), "4 artists")

    def test_summary_truncates_past_its_own_limit(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"label": "x" * 200}
        summary = resolved_summary(chain)
        self.assertLessEqual(len(summary), 120)
        self.assertTrue(summary.endswith("…"))

    def test_detail_with_no_subject_is_the_style_text_unframed(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"label": "Cyanotype", "prose": "a cyanotype print."}
        meta = resolve_meta(chain)
        self.assertEqual(
            readout_detail(chain, meta, ""),
            render_prompt(chain, meta, ""),
        )
        self.assertNotIn("[subject]", readout_detail(chain, meta, ""))

    def test_detail_with_a_subject_marks_it_with_a_literal_token(self):
        chain = json.loads(EMPTY_CHAIN)
        chain["style"] = {"label": "Cyanotype", "prose": "a cyanotype print."}
        meta = resolve_meta(chain)
        detail = readout_detail(chain, meta, "a woman in a red coat")
        self.assertTrue(detail.startswith("[subject] "))
        # The user's own words must not appear in the detail line -- that
        # is the whole point of the marker.
        self.assertNotIn("red coat", detail)

    def test_detail_with_a_subject_and_no_style_is_just_the_marker(self):
        chain = json.loads(EMPTY_CHAIN)
        meta = resolve_meta(chain)
        self.assertEqual(readout_detail(chain, meta, "a woman"), "[subject]")


class StyleNodeTests(unittest.TestCase):
    """Regression cover for the node being a no-op at its defaults."""

    def test_default_mode_produces_a_style(self):
        chain, warnings = build_style_chain(
            "", opt.DEFAULTS["style"], opt.DEFAULTS["mode"],
            opt.DEFAULTS["category"], "", seed=1, cycle_index=0,
        )
        self.assertIsNotNone(chain["style"])
        self.assertEqual(warnings, [])

    def test_pick_none_applies_nothing(self):
        chain, warnings = build_style_chain(
            "", opt.NONE, opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
        )
        self.assertIsNone(chain["style"])
        self.assertEqual(warnings, [])

    def test_pick_by_label_resolves(self):
        chain, _ = build_style_chain(
            "", "Cyanotype", opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
        )
        self.assertEqual(chain["style"]["id"], "cyanotype")

    def test_unknown_label_warns_and_applies_nothing(self):
        chain, warnings = build_style_chain(
            "", "Not A Real Style", opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
        )
        self.assertIsNone(chain["style"])
        self.assertTrue(any("no style named" in w for w in warnings))

    def test_empty_pool_warns(self):
        _, warnings = build_style_chain(
            "", opt.NONE, opt.MODE_RANDOM, opt.CATEGORY_ALL, "zzzznope", 0, 0,
        )
        self.assertTrue(any("no style matches" in w for w in warnings))

    def test_second_style_replaces_first_with_a_warning(self):
        first, _ = build_style_chain(
            "", "Cyanotype", opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
        )
        second, warnings = build_style_chain(
            dump_chain(first), "Linocut", opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
        )
        self.assertEqual(second["style"]["id"], "linocut")
        self.assertTrue(any("exclusive" in w for w in warnings))

    def test_meta_override_is_recorded(self):
        chain, _ = build_style_chain(
            "", opt.NONE, opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
            meta_overrides={"format": "tags", "strength": "strong"},
        )
        self.assertEqual(chain["_meta"]["format"], "tags")
        self.assertEqual(chain["_meta"]["strength"], "strong")

    def test_blank_override_is_ignored(self):
        chain, _ = build_style_chain(
            "", opt.NONE, opt.MODE_PICK, opt.CATEGORY_ALL, "", 0, 0,
            meta_overrides={"format": "", "strength": "subtle"},
        )
        self.assertNotIn("format", chain["_meta"])
        self.assertEqual(chain["_meta"]["strength"], "subtle")


def pick_artist(chain_json, label, detail=None, **kwargs):
    """Add one artist in Pick mode. Keeps the tests readable."""
    return add_artist(
        chain_json=chain_json,
        artist_label=label,
        mode=kwargs.pop("mode", opt.MODE_PICK),
        category=kwargs.pop("category", opt.ARTIST_CATEGORY_ALL),
        tag_filter=kwargs.pop("tag_filter", ""),
        seed=kwargs.pop("seed", 0),
        cycle_index=kwargs.pop("cycle_index", 0),
        artist_detail=detail or opt.DEFAULTS["artist_detail"],
    )


class ArtistNodeTests(unittest.TestCase):
    def test_pick_none_adds_nothing(self):
        chain, warnings = pick_artist("", opt.NONE)
        self.assertEqual(chain["artists"], [])
        self.assertEqual(warnings, [])

    def test_default_mode_produces_an_artist(self):
        """A freshly dropped Artist node renders something. It used to sit
        on None until configured, which reads as broken rather than
        empty, and is why the boolean became a mode."""
        chain, warnings = pick_artist("", opt.NONE, mode=opt.DEFAULTS["artist_mode"])
        self.assertEqual(len(chain["artists"]), 1)
        self.assertEqual(warnings, [])

    def test_random_is_reproducible_for_a_seed(self):
        a, _ = pick_artist("", opt.NONE, mode=opt.MODE_RANDOM, seed=99)
        b, _ = pick_artist("", opt.NONE, mode=opt.MODE_RANDOM, seed=99)
        self.assertEqual(len(a["artists"]), 1)
        self.assertEqual(a["artists"][0]["label"], b["artists"][0]["label"])

    def test_random_respects_the_category_filter(self):
        chain, _ = pick_artist(
            "", opt.NONE, mode=opt.MODE_RANDOM, seed=7, category="Photography"
        )
        self.assertEqual(chain["artists"][0]["category"], "photography")

    def test_random_respects_the_tag_filter(self):
        chain, _ = pick_artist(
            "", opt.NONE, mode=opt.MODE_RANDOM, seed=3, tag_filter="woodblock"
        )
        record = chain["artists"][0]
        haystack = (record["descriptor"] + record["label"]).lower()
        self.assertIn("woodblock", haystack)

    def test_cycle_is_deterministic_and_wraps(self):
        first, _ = pick_artist("", opt.NONE, mode=opt.MODE_CYCLE, cycle_index=0)
        again, _ = pick_artist("", opt.NONE, mode=opt.MODE_CYCLE, cycle_index=0)
        second, _ = pick_artist("", opt.NONE, mode=opt.MODE_CYCLE, cycle_index=1)
        wrapped, _ = pick_artist(
            "", opt.NONE, mode=opt.MODE_CYCLE, cycle_index=len(ARTISTS)
        )
        self.assertEqual(first["artists"][0]["label"], again["artists"][0]["label"])
        self.assertNotEqual(first["artists"][0]["label"],
                            second["artists"][0]["label"])
        self.assertEqual(first["artists"][0]["label"],
                         wrapped["artists"][0]["label"])

    def test_impossible_filter_warns_instead_of_silently_adding_nothing(self):
        chain, warnings = pick_artist(
            "", opt.NONE, mode=opt.MODE_RANDOM, tag_filter="zzzznotathing"
        )
        self.assertEqual(chain["artists"], [])
        self.assertTrue(any("no artist matches" in w for w in warnings))

    def test_pick_by_label(self):
        chain, _ = pick_artist("", "Claude Monet")
        self.assertEqual(chain["artists"][0]["label"], "Claude Monet")

    def test_unknown_label_warns_and_applies_nothing(self):
        chain, warnings = pick_artist("", "Not A Real Person")
        self.assertEqual(chain["artists"], [])
        self.assertTrue(any("no artist named" in w for w in warnings))

    def test_cap_keeps_the_fifth_and_refuses_the_sixth(self):
        """Regression: the cap used to drop the fifth artist, so the
        effective maximum was four, not the five it advertised."""
        chain_json = ""
        labels = sorted(a["label"] for a in ARTISTS.values())[:opt.ARTIST_MAX]
        for label in labels:
            chain, warnings = pick_artist(chain_json, label)
            chain_json = dump_chain(chain)
        self.assertEqual(len(chain["artists"]), opt.ARTIST_MAX)

        overflow, warnings = pick_artist(chain_json, "Claude Monet")
        self.assertEqual(len(overflow["artists"]), opt.ARTIST_MAX)
        self.assertTrue(any("maximum" in w for w in warnings))

    def test_the_same_artist_is_not_added_twice(self):
        """Two Artist nodes on the shipped defaults (Random, seed 0)
        resolve to the same artist, so the chain carried it twice: the
        descriptor rendered twice in the prompt and the duplicate counted
        against ARTIST_MAX. Blend already refused to merge an artist the
        chain holds; this is the same rule where the artist is added."""
        chain, _ = pick_artist("", "Claude Monet")
        again, warnings = pick_artist(dump_chain(chain), "Claude Monet")
        self.assertEqual(len(again["artists"]), 1)
        self.assertTrue(any("already holds" in w for w in warnings))

    def test_a_different_artist_still_stacks(self):
        chain, _ = pick_artist("", "Claude Monet")
        both, _ = pick_artist(dump_chain(chain), "Ansel Adams")
        self.assertEqual(
            [a["label"] for a in both["artists"]],
            ["Claude Monet", "Ansel Adams"],
        )

    def test_warns_past_the_threshold(self):
        chain_json = ""
        labels = sorted(a["label"] for a in ARTISTS.values())[:4]
        seen = []
        for label in labels:
            chain, warnings = pick_artist(chain_json, label)
            chain_json = dump_chain(chain)
            seen.extend(warnings)
        self.assertTrue(any("chained" in w for w in seen))

    def test_artist_detail_sets_meta(self):
        chain, _ = pick_artist("", opt.NONE, "Descriptor only")
        self.assertEqual(chain["_meta"]["artist_detail"], "descriptor_only")

    def test_artist_detail_is_always_recorded(self):
        """There is no longer an inherit option: the widget always says
        what it wants, so the chain always carries it."""
        chain, _ = pick_artist("", opt.NONE, "Names only")
        self.assertEqual(chain["_meta"]["artist_detail"], "names_only")


def pick_modifier(chain_json, axis, label, **kwargs):
    """Apply one modifier in Pick mode unless told otherwise."""
    return apply_modifier(
        chain_json=chain_json,
        axis=axis,
        modifier_label=label,
        mode=kwargs.pop("mode", opt.MODE_PICK),
        seed=kwargs.pop("seed", 0),
        cycle_index=kwargs.pop("cycle_index", 0),
    )


class ModifierNodeTests(unittest.TestCase):
    def test_off_applies_nothing(self):
        chain, warnings = pick_modifier("", "lighting", opt.OFF)
        self.assertEqual(chain["modifiers"], [])
        self.assertEqual(warnings, [])

    def test_a_fresh_node_applies_nothing(self):
        """The one node that does not default to Random. A modifier is a
        deliberate finishing tilt, so landing one on the canvas must not
        change the image on its own."""
        chain, warnings = pick_modifier(
            "", opt.DEFAULTS["axis"], opt.DEFAULTS["modifier"],
            mode=opt.DEFAULTS["modifier_mode"],
        )
        self.assertEqual(chain["modifiers"], [])
        self.assertEqual(warnings, [])

    def test_applies_modifier_on_its_axis(self):
        chain, warnings = pick_modifier("", "lighting", "Golden Hour")
        self.assertEqual(len(chain["modifiers"]), 1)
        self.assertEqual(chain["modifiers"][0]["axis"], "lighting")
        self.assertEqual(warnings, [])

    def test_axis_mismatch_names_the_right_axis(self):
        _, warnings = pick_modifier("", "mood", "Golden Hour")
        self.assertTrue(any("'lighting' axis" in w for w in warnings))

    def test_same_axis_replaces_with_a_warning(self):
        first, _ = pick_modifier("", "lighting", "Golden Hour")
        second, warnings = pick_modifier(
            dump_chain(first), "lighting", "Rim Lighting"
        )
        self.assertEqual(len(second["modifiers"]), 1)
        self.assertEqual(second["modifiers"][0]["label"], "Rim Lighting")
        self.assertTrue(any("Replaced" in w for w in warnings))

    def test_different_axes_stack(self):
        first, _ = pick_modifier("", "lighting", "Golden Hour")
        second, _ = pick_modifier(dump_chain(first), "mood", "Serene")
        self.assertEqual(len(second["modifiers"]), 2)

    def test_random_is_reproducible_and_on_axis(self):
        a, _ = pick_modifier("", "mood", opt.OFF, mode=opt.MODE_RANDOM, seed=5)
        b, _ = pick_modifier("", "mood", opt.OFF, mode=opt.MODE_RANDOM, seed=5)
        self.assertEqual(a["modifiers"][0]["label"], b["modifiers"][0]["label"])
        self.assertEqual(a["modifiers"][0]["axis"], "mood")

    def test_cycle_steps_the_axis_and_wraps(self):
        axis = "lighting"
        size = len(MODIFIERS_BY_AXIS[axis])
        first, _ = pick_modifier("", axis, opt.OFF, mode=opt.MODE_CYCLE,
                                 cycle_index=0)
        second, _ = pick_modifier("", axis, opt.OFF, mode=opt.MODE_CYCLE,
                                  cycle_index=1)
        wrapped, _ = pick_modifier("", axis, opt.OFF, mode=opt.MODE_CYCLE,
                                   cycle_index=size)
        self.assertEqual(first["modifiers"][0]["axis"], axis)
        self.assertNotEqual(first["modifiers"][0]["label"],
                            second["modifiers"][0]["label"])
        self.assertEqual(first["modifiers"][0]["label"],
                         wrapped["modifiers"][0]["label"])

    def test_blocked_axis_is_refused_with_a_reason(self):
        chain = parse_chain("")
        chain["style"] = {"id": "s", "label": "S", "blocks": ["color_grade"]}
        result, warnings = pick_modifier(
            dump_chain(chain), "color_grade", "Sepia"
        )
        self.assertEqual(result["modifiers"], [])
        self.assertTrue(any("already fixes" in w for w in warnings))


class BlendTests(unittest.TestCase):
    A = {"id": "a", "label": "A", "tags": "a1, a2, a3, a4",
         "prose": "A prose.", "negative": "na", "blocks": []}
    B = {"id": "b", "label": "B", "tags": "b1, b2, b3, b4",
         "prose": "B prose.", "negative": "nb", "blocks": []}

    def test_ratio_changes_the_output_between_the_endpoints(self):
        """Regression: the ratio slider used to be inert, producing an
        identical string for every value in (0.01, 0.99)."""
        seen = {
            blend_styles(self.A, self.B, r)["tags"]
            for r in (0.2, 0.35, 0.5, 0.65, 0.8)
        }
        self.assertGreater(len(seen), 1)

    def test_low_ratio_leads_with_a(self):
        self.assertTrue(blend_styles(self.A, self.B, 0.2)["tags"].startswith("a1"))

    def test_high_ratio_leads_with_b(self):
        self.assertTrue(blend_styles(self.A, self.B, 0.8)["tags"].startswith("b1"))

    def test_higher_ratio_gives_b_more_of_the_tag_budget(self):
        low = blend_styles(self.A, self.B, 0.25)["tags"]
        high = blend_styles(self.A, self.B, 0.75)["tags"]
        count_b = lambda s: sum(1 for t in s.split(", ") if t.startswith("b"))  # noqa: E731
        self.assertGreater(count_b(high), count_b(low))

    def test_each_side_always_contributes_something(self):
        for ratio in (0.05, 0.5, 0.95):
            tags = blend_styles(self.A, self.B, ratio)["tags"]
            self.assertTrue(any(t.startswith("a") for t in tags.split(", ")))
            self.assertTrue(any(t.startswith("b") for t in tags.split(", ")))

    def test_negatives_from_both_sides_survive(self):
        neg = blend_styles(self.A, self.B, 0.5)["negative"]
        self.assertIn("na", neg)
        self.assertIn("nb", neg)

    def test_endpoints_are_pure(self):
        chain_a = dump_chain({"_meta": {}, "style": self.A,
                              "modifiers": [], "artists": []})
        chain_b = dump_chain({"_meta": {}, "style": self.B,
                              "modifiers": [], "artists": []})
        pure_a, _ = build_blend_chain(chain_a, chain_b, 0.0)
        pure_b, _ = build_blend_chain(chain_a, chain_b, 1.0)
        self.assertEqual(pure_a["style"]["id"], "a")
        self.assertEqual(pure_b["style"]["id"], "b")

    def test_missing_b_passes_a_through_with_a_warning(self):
        chain_a = dump_chain({"_meta": {}, "style": self.A,
                              "modifiers": [], "artists": []})
        result, warnings = build_blend_chain(chain_a, "", 0.5)
        self.assertEqual(result["style"]["id"], "a")
        self.assertTrue(any("style B" in w for w in warnings))

    def test_a_prompt_wired_into_a_chain_input_is_not_a_chain(self):
        """Belt and braces behind the socket type. If a rendered prompt
        ever reaches a chain input, it must read as no chain rather than
        as a corrupt one."""
        chain_a = dump_chain({"_meta": {}, "style": self.A,
                              "modifiers": [], "artists": []})
        result, warnings = build_blend_chain(
            chain_a, "A cat on a wall. Rendered as a test slide.", 0.5
        )
        self.assertEqual(result["style"]["id"], "a")
        self.assertTrue(any("style B" in w for w in warnings))

    def test_modifiers_from_the_b_branch_survive(self):
        """Regression: only artists were merged, while the comment beside
        the loop claimed artists and modifiers both."""
        chain_a = dump_chain({"_meta": {}, "style": self.A, "artists": [],
                              "modifiers": [{"axis": "lighting",
                                             "label": "Golden Hour"}]})
        chain_b = dump_chain({"_meta": {}, "style": self.B, "artists": [],
                              "modifiers": [{"axis": "era", "label": "1970s"}]})
        result, warnings = build_blend_chain(chain_a, chain_b, 0.5)
        axes = sorted(m["axis"] for m in result["modifiers"])
        self.assertEqual(axes, ["era", "lighting"])
        self.assertEqual(warnings, [])

    def test_the_a_branch_keeps_an_axis_both_sides_claim(self):
        """One modifier per axis still holds across a blend, and A is the
        primary chain, so B's loss is reported rather than silent."""
        chain_a = dump_chain({"_meta": {}, "style": self.A, "artists": [],
                              "modifiers": [{"axis": "lighting",
                                             "label": "Golden Hour"}]})
        chain_b = dump_chain({"_meta": {}, "style": self.B, "artists": [],
                              "modifiers": [{"axis": "lighting",
                                             "label": "Moonlight"}]})
        result, warnings = build_blend_chain(chain_a, chain_b, 0.5)
        self.assertEqual([m["label"] for m in result["modifiers"]],
                         ["Golden Hour"])
        self.assertTrue(any("both branches set the lighting" in w
                            for w in warnings))


def draw_sheet(subject, count, category=None, tag_filter="", seed=1,
               chain_json="", styles=""):
    """Build a sheet from the seeded pool. Keeps the tests readable."""
    return build_sheet(
        chain_json=chain_json,
        user_prompt=subject,
        styles=styles,
        count=count,
        category=category or opt.CATEGORY_ALL,
        tag_filter=tag_filter,
        seed=seed,
    )


class SheetTests(unittest.TestCase):
    def test_emits_one_prompt_per_style(self):
        prompts, negatives, labels, warnings = draw_sheet("a cat", 5)
        self.assertEqual(len(prompts), 5)
        self.assertEqual(len(negatives), 5)
        self.assertEqual(len(labels), 5)
        self.assertEqual(warnings, [])

    def test_every_prompt_carries_the_subject(self):
        prompts, _, _, _ = draw_sheet("a red bicycle", 4, seed=2)
        for prompt in prompts:
            self.assertIn("red bicycle", prompt.lower())

    def test_prompts_differ_from_each_other(self):
        prompts, _, _, _ = draw_sheet("a cat", 6, seed=3)
        self.assertEqual(len(set(prompts)), 6)

    def test_reproducible_for_a_seed(self):
        first, _, _, _ = draw_sheet("a cat", 4, seed=9)
        second, _, _, _ = draw_sheet("a cat", 4, seed=9)
        self.assertEqual(first, second)

    def test_warns_when_the_pool_is_smaller_than_requested(self):
        _, _, _, warnings = draw_sheet("a cat", 999, category="comics")
        self.assertTrue(any("fewer than" in w for w in warnings))

    def test_empty_pool_warns_and_emits_nothing(self):
        prompts, _, _, warnings = draw_sheet("a cat", 4, tag_filter="zzzznope")
        self.assertEqual(prompts, [])
        self.assertTrue(any("no style matches" in w for w in warnings))

    def test_upstream_artists_apply_to_every_entry(self):
        chain, _ = pick_artist("", "Claude Monet")
        prompts, _, _, _ = draw_sheet(
            "a cat", 3, seed=4, chain_json=dump_chain(chain)
        )
        for prompt in prompts:
            self.assertIn("Monet", prompt)


class SheetStyleListTests(unittest.TestCase):
    """The explicit style list, which is what the seeded draw is for when
    you have not chosen. Choosing beats drawing, so it wins outright."""

    def test_accepts_one_per_line_and_keeps_the_order(self):
        self.assertEqual(
            parse_style_list("Cyanotype\nRisograph\n"),
            ["Cyanotype", "Risograph"],
        )

    def test_accepts_a_comma_separated_list(self):
        self.assertEqual(
            parse_style_list("Cyanotype, Risograph"),
            ["Cyanotype", "Risograph"],
        )

    def test_drops_blanks_and_duplicates_without_reordering(self):
        self.assertEqual(
            parse_style_list("Risograph\n\nCyanotype\nrisograph\n  \n"),
            ["Risograph", "Cyanotype"],
        )

    def test_the_list_wins_over_count_and_filters(self):
        """A list somebody typed out must not be silently trimmed to
        `count` or filtered away by a category they left set."""
        prompts, _, labels, warnings = draw_sheet(
            "a cat", 2, category="Comics", styles="Cyanotype, Risograph"
        )
        self.assertEqual(labels, ["Cyanotype", "Risograph"])
        self.assertEqual(len(prompts), 2)
        self.assertEqual(warnings, [])

    def test_a_well_known_alias_resolves(self):
        """The box is hand-typeable, so "Ukiyo-e" has to work. It is an
        alias of Woodblock Print rather than a label of its own."""
        _, _, labels, warnings = draw_sheet("a cat", 4, styles="Ukiyo-e")
        self.assertEqual(labels, ["Woodblock Print"])
        self.assertEqual(warnings, [])

    def test_a_label_beats_someone_elses_alias(self):
        """12 aliases collide with a real label elsewhere in the pack.
        "Deep Focus" is both, and the label is what you meant."""
        _, _, labels, _ = draw_sheet("a cat", 4, styles="Deep Focus")
        self.assertEqual(labels, ["Deep Focus"])

    def test_an_ambiguous_alias_names_the_candidates(self):
        """"diorama" is claimed by Tilt-Shift and Museum Diorama.
        Picking one would be a coin flip presented as an answer."""
        _, _, labels, warnings = draw_sheet("a cat", 4, styles="diorama")
        self.assertEqual(labels, [])
        self.assertTrue(any("Museum Diorama" in w and "Tilt-Shift" in w
                            for w in warnings))

    def test_an_unknown_name_is_named_and_skipped(self):
        prompts, _, labels, warnings = draw_sheet(
            "a cat", 4, styles="Cyanotype, Not A Real Style"
        )
        self.assertEqual(labels, ["Cyanotype"])
        self.assertEqual(len(prompts), 1)
        self.assertTrue(any("Not A Real Style" in w for w in warnings))

    def test_all_names_unknown_emits_nothing_and_says_so(self):
        prompts, _, _, warnings = draw_sheet("a cat", 4, styles="Nope, Also Nope")
        self.assertEqual(prompts, [])
        self.assertTrue(any("none of the chosen styles" in w for w in warnings))

    def test_an_empty_list_falls_back_to_the_seeded_draw(self):
        prompts, _, _, _ = draw_sheet("a cat", 3, styles="   \n  ")
        self.assertEqual(len(prompts), 3)


class MetaTests(unittest.TestCase):
    def test_unset_falls_back_to_defaults(self):
        meta = resolve_meta(parse_chain(""))
        self.assertEqual(meta["format"], "prose")
        self.assertEqual(meta["placement"], "append")
        self.assertEqual(meta["strength"], "normal")

    def test_no_default_is_the_removed_auto(self):
        """Both "auto" options are gone: format's was a fiction, and
        placement's hid a real rule behind a word that described nothing."""
        meta = resolve_meta(parse_chain(""))
        self.assertNotIn("auto", meta.values())

    def test_explicit_values_win(self):
        chain = parse_chain('{"_meta":{"format":"tags","placement":"append"}}')
        meta = resolve_meta(chain)
        self.assertEqual(meta["format"], "tags")
        self.assertEqual(meta["placement"], "append")


class SchemaOptionTests(unittest.TestCase):
    """Validate every dropdown without needing ComfyUI installed.

    The previous suite built these through ``io.Schema``, so the whole
    class skipped in CI and raised NameError anywhere ComfyUI existed.
    """

    #: Every entry in DEFAULTS and the option list it must belong to.
    #: A KeyError here means a default was added without a list, which is
    #: the failure this test exists to catch, so it is not softened.
    OPTION_LISTS = {
        "mode": opt.MODES,
        "artist_mode": opt.MODES,
        "modifier_mode": opt.MODES,
        "style": opt.style_options,
        "category": opt.category_options,
        "artist": opt.artist_options,
        "artist_category": opt.artist_category_options,
        "axis": opt.axis_options,
        "modifier": opt.modifier_options,
        "format": opt.FORMATS,
        "strength": opt.STRENGTHS,
        "placement": opt.PLACEMENTS,
        "artist_detail": opt.ARTIST_DETAILS,
    }

    def _options(self, name):
        source = self.OPTION_LISTS[name]
        return list(source() if callable(source) else source)

    def test_every_default_is_in_its_option_list(self):
        for name, default in opt.DEFAULTS.items():
            with self.subTest(name):
                self.assertIn(default, self._options(name),
                              f"default {default!r} for '{name}' is not an option")

    def test_every_default_has_an_option_list(self):
        missing = sorted(set(opt.DEFAULTS) - set(self.OPTION_LISTS))
        self.assertEqual(missing, [], "these defaults are unchecked")

    def test_no_option_list_has_duplicates(self):
        for name, values in (
            ("style", opt.style_options()),
            ("artist", opt.artist_options()),
            ("category", opt.category_options()),
            ("modifier", opt.modifier_options()),
            ("axis", opt.axis_options()),
        ):
            self.assertEqual(len(values), len(set(values)),
                             f"'{name}' options contain a duplicate")

    def test_sentinels_come_first(self):
        self.assertEqual(opt.style_options()[0], opt.NONE)
        self.assertEqual(opt.artist_options()[0], opt.NONE)
        self.assertEqual(opt.modifier_options()[0], opt.OFF)
        self.assertEqual(opt.category_options()[0], opt.CATEGORY_ALL)

    def test_random_is_not_a_style_option(self):
        """Regression: 'Random' sat in this list, was the default, and
        resolved to no style at all."""
        self.assertNotIn("Random", opt.style_options())
        self.assertNotIn("Random", opt.artist_options())

    def test_no_record_claims_a_sentinel_label(self):
        for values in (opt.style_options()[1:], opt.artist_options()[1:],
                       opt.modifier_options()[1:]):
            for value in values:
                self.assertNotIn(value, opt.SENTINELS)

    def test_per_axis_modifier_lists_are_subsets_of_the_full_list(self):
        full = set(opt.modifier_options())
        for axis, values in opt.modifier_options_by_axis().items():
            self.assertTrue(set(values) <= full, f"axis '{axis}' has strays")
            for label in values[1:]:
                self.assertEqual(get_modifier(label, axis)["axis"], axis)

    def test_category_options_are_readable_names(self):
        """Regression: the dropdown and the gallery tabs showed raw ids,
        so 3D & Digital appeared as "Three D Digital"."""
        options = opt.category_options()
        self.assertEqual(options[0], opt.CATEGORY_ALL)
        for name in options[1:]:
            self.assertNotIn("_", name, f"{name!r} is an id, not a name")
        self.assertIn("3D & Digital", options)
        self.assertNotIn("Three D Digital", options)

    def test_every_category_label_resolves_back_to_its_id(self):
        for cid in CATEGORIES:
            self.assertEqual(opt.category_id(CATEGORY_LABELS[cid]), cid)

    def test_category_all_means_no_filter(self):
        self.assertIsNone(opt.category_id(opt.CATEGORY_ALL))
        self.assertIsNone(opt.category_id(""))

    def test_unknown_category_does_not_raise(self):
        self.assertIsNone(opt.category_id("not a category"))

    def test_no_option_list_offers_inherit(self):
        """inherit meant "use the default" on a node that had no upstream,
        which is a setting that does nothing."""
        for values in (list(opt.FORMATS), list(opt.STRENGTHS),
                       list(opt.PLACEMENTS), list(opt.ARTIST_DETAILS)):
            self.assertNotIn("inherit", values)

    def test_format_has_no_fake_auto(self):
        """auto chose prose whenever a style had prose text, and every
        style has prose text, so it was always prose."""
        self.assertNotIn("auto", opt.FORMATS)
        self.assertEqual(set(opt.FORMATS), {"prose", "tags"})

    #: Era reads by date, not by name. Sorting alphabetically drops 1920s
    #: between "Ancient Classical" and "Edwardian", and insertion order
    #: once put 1970s ahead of 1920s.
    ERA_ORDER = ["Ancient Classical", "Medieval", "Renaissance",
                 "Baroque (17th Century)", "Georgian (18th Century)",
                 "Victorian", "Edwardian", "1910s", "1920s", "1930s-40s", "1950s", "1960s", "1970s", "1980s",
                 "1990s", "2000s", "2010s", "2020s", "Near Future", "Far Future"]

    #: period_dress is era's sibling: it reads by the same dates, so it is
    #: exempt from the alphabetical rule for the same reason. Keeping the
    #: two lists side by side is also how the pairing is checked - one
    #: dress entry per era, in the same order.
    PERIOD_DRESS_ORDER = ["Ancient Classical Dress", "Medieval Dress",
                          "Renaissance Dress", "Baroque Dress (17th Century)",
                          "Georgian Dress (18th Century)", "Victorian Dress",
                          "Edwardian Dress", "1910s Dress", "1920s Dress",
                          "1930s-40s Dress", "1950s Dress", "1960s Dress",
                          "1970s Dress", "1980s Dress", "1990s Dress",
                          "2000s Dress", "2010s Dress", "2020s Dress",
                          "Near Future Dress", "Far Future Dress"]

    #: The axes that read by date rather than by name.
    CHRONOLOGICAL_AXES = {"era", "period_dress"}

    def test_era_modifiers_are_chronological(self):
        self.assertEqual(opt.modifier_options("era")[1:], self.ERA_ORDER)

    def test_period_dress_modifiers_are_chronological(self):
        self.assertEqual(opt.modifier_options("period_dress")[1:],
                         self.PERIOD_DRESS_ORDER)

    def test_every_era_has_exactly_one_period_dress_partner(self):
        """The split is only non-lossy if the pairing is complete.

        era stopped naming garments in 0.12.0 and period_dress is where
        that text went. An era with no dress partner is wardrobe the pack
        used to be able to produce and now cannot.
        """
        self.assertEqual(len(self.PERIOD_DRESS_ORDER), len(self.ERA_ORDER))
        for era, dress in zip(self.ERA_ORDER, self.PERIOD_DRESS_ORDER):
            with self.subTest(era):
                stem = era.split(" (")[0]
                self.assertIn(stem, dress)

    def test_non_chronological_modifiers_are_alphabetical(self):
        for axis in opt.axis_options():
            if axis in self.CHRONOLOGICAL_AXES:
                continue
            labels = opt.modifier_options(axis)[1:]
            with self.subTest(axis):
                self.assertEqual(labels, sorted(labels, key=str.lower),
                                 f"{axis} modifiers are out of order")

    def test_every_axis_has_a_usable_number_of_modifiers(self):
        """Three options is not an axis. Each one carries a real choice."""
        for axis in opt.axis_options():
            with self.subTest(axis):
                self.assertGreaterEqual(len(opt.modifier_options(axis)) - 1, 10)

    def test_option_lists_are_not_empty(self):
        self.assertGreater(len(opt.style_options()), 100)
        self.assertGreater(len(opt.artist_options()), 100)
        self.assertEqual(len(opt.category_options()), 13)


class DocumentedCountTests(unittest.TestCase):
    """The README and the registry description quote counts.

    They drifted once already: the README claimed 190 styles and 247
    artists while the pack shipped 468 and 597.
    """

    DOCS = ("README.md", "pyproject.toml", "ARCHITECTURE.md")

    #: An open-ended count may not undershoot the truth by more than this.
    #: "430+" beside 433 styles is a fair way to say "about this many"
    #: without a doc edit on every addition. "200+" beside 433 is not.
    MAX_UNDERSHOOT = 60

    def _quoted(self, noun: str) -> list[tuple[str, int, bool]]:
        """Every "<number> <noun>" in the docs.

        Returns (filename, number, is_open_ended). A trailing "+" makes it
        open-ended: a lower bound rather than a claim of exactness, which
        is how the docs avoid needing an edit every time a style lands.

        Plain tokenising rather than a regex. Writing a pattern through
        the tooling that maintains this file has twice produced one that
        silently matched nothing, and a guard that matches nothing passes
        forever while checking nothing.
        """
        found: list[tuple[str, int, bool]] = []
        for name in self.DOCS:
            path = ROOT / name
            self.assertTrue(path.is_file(), f"doc not found: {path}")
            words = path.read_text(encoding="utf-8").replace(",", " ").split()
            # Quotes matter: the registry description lives inside a TOML
            # string, so its first number arrives as '"433'.
            clean = [w.strip("*_()[].,:;`" + chr(34) + chr(39)) for w in words]
            for index, token in enumerate(clean):
                open_ended = token.endswith("+")
                digits = token[:-1] if open_ended else token
                if not digits.isdigit():
                    continue
                # Allow one adjective in between, as in "433 visual styles".
                window = [w.lower() for w in clean[index + 1:index + 3]]
                if noun in window:
                    found.append((name, int(digits), open_ended))
        return found

    def _assert_counts(self, noun: str, actual: int) -> None:
        quoted = self._quoted(noun)
        self.assertTrue(quoted, f"no document quotes a {noun[:-1]} count")
        wrong = []
        for name, value, open_ended in quoted:
            if open_ended:
                if value > actual or actual - value > self.MAX_UNDERSHOOT:
                    wrong.append((name, f"{value}+"))
            elif value != actual:
                wrong.append((name, value))
        self.assertEqual(wrong, [], f"docs disagree with {actual} {noun}")

    def test_documented_style_count_is_correct(self):
        self._assert_counts("styles", len(STYLES))

    def test_documented_artist_count_is_correct(self):
        self._assert_counts("artists", len(ARTISTS))

    def test_documented_modifier_count_is_correct(self):
        self._assert_counts("modifiers", len(MODIFIERS))


class ExampleWorkflowTests(unittest.TestCase):
    """The shipped example workflows must match the current schemas.

    Both examples had drifted: widget arrays still carried a removed
    `sheet_count` and a removed `name_handling`, and a category value of
    "None" that is no longer an option. A workflow that will not load is
    worse than no example, and nothing was checking.
    """

    EXAMPLES = sorted((ROOT / "examples").glob("*.json"))

    # The single source of truth moved to schema_options.WIDGET_ORDER, so
    # that both this test and the JS fixture generator
    # (scripts/dump_frontend_fixtures.py) read the same list.
    EXPECTED = opt.WIDGET_ORDER

    OPTIONS = {
        "mode": lambda: list(opt.MODES),
        "style": opt.style_options,
        "category": opt.category_options,
        "artist": opt.artist_options,
        "axis": opt.axis_options,
        "modifier": opt.modifier_options,
        "format": lambda: list(opt.FORMATS),
        "strength": lambda: list(opt.STRENGTHS),
        "placement": lambda: list(opt.PLACEMENTS),
        "artist_detail": lambda: list(opt.ARTIST_DETAILS),
        # Qualified entries win over the bare name.
        "StylebookArtist.category": opt.artist_category_options,
    }

    def test_chain_sockets_carry_the_chain_type(self):
        """A chain socket must not be a STRING any more. When it was, the
        prompt output connected happily to a chain input and then parsed
        as an empty chain, which is what made Blend report an unconnected
        style B while looking wired up."""
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            for node in graph["nodes"]:
                if not str(node["type"]).startswith("Stylebook"):
                    continue
                slots = (node.get("inputs") or []) + (node.get("outputs") or [])
                for slot in slots:
                    if slot.get("name") in ("style_chain", "style_b"):
                        with self.subTest(f"{path.name}:{node['type']}"):
                            self.assertEqual(slot.get("type"), opt.CHAIN_TYPE)

    def test_examples_exist(self):
        self.assertTrue(self.EXAMPLES, "no example workflows found")

    def test_examples_are_valid_json(self):
        for path in self.EXAMPLES:
            with self.subTest(path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_stylebook_nodes_have_the_right_widget_count(self):
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            for node in graph["nodes"]:
                expected = self.EXPECTED.get(node["type"])
                if expected is None:
                    continue
                values = node.get("widgets_values") or []
                with self.subTest(f"{path.name}:{node['type']}"):
                    self.assertEqual(
                        len(values), len(expected),
                        f"{node['type']} has {len(values)} widget values, "
                        f"schema expects {len(expected)}: {expected}")

    def test_combo_values_are_real_options(self):
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            for node in graph["nodes"]:
                expected = self.EXPECTED.get(node["type"])
                if expected is None:
                    continue
                values = node.get("widgets_values") or []
                for name, value in zip(expected, values):
                    # A widget name is not unique across nodes: `category`
                    # narrows styles on Style and Sheet, and artists on
                    # Artist, and those are different option lists.
                    builder = self.OPTIONS.get(f"{node['type']}.{name}",
                                               self.OPTIONS.get(name))
                    if builder is None:
                        continue
                    with self.subTest(f"{path.name}:{node['type']}.{name}"):
                        self.assertIn(value, builder(),
                                      f"'{value}' is not a valid {name}")

    NUMERIC = {"seed", "cycle_index", "count", "ratio"}

    def test_numeric_widgets_hold_numbers(self):
        """The widget count alone is a weak check: a removed int widget and
        an added string widget cancel out. Positions must also hold the
        right kind of value."""
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            for node in graph["nodes"]:
                expected = self.EXPECTED.get(node["type"])
                if expected is None:
                    continue
                values = node.get("widgets_values") or []
                for name, value in zip(expected, values):
                    with self.subTest(f"{path.name}:{node['type']}.{name}"):
                        if name in self.NUMERIC:
                            self.assertIsInstance(
                                value, (int, float),
                                f"{name} should be a number, got {value!r}")
                        elif name in self.OPTIONS or name == "control_after_generate":
                            self.assertIsInstance(
                                value, str,
                                f"{name} should be a string, got {value!r}")

    def test_chroma_examples_do_not_use_a_checkpoint_loader(self):
        """Chroma is a UNet, not a checkpoint.

        Both examples loaded Chroma1-HD through CheckpointLoaderSimple,
        which cannot work: it needs UNETLoader plus a chroma CLIPLoader
        plus a VAELoader.
        """
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            types = {n["type"] for n in graph["nodes"]}
            with self.subTest(path.name):
                if any("hroma" in json.dumps(n.get("widgets_values", []))
                       for n in graph["nodes"]):
                    self.assertNotIn("CheckpointLoaderSimple", types)
                    self.assertIn("UNETLoader", types)
                    self.assertIn("CLIPLoader", types)
                    self.assertIn("VAELoader", types)

    def test_every_link_refers_to_real_nodes_and_slots(self):
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            ids = {n["id"] for n in graph["nodes"]}
            by_id = {n["id"]: n for n in graph["nodes"]}
            for link in graph["links"]:
                link_id, src, src_slot, dst, dst_slot, _ = link
                with self.subTest(f"{path.name}:link{link_id}"):
                    self.assertIn(src, ids, f"link {link_id} from unknown node")
                    self.assertIn(dst, ids, f"link {link_id} to unknown node")
                    self.assertLess(src_slot, len(by_id[src].get("outputs", [])),
                                    f"link {link_id} uses a missing output slot")
                    self.assertLess(dst_slot, len(by_id[dst].get("inputs", [])),
                                    f"link {link_id} uses a missing input slot")

    def test_stylebook_prompt_reaches_a_text_encoder(self):
        """An example that never wires prompt into CLIPTextEncode is not
        showing anyone how to use the pack."""
        for path in self.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            by_id = {n["id"]: n for n in graph["nodes"]}
            reaches = False
            for link in graph["links"]:
                _, src, src_slot, dst, _, _ = link
                src_node, dst_node = by_id[src], by_id[dst]
                if (src_node["type"].startswith("Stylebook")
                        and dst_node["type"] == "CLIPTextEncode"
                        and src_slot == 0):
                    reaches = True
            with self.subTest(path.name):
                self.assertTrue(reaches, "prompt never reaches a CLIPTextEncode")


class IdentityForgeDriftTests(unittest.TestCase):
    """Catches the exact class of drift that broke
    stylebook_with_identity_forge.json: Identity Forge's own schema moved
    (a new field, a renamed output slot) out from under our saved example,
    and nothing here noticed until diagnose_workflow did it by hand.

    Best-effort and environment-gated: point ``IDENTITY_FORGE_REPO`` at a
    comfyui-identity-forge checkout to run this locally. It is a plain
    skip everywhere else, including CI, which has neither repo -- this is
    a local safety net, not a hard gate.

    Runs in a subprocess, not this process. Both packages import a
    top-level ``data`` package; in-process, Stylebook's own ``data`` (from
    this very test run) shadows Identity Forge's in ``sys.modules``, and
    ``from data.fields import ...`` inside Identity Forge's node module
    resolves to Stylebook's data layer instead, which has no ``fields``
    submodule. A fresh subprocess never loads Stylebook's ``data`` at all,
    so there is nothing to collide with. It reuses this repo's own
    ``tests/comfy_stub`` for ``comfy_api.latest.io`` -- Identity Forge's
    node module uses only Combo/ComfyNode/Int/NodeOutput/Schema/String,
    all of which the stub already covers -- with the same real-first,
    stub-fallback rule as everywhere else it is used.
    """

    def test_saved_identity_forge_widget_count_matches_the_live_schema(self):
        import subprocess

        repo = os.environ.get("IDENTITY_FORGE_REPO")
        if not repo:
            raise unittest.SkipTest(
                "IDENTITY_FORGE_REPO not set; point it at a comfyui-identity-forge "
                "checkout to run this locally"
            )
        repo_path = Path(repo)
        if not repo_path.is_dir():
            raise unittest.SkipTest(f"IDENTITY_FORGE_REPO does not exist: {repo}")

        stub_path = ROOT / "tests" / "comfy_stub"
        script = f"""
import sys
sys.path.insert(0, {str(repo_path)!r})
try:
    import comfy_api.latest.io
except ImportError:
    sys.path.insert(0, {str(stub_path)!r})
from nodes.identity_forge import IdentityForge
schema = IdentityForge.define_schema()
# hasattr(default) tells a widget-shaped Input apart from a socket-only
# one (e.g. a Custom chain type); force_input=True is the other way an
# Input that would otherwise be a widget stops serialising into
# widgets_values -- archetype_json is one, string-typed but connection-
# only. Both must be excluded for the count to match what ComfyUI
# actually writes.
count = sum(
    1 for inp in schema.inputs
    if hasattr(inp, "default") and not getattr(inp, "force_input", False)
)
seed = next((i for i in schema.inputs if i.id == "seed"), None)
if seed is not None and getattr(seed, "control_after_generate", None):
    count += 1
print(count)
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(
                f"could not inspect Identity Forge's live schema: "
                f"{result.stderr.strip().splitlines()[-1] if result.stderr else 'unknown error'}"
            )
        widget_count = int(result.stdout.strip())

        for path in ExampleWorkflowTests.EXAMPLES:
            graph = json.loads(path.read_text(encoding="utf-8"))
            for node in graph["nodes"]:
                if node["type"] != "IdentityForge":
                    continue
                values = node.get("widgets_values") or []
                with self.subTest(path.name):
                    self.assertEqual(
                        len(values), widget_count,
                        f"IdentityForge in {path.name} has {len(values)} widget "
                        f"values, the live schema expects {widget_count}"
                    )


if __name__ == "__main__":
    unittest.main()
