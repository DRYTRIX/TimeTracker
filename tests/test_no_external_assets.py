"""
Guards the self-hosting guarantee.

TimeTracker is deployed self-hosted and privacy-focused, and must render fully with
no outbound network access. Templates previously pulled 17 third-party resources from
cdnjs, jsDelivr, uicdn.toast.com and fonts.bunny.net at runtime, which leaked every
user's IP to those hosts and broke air-gapped installs outright.

Everything is now vendored under app/static/vendor (see scripts/copy-vendor.mjs).
These tests fail if a remote asset reference creeps back in.
"""

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

TEMPLATES = Path("app/templates")
STATIC = Path("app/static")

#: Hosts that must never appear in an asset-loading position.
FORBIDDEN_ASSET_HOSTS = (
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "uicdn.toast.com",
    "fonts.bunny.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "code.jquery.com",
    "cdn.datatables.net",
    "esm.sh",
    "unpkg.com",
)

#: src=/href= on a tag that loads a subresource.
ASSET_REF = re.compile(r'(?:src|href)\s*=\s*"(https?://[^"]+)"')


def _template_files():
    return sorted(TEMPLATES.rglob("*.html"))


def test_no_remote_asset_references_in_templates():
    """No <script src>, <link href> or <img src> may point at a third-party host."""
    offenders = []
    for path in _template_files():
        text = path.read_text(encoding="utf-8")
        for url in ASSET_REF.findall(text):
            if any(host in url for host in FORBIDDEN_ASSET_HOSTS):
                offenders.append(f"{path}: {url}")

    assert not offenders, "Remote asset references found (vendor them instead):\n" + "\n".join(offenders)


def test_no_remote_imports_in_static_javascript():
    """
    ES module imports must resolve locally.

    app/static/js/command-palette.js previously did
    `import { commandScore } from 'https://cdn.jsdelivr.net/npm/cmdk@.../command-score.mjs'`,
    which silently broke the Ctrl+K palette without network access. It now imports the
    bare specifier `cmdk/command-score`, resolved at build time by the ALIASES map in
    scripts/build-js.mjs.
    """
    offenders = []
    for path in sorted(STATIC.rglob("*.js")) + sorted(STATIC.rglob("*.mjs")):
        if "dist" in path.parts or "vendor" in path.parts:
            continue
        for match in re.finditer(
            r'^\s*import\s[^\n]*?[\'"](https?://[^\'"]+)[\'"]', path.read_text(encoding="utf-8"), re.M
        ):
            offenders.append(f"{path}: {match.group(1)}")

    assert not offenders, "Remote ES imports found (add to ALIASES in scripts/build-js.mjs):\n" + "\n".join(offenders)


def test_stylesheets_do_not_import_remote_fonts():
    """input.css used to @import Inter from fonts.bunny.net on every page load."""
    offenders = []
    for path in sorted(STATIC.rglob("*.css")):
        if "vendor" in path.parts or "dist" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"@import\s+url\(\s*['\"]?(https?://[^'\")]+)", text):
            offenders.append(f"{path}: {match.group(1)}")

    assert not offenders, "Remote @import found (self-host the font instead):\n" + "\n".join(offenders)


def test_font_awesome_is_not_loaded_twice():
    """
    The CSS build and the SVG-with-JS build used to be loaded together.

    They conflict (the JS build rewrites <i> elements into <svg>) and roughly doubled
    the icon payload. Exactly one Font Awesome reference per template, and never as a
    <script>.
    """
    for path in _template_files():
        text = path.read_text(encoding="utf-8")
        refs = re.findall(r"[^\n]*fontawesome[^\n]*", text, re.I)
        asset_refs = [r for r in refs if "url_for" in r or "http" in r]
        assert len(asset_refs) <= 1, f"{path}: Font Awesome referenced {len(asset_refs)} times"
        for ref in asset_refs:
            assert "<script" not in ref, f"{path}: Font Awesome CSS loaded via <script> (no-op)"


def test_content_security_policy_allows_no_cdn(app):
    """The enforced CSP must not allowlist any third-party origin."""
    with app.test_client() as client:
        response = client.get("/login")
        csp = response.headers.get("Content-Security-Policy", "")

    assert csp, "No CSP header set"
    for host in FORBIDDEN_ASSET_HOSTS:
        assert host not in csp, f"CSP still allowlists {host}"


def test_inline_scripts_carry_a_nonce():
    """
    Every inline <script> must be noncable so the strict CSP can eventually be enforced.

    The nonce-based policy currently ships as Content-Security-Policy-Report-Only; it
    can only become the enforced policy once no inline block is missing its nonce.
    """
    offenders = []
    for path in _template_files():
        for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", path.read_text(encoding="utf-8")):
            if "nonce=" not in match.group(0):
                offenders.append(f"{path}: {match.group(0)[:80]}")

    assert not offenders, "Inline <script> without nonce:\n" + "\n".join(offenders)


def test_every_referenced_bundle_is_built_and_vice_versa():
    """
    asset_url() names in templates must match the build manifest exactly.

    A name that is referenced but not built renders an empty src (the script silently
    never loads); a bundle that is built but never referenced is dead weight in the
    image. Skipped when the JS build has not run.
    """
    import json

    manifest_path = STATIC / "dist" / "manifest.json"
    if not manifest_path.exists():
        pytest.skip("JS bundles not built (run `npm run build:js`)")

    built = set(json.loads(manifest_path.read_text(encoding="utf-8")))
    referenced = set()
    for path in _template_files():
        referenced.update(re.findall(r"asset_url\(\s*'([^']+)'", path.read_text(encoding="utf-8")))

    assert not (referenced - built), f"referenced but not built: {sorted(referenced - built)}"
    assert not (built - referenced), f"built but never referenced: {sorted(built - referenced)}"


def test_font_awesome_loads_before_tailwind():
    """
    Font Awesome's stylesheet must precede dist/output.css.

    Font Awesome declares `.fa-solid,.fab,.far,.fas { display: var(--fa-display,
    inline-block) }`. Tailwind declares `.hidden { display: none }`. Both are
    single-class selectors, so specificity ties and source order decides — and Tailwind
    is not configured with the `important` strategy.

    If Font Awesome loads last it silently wins, and every `hidden` applied to an icon
    becomes a no-op. That is what made the theme toggle render all three of its icons
    at once.
    """
    fa_link = re.compile(r"<link[^>]*vendor/fontawesome[^>]*>")
    css_link = re.compile(r"<link[^>]*dist/output\.css[^>]*>")

    offenders = []
    for path in _template_files():
        text = path.read_text(encoding="utf-8")
        fa = fa_link.search(text)
        css = css_link.search(text)
        if fa and css and fa.start() > css.start():
            offenders.append(str(path))

    assert not offenders, (
        "Font Awesome is loaded after dist/output.css in:\n  "
        + "\n  ".join(offenders)
        + "\nThis makes Tailwind's `hidden` (and other display utilities) ineffective on icons."
    )
