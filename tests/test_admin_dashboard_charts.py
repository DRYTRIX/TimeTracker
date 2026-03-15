"""
Tests for admin dashboard chart data (optimized GROUP BY queries).
"""

from datetime import datetime, timedelta


def test_admin_dashboard_returns_chart_data_with_30_days(client, app, admin_user):
    """Admin dashboard returns 200 and chart data with 30 points for user_activity and time_entries_daily."""
    from app import db
    from app.models import TimeEntry, Settings

    with app.app_context():
        # Ensure admin module accessible
        settings = Settings.get_settings()
        disabled = list(settings.disabled_module_ids or [])
        if "admin" in disabled:
            settings.disabled_module_ids = [m for m in disabled if m != "admin"]
            db.session.add(settings)
            db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)
        sess["_fresh"] = True

    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} (redirect to login?)"

    data = resp.get_data(as_text=True)
    # Admin dashboard shows stats and charts (template uses chart_data.user_activity etc.)
    assert "Admin" in data or "Dashboard" in data or "dashboard" in data
    # Chart JS uses these canvas/context IDs when chart_data is present
    assert "userActivityChart" in data or "timeEntryChart" in data or "projectStatusChart" in data
    # 30-day series: page should contain many date strings (YYYY-MM-DD)
    import re
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    dates_in_page = re.findall(date_pattern, data)
    assert len(dates_in_page) >= 30, "Chart data should include at least 30 date values (30-day series)"
