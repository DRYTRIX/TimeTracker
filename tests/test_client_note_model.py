"""
Test suite for ClientNote model.
Tests model creation, relationships, properties, and business logic.
"""

import pytest
from datetime import datetime
from app.models import ClientNote, Client, User
from app import db


# ============================================================================
# ClientNote Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.models
@pytest.mark.smoke
def test_client_note_creation(app, user, test_client):
    """Test basic client note creation."""
    with app.app_context():
        note = ClientNote(
            content="Important note about the client",
            user_id=user.id,
            client_id=test_client.id,
            is_important=False
        )
        db.session.add(note)
        db.session.commit()
        
        assert note.id is not None
        assert note.content == "Important note about the client"
        assert note.user_id == user.id
        assert note.client_id == test_client.id
        assert note.is_important is False
        assert note.created_at is not None
        assert note.updated_at is not None


@pytest.mark.unit
@pytest.mark.models
def test_client_note_requires_client(app, user):
    """Test that client note requires a client."""
    with app.app_context():
        with pytest.raises(ValueError, match="Note must be associated with a client"):
            note = ClientNote(
                content="Note without client",
                user_id=user.id,
                client_id=None
            )


@pytest.mark.unit
@pytest.mark.models
def test_client_note_requires_content(app, user, test_client):
    """Test that client note requires content."""
    with app.app_context():
        with pytest.raises(ValueError, match="Note content cannot be empty"):
            note = ClientNote(
                content="",
                user_id=user.id,
                client_id=test_client.id
            )


@pytest.mark.unit
@pytest.mark.models
def test_client_note_strips_content(app, user, test_client):
    """Test that client note content is stripped of whitespace."""
    with app.app_context():
        note = ClientNote(
            content="  Note with spaces  ",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        assert note.content == "Note with spaces"


@pytest.mark.unit
@pytest.mark.models
def test_client_note_author_relationship(app, user, test_client):
    """Test client note author relationship."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        assert note.author is not None
        assert note.author.id == user.id
        assert note.author.username == user.username


@pytest.mark.unit
@pytest.mark.models
def test_client_note_client_relationship(app, user, test_client):
    """Test client note client relationship."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        assert note.client is not None
        assert note.client.id == test_client.id
        assert note.client.name == test_client.name


@pytest.mark.unit
@pytest.mark.models
def test_client_has_notes_relationship(app, user, test_client):
    """Test that client has notes relationship."""
    with app.app_context():
        # Re-query the client to ensure it's in the current session
        from app.models import Client
        client = Client.query.get(test_client.id)
        
        note1 = ClientNote(
            content="First note",
            user_id=user.id,
            client_id=client.id
        )
        note2 = ClientNote(
            content="Second note",
            user_id=user.id,
            client_id=client.id,
            is_important=True
        )
        db.session.add_all([note1, note2])
        db.session.commit()
        
        db.session.refresh(client)
        assert len(client.notes) == 2


@pytest.mark.unit
@pytest.mark.models
def test_client_note_author_name_property(app, user, test_client):
    """Test client note author_name property."""
    with app.app_context():
        # Ensure user has no full_name set (clean state)
        user.full_name = None
        db.session.commit()
        
        # Test with username only
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        assert note.author_name == user.username
        
        # Test with full name
        user.full_name = "Test User Full Name"
        db.session.commit()
        db.session.refresh(note)
        db.session.refresh(user)  # Refresh user to ensure full_name is loaded
        assert note.author_name == "Test User Full Name"


@pytest.mark.unit
@pytest.mark.models
def test_client_note_client_name_property(app, user, test_client):
    """Test client note client_name property."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        assert note.client_name == test_client.name


@pytest.mark.unit
@pytest.mark.models
def test_client_note_can_edit(app, user, admin_user, test_client):
    """Test client note can_edit permission."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        # Author can edit
        assert note.can_edit(user) is True
        
        # Admin can edit
        assert note.can_edit(admin_user) is True
        
        # Other user cannot edit
        other_user = User(username='otheruser', role='user')
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()
        
        assert note.can_edit(other_user) is False


@pytest.mark.unit
@pytest.mark.models
def test_client_note_can_delete(app, user, admin_user, test_client):
    """Test client note can_delete permission."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        # Author can delete
        assert note.can_delete(user) is True
        
        # Admin can delete
        assert note.can_delete(admin_user) is True
        
        # Other user cannot delete
        other_user = User(username='otheruser', role='user')
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()
        
        assert note.can_delete(other_user) is False


@pytest.mark.unit
@pytest.mark.models
def test_client_note_edit_content(app, user, test_client):
    """Test editing client note content."""
    with app.app_context():
        note = ClientNote(
            content="Original content",
            user_id=user.id,
            client_id=test_client.id,
            is_important=False
        )
        db.session.add(note)
        db.session.commit()
        
        # Edit content
        note.edit_content("Updated content", user, is_important=True)
        db.session.commit()
        
        assert note.content == "Updated content"
        assert note.is_important is True


@pytest.mark.unit
@pytest.mark.models
def test_client_note_edit_content_permission_denied(app, user, test_client):
    """Test editing client note without permission."""
    with app.app_context():
        note = ClientNote(
            content="Original content",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        # Create another user
        other_user = User(username='otheruser', role='user')
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()
        
        # Try to edit as other user
        with pytest.raises(PermissionError, match="User does not have permission to edit this note"):
            note.edit_content("Hacked content", other_user)


@pytest.mark.unit
@pytest.mark.models
def test_client_note_edit_content_empty_fails(app, user, test_client):
    """Test editing client note with empty content fails."""
    with app.app_context():
        note = ClientNote(
            content="Original content",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        # Try to edit with empty content
        with pytest.raises(ValueError, match="Note content cannot be empty"):
            note.edit_content("", user)


@pytest.mark.unit
@pytest.mark.models
def test_client_note_to_dict(app, user, test_client):
    """Test client note serialization to dictionary."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id,
            is_important=True
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        note_dict = note.to_dict()
        
        assert 'id' in note_dict
        assert 'content' in note_dict
        assert 'client_id' in note_dict
        assert 'client_name' in note_dict
        assert 'user_id' in note_dict
        assert 'author' in note_dict
        assert 'author_name' in note_dict
        assert 'is_important' in note_dict
        assert 'created_at' in note_dict
        assert 'updated_at' in note_dict
        
        assert note_dict['content'] == "Test note"
        assert note_dict['is_important'] is True


@pytest.mark.unit
@pytest.mark.models
def test_get_client_notes(app, user, test_client):
    """Test getting notes for a client."""
    with app.app_context():
        # Create multiple notes
        note1 = ClientNote(
            content="First note",
            user_id=user.id,
            client_id=test_client.id,
            is_important=False
        )
        note2 = ClientNote(
            content="Second note",
            user_id=user.id,
            client_id=test_client.id,
            is_important=True
        )
        note3 = ClientNote(
            content="Third note",
            user_id=user.id,
            client_id=test_client.id,
            is_important=False
        )
        db.session.add_all([note1, note2, note3])
        db.session.commit()
        
        # Get all notes
        notes = ClientNote.get_client_notes(test_client.id)
        assert len(notes) == 3
        
        # Get notes ordered by importance
        notes_ordered = ClientNote.get_client_notes(test_client.id, order_by_important=True)
        assert len(notes_ordered) == 3
        # Important note should be first
        assert notes_ordered[0].is_important is True


@pytest.mark.unit
@pytest.mark.models
def test_get_important_notes(app, user, test_client):
    """Test getting only important notes."""
    with app.app_context():
        # Create multiple notes
        note1 = ClientNote(
            content="Regular note",
            user_id=user.id,
            client_id=test_client.id,
            is_important=False
        )
        note2 = ClientNote(
            content="Important note 1",
            user_id=user.id,
            client_id=test_client.id,
            is_important=True
        )
        note3 = ClientNote(
            content="Important note 2",
            user_id=user.id,
            client_id=test_client.id,
            is_important=True
        )
        db.session.add_all([note1, note2, note3])
        db.session.commit()
        
        # Get all important notes
        important_notes = ClientNote.get_important_notes()
        assert len(important_notes) == 2
        assert all(note.is_important for note in important_notes)
        
        # Get important notes for specific client
        client_important = ClientNote.get_important_notes(client_id=test_client.id)
        assert len(client_important) == 2


@pytest.mark.unit
@pytest.mark.models
def test_get_user_notes(app, user, test_client):
    """Test getting notes by a specific user."""
    with app.app_context():
        # Create notes by user
        note1 = ClientNote(
            content="User note 1",
            user_id=user.id,
            client_id=test_client.id
        )
        note2 = ClientNote(
            content="User note 2",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add_all([note1, note2])
        
        # Create note by other user
        other_user = User(username='otheruser', role='user')
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()
        
        note3 = ClientNote(
            content="Other user note",
            user_id=other_user.id,
            client_id=test_client.id
        )
        db.session.add(note3)
        db.session.commit()
        
        # Get notes by specific user
        user_notes = ClientNote.get_user_notes(user.id)
        assert len(user_notes) == 2
        assert all(note.user_id == user.id for note in user_notes)
        
        # Test with limit
        limited_notes = ClientNote.get_user_notes(user.id, limit=1)
        assert len(limited_notes) == 1


@pytest.mark.unit
@pytest.mark.models
def test_get_recent_notes(app, user, test_client):
    """Test getting recent notes across all clients."""
    with app.app_context():
        # Create multiple notes
        for i in range(15):
            note = ClientNote(
                content=f"Note {i}",
                user_id=user.id,
                client_id=test_client.id
            )
            db.session.add(note)
        db.session.commit()
        
        # Get recent notes with default limit
        recent_notes = ClientNote.get_recent_notes()
        assert len(recent_notes) == 10
        
        # Get recent notes with custom limit
        recent_notes_5 = ClientNote.get_recent_notes(limit=5)
        assert len(recent_notes_5) == 5


@pytest.mark.unit
@pytest.mark.models
def test_client_note_repr(app, user, test_client):
    """Test client note string representation."""
    with app.app_context():
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=test_client.id
        )
        db.session.add(note)
        db.session.commit()
        
        db.session.refresh(note)
        repr_str = repr(note)
        assert 'ClientNote' in repr_str
        assert user.username in repr_str
        assert str(test_client.id) in repr_str


@pytest.mark.unit
@pytest.mark.models
def test_client_note_cascade_delete(app, user, test_client):
    """Test that notes are deleted when client is deleted."""
    with app.app_context():
        # Re-query the client to ensure it's in the current session
        from app.models import Client
        client = Client.query.get(test_client.id)
        
        note = ClientNote(
            content="Test note",
            user_id=user.id,
            client_id=client.id
        )
        db.session.add(note)
        db.session.commit()
        
        note_id = note.id
        
        # Delete client
        db.session.delete(client)
        db.session.commit()
        
        # Note should be deleted
        deleted_note = ClientNote.query.get(note_id)
        assert deleted_note is None

