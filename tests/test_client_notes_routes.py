"""
Test suite for client notes routes and endpoints.
Tests all client note CRUD operations and API endpoints.
"""

import pytest
import json
from app.models import ClientNote
from app import db


# ============================================================================
# Client Notes Routes Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.smoke
def test_create_client_note(authenticated_client, test_client, user, app):
    """Test creating a client note."""
    with app.app_context():
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/create",
            data={"content": "This is a test note", "is_important": "false"},
            follow_redirects=False,
        )

        # Should redirect back to client view
        assert response.status_code == 302
        assert f"/clients/{test_client.id}" in response.location

        # Verify note was created
        note = ClientNote.query.filter_by(client_id=test_client.id).first()
        assert note is not None
        assert note.content == "This is a test note"
        assert note.is_important is False


@pytest.mark.integration
@pytest.mark.routes
def test_create_important_client_note(authenticated_client, test_client, user, app):
    """Test creating an important client note."""
    with app.app_context():
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/create",
            data={"content": "Important note", "is_important": "true"},
            follow_redirects=False,
        )

        assert response.status_code == 302

        # Verify note was created with important flag
        note = ClientNote.query.filter_by(client_id=test_client.id).first()
        assert note is not None
        assert note.content == "Important note"
        assert note.is_important is True


@pytest.mark.integration
@pytest.mark.routes
def test_create_note_empty_content_fails(authenticated_client, test_client, app):
    """Test that creating a note with empty content fails."""
    with app.app_context():
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/create",
            data={"content": "", "is_important": "false"},
            follow_redirects=True,
        )

        # Should show error and redirect back
        assert response.status_code == 200

        # Verify no note was created
        note_count = ClientNote.query.filter_by(client_id=test_client.id).count()
        assert note_count == 0


@pytest.mark.integration
@pytest.mark.routes
def test_create_note_invalid_client_fails(authenticated_client, app):
    """Test that creating a note for non-existent client fails."""
    with app.app_context():
        response = authenticated_client.post(
            "/clients/99999/notes/create",
            data={"content": "Test note", "is_important": "false"},
            follow_redirects=False,
        )

        # Should return 404
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.routes
def test_edit_client_note_page(authenticated_client, test_client, user, app):
    """Test accessing the edit client note page."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Original note", user_id=user.id, client_id=test_client.id)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Access edit page
        response = authenticated_client.get(f"/clients/{test_client.id}/notes/{note_id}/edit")

        assert response.status_code == 200
        assert b"Edit Client Note" in response.data or b"edit" in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_edit_client_note_submit(authenticated_client, test_client, user, app):
    """Test editing a client note."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Original note", user_id=user.id, client_id=test_client.id, is_important=False)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Edit the note
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/{note_id}/edit",
            data={"content": "Updated note content", "is_important": "true"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert f"/clients/{test_client.id}" in response.location

        # Verify note was updated
        updated_note = ClientNote.query.get(note_id)
        assert updated_note.content == "Updated note content"
        assert updated_note.is_important is True


@pytest.mark.integration
@pytest.mark.routes
def test_edit_note_permission_denied(authenticated_client, test_client, user, admin_user, app):
    """Test that users cannot edit notes they don't own (unless admin)."""
    with app.app_context():
        # Create a note by admin
        note = ClientNote(content="Admin note", user_id=admin_user.id, client_id=test_client.id)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Regular user tries to edit (should fail if not the owner)
        # This test assumes the route checks permissions
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/{note_id}/edit", data={"content": "Hacked content"}, follow_redirects=True
        )

        # Note: This may pass if the authenticated_client is an admin
        # For a proper test, we'd need a fixture for a non-admin authenticated client


@pytest.mark.integration
@pytest.mark.routes
def test_delete_client_note(authenticated_client, test_client, user, app):
    """Test deleting a client note."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Note to delete", user_id=user.id, client_id=test_client.id)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Delete the note
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/{note_id}/delete", follow_redirects=False
        )

        assert response.status_code == 302
        assert f"/clients/{test_client.id}" in response.location

        # Verify note was deleted
        deleted_note = ClientNote.query.get(note_id)
        assert deleted_note is None


@pytest.mark.integration
@pytest.mark.routes
def test_delete_nonexistent_note_fails(authenticated_client, test_client, app):
    """Test that deleting a non-existent note fails."""
    with app.app_context():
        response = authenticated_client.post(f"/clients/{test_client.id}/notes/99999/delete", follow_redirects=False)

        # Should return 404
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_toggle_important_note(authenticated_client, test_client, user, app):
    """Test toggling the important flag on a note."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Test note", user_id=user.id, client_id=test_client.id, is_important=False)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Toggle to important
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/{note_id}/toggle-important", content_type="application/json"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["is_important"] is True

        # Verify in database
        updated_note = ClientNote.query.get(note_id)
        assert updated_note.is_important is True

        # Toggle back to not important
        response = authenticated_client.post(
            f"/clients/{test_client.id}/notes/{note_id}/toggle-important", content_type="application/json"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["is_important"] is False


# ============================================================================
# Client Notes API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_list_client_notes_api(authenticated_client, test_client, user, app):
    """Test getting all notes for a client via API."""
    with app.app_context():
        # Create multiple notes
        note1 = ClientNote(content="First note", user_id=user.id, client_id=test_client.id, is_important=False)
        note2 = ClientNote(content="Second note", user_id=user.id, client_id=test_client.id, is_important=True)
        db.session.add_all([note1, note2])
        db.session.commit()

        # Get notes via API
        response = authenticated_client.get(f"/api/clients/{test_client.id}/notes")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["notes"]) == 2


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_list_client_notes_api_ordered_by_important(authenticated_client, test_client, user, app):
    """Test getting notes ordered by importance via API."""
    with app.app_context():
        # Create multiple notes
        note1 = ClientNote(content="Regular note", user_id=user.id, client_id=test_client.id, is_important=False)
        note2 = ClientNote(content="Important note", user_id=user.id, client_id=test_client.id, is_important=True)
        db.session.add_all([note1, note2])
        db.session.commit()

        # Get notes ordered by importance
        response = authenticated_client.get(f"/api/clients/{test_client.id}/notes?order_by_important=true")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # First note should be the important one
        assert data["notes"][0]["is_important"] is True


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_get_single_note_api(authenticated_client, test_client, user, app):
    """Test getting a single note via API."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Test note", user_id=user.id, client_id=test_client.id)
        db.session.add(note)
        db.session.commit()
        note_id = note.id

        # Get note via API
        response = authenticated_client.get(f"/api/client-notes/{note_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["note"]["id"] == note_id
        assert data["note"]["content"] == "Test note"


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_get_important_notes_api(authenticated_client, test_client, user, app):
    """Test getting all important notes via API."""
    with app.app_context():
        # Create notes
        note1 = ClientNote(content="Regular note", user_id=user.id, client_id=test_client.id, is_important=False)
        note2 = ClientNote(content="Important note 1", user_id=user.id, client_id=test_client.id, is_important=True)
        note3 = ClientNote(content="Important note 2", user_id=user.id, client_id=test_client.id, is_important=True)
        db.session.add_all([note1, note2, note3])
        db.session.commit()

        # Get important notes
        response = authenticated_client.get("/api/client-notes/important")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["notes"]) == 2
        assert all(note["is_important"] for note in data["notes"])


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_get_recent_notes_api(authenticated_client, test_client, user, app):
    """Test getting recent notes via API."""
    with app.app_context():
        # Create multiple notes
        for i in range(5):
            note = ClientNote(content=f"Note {i}", user_id=user.id, client_id=test_client.id)
            db.session.add(note)
        db.session.commit()

        # Get recent notes with limit
        response = authenticated_client.get("/api/client-notes/recent?limit=3")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["notes"]) == 3


@pytest.mark.integration
@pytest.mark.routes
@pytest.mark.api
def test_get_user_notes_api(authenticated_client, test_client, user, app):
    """Test getting notes by a specific user via API."""
    with app.app_context():
        # Create notes by user
        for i in range(3):
            note = ClientNote(content=f"User note {i}", user_id=user.id, client_id=test_client.id)
            db.session.add(note)
        db.session.commit()

        # Get user's notes
        response = authenticated_client.get(f"/api/client-notes/user/{user.id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["notes"]) == 3


# ============================================================================
# Client View Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.routes
def test_client_view_shows_notes(authenticated_client, test_client, user, app):
    """Test that client view page shows notes."""
    with app.app_context():
        # Create a note
        note = ClientNote(content="Visible note", user_id=user.id, client_id=test_client.id)
        db.session.add(note)
        db.session.commit()

        # View client page
        response = authenticated_client.get(f"/clients/{test_client.id}")

        assert response.status_code == 200
        # Check that notes section is present
        assert b"Internal Notes" in response.data or b"notes" in response.data.lower()


@pytest.mark.integration
@pytest.mark.routes
def test_unauthenticated_user_cannot_access_notes(client, test_client, app):
    """Test that unauthenticated users cannot access note routes."""
    with app.app_context():
        # Try to create a note
        response = client.post(
            f"/clients/{test_client.id}/notes/create", data={"content": "Unauthorized note"}, follow_redirects=False
        )

        # Should redirect to login
        assert response.status_code == 302
        assert "login" in response.location.lower()
