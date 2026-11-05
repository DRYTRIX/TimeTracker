#!/usr/bin/env python3
"""
Fill empty msgstr in a .po file using Argos Translate (offline en→pt, etc.).

Usage (from repo root, with venv activated and Argos model installed):
  python scripts/fill_po_argos.py translations/pt/LC_MESSAGES/messages.po --from en --to pt
  python scripts/sanitize_po_format_strings.py translations/pt/LC_MESSAGES/messages.po
  msgfmt --check-format -o /dev/null translations/pt/LC_MESSAGES/messages.po

Requires: pip install polib argostranslate
Install Argos language pair once, e.g.:
  python -c "import argostranslate.package as p; p.update_package_index(); ..."
"""

from __future__ import annotations

import argparse
import sys

import argostranslate.translate
import polib


def translate_text(text: str, from_code: str, to_code: str) -> str:
    if not text or not text.strip():
        return text
    try:
        return argostranslate.translate.translate(text, from_code, to_code)
    except Exception:
        return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill empty PO msgstr using Argos Translate")
    parser.add_argument("po_path", help="Path to messages.po to update")
    parser.add_argument("--from", dest="from_code", default="en", help="Source language code (default: en)")
    parser.add_argument("--to", dest="to_code", default="pt", help="Target language code (default: pt)")
    parser.add_argument("--limit", type=int, default=0, help="Max messages to translate (0 = all)")
    args = parser.parse_args()

    po = polib.pofile(args.po_path)
    done = 0
    limit = args.limit or None

    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue
        if entry.translated() and entry.msgstr.strip():
            continue

        if entry.msgid_plural:
            # Portuguese: two plural forms typical in our header
            t0 = translate_text(entry.msgid, args.from_code, args.to_code)
            t1 = translate_text(entry.msgid_plural, args.from_code, args.to_code)
            entry.msgstr_plural = {0: t0, 1: t1}
        else:
            entry.msgstr = translate_text(entry.msgid, args.from_code, args.to_code)

        entry.flags = [f for f in entry.flags if f != "fuzzy"]
        done += 1
        if done % 500 == 0:
            print(f"translated {done}...", flush=True)
        if limit is not None and done >= limit:
            break

    po.metadata["Last-Translator"] = "Argos Translate (machine) + scripts/fill_po_argos.py"
    po.save(args.po_path)
    print(f"Done. Updated {done} entries in {args.po_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
