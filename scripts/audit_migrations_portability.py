"""
Static audit for Alembic migration portability (SQLite vs PostgreSQL).

This script does NOT connect to a database. It scans migration source files for
patterns that commonly break cross-database upgrades, and prints a report.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = REPO_ROOT / "migrations" / "versions"


@dataclass
class Finding:
    code: str
    message: str
    evidence: list[str] = field(default_factory=list)


def _iter_py_files(path: Path) -> Iterable[Path]:
    for p in sorted(path.glob("*.py")):
        if p.name == "__init__.py":
            continue
        yield p


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _get_revision_id(tree: ast.AST) -> str | None:
    revision = None
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "revision":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    revision = node.value.value
    return revision


def _grep_lines(text: str, pattern: re.Pattern[str], max_lines: int = 10) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if pattern.search(line):
            out.append(line.strip())
            if len(out) >= max_lines:
                break
    return out


def audit_file(path: Path) -> list[Finding]:
    text = _read_text(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as e:
        return [
            Finding(
                code="syntax-error",
                message=f"SyntaxError parsing migration: {e}",
                evidence=[str(e)],
            )
        ]

    findings: list[Finding] = []

    def segment_for_func(func_name: str) -> str:
        for node in getattr(tree, "body", []):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                seg = ast.get_source_segment(text, node)
                return seg or ""
        return ""

    upgrade_src = segment_for_func("upgrade")
    downgrade_src = segment_for_func("downgrade")

    # 1) Revision id length (Postgres installs may have alembic_version VARCHAR(32)).
    rev = _get_revision_id(tree)
    if rev and len(rev) > 32:
        findings.append(
            Finding(
                code="rev-id-too-long",
                message=f"Revision id length {len(rev)} (>32) may fail if alembic_version.version_num is VARCHAR(32)",
                evidence=[rev],
            )
        )

    # 2) Raw SQL / op.execute usage.
    if re.search(r"\bop\.execute\s*\(", text):
        evidence = _grep_lines(text, re.compile(r"\bop\.execute\s*\("))
        findings.append(
            Finding(
                code="raw-sql",
                message="Uses op.execute() raw SQL; verify SQL is portable or properly guarded by dialect checks",
                evidence=evidence,
            )
        )

    # 3) SQLite limitations: ALTER COLUMN / DROP COLUMN / constraint alterations.
    # These often require batch_alter_table() on SQLite.
    sqlite_alter_ops = re.compile(
        r"\bop\.(alter_column|drop_column|drop_constraint|create_foreign_key|create_unique_constraint|drop_index)\s*\("
    )
    sqlite_batch = re.compile(r"\bbatch_alter_table\s*\(")
    # Report separately for upgrade vs downgrade since real installs mostly run upgrades.
    if sqlite_alter_ops.search(upgrade_src) and not sqlite_batch.search(upgrade_src):
        evidence = _grep_lines(upgrade_src, sqlite_alter_ops)
        findings.append(
            Finding(
                code="sqlite-upgrade-alter-without-batch",
                message="Upgrade uses schema-altering ops that often fail on SQLite unless run in batch_alter_table(); confirm dialect guards or batch usage",
                evidence=evidence,
            )
        )
    if sqlite_alter_ops.search(downgrade_src) and not sqlite_batch.search(downgrade_src):
        evidence = _grep_lines(downgrade_src, sqlite_alter_ops)
        findings.append(
            Finding(
                code="sqlite-downgrade-alter-without-batch",
                message="Downgrade uses schema-altering ops that often fail on SQLite unless run in batch_alter_table(); downgrade may be broken on SQLite",
                evidence=evidence,
            )
        )

    # 4) Postgres-only DDL patterns (enums/types/extensions, DO $$, etc).
    pg_only = re.compile(
        r"CREATE\s+TYPE|DROP\s+TYPE|CREATE\s+EXTENSION|DO\s*\$\$|USING\s+gin|\bCONCURRENTLY\b",
        re.IGNORECASE,
    )
    if pg_only.search(upgrade_src):
        evidence = _grep_lines(upgrade_src, pg_only)
        findings.append(
            Finding(
                code="postgres-only-ddl-upgrade",
                message="Upgrade contains PostgreSQL-specific DDL; ensure wrapped in Postgres-only guards (bind.dialect.name == 'postgresql')",
                evidence=evidence,
            )
        )
    if pg_only.search(downgrade_src):
        evidence = _grep_lines(downgrade_src, pg_only)
        findings.append(
            Finding(
                code="postgres-only-ddl-downgrade",
                message="Downgrade contains PostgreSQL-specific DDL; ensure wrapped in Postgres-only guards",
                evidence=evidence,
            )
        )

    # 5) Postgres dialect types (JSONB, ARRAY, etc) – must be guarded or have SQLite fallbacks.
    pg_types = re.compile(r"\bpostgresql\.(JSONB|JSON|ARRAY|UUID|HSTORE|CITEXT)\b")
    if pg_types.search(upgrade_src):
        evidence = _grep_lines(upgrade_src, pg_types)
        findings.append(
            Finding(
                code="postgres-dialect-types-upgrade",
                message="Upgrade uses sqlalchemy.dialects.postgresql.* types; ensure SQLite fallback exists or op is guarded",
                evidence=evidence,
            )
        )
    if pg_types.search(downgrade_src):
        evidence = _grep_lines(downgrade_src, pg_types)
        findings.append(
            Finding(
                code="postgres-dialect-types-downgrade",
                message="Downgrade uses sqlalchemy.dialects.postgresql.* types; ensure SQLite fallback exists or op is guarded",
                evidence=evidence,
            )
        )

    # 6) Risky server_default patterns for JSON/booleans across DBs.
    # - SQLite tends to accept '0'/'1' while Postgres expects true/false.
    server_default_bool = re.compile(r"server_default\s*=\s*('true'|'false'|\"true\"|\"false\")")
    if server_default_bool.search(upgrade_src):
        evidence = _grep_lines(upgrade_src, server_default_bool)
        findings.append(
            Finding(
                code="server-default-bool-literal-upgrade",
                message="Upgrade uses server_default 'true'/'false' literals; verify dialect branching (SQLite usually wants 0/1) or use sa.text('true') safely",
                evidence=evidence,
            )
        )

    # 7) Imports that can break migrations when app package changes (best practice: keep migrations self-contained).
    if re.search(r"^\s*from\s+app\s+import|^\s*import\s+app\b", text, flags=re.M):
        evidence = _grep_lines(text, re.compile(r"^\s*(from\s+app\s+import|import\s+app\b)", re.M))
        findings.append(
            Finding(
                code="imports-app",
                message="Migration imports application code; can break on upgrades if app code changes. Prefer pure SQLAlchemy/Alembic ops",
                evidence=evidence,
            )
        )

    return findings


def main() -> int:
    if not VERSIONS_DIR.exists():
        print(f"ERROR: versions dir not found: {VERSIONS_DIR}", file=sys.stderr)
        return 2

    # First pass: parse revisions + down_revisions to validate graph integrity.
    revisions_by_file: dict[Path, str] = {}
    down_by_file: dict[Path, str | None] = {}
    duplicate_revisions: dict[str, list[Path]] = {}

    for p in _iter_py_files(VERSIONS_DIR):
        text = _read_text(p)
        try:
            tree = ast.parse(text, filename=str(p))
        except SyntaxError:
            continue

        rev = _get_revision_id(tree)
        down: str | None = None
        for node in getattr(tree, "body", []):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "down_revision":
                    if isinstance(node.value, ast.Constant):
                        down = node.value.value if isinstance(node.value.value, str) else None

        if rev:
            revisions_by_file[p] = rev
            duplicate_revisions.setdefault(rev, []).append(p)
            down_by_file[p] = down

    revision_set = set(revisions_by_file.values())

    results: dict[Path, list[Finding]] = {}
    for p in _iter_py_files(VERSIONS_DIR):
        findings = audit_file(p)
        if findings:
            results[p] = findings

    # Graph integrity findings (add to per-file findings for visibility).
    for rev, paths in duplicate_revisions.items():
        if len(paths) > 1:
            for p in paths:
                results.setdefault(p, []).append(
                    Finding(
                        code="revision-duplicate",
                        message=f"Revision id '{rev}' is duplicated across multiple migration files",
                        evidence=[str(x.relative_to(REPO_ROOT)) for x in paths],
                    )
                )

    for p, down in down_by_file.items():
        if down is None:
            # down_revision may legitimately be None for the *first* migration only.
            # If it's not the initial schema, flag it.
            if revisions_by_file.get(p) not in {"001", "001_initial_schema", "001_initial_schema.py"}:
                # Heuristic: If file isn't an obvious "initial" migration, flag.
                if "initial" not in p.name.lower() and revisions_by_file.get(p) not in {"001_initial_schema"}:
                    results.setdefault(p, []).append(
                        Finding(
                            code="down-revision-none",
                            message="down_revision is None; this creates a new root/branchpoint and can break upgrade ordering unless intentional",
                            evidence=["down_revision = None"],
                        )
                    )
        else:
            if down not in revision_set:
                results.setdefault(p, []).append(
                    Finding(
                        code="down-revision-missing",
                        message=f"down_revision '{down}' not found among known revisions; migration graph is broken",
                        evidence=[f"down_revision = {down!r}"],
                    )
                )

    print(f"Scanned: {len(list(_iter_py_files(VERSIONS_DIR)))} migration files in {VERSIONS_DIR}")
    print(f"Files with findings: {len(results)}")
    print("")

    # Group by finding code for a quick summary.
    by_code: dict[str, int] = {}
    for findings in results.values():
        for f in findings:
            by_code[f.code] = by_code.get(f.code, 0) + 1

    print("Summary (finding_code -> count):")
    for code, count in sorted(by_code.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"- {code}: {count}")
    print("")

    # Detailed per-file output.
    for path in sorted(results.keys()):
        rel = path.relative_to(REPO_ROOT)
        print(f"{rel}:")
        for f in results[path]:
            print(f"  - [{f.code}] {f.message}")
            for ev in f.evidence:
                print(f"      {ev}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

