from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Quote, QuoteItem, Client, Project, Invoice
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required, permission_required

quotes_bp = Blueprint('quotes', __name__)

@quotes_bp.route('/quotes')
@login_required
def list_quotes():
    """List all quotes"""
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()
    
    query = Quote.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Quote.title.ilike(like),
                Quote.quote_number.ilike(like),
                Quote.description.ilike(like)
            )
        )
    
    quotes = query.order_by(Quote.created_at.desc()).all()
    
    return render_template('quotes/list.html', quotes=quotes, status=status, search=search)

@quotes_bp.route('/quotes/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('create_quotes')
def create_quote():
    """Create a new quote"""
    if request.method == 'POST':
        client_id = request.form.get('client_id', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        total_amount = request.form.get('total_amount', '').strip()
        hourly_rate = request.form.get('hourly_rate', '').strip()
        estimated_hours = request.form.get('estimated_hours', '').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        valid_until = request.form.get('valid_until', '').strip()
        notes = request.form.get('notes', '').strip()
        terms = request.form.get('terms', '').strip()
        
        try:
            current_app.logger.info(
                "POST /quotes/create user=%s title=%s client_id=%s",
                current_user.username,
                title or '<empty>',
                client_id or '<empty>'
            )
        except Exception:
            pass
        
        # Validate required fields
        if not title or not client_id:
            flash(_('Quote title and client are required'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        # Get client and validate
        client = Client.query.get(client_id)
        if not client:
            flash(_('Selected client not found'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        # Validate amounts
        try:
            total_amount = Decimal(total_amount) if total_amount else None
            if total_amount is not None and total_amount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid total amount format'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        try:
            hourly_rate = Decimal(hourly_rate) if hourly_rate else None
            if hourly_rate is not None and hourly_rate < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid hourly rate format'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
            if estimated_hours is not None and estimated_hours < 0:
                raise ValueError
        except ValueError:
            flash(_('Invalid estimated hours format'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        try:
            tax_rate = Decimal(tax_rate) if tax_rate else Decimal('0')
            if tax_rate < 0 or tax_rate > 100:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid tax rate format'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        # Parse valid_until date
        valid_until_date = None
        if valid_until:
            try:
                valid_until_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
            except ValueError:
                flash(_('Invalid date format for valid until'), 'error')
                return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        # Generate quote number
        quote_number = Quote.generate_quote_number()
        
        # Create quote
        quote = Quote(
            quote_number=quote_number,
            client_id=client_id,
            title=title,
            created_by=current_user.id,
            description=description,
            tax_rate=tax_rate,
            currency_code=currency_code,
            valid_until=valid_until_date,
            notes=notes,
            terms=terms
        )
        
        db.session.add(quote)
        db.session.flush()  # Get quote ID for items
        
        # Process line items if provided
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        item_units = request.form.getlist('item_unit[]')
        
        for desc, qty, price, unit in zip(item_descriptions, item_quantities, item_prices, item_units):
            if desc.strip():
                try:
                    item = QuoteItem(
                        quote_id=quote.id,
                        description=desc.strip(),
                        quantity=Decimal(qty) if qty else Decimal('1'),
                        unit_price=Decimal(price) if price else Decimal('0'),
                        unit=unit.strip() if unit else None
                    )
                    db.session.add(item)
                except (ValueError, InvalidOperation):
                    pass  # Skip invalid items
        
        quote.calculate_totals()
        
        if not safe_commit('create_quote', {'title': title, 'client_id': client_id}):
            flash(_('Could not create quote due to a database error. Please check server logs.'), 'error')
            return render_template('quotes/create.html', clients=Client.get_active_clients())
        
        # Log event
        log_event("quote.created", 
                 user_id=current_user.id, 
                 quote_id=quote.id, 
                 quote_title=title,
                 client_id=client_id)
        track_event(current_user.id, "quote.created", {
            "quote_id": quote.id,
            "quote_title": title,
            "client_id": client_id
        })
        
        flash(_('Quote created successfully'), 'success')
        return redirect(url_for('quotes.view_quote', quote_id=quote.id))
    
    return render_template('quotes/create.html', clients=Client.get_active_clients())

@quotes_bp.route('/quotes/<int:quote_id>')
@login_required
def view_quote(quote_id):
    """View quote details"""
    quote = Quote.query.get_or_404(quote_id)
    return render_template('quotes/view.html', quote=quote)

@quotes_bp.route('/quotes/<int:quote_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('edit_quotes')
def edit_quote(quote_id):
    """Edit an quote"""
    quote = Quote.query.get_or_404(quote_id)
    
    # Only allow editing draft quotes
    if quote.status != 'draft':
        flash(_('Only draft quotes can be edited'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        total_amount = request.form.get('total_amount', '').strip()
        hourly_rate = request.form.get('hourly_rate', '').strip()
        estimated_hours = request.form.get('estimated_hours', '').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        currency_code = request.form.get('currency_code', 'EUR').strip()
        valid_until = request.form.get('valid_until', '').strip()
        notes = request.form.get('notes', '').strip()
        terms = request.form.get('terms', '').strip()
        
        # Validate amounts
        try:
            total_amount = Decimal(total_amount) if total_amount else None
            if total_amount is not None and total_amount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid total amount format'), 'error')
            return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        try:
            hourly_rate = Decimal(hourly_rate) if hourly_rate else None
            if hourly_rate is not None and hourly_rate < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid hourly rate format'), 'error')
            return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
            if estimated_hours is not None and estimated_hours < 0:
                raise ValueError
        except ValueError:
            flash(_('Invalid estimated hours format'), 'error')
            return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        try:
            tax_rate = Decimal(tax_rate) if tax_rate else Decimal('0')
            if tax_rate < 0 or tax_rate > 100:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_('Invalid tax rate format'), 'error')
            return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        # Parse valid_until date
        valid_until_date = None
        if valid_until:
            try:
                valid_until_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
            except ValueError:
                flash(_('Invalid date format for valid until'), 'error')
                return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        # Update quote
        quote.title = title
        quote.description = description.strip() if description else None
        quote.total_amount = total_amount
        quote.hourly_rate = hourly_rate
        quote.estimated_hours = estimated_hours
        quote.tax_rate = tax_rate
        quote.currency_code = currency_code
        quote.valid_until = valid_until_date
        quote.notes = notes.strip() if notes else None
        quote.terms = terms.strip() if terms else None
        
        if not safe_commit('edit_quote', {'quote_id': quote_id}):
            flash(_('Could not update quote due to a database error. Please check server logs.'), 'error')
            return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())
        
        log_event("quote.updated", 
                 user_id=current_user.id, 
                 quote_id=quote.id, 
                 quote_title=title)
        track_event(current_user.id, "quote.updated", {
            "quote_id": quote.id,
            "quote_title": title
        })
        
        flash(_('Quote updated successfully'), 'success')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    return render_template('quotes/edit.html', quote=quote, clients=Client.get_active_clients())

@quotes_bp.route('/quotes/<int:quote_id>/send', methods=['POST'])
@login_required
@admin_or_permission_required('edit_quotes')
def send_quote(quote_id):
    """Send an quote to the client"""
    quote = Quote.query.get_or_404(quote_id)
    
    if quote.status != 'draft':
        flash(_('Only draft quotes can be sent'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    quote.send()
    
    if not safe_commit('send_quote', {'quote_id': quote_id}):
        flash(_('Could not send quote due to a database error. Please check server logs.'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    log_event("quote.sent", 
             user_id=current_user.id, 
             quote_id=quote.id, 
             quote_title=quote.title)
    track_event(current_user.id, "quote.sent", {
        "quote_id": quote.id,
        "quote_title": quote.title
    })
    
    flash(_('Quote sent successfully'), 'success')
    return redirect(url_for('quotes.view_quote', quote_id=quote_id))

@quotes_bp.route('/quotes/<int:quote_id>/accept', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('accept_quotes')
def accept_quote(quote_id):
    """Accept an quote and create a project"""
    quote = Quote.query.get_or_404(quote_id)
    
    if not quote.can_be_accepted:
        flash(_('This quote cannot be accepted'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    if request.method == 'POST':
        # Create project from quote
        project_name = request.form.get('project_name', quote.title).strip()
        if not project_name:
            project_name = quote.title
        
        # Use quote's budget as project budget
        budget_amount = quote.total_amount
        
        # Create project
        project = Project(
            name=project_name,
            client_id=quote.client_id,
            description=quote.description,
            billable=True,
            hourly_rate=quote.hourly_rate,
            budget_amount=budget_amount,
            quote_id=quote.id,
            status='active'
        )
        
        db.session.add(project)
        
        # Accept the quote
        try:
            db.session.flush()  # Get project ID
            quote.accept(current_user.id, project.id)
        except ValueError as e:
            flash(_('Could not accept quote: %(error)s', error=str(e)), 'error')
            db.session.rollback()
            return redirect(url_for('quotes.view_quote', quote_id=quote_id))
        
        if not safe_commit('accept_quote', {'quote_id': quote_id, 'project_id': project.id}):
            flash(_('Could not accept quote due to a database error. Please check server logs.'), 'error')
            return redirect(url_for('quotes.view_quote', quote_id=quote_id))
        
        log_event("quote.accepted", 
                 user_id=current_user.id, 
                 quote_id=quote.id, 
                 quote_title=quote.title,
                 project_id=project.id)
        track_event(current_user.id, "quote.accepted", {
            "quote_id": quote.id,
            "quote_title": quote.title,
            "project_id": project.id
        })
        
        flash(_('Quote accepted and project created successfully'), 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('quotes/accept.html', quote=quote)

@quotes_bp.route('/quotes/<int:quote_id>/reject', methods=['POST'])
@login_required
@admin_or_permission_required('edit_quotes')
def reject_quote(quote_id):
    """Reject an quote"""
    quote = Quote.query.get_or_404(quote_id)
    
    if quote.status not in ['sent', 'draft']:
        flash(_('This quote cannot be rejected'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    try:
        quote.reject()
    except ValueError as e:
        flash(_('Could not reject quote: %(error)s', error=str(e)), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    if not safe_commit('reject_quote', {'quote_id': quote_id}):
        flash(_('Could not reject quote due to a database error. Please check server logs.'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    log_event("quote.rejected", 
             user_id=current_user.id, 
             quote_id=quote.id, 
             quote_title=quote.title)
    track_event(current_user.id, "quote.rejected", {
        "quote_id": quote.id,
        "quote_title": quote.title
    })
    
    flash(_('Quote rejected'), 'success')
    return redirect(url_for('quotes.view_quote', quote_id=quote_id))

@quotes_bp.route('/quotes/<int:quote_id>/delete', methods=['POST'])
@login_required
@admin_or_permission_required('delete_quotes')
def delete_quote(quote_id):
    """Delete an quote"""
    quote = Quote.query.get_or_404(quote_id)
    
    # Only allow deleting draft or rejected quotes
    if quote.status not in ['draft', 'rejected']:
        flash(_('Only draft or rejected quotes can be deleted'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    quote_title = quote.title
    db.session.delete(quote)
    
    if not safe_commit('delete_quote', {'quote_id': quote_id}):
        flash(_('Could not delete quote due to a database error. Please check server logs.'), 'error')
        return redirect(url_for('quotes.view_quote', quote_id=quote_id))
    
    log_event("quote.deleted", 
             user_id=current_user.id, 
             quote_id=quote_id, 
             quote_title=quote_title)
    track_event(current_user.id, "quote.deleted", {
        "quote_id": quote_id,
        "quote_title": quote_title
    })
    
    flash(_('Quote deleted successfully'), 'success')
    return redirect(url_for('quotes.list_quotes'))

