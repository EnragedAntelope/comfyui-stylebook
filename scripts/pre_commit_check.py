"""Run the Python half of what CI runs, in the same order, before you commit.

    python scripts/pre_commit_check.py

Exit 0 means clean. Anything else names what to fix. Does not run
`npm run test:frontend` -- that needs Node/npm, which this script does not
assume are installed; run it yourself alongside this one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: list[tuple[str, list[str]]] = [
    ("Lint (ruff)", [sys.executable, "-m", "ruff", "check", "."]),
    ("Data integrity", [sys.executable, "tests/validate_data.py"]),
    ("Unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
    ("Generated JS data", [sys.executable, "scripts/generate_js_data.py", "--check"]),
    ("Frontend test fixtures", [sys.executable, "scripts/dump_frontend_fixtures.py", "--check"]),
    ("Preview manifest", [sys.executable, "scripts/build_previews.py", "--check"]),
]


def run(label: str, command: list[str]) -> bool:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  PASS  {label}")
        return True
    print(f"  FAIL  {label}")
    for stream in (result.stdout, result.stderr):
        text = (stream or "").strip()
        if text:
            for line in text.splitlines()[-12:]:
                print(f"        {line}")
    return False


def main() -> int:
    print("Stylebook pre-commit check\n")
    failures = [label for label, command in CHECKS if not run(label, command)]
    if failures:
        print(f"\n{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
