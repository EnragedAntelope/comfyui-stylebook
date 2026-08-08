"""The one ordering rule for every list a person reads.

A bare ``sorted()`` ranks by code point, which gets two things wrong in a
pack whose labels are art-historical names:

  - Accented names sort past Z. "Élisabeth Vigée Le Brun" was the *last*
    entry in the artist dropdown, after "ZBrush Sculpt Render", because
    É is U+00C9. "Cliché-Verre", "Naïve Art" and "Wiener Werkstätte" were
    misplaced in the style dropdown for the same reason.
  - Digits rank as text, so "16-Bit Pixel Art" came before "3D Matte
    Painting" and "8-Bit Pixel Art".

This folds accents and case away and compares runs of digits as numbers,
so "8-Bit" precedes "16-Bit" and "Naïve" sits where a reader expects it.

``js/stylebook_gallery.js`` implements the same rule with ``Intl.Collator``
(sensitivity "base", numeric true), because the gallery has to interleave
entries from a user's own ``user_styles.json`` that the generator never
saw. One rule in two languages is a drift risk, so a frontend test
asserts that re-sorting this module's output with the JS comparator is a
no-op. If the two ever disagree, CI says so.

Modifier axes are deliberately exempt: the ``era`` axis reads
chronologically (Ancient Classical -> Edwardian -> 1920s), and sorting it
would scatter the decades. See ``stylebook_nodes.schema_options``.
"""

from __future__ import annotations

import re
import unicodedata

#: Split a label into alternating text and digit runs. The capturing
#: group keeps the digits, which ``str.split`` would otherwise discard.
_DIGITS = re.compile(r"(\d+)")


def _fold(label: str) -> str:
    """Strip accents and case so "Naïve" and "Naive" rank together."""
    decomposed = unicodedata.normalize("NFKD", label)
    return "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    ).casefold()


def label_sort_key(label: str) -> tuple:
    """Sort key for a display label: accent- and case-insensitive, digits numeric.

    Every part is a uniform 3-tuple so a digit run and a text run never
    compare an ``int`` against a ``str`` -- which would raise rather than
    just sort oddly. Digit runs carry ``(0, value, "")`` and text runs
    ``(1, 0, text)``, so a number always ranks before a letter at the
    same position.

    The raw label trails as a tiebreak, because two labels can fold to
    the same key ("Naive Art" and "Naïve Art" would) and a sort with ties
    is only as stable as its input order.
    """
    parts = tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in _DIGITS.split(_fold(label))
        if part
    )
    return parts, label
