#!/usr/bin/env python3
"""
Ratchet down silently-swallowed exceptions.

The codebase has ~511 broad `except Exception:` handlers, 186 of which do nothing but
`pass`. Those hide real faults: e.g. main.dashboard() falls back to recomputing
donation stats when DonationInteraction raises, so a genuine database error surfaces
only as a slow page.

Fixing all 186 at once is not realistic, so this enforces a budget instead: the count
may go down but never up. Lower MAX_SILENT_EXCEPTS as handlers are triaged.

A handler is "silent" when its entire body is `pass` (optionally preceded by comments).
Replace with one of:
    except Exception:
        logger.debug("...", exc_info=True)   # genuinely optional
        logger.warning("...", exc_info=True) # degraded, should be known
or fix the underlying bug.

Usage:
    python scripts/check_silent_excepts.py            # enforce the budget
    python scripts/check_silent_excepts.py --list     # show every occurrence
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

SEARCH_ROOT = Path("app")
EXCLUDE_PARTS = {"migrations", "__pycache__", ".venv", "venv", "node_modules"}

#: Current budget, measured by AST (an earlier grep-based estimate of 186 undercounted
#: handlers whose `pass` is preceded by a comment). Must only ever decrease.
MAX_SILENT_EXCEPTS = 202


def _is_silent(handler: ast.ExceptHandler) -> bool:
    """True when the handler body is nothing but `pass`."""
    body = [node for node in handler.body if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant)]
    return len(body) == 1 and isinstance(body[0], ast.Pass)


def _is_broad(handler: ast.ExceptHandler) -> bool:
    """True for `except:` or `except Exception:`/`except BaseException:`."""
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name):
        return handler.type.id in {"Exception", "BaseException"}
    return False


def find_silent_excepts():
    findings = []
    for path in sorted(SEARCH_ROOT.rglob("*.py")):
        if EXCLUDE_PARTS & set(path.parts):
            continue
        try:
            # utf-8-sig: a few modules (app/models/time_off.py and friends) carry a
            # UTF-8 BOM, which plain utf-8 decoding turns into a SyntaxError here even
            # though Python's own import machinery accepts it.
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            print(f"WARNING: could not parse {path}: {exc}", file=sys.stderr)
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _is_broad(node) and _is_silent(node):
                findings.append((str(path), node.lineno))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print every occurrence")
    args = parser.parse_args()

    findings = find_silent_excepts()
    count = len(findings)

    if args.list:
        for path, lineno in findings:
            print(f"{path}:{lineno}: silent `except ...: pass`")
        print()

    print(f"silent broad excepts: {count} (budget {MAX_SILENT_EXCEPTS})")

    if count > MAX_SILENT_EXCEPTS:
        print(
            f"\nFAIL: {count - MAX_SILENT_EXCEPTS} new silent exception handler(s).\n"
            "Log the exception instead of swallowing it, or fix the underlying error.\n"
            "Run with --list to see them.",
            file=sys.stderr,
        )
        return 1

    if count < MAX_SILENT_EXCEPTS:
        print(
            f"\nBudget is now loose by {MAX_SILENT_EXCEPTS - count}. "
            f"Lower MAX_SILENT_EXCEPTS to {count} in {__file__} to lock in the improvement."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
