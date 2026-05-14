#!/usr/bin/env python3
"""Rewrite absolute workspace paths in a Safety --save-json report to repo-relative paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _scrub(obj: object, root_resolved: str) -> object:
    prefix = root_resolved + "/"
    if isinstance(obj, dict):
        return {k: _scrub(v, root_resolved) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v, root_resolved) for v in obj]
    if isinstance(obj, str) and obj.startswith(prefix):
        try:
            return str(Path(obj).resolve().relative_to(Path(root_resolved)))
        except ValueError:
            return obj
    return obj


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: sanitize_safety_report.py REPORT.json WORKSPACE_ROOT", file=sys.stderr)
        sys.exit(2)
    report_path = Path(sys.argv[1])
    root = Path(sys.argv[2]).resolve()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    data = _scrub(data, str(root))
    report_path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
