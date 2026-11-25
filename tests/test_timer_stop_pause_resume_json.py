"""Issue #938: /timer/stop|pause|resume return JSON when Accept: application/json."""

from app import db
from app.models.time_entry import TimeEntry, local_now

JSON_HEADERS = {"Accept": "application/json"}


def _start_timer(user, project):
    timer = TimeEntry(
        user_id=user.id,
        project_id=project.id,
        start_time=local_now(),
        source="auto",
        billable=True,
    )
    db.session.add(timer)
    db.session.commit()
    db.session.refresh(timer)
    return timer


class TestTimerStopPauseResumeJson:
    def test_stop_accept_json_returns_200(self, authenticated_client, user, project):
        with authenticated_client.application.app_context():
            timer = _start_timer(user, project)
            timer_id = timer.id

        response = authenticated_client.post("/timer/stop", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 200
        assert response.is_json
        data = response.get_json()
        assert data["success"] is True
        assert "duration" in data
        assert "project_name" in data

        with authenticated_client.application.app_context():
            stopped = TimeEntry.query.get(timer_id)
            assert stopped is not None
            assert stopped.end_time is not None

    def test_stop_without_accept_still_redirects(self, authenticated_client, user, project):
        with authenticated_client.application.app_context():
            _start_timer(user, project)

        response = authenticated_client.post("/timer/stop", follow_redirects=False)

        assert response.status_code in (301, 302)
        assert not response.is_json

    def test_stop_accept_json_no_active_timer(self, authenticated_client):
        response = authenticated_client.post("/timer/stop", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 400
        assert response.is_json
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "no_active_timer"

    def test_pause_accept_json_returns_200(self, authenticated_client, user, project):
        with authenticated_client.application.app_context():
            timer = _start_timer(user, project)
            timer_id = timer.id

        response = authenticated_client.post("/timer/pause", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 200
        assert response.get_json()["success"] is True

        with authenticated_client.application.app_context():
            paused = TimeEntry.query.get(timer_id)
            assert paused is not None
            assert paused.paused_at is not None
            assert paused.end_time is None

    def test_resume_accept_json_returns_200(self, authenticated_client, user, project):
        with authenticated_client.application.app_context():
            timer = _start_timer(user, project)
            timer.pause_timer()
            timer_id = timer.id

        response = authenticated_client.post("/timer/resume", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 200
        assert response.get_json()["success"] is True

        with authenticated_client.application.app_context():
            resumed = TimeEntry.query.get(timer_id)
            assert resumed is not None
            assert resumed.paused_at is None
            assert resumed.end_time is None

    def test_pause_accept_json_no_active_timer(self, authenticated_client):
        response = authenticated_client.post("/timer/pause", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 400
        assert response.get_json()["error"] == "no_active_timer"

    def test_resume_accept_json_no_active_timer(self, authenticated_client):
        response = authenticated_client.post("/timer/resume", headers=JSON_HEADERS, follow_redirects=False)

        assert response.status_code == 400
        assert response.get_json()["error"] == "no_active_timer"
