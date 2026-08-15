"""Guard against Jinja blocks that never render (same class of bug as #728)."""

import re
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "app" / "templates"

# Blocks defined by known layout templates (parents that children extend).
LAYOUT_BLOCKS = {
    "base.html": {
        "title",
        "og_title",
        "og_description",
        "og_image",
        "twitter_title",
        "twitter_description",
        "twitter_image",
        "extra_css",
        "extra_head",
        "content",
        "scripts_extra",
        "extra_js",
    },
    "client_portal/base.html": {
        "title",
        "og_title",
        "og_description",
        "og_image",
        "twitter_title",
        "twitter_description",
        "twitter_image",
        "content",
    },
    "kiosk/base.html": {
        "title",
        "extra_head",
        "timer_display",
        "content",
        "extra_scripts",
    },
    "integrations/wizard_base.html": {
        # extends base.html and adds:
        "wizard_steps",
        "wizard_js",
        # plus all base blocks
        "title",
        "og_title",
        "og_description",
        "og_image",
        "twitter_title",
        "twitter_description",
        "twitter_image",
        "extra_css",
        "extra_head",
        "content",
        "scripts_extra",
        "extra_js",
    },
}

EXTENDS_RE = re.compile(r"""\{%\s*extends\s+["']([^"']+)["']\s*%}""")
BLOCK_RE = re.compile(r"""\{%\s*block\s+([a-zA-Z0-9_]+)\s*%}""")


def _resolve_parent_blocks(extends_path: str, seen=None) -> set:
    seen = seen or set()
    if extends_path in seen:
        return set()
    seen.add(extends_path)

    blocks = set(LAYOUT_BLOCKS.get(extends_path, set()))
    # Intermediate layouts may themselves extend another template
    parent_file = TEMPLATES_ROOT / extends_path
    if parent_file.is_file() and extends_path not in LAYOUT_BLOCKS:
        text = parent_file.read_text(encoding="utf-8")
        m = EXTENDS_RE.search(text)
        if m:
            blocks |= _resolve_parent_blocks(m.group(1), seen)
        blocks |= set(BLOCK_RE.findall(text))
    elif extends_path in LAYOUT_BLOCKS:
        # Also merge ancestor if wizard_base extends base
        if extends_path == "integrations/wizard_base.html":
            blocks |= LAYOUT_BLOCKS["base.html"]
    return blocks


def test_no_undefined_template_blocks():
    """Every {% block X %} in a child must be defined by an ancestor layout."""
    dead = []
    for path in TEMPLATES_ROOT.rglob("*.html"):
        rel = path.relative_to(TEMPLATES_ROOT).as_posix()
        if rel in LAYOUT_BLOCKS:
            continue
        text = path.read_text(encoding="utf-8")
        m = EXTENDS_RE.search(text)
        if not m:
            continue
        parent = m.group(1)
        allowed = _resolve_parent_blocks(parent)
        # Nested blocks defined inside another block of the same file are still
        # "overrides" of the parent — they must be in allowed.
        for block_name in BLOCK_RE.findall(text):
            if block_name not in allowed:
                dead.append(f"{rel}: block '{block_name}' (extends {parent})")

    assert not dead, "Undefined template blocks (will never render):\n" + "\n".join(dead)
