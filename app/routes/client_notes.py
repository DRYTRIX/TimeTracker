from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import ClientNote, Client
from app.utils.db import safe_commit

client_notes_bp = Blueprint('client_notes', __name__)

@client_notes_bp.route('/clients/<int:client_id>/notes/create', methods=['POST'])
@login_required
def create_note(client_id):
    """Create a new note for a client"""
    # Verify client exists first (before try block to let 404 abort properly)
    client = Client.query.get_or_404(client_id)
    
    try:
        content = request.form.get('content', '').strip()
        is_important = request.form.get('is_important', 'false').lower() == 'true'
        
        # Validation
        if not content:
            flash(_('Note content cannot be empty'), 'error')
            return redirect(url_for('clients.view_client', client_id=client_id))
        
        # Create the note
        note = ClientNote(
            content=content,
            user_id=current_user.id,
            client_id=client_id,
            is_important=is_important
        )
        
        db.session.add(note)
        if safe_commit('create_client_note', {'client_id': client_id}):
            # Log note creation
            log_event("client_note.created", 
                     user_id=current_user.id, 
                     client_note_id=note.id,
                     client_id=client_id)
            track_event(current_user.id, "client_note.created", {
                "note_id": note.id,
                "client_id": client_id
            })
            flash(_('Note added successfully'), 'success')
        else:
            flash(_('Error adding note'), 'error')
    
    except ValueError as e:
        flash(_('Error adding note: %(error)s', error=str(e)), 'error')
    except Exception as e:
        flash(_('Error adding note: %(error)s', error=str(e)), 'error')
    
    # Redirect back to the client page
    return redirect(url_for('clients.view_client', client_id=client_id))

@client_notes_bp.route('/clients/<int:client_id>/notes/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_note(client_id, note_id):
    """Edit an existing client note"""
    note = ClientNote.query.get_or_404(note_id)
    
    # Verify note belongs to this client
    if note.client_id != client_id:
        flash(_('Note does not belong to this client'), 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    # Check permissions
    if not note.can_edit(current_user):
        flash(_('You do not have permission to edit this note'), 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    if request.method == 'POST':
        try:
            content = request.form.get('content', '').strip()
            is_important = request.form.get('is_important', 'false').lower() == 'true'
            
            if not content:
                flash(_('Note content cannot be empty'), 'error')
                return render_template('client_notes/edit.html', note=note, client_id=client_id)
            
            note.edit_content(content, current_user, is_important=is_important)
            
            if not safe_commit('edit_client_note', {'note_id': note_id}):
                flash(_('Error updating note'), 'error')
                return render_template('client_notes/edit.html', note=note, client_id=client_id)
            
            # Log note update
            log_event("client_note.updated", user_id=current_user.id, client_note_id=note.id)
            track_event(current_user.id, "client_note.updated", {"note_id": note.id})
            
            flash(_('Note updated successfully'), 'success')
            return redirect(url_for('clients.view_client', client_id=client_id))
        
        except ValueError as e:
            flash(_('Error updating note: %(error)s', error=str(e)), 'error')
        except Exception as e:
            flash(_('Error updating note: %(error)s', error=str(e)), 'error')
    
    return render_template('client_notes/edit.html', note=note, client_id=client_id)

@client_notes_bp.route('/clients/<int:client_id>/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(client_id, note_id):
    """Delete a client note"""
    note = ClientNote.query.get_or_404(note_id)
    
    # Verify note belongs to this client
    if note.client_id != client_id:
        flash(_('Note does not belong to this client'), 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    # Check permissions
    if not note.can_delete(current_user):
        flash(_('You do not have permission to delete this note'), 'error')
        return redirect(url_for('clients.view_client', client_id=client_id))
    
    try:
        note_id_for_log = note.id
        
        db.session.delete(note)
        
        if not safe_commit('delete_client_note', {'note_id': note_id}):
            flash(_('Error deleting note'), 'error')
            return redirect(url_for('clients.view_client', client_id=client_id))
        
        # Log note deletion
        log_event("client_note.deleted", user_id=current_user.id, client_note_id=note_id_for_log)
        track_event(current_user.id, "client_note.deleted", {"note_id": note_id_for_log})
        
        flash(_('Note deleted successfully'), 'success')
    
    except Exception as e:
        flash(_('Error deleting note: %(error)s', error=str(e)), 'error')
    
    return redirect(url_for('clients.view_client', client_id=client_id))

@client_notes_bp.route('/clients/<int:client_id>/notes/<int:note_id>/toggle-important', methods=['POST'])
@login_required
def toggle_important(client_id, note_id):
    """Toggle the important flag on a client note"""
    note = ClientNote.query.get_or_404(note_id)
    
    # Verify note belongs to this client
    if note.client_id != client_id:
        return jsonify({'error': 'Note does not belong to this client'}), 400
    
    # Check permissions
    if not note.can_edit(current_user):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        note.is_important = not note.is_important
        
        if not safe_commit('toggle_important_note', {'note_id': note_id}):
            return jsonify({'error': 'Error updating note'}), 500
        
        # Log note update
        log_event("client_note.importance_toggled", 
                 user_id=current_user.id, 
                 client_note_id=note.id,
                 is_important=note.is_important)
        track_event(current_user.id, "client_note.importance_toggled", {
            "note_id": note.id,
            "is_important": note.is_important
        })
        
        return jsonify({
            'success': True,
            'is_important': note.is_important
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_notes_bp.route('/api/clients/<int:client_id>/notes')
@login_required
def list_notes(client_id):
    """API endpoint to get notes for a client"""
    order_by_important = request.args.get('order_by_important', 'false').lower() == 'true'
    
    try:
        # Verify client exists
        client = Client.query.get_or_404(client_id)
        notes = ClientNote.get_client_notes(client_id, order_by_important)
        
        return jsonify({
            'success': True,
            'notes': [note.to_dict() for note in notes]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_notes_bp.route('/api/client-notes/<int:note_id>')
@login_required
def get_note(note_id):
    """API endpoint to get a single client note"""
    try:
        note = ClientNote.query.get_or_404(note_id)
        return jsonify({
            'success': True,
            'note': note.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_notes_bp.route('/api/client-notes/important')
@login_required
def get_important_notes():
    """API endpoint to get all important client notes"""
    client_id = request.args.get('client_id', type=int)
    
    try:
        notes = ClientNote.get_important_notes(client_id)
        return jsonify({
            'success': True,
            'notes': [note.to_dict() for note in notes]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_notes_bp.route('/api/client-notes/recent')
@login_required
def get_recent_notes():
    """API endpoint to get recent client notes"""
    limit = request.args.get('limit', 10, type=int)
    
    try:
        notes = ClientNote.get_recent_notes(limit)
        return jsonify({
            'success': True,
            'notes': [note.to_dict() for note in notes]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@client_notes_bp.route('/api/client-notes/user/<int:user_id>')
@login_required
def get_user_notes(user_id):
    """API endpoint to get notes by a specific user"""
    limit = request.args.get('limit', type=int)
    
    # Only allow users to see their own notes unless they're admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        notes = ClientNote.get_user_notes(user_id, limit)
        return jsonify({
            'success': True,
            'notes': [note.to_dict() for note in notes]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

