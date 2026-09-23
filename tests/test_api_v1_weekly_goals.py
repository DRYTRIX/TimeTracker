"""API v1 weekly goals list endpoint."""

import pytest

pytestmark = [pytest.mark.unit]


def _auth(plain_token):
    return {"Authorization": f"Bearer {plain_token}"}


@pytest.mark.unit
def test_list_weekly_goals(client_with_token, api_token, app, user):
    _token_model, plain_token = api_token
    response = client_with_token.get("/api/v1/weekly-goals", headers=_auth(plain_token))
    assert response.status_code == 200
    data = response.get_json()
    assert "weekly_goals" in data
    assert isinstance(data["weekly_goals"], list)


@pytest.mark.unit
def test_list_weekly_goals_with_goal(client_with_token, api_token, app, user):
    from datetime import date, timedelta

    from app import db
    from app.models import WeeklyTimeGoal

    _token_model, plain_token = api_token
    with app.app_context():
        start = date.today() - timedelta(days=date.today().weekday())
        goal = WeeklyTimeGoal(user_id=user.id, target_hours=40.0, week_start_date=start)
        db.session.add(goal)
        db.session.commit()

    response = client_with_token.get("/api/v1/weekly-goals", headers=_auth(plain_token))
    assert response.status_code == 200
    payload = response.get_json()["weekly_goals"]
    assert len(payload) >= 1
    assert payload[0]["target_hours"] == 40.0
