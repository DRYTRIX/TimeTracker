#!/usr/bin/env python3
"""Single source of truth for TimeTracker version bumps.

Usage:
  python scripts/bump_version.py 5.19.0          # bump all version locations + CHANGELOG
  python scripts/bump_version.py --check         # fail if version files disagree
  python scripts/bump_version.py --current       # print current setup.py version
  python scripts/bump_version.py --bump patch    # compute next patch/minor/major and apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_setup_version() -> str:
    text = (ROOT / "setup.py").read_text(encoding="utf-8")
    m = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not m:
        raise SystemExit("Could not parse version from setup.py")
    return m.group(1)


def parse_semver(version: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not m:
        raise SystemExit(f"Version must be X.Y.Z (got {version!r})")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_semver(version: str, kind: str) -> str:
    major, minor, patch = parse_semver(version)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"Unknown bump kind: {kind}")


def replace_file(path: Path, pattern: str, repl: str, flags: int = 0) -> bool:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n == 0:
        return False
    if new != text:
        path.write_text(new, encoding="utf-8")
    return True


def update_json_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_package_lock(path: Path, version: str) -> None:
    """Update root package version in package-lock.json (v2/v3)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    if isinstance(data.get("packages"), dict) and "" in data["packages"]:
        data["packages"][""]["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def promote_changelog(version: str, release_date: str | None = None) -> None:
    path = ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    day = release_date or date.today().isoformat()
    # Already promoted?
    if re.search(rf"^## \[{re.escape(version)}\]", text, re.M):
        return
    replacement = f"## [Unreleased]\n\n## [{version}] - {day}"
    new, n = re.subn(r"^## \[Unreleased\]\s*$", replacement, text, count=1, flags=re.M)
    if n == 0:
        raise SystemExit("CHANGELOG.md: could not find '## [Unreleased]' heading")
    path.write_text(new, encoding="utf-8")


def extract_changelog_section(version: str) -> str:
    """Return the CHANGELOG body for a version (without the heading)."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Match ## [version] ... until next ## [
    pattern = rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
    m = re.search(pattern, text, re.M | re.S)
    if not m:
        return f"Release {version}\n"
    return m.group(1).strip() + "\n"


def apply_version(version: str, *, promote_cl: bool = True) -> None:
    parse_semver(version)

    # setup.py
    if not replace_file(ROOT / "setup.py", r"(version\s*=\s*['\"])[^'\"]+(['\"])", rf"\g<1>{version}\2"):
        raise SystemExit("Failed to update setup.py")

    # VERSION
    (ROOT / "VERSION").write_text(version + "\n", encoding="utf-8")

    # README latest release line
    replace_file(
        ROOT / "README.md",
        r"(\*\*Latest release:\s*v)[0-9]+\.[0-9]+\.[0-9]+(\*\*)",
        rf"\g<1>{version}\2",
    )

    # browser-extension
    update_json_version(ROOT / "browser-extension" / "package.json", version)
    update_json_version(ROOT / "browser-extension" / "manifest.json", version)

    # desktop
    update_json_version(ROOT / "desktop" / "package.json", version)
    lock = ROOT / "desktop" / "package-lock.json"
    if lock.exists():
        update_package_lock(lock, version)

    # mobile pubspec: keep or bump +build number
    pubspec = ROOT / "mobile" / "pubspec.yaml"
    pub_text = pubspec.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*([0-9.]+)\+(\d+)\s*$", pub_text, re.M)
    build = int(m.group(2)) + 1 if m else 1
    if not replace_file(pubspec, r"^version:\s*.*$", f"version: {version}+{build}", flags=re.M):
        raise SystemExit("Failed to update mobile/pubspec.yaml")

    # docs/GAP_ROADMAP.md — best-effort mirrors
    roadmap = ROOT / "docs" / "GAP_ROADMAP.md"
    if roadmap.exists():
        text = roadmap.read_text(encoding="utf-8")
        text = re.sub(
            r"(Source of truth: `setup\.py` \(`)[0-9.]+(`\))",
            rf"\g<1>{version}\2",
            text,
            count=1,
        )
        text = re.sub(
            r"(`mobile/pubspec\.yaml` \(`)[0-9.]+(?:\+\d+)?(`\))",
            rf"\g<1>{version}+{build}\2",
            text,
            count=1,
        )
        roadmap.write_text(text, encoding="utf-8")

    if promote_cl:
        promote_changelog(version)

    print(f"✅ Bumped version to {version} (mobile build +{build})")


def collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    versions["setup.py"] = read_setup_version()
    versions["VERSION"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    for label, path, key in [
        ("browser-extension/package.json", ROOT / "browser-extension" / "package.json", "version"),
        ("browser-extension/manifest.json", ROOT / "browser-extension" / "manifest.json", "version"),
        ("desktop/package.json", ROOT / "desktop" / "package.json", "version"),
    ]:
        data = json.loads(path.read_text(encoding="utf-8"))
        versions[label] = data[key]

    pub = (ROOT / "mobile" / "pubspec.yaml").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*([0-9.]+)", pub, re.M)
    versions["mobile/pubspec.yaml"] = m.group(1) if m else ""

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*Latest release:\s*v([0-9.]+)\*\*", readme)
    versions["README.md"] = m.group(1) if m else ""

    return versions


def check_versions() -> int:
    versions = collect_versions()
    expected = versions["setup.py"]
    print(f"Expected version (setup.py): {expected}")
    bad = False
    for loc, ver in versions.items():
        status = "OK" if ver == expected else "MISMATCH"
        if ver != expected:
            bad = True
        print(f"  [{status}] {loc}: {ver}")
    if bad:
        print("❌ Version files disagree. Run: python scripts/bump_version.py <version>")
        return 1
    print("✅ All version locations agree")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="Target version X.Y.Z")
    parser.add_argument("--check", action="store_true", help="Verify all locations match")
    parser.add_argument("--current", action="store_true", help="Print current version")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Bump from current")
    parser.add_argument(
        "--print-next",
        choices=["major", "minor", "patch"],
        help="Print next version without writing files",
    )
    parser.add_argument("--extract-notes", metavar="VERSION", help="Print CHANGELOG section for version")
    parser.add_argument("--no-changelog", action="store_true", help="Do not promote Unreleased")
    args = parser.parse_args(argv)

    if args.extract_notes:
        sys.stdout.write(extract_changelog_section(args.extract_notes.lstrip("v")))
        return 0
    if args.current:
        print(read_setup_version())
        return 0
    if args.print_next:
        print(bump_semver(read_setup_version(), args.print_next))
        return 0
    if args.check:
        return check_versions()

    if args.bump:
        target = bump_semver(read_setup_version(), args.bump)
    elif args.version:
        target = args.version.lstrip("v")
    else:
        parser.print_help()
        return 2

    apply_version(target, promote_cl=not args.no_changelog)
    return check_versions()


if __name__ == "__main__":
    raise SystemExit(main())
