#!/usr/bin/env python3
"""Warn when app/routes/*.py files grow past size thresholds.

Grandfathered fat modules (pre-Phase-6) only warn. New route modules that
exceed FAIL_LINES fail the check so the tree does not grow further without
extraction. Soft CI step / `make check-route-sizes`.

Exit codes:
  0 — OK or only warnings (grandfathered overages)
  1 — a non-grandfathered file exceeds FAIL_LINES
"""

from __future__ import annotations

import sys
from pathlib import Path

WARN_LINES = 2000
FAIL_LINES = 2500

# Pre-existing fat route modules — warn only until opportunistically split.
GRANDFATHERED = frozenset(
    {
        "app/routes/admin.py",
        "app/routes/api.py",
        "app/routes/api_v1.py",
        "app/routes/inventory.py",
        "app/routes/timer.py",
        "app/routes/invoices.py",
        "app/routes/projects.py",
        "app/routes/quotes.py",
        "app/routes/reports.py",
        "app/routes/tasks.py",
    }
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    routes_dir = repo_root / "app" / "routes"
    if not routes_dir.is_dir():
        print(f"ERROR: routes directory not found: {routes_dir}", file=sys.stderr)
        return 1

    warnings: list[tuple[str, int]] = []
    failures: list[tuple[str, int]] = []

    for path in sorted(routes_dir.glob("*.py")):
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
        except OSError as exc:
            print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)
            return 1
        rel = path.relative_to(repo_root).as_posix()
        if line_count > FAIL_LINES and rel not in GRANDFATHERED:
            failures.append((rel, line_count))
        elif line_count > WARN_LINES:
            warnings.append((rel, line_count))

    if warnings:
        print(f"WARNING: route files exceeding {WARN_LINES} lines (soft / grandfathered):")
        for rel, count in warnings:
            tag = " [grandfathered]" if rel in GRANDFATHERED else ""
            print(f"  {rel}: {count} lines{tag}")

    if failures:
        print(f"FAIL: new route files exceeding {FAIL_LINES} lines (extract into sub-blueprints):")
        for rel, count in failures:
            print(f"  {rel}: {count} lines")
        return 1

    if not warnings:
        print(f"OK: no app/routes/*.py files over {WARN_LINES} lines")
    else:
        print("OK (with warnings): exiting 0 — soft check; split grandfathered files when touching them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
