"""Routes for contact management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Contact, Client, ContactCommunication
from app.utils.db import safe_commit
from app.utils.timezone import parse_local_datetime
from datetime import datetime

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('/clients/<int:client_id>/contacts')
@login_required
def list_contacts(client_id):
    """List all contacts for a client"""
    client = Client.query.get_or_404(client_id)
    contacts = Contact.get_active_contacts(client_id)
    return render_template('contacts/list.html', client=client, contacts=contacts)

@contacts_bp.route('/clients/<int:client_id>/contacts/create', methods=['GET', 'POST'])
@login_required
def create_contact(client_id):
    """Create a new contact for a client"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        try:
            contact = Contact(
                client_id=client_id,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                created_by=current_user.id,
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                mobile=request.form.get('mobile', '').strip() or None,
                title=request.form.get('title', '').strip() or None,
                department=request.form.get('department', '').strip() or None,
                role=request.form.get('role', 'contact').strip() or 'contact',
                is_primary=request.form.get('is_primary') == 'on',
                address=request.form.get('address', '').strip() or None,
                notes=request.form.get('notes', '').strip() or None,
                tags=request.form.get('tags', '').strip() or None
            )
            
            db.session.add(contact)
            
            # If this is set as primary, unset others
            if contact.is_primary:
                Contact.query.filter(
                    Contact.client_id == client_id,
                    Contact.id != contact.id,
                    Contact.is_primary == True
                ).update({'is_primary': False})
            
            if safe_commit():
                flash(_('Contact created successfully'), 'success')
                return redirect(url_for('contacts.list_contacts', client_id=client_id))
        except Exception as e:
            db.session.rollback()
            flash(_('Error creating contact: %(error)s', error=str(e)), 'error')
    
    return render_template('contacts/form.html', client=client, contact=None)

@contacts_bp.route('/contacts/<int:contact_id>')
@login_required
def view_contact(contact_id):
    """View a contact"""
    contact = Contact.query.get_or_404(contact_id)
    communications = ContactCommunication.get_recent_communications(contact_id, limit=20)
    return render_template('contacts/view.html', contact=contact, communications=communications)

@contacts_bp.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    """Edit a contact"""
    contact = Contact.query.get_or_404(contact_id)
    
    if request.method == 'POST':
        try:
            contact.first_name = request.form.get('first_name', '').strip()
            contact.last_name = request.form.get('last_name', '').strip()
            contact.email = request.form.get('email', '').strip() or None
            contact.phone = request.form.get('phone', '').strip() or None
            contact.mobile = request.form.get('mobile', '').strip() or None
            contact.title = request.form.get('title', '').strip() or None
            contact.department = request.form.get('department', '').strip() or None
            contact.role = request.form.get('role', 'contact').strip() or 'contact'
            contact.is_primary = request.form.get('is_primary') == 'on'
            contact.address = request.form.get('address', '').strip() or None
            contact.notes = request.form.get('notes', '').strip() or None
            contact.tags = request.form.get('tags', '').strip() or None
            contact.updated_at = datetime.utcnow()
            
            # If this is set as primary, unset others
            if contact.is_primary:
                Contact.query.filter(
                    Contact.client_id == contact.client_id,
                    Contact.id != contact.id,
                    Contact.is_primary == True
                ).update({'is_primary': False})
            
            if safe_commit():
                flash(_('Contact updated successfully'), 'success')
                return redirect(url_for('contacts.view_contact', contact_id=contact_id))
        except Exception as e:
            db.session.rollback()
            flash(_('Error updating contact: %(error)s', error=str(e)), 'error')
    
    return render_template('contacts/form.html', client=contact.client, contact=contact)

@contacts_bp.route('/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Delete a contact (soft delete by setting is_active=False)"""
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        contact.is_active = False
        contact.updated_at = datetime.utcnow()
        
        if safe_commit():
            flash(_('Contact deleted successfully'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Error deleting contact: %(error)s', error=str(e)), 'error')
    
    return redirect(url_for('contacts.list_contacts', client_id=contact.client_id))

@contacts_bp.route('/contacts/<int:contact_id>/set-primary', methods=['POST'])
@login_required
def set_primary_contact(contact_id):
    """Set a contact as primary"""
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        contact.set_as_primary()
        if safe_commit():
            flash(_('Contact set as primary'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Error setting primary contact: %(error)s', error=str(e)), 'error')
    
    return redirect(url_for('contacts.list_contacts', client_id=contact.client_id))

@contacts_bp.route('/contacts/<int:contact_id>/communications/create', methods=['GET', 'POST'])
@login_required
def create_communication(contact_id):
    """Create a communication record for a contact"""
    contact = Contact.query.get_or_404(contact_id)
    
    if request.method == 'POST':
        try:
            comm_date_str = request.form.get('communication_date', '')
            comm_date = parse_local_datetime(comm_date_str) if comm_date_str else datetime.utcnow()
            
            follow_up_str = request.form.get('follow_up_date', '')
            follow_up_date = parse_local_datetime(follow_up_str) if follow_up_str else None
            
            communication = ContactCommunication(
                contact_id=contact_id,
                type=request.form.get('type', 'note').strip(),
                created_by=current_user.id,
                subject=request.form.get('subject', '').strip() or None,
                content=request.form.get('content', '').strip() or None,
                direction=request.form.get('direction', 'outbound').strip(),
                status=request.form.get('status', 'completed').strip() or None,
                communication_date=comm_date,
                follow_up_date=follow_up_date,
                related_project_id=int(request.form.get('related_project_id')) if request.form.get('related_project_id') else None,
                related_quote_id=int(request.form.get('related_quote_id')) if request.form.get('related_quote_id') else None,
                related_deal_id=int(request.form.get('related_deal_id')) if request.form.get('related_deal_id') else None
            )
            
            db.session.add(communication)
            
            if safe_commit():
                flash(_('Communication recorded successfully'), 'success')
                return redirect(url_for('contacts.view_contact', contact_id=contact_id))
        except Exception as e:
            db.session.rollback()
            flash(_('Error recording communication: %(error)s', error=str(e)), 'error')
    
    return render_template('contacts/communication_form.html', contact=contact, communication=None)

