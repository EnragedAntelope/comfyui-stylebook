"""Pre-commit validation for the Stylebook pack.

Run before every commit. Catches the class of bugs that we keep
tripping over: syntax errors, duplicate input IDs, facet coverage
gaps, and broken tests.

Usage: python scripts/pre_commit_check.py
Exits 0 = clean, non-zero = something to fix.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

errors = 0


def check(label: str, cmd: list[str]) -> bool:
    """Run *cmd*, print whether it passed. Returns True on success."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  OK  {label}")
        return True
    else:
        print(f"  FAIL {label}")
        if result.stdout.strip():
            print(f"       {result.stdout.strip()[:200]}")
        if result.stderr.strip():
            print(f"       {result.stderr.strip()[:200]}")
        return False


def check_input_ids() -> list[str]:
    """Check for duplicate input IDs in node files. Returns error msgs."""
    errs = []
    for f in sorted((ROOT / "stylebook_nodes").glob("*.py")):
        if f.name == "__init__.py":
            continue
        content = f.read_text(encoding="utf-8")
        ids = re.findall(r'^\s+"(\w+)",\s*$', content, re.MULTILINE)
        seen: dict[str, int] = {}
        for i in ids:
            if i in ("inherit", "category"):
                continue
            seen[i] = seen.get(i, 0) + 1
        dups = [k for k, v in seen.items() if v > 1]
        for d in dups:
            errs.append(f"{f.name}: duplicate input ID '{d}' ({seen[d]} times)")
    return errs


print("=== Stylebook pre-commit check ===\n")

# 1. Syntax on all Python files
for f in sorted(ROOT.rglob("*.py")):
    rel = str(f.relative_to(ROOT))
    try:
        compile(f.read_text(encoding="utf-8"), str(f), "exec")
    except SyntaxError as e:
        print(f"  FAIL {rel}: {e}")
        errors += 1

# 2. Duplicate input IDs
dup_errs = check_input_ids()
for e in dup_errs:
    print(f"  FAIL {e}")
    errors += len(dup_errs)
if not dup_errs:
    print("  OK  No duplicate input IDs")

# 3. Data validation
if not check("Validate data", [sys.executable, "tests/validate_data.py"]):
    errors += 1

# 4. Unit tests
if not check("Unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]):
    errors += 1

# 5. JS data sync
if not check("JS data sync", [sys.executable, "scripts/generate_js_data.py", "--check"]):
    errors += 1

print(f"\n{'PASS' if errors == 0 else f'{errors} FAILURES'}")
sys.exit(0 if errors == 0 else 1)
