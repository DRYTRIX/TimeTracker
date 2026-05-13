"""Tests for optional PDF template JSON fields (issue #619 extensions)."""

from app.utils.pdf_template_schema import validate_template_json


def _minimal_template(**element):
    return {
        "page": {"size": "A4", "margin": {"top": 20, "right": 20, "bottom": 20, "left": 20}},
        "elements": [
            {
                "type": "text",
                "x": 10,
                "y": 10,
                "text": "Hello",
                "width": 100,
                "style": {"font": "Helvetica", "size": 10, "color": "#000", "align": "left"},
                **element,
            }
        ],
    }


def test_validate_accepts_text_style_vertical_align():
    t = _minimal_template()
    t["elements"][0]["style"]["verticalAlign"] = "middle"
    ok, err = validate_template_json(t)
    assert ok, err


def test_validate_accepts_optional_metadata_on_text():
    t = _minimal_template(
        group_id="g-1",
        locked=True,
        hidden=False,
    )
    ok, err = validate_template_json(t)
    assert ok, err


def test_validate_accepts_justify_align():
    t = _minimal_template()
    t["elements"][0]["style"]["align"] = "justify"
    ok, err = validate_template_json(t)
    assert ok, err


def test_validate_rejects_bad_page_size():
    t = _minimal_template()
    t["page"]["size"] = "BadSize"
    ok, err = validate_template_json(t)
    assert not ok
