#!/usr/bin/env python3
"""
Clear msgstr / msgstr_plural when they break Python formatting vs msgid.

Machine translations often corrupt %(name)s (spaces, wrong names) or
brace placeholders {name}, which causes gettext to raise at runtime
(e.g. ValueError: unsupported format character '(').

Usage (repo root, venv with polib):
  python scripts/sanitize_po_format_strings.py translations/pt/LC_MESSAGES/messages.po
"""

from __future__ import annotations

import argparse
import re
import sys
from string import Formatter

import polib


def _percent_keys(msgid: str) -> list[str]:
    return re.findall(r"%\(([^)]+)\)", msgid)


def _safe_percent(msgid: str, msgstr: str) -> bool:
    if not msgstr:
        return True
    keys_m = _percent_keys(msgid)
    keys_s = _percent_keys(msgstr)
    if keys_m:
        # Machine translation often turns %(name)s into %s — dict apply then "succeeds" wrongly.
        if set(keys_m) != set(keys_s):
            return False
        d = {k: "__x__" for k in keys_m}
        try:
            msgstr % d
            return True
        except (ValueError, KeyError, TypeError):
            return False
    if "%" not in msgid.replace("%%", ""):
        return True
    if "%(" in msgid:
        return True
    # Positional %s / %d / %(no) — approximate count of conversion specs
    pat = re.compile(
        r"(?<!%)(?:%%)*(?:%(?!%))(?!\()" r"(?:\d+\$)?[-#+0 ]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrsa%]"
    )
    nm, ns = len(pat.findall(msgid)), len(pat.findall(msgstr))
    if nm == 0:
        return True
    if nm != ns:
        return False
    try:
        msgstr % tuple(["0"] * nm)
        return True
    except (ValueError, TypeError):
        return False


def _brace_field_names(msgid: str) -> set[str]:
    out: set[str] = set()
    try:
        for _, field_name, _, _ in Formatter().parse(msgid):
            if field_name is not None:
                parts = field_name.split(".")
                out.add(parts[0])
    except ValueError:
        return set()
    return out


def _safe_brace(msgid: str, msgstr: str) -> bool:
    if not msgstr:
        return True
    if "{" not in msgid:
        return True
    names = _brace_field_names(msgid)
    if not names:
        return True
    kw = {n: "__x__" for n in names}
    try:
        msgstr.format(**kw)
        return True
    except (ValueError, KeyError, IndexError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("po_path")
    args = ap.parse_args()

    po = polib.pofile(args.po_path)
    cleared = 0

    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue
        if entry.msgid_plural:
            bad = False
            if entry.msgstr_plural:
                for idx, s in entry.msgstr_plural.items():
                    if not s:
                        continue
                    i = int(idx) if str(idx).isdigit() else 0
                    mid = entry.msgid if i == 0 else entry.msgid_plural
                    if ("python-brace-format" in entry.flags) or ("{" in mid and "{" in s):
                        if not _safe_brace(mid, s):
                            bad = True
                            break
                    if ("%(" in mid) or ("python-format" in entry.flags):
                        if not _safe_percent(mid, s):
                            bad = True
                            break
            if bad:
                entry.msgstr_plural = {}
                entry.flags = [f for f in entry.flags if f != "fuzzy"]
                cleared += 1
            continue

        msgstr = entry.msgstr or ""
        if not msgstr:
            continue
        bad = False
        if ("python-brace-format" in entry.flags) or ("{" in entry.msgid and "{" in msgstr):
            if not _safe_brace(entry.msgid, msgstr):
                bad = True
        if not bad and ("%(" in entry.msgid or "python-format" in entry.flags):
            if not _safe_percent(entry.msgid, msgstr):
                bad = True
        if bad:
            entry.msgstr = ""
            entry.flags = [f for f in entry.flags if f != "fuzzy"]
            cleared += 1

    po.metadata["Last-Translator"] = "Sanitized invalid format strings (scripts/sanitize_po_format_strings.py)"
    po.save(args.po_path)
    print(f"Cleared {cleared} broken format translation(s) in {args.po_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
