"""What `.comfyignore` keeps out of the registry package, and what it must not.

`.comfyignore` is gitignore syntax, which means an unanchored directory
pattern matches that directory name at *any* depth. A plain `previews/`
line intended for the build ledger at the repository root also matched
`js/previews/` -- the WebP sprite atlases the style gallery draws every
thumbnail from. Nothing in CI would have noticed: the tests pass, the
repository is fine, and the damage only appears in an install made from
the published archive, where the gallery opens with no pictures in it.

So this file re-implements just enough of the matcher to answer one
question -- does a file survive packaging? -- and pins the answer for the
handful of paths where being wrong is expensive.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMFYIGNORE = ROOT / ".comfyignore"

#: Syntax the matcher below does not implement. A pattern using any of it
#: would be silently under-matched here, so the test refuses to guess.
UNSUPPORTED = ("*", "?", "[", "!")


def _patterns() -> list[str]:
    lines = COMFYIGNORE.read_text(encoding="utf-8").splitlines()
    return [
        line.strip() for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def _matches(pattern: str, path: str) -> bool:
    """Gitignore matching, restricted to the syntax this file uses."""
    anchored = pattern.startswith("/")
    dir_only = pattern.endswith("/")
    core = pattern.strip("/")

    candidates = [path]
    if not anchored:
        parts = path.split("/")
        candidates = ["/".join(parts[i:]) for i in range(len(parts))]

    for candidate in candidates:
        if candidate.startswith(core + "/"):
            return True
        if not dir_only and candidate == core:
            return True
    return False


def is_packaged(path: str) -> bool:
    """True when *path* (repo-relative, posix) reaches the registry archive."""
    return not any(_matches(p, path) for p in _patterns())


class ComfyignoreSyntaxTests(unittest.TestCase):
    def test_no_pattern_uses_syntax_this_test_cannot_read(self):
        for pattern in _patterns():
            with self.subTest(pattern=pattern):
                for token in UNSUPPORTED:
                    self.assertNotIn(
                        token, pattern,
                        f"{pattern!r} uses glob syntax this guard does not "
                        f"implement, so it would be checked incorrectly. "
                        f"Extend _matches() before adding it.",
                    )

    def test_every_root_only_directory_pattern_is_anchored(self):
        """An unanchored `foo/` also excludes `js/foo/`, `data/foo/`, ...

        `node_modules/` is the deliberate exception: a nested one is still
        node_modules and still has no business in the archive.
        """
        allowed_unanchored = {"node_modules/"}
        for pattern in _patterns():
            if pattern in allowed_unanchored:
                continue
            with self.subTest(pattern=pattern):
                self.assertTrue(
                    pattern.startswith("/"),
                    f"{pattern!r} is unanchored, so it matches that name at "
                    f"any depth. Add a leading slash unless matching at "
                    f"depth is what you meant.",
                )


class PackagedContentTests(unittest.TestCase):
    """The archive has to carry a working pack, not just a tidy one."""

    MUST_SHIP = (
        "__init__.py",
        "requirements.txt",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        # Named in the README; a dead link on the registry page is worse
        # than the bytes.
        "ARCHITECTURE.md",
        "docs/custom-styles.md",
        "docs/images/style-gallery.png",
        # The data layer and the frontend that reads it.
        "data/styles/painting.py",
        "data/artists.py",
        "js/stylebook_data.js",
        # The corpus. It is a .json rather than a .js so ComfyUI's
        # extension glob does not parse 300 KB at app start, and that
        # makes it exactly the kind of file an ignore rule drops by
        # accident -- with the symptom being an empty gallery on a
        # registry install and a full one in the dev tree.
        "js/stylebook_data.json",
        "js/stylebook_gallery.js",
        "js/stylebook_gallery.css",
        # The whole point of the gallery.
        "js/previews/index.json",
        "js/previews/painting.webp",
    )

    MUST_NOT_SHIP = (
        "tests/test_engine.py",
        "scripts/build_previews.py",
        "examples/stylebook_basic.json",
        "package.json",
        "user_styles.example.json",
        "AGENTS.md",
        "CLAUDE.md",
        ".github/workflows/ci.yml",
        # Read only by a script that is itself excluded.
        "previews/manifest.json",
        # The public web gallery; a ComfyUI install reads the js/ data.
        "docs/gallery/index.html",
        # data/versions.py ships (the generator reads it), but the script
        # that maintains it does not.
        "scripts/stamp_versions.py",
    )

    def test_the_files_the_pack_needs_survive_packaging(self):
        for path in self.MUST_SHIP:
            with self.subTest(path=path):
                self.assertTrue(
                    (ROOT / path).exists(),
                    f"{path} is missing from the repository, so this "
                    f"assertion is no longer testing anything",
                )
                self.assertTrue(
                    is_packaged(path),
                    f".comfyignore excludes {path}, which the pack needs at "
                    f"runtime or links to from the README",
                )

    def test_the_development_files_stay_out(self):
        for path in self.MUST_NOT_SHIP:
            with self.subTest(path=path):
                self.assertFalse(
                    is_packaged(path),
                    f".comfyignore no longer excludes {path}",
                )


if __name__ == "__main__":
    unittest.main()
