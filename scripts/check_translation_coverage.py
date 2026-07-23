#!/usr/bin/env python3
"""
Fail when a locale's translation coverage drops below a floor.

Context: 1,877 of 5,508 strings were untranslated in 9 of the 11 shipped locales,
so roughly a third of the UI silently fell back to English. Nothing detected that,
and nothing stopped it getting worse as new strings landed.

This script measures coverage per locale from the .po catalogues and exits non-zero
if any locale is below the floor. Raise the floor as translations land.

Usage:
    python scripts/check_translation_coverage.py                 # use default floor
    python scripts/check_translation_coverage.py --min 70        # custom floor
    python scripts/check_translation_coverage.py --report        # print only, never fail
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TRANSLATIONS_DIR = Path("translations")

#: Locale that *is* the source language; its msgstr values are empty by design.
SOURCE_LOCALE = "en"

#: Current floor. Deliberately just below today's worst locale (fi, 55.0%) so CI is
#: green on introduction and can only ratchet upward. Raise it as Crowdin work lands;
#: never lower it without a deliberate decision.
DEFAULT_MIN_COVERAGE = 54.0

#: Entry separator in a .po file is a blank line.
ENTRY_RE = re.compile(r"\n\s*\n")


def _parse_po(path: Path) -> tuple[int, int]:
    """
    Return (translated, total) for a catalogue.

    Counts entries with a non-empty msgid, ignoring the header entry and anything
    marked fuzzy (a fuzzy translation is not shown to users).
    """
    text = path.read_text(encoding="utf-8")
    translated = total = 0

    for block in ENTRY_RE.split(text):
        if "msgid" not in block:
            continue
        if re.search(r'^msgid\s+""\s*$', block, re.M) and "msgstr" in block and total == 0:
            continue  # header

        msgid = re.search(r'^msgid\s+"((?:[^"\\]|\\.)*)"', block, re.M)
        if not msgid or not msgid.group(1):
            continue

        total += 1
        if re.search(r"^#,.*\bfuzzy\b", block, re.M):
            continue

        # msgstr may be a single line or a multi-line continuation.
        msgstr = re.search(r'^msgstr\s+"((?:[^"\\]|\\.)*)"((?:\s*\n"(?:[^"\\]|\\.)*")*)', block, re.M)
        if msgstr and (msgstr.group(1) or re.search(r'"\s*[^"\s]', msgstr.group(2) or "")):
            translated += 1

    return translated, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min", type=float, default=DEFAULT_MIN_COVERAGE, help="minimum coverage percent")
    parser.add_argument("--report", action="store_true", help="report only, always exit 0")
    args = parser.parse_args()

    catalogues = sorted(TRANSLATIONS_DIR.glob("*/LC_MESSAGES/messages.po"))
    if not catalogues:
        print("No .po catalogues found under translations/", file=sys.stderr)
        return 1

    failures = []
    print(f"{'locale':<8} {'coverage':>9}  {'translated':>10} / total")
    print("-" * 44)

    for path in catalogues:
        locale = path.parts[1]
        translated, total = _parse_po(path)
        if locale == SOURCE_LOCALE:
            print(f"{locale:<8} {'(source)':>9}  {total:>10}   entries")
            continue

        coverage = (translated / total * 100) if total else 0.0
        flag = "" if coverage >= args.min else "  <-- BELOW FLOOR"
        print(f"{locale:<8} {coverage:>8.1f}%  {translated:>10} / {total}{flag}")
        if coverage < args.min:
            failures.append((locale, coverage))

    print()
    if failures:
        stream = sys.stdout if args.report else sys.stderr
        verdict = "REPORT" if args.report else "FAIL"
        print(f"{verdict}: {len(failures)} locale(s) below {args.min:.1f}% coverage:", file=stream)
        for locale, coverage in failures:
            print(f"  {locale}: {coverage:.1f}%", file=stream)
        if args.report:
            return 0
        print(
            "\nRun the Crowdin sync workflow to pull new translations, "
            "or lower --min only with a deliberate decision.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: all locales at or above {args.min:.1f}% coverage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
