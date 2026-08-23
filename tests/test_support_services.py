"""Tests for support prompt and usage stats services."""

from app.services.support_prompt_service import SupportPromptService
from app.services.usage_stats_service import UsageStatsService


def test_usage_stats_service_shape(app, test_user):
    with app.app_context():
        s = UsageStatsService.get_for_user(test_user.id)
        assert "total_hours" in s
        assert "time_entries_count" in s
        assert "days_since_signup" in s
        assert "reports_generated_count" in s


def test_consume_layout_prompt_sets_consumed():
    session = {"support_prompt_trigger": SupportPromptService.VARIANT_AFTER_REPORT}
    payload = SupportPromptService.consume_layout_prompt(
        session,
        ui_show_donate=True,
        is_supporter=False,
        support_banner_suppressed=False,
    )
    assert payload is not None
    assert payload.get("variant") == SupportPromptService.VARIANT_AFTER_REPORT
    assert session.get(SupportPromptService.SESSION_SOFT_PROMPT_CONSUMED) is True
    assert "support_prompt_trigger" not in session


def test_support_prompt_suppressed_for_supporter():
    session = {"support_prompt_trigger": SupportPromptService.VARIANT_AFTER_REPORT}
    payload = SupportPromptService.consume_layout_prompt(
        session,
        ui_show_donate=True,
        is_supporter=True,
        support_banner_suppressed=False,
    )
    assert payload is None


def test_support_prompt_respects_ui_show_donate():
    session = {"support_prompt_trigger": SupportPromptService.VARIANT_AFTER_REPORT}
    payload = SupportPromptService.consume_layout_prompt(
        session,
        ui_show_donate=False,
        is_supporter=False,
        support_banner_suppressed=False,
    )
    assert payload is None


def test_pick_dashboard_skips_when_after_report_pending():
    session = {"support_prompt_trigger": SupportPromptService.VARIANT_AFTER_REPORT}
    user_stats = {"days_since_signup": 100, "time_entries_count": 1, "total_hours": 1.0}
    picked = SupportPromptService.pick_dashboard_prompt(
        session,
        user_stats,
        ui_show_donate=True,
        is_supporter=False,
        support_banner_suppressed=False,
        today_hours=8.0,
    )
    assert picked is None


def test_pick_dashboard_hours_milestone():
    session = {}
    user_stats = {"days_since_signup": 3, "time_entries_count": 50, "total_hours": 520.0}
    picked = SupportPromptService.pick_dashboard_prompt(
        session,
        user_stats,
        ui_show_donate=True,
        is_supporter=False,
        support_banner_suppressed=False,
        today_hours=1.0,
    )
    assert picked is not None
    assert picked.get("variant") == SupportPromptService.VARIANT_HOURS_MILESTONE
    assert picked.get("milestone") == 500


def test_pick_dashboard_anniversary_30d():
    session = {}
    user_stats = {"days_since_signup": 35, "time_entries_count": 10, "total_hours": 20.0}
    picked = SupportPromptService.pick_dashboard_prompt(
        session,
        user_stats,
        ui_show_donate=True,
        is_supporter=False,
        support_banner_suppressed=False,
        today_hours=1.0,
    )
    assert picked is not None
    assert picked.get("variant") == SupportPromptService.VARIANT_ANNIVERSARY_30D


def test_consume_layout_prompt_first_invoice():
    session = {"support_prompt_trigger": SupportPromptService.VARIANT_FIRST_INVOICE}
    payload = SupportPromptService.consume_layout_prompt(
        session,
        ui_show_donate=True,
        is_supporter=False,
        support_banner_suppressed=False,
    )
    assert payload is not None
    assert payload.get("variant") == SupportPromptService.VARIANT_FIRST_INVOICE
    assert session.get(SupportPromptService.SESSION_SOFT_PROMPT_CONSUMED) is True
