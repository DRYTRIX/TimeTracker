from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Quote, QuoteItem, QuoteAttachment, Client, Project, Invoice
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required, permission_required

quotes_bp = Blueprint("quotes", __name__)


@quotes_bp.route("/quotes")
@login_required
def list_quotes():
    """List all quotes with optional analytics"""
    status = request.args.get("status", "all")
    search = request.args.get("search", "").strip()
    show_analytics = request.args.get("analytics", "false").lower() == "true"

    # Use service layer for quote listing with analytics
    from app.services import QuoteService
    
    quote_service = QuoteService()
    result = quote_service.list_quotes(
        user_id=current_user.id if not current_user.is_admin else None,
        is_admin=current_user.is_admin,
        status=status,
        search=search if search else None,
        include_analytics=show_analytics,
    )
    
    quotes = result["quotes"]
    analytics = result.get("analytics")

    return render_template(
        "quotes/list.html",
        quotes=quotes,
        status=status,
        search=search,
        analytics=analytics,
        show_analytics=show_analytics,
    )


@quotes_bp.route("/quotes/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("create_quotes")
def create_quote():
    """Create a new quote"""
    if request.method == "POST":
        client_id = request.form.get("client_id", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        total_amount = request.form.get("total_amount", "").strip()
        hourly_rate = request.form.get("hourly_rate", "").strip()
        estimated_hours = request.form.get("estimated_hours", "").strip()
        tax_rate = request.form.get("tax_rate", "0").strip()
        currency_code = request.form.get("currency_code", "EUR").strip()
        valid_until = request.form.get("valid_until", "").strip()
        notes = request.form.get("notes", "").strip()
        terms = request.form.get("terms", "").strip()

        try:
            current_app.logger.info(
                "POST /quotes/create user=%s title=%s client_id=%s",
                current_user.username,
                title or "<empty>",
                client_id or "<empty>",
            )
        except Exception:
            pass

        # Validate required fields
        if not title or not client_id:
            flash(_("Quote title and client are required"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        # Get client and validate
        client = Client.query.get(client_id)
        if not client:
            flash(_("Selected client not found"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        # Validate amounts
        try:
            total_amount = Decimal(total_amount) if total_amount else None
            if total_amount is not None and total_amount < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_("Invalid total amount format"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        try:
            hourly_rate = Decimal(hourly_rate) if hourly_rate else None
            if hourly_rate is not None and hourly_rate < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_("Invalid hourly rate format"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        try:
            estimated_hours = float(estimated_hours) if estimated_hours else None
            if estimated_hours is not None and estimated_hours < 0:
                raise ValueError
        except ValueError:
            flash(_("Invalid estimated hours format"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        try:
            tax_rate = Decimal(tax_rate) if tax_rate else Decimal("0")
            if tax_rate < 0 or tax_rate > 100:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_("Invalid tax rate format"), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        # Validate discount fields
        discount_amount_decimal = None
        if discount_type and discount_amount:
            try:
                discount_amount_decimal = Decimal(discount_amount)
                if discount_type == "percentage":
                    if discount_amount_decimal < 0 or discount_amount_decimal > 100:
                        raise InvalidOperation
                elif discount_type == "fixed":
                    if discount_amount_decimal < 0:
                        raise InvalidOperation
                else:
                    discount_type = None  # Invalid type, ignore discount
            except (InvalidOperation, ValueError):
                flash(_("Invalid discount amount format"), "error")
                return render_template("quotes/create.html", clients=Client.get_active_clients())

        # Parse valid_until date
        valid_until_date = None
        if valid_until:
            try:
                valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
            except ValueError:
                flash(_("Invalid date format for valid until"), "error")
                return render_template("quotes/create.html", clients=Client.get_active_clients())

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
            terms=terms,
            payment_terms=payment_terms if payment_terms else None,
            discount_type=discount_type if discount_type else None,
            discount_amount=discount_amount_decimal if discount_amount_decimal else None,
            discount_reason=discount_reason if discount_reason else None,
            coupon_code=coupon_code.upper() if coupon_code else None,
        )

        db.session.add(quote)
        db.session.flush()  # Get quote ID for items

        # Process line items if provided
        item_descriptions = request.form.getlist("item_description[]")
        item_quantities = request.form.getlist("item_quantity[]")
        item_prices = request.form.getlist("item_price[]")
        item_units = request.form.getlist("item_unit[]")
        item_stock_ids = request.form.getlist("item_stock_item_id[]")
        item_warehouse_ids = request.form.getlist("item_warehouse_id[]")

        for desc, qty, price, unit, stock_id, wh_id in zip(
            item_descriptions, item_quantities, item_prices, item_units, item_stock_ids, item_warehouse_ids
        ):
            if desc.strip():
                try:
                    stock_item_id = int(stock_id) if stock_id and stock_id.strip() else None
                    warehouse_id = int(wh_id) if wh_id and wh_id.strip() else None

                    item = QuoteItem(
                        quote_id=quote.id,
                        description=desc.strip(),
                        quantity=Decimal(qty) if qty else Decimal("1"),
                        unit_price=Decimal(price) if price else Decimal("0"),
                        unit=unit.strip() if unit else None,
                        stock_item_id=stock_item_id,
                        warehouse_id=warehouse_id,
                    )
                    db.session.add(item)
                except (ValueError, InvalidOperation):
                    pass  # Skip invalid items

        quote.calculate_totals()

        if not safe_commit("create_quote", {"title": title, "client_id": client_id}):
            flash(_("Could not create quote due to a database error. Please check server logs."), "error")
            return render_template("quotes/create.html", clients=Client.get_active_clients())

        # Log event
        log_event("quote.created", user_id=current_user.id, quote_id=quote.id, quote_title=title, client_id=client_id)
        track_event(
            current_user.id, "quote.created", {"quote_id": quote.id, "quote_title": title, "client_id": client_id}
        )

        flash(_("Quote created successfully"), "success")
        return redirect(url_for("quotes.view_quote", quote_id=quote.id))

    return render_template("quotes/create.html", clients=Client.get_active_clients())


@quotes_bp.route("/quotes/<int:quote_id>")
@login_required
def view_quote(quote_id):
    """View quote details"""
    from app.services import QuoteService
    from sqlalchemy.orm import joinedload
    from app.models import Comment
    
    # Use service layer with eager loading
    quote_service = QuoteService()
    quote = quote_service.get_quote_with_details(
        quote_id=quote_id,
        user_id=current_user.id if not current_user.is_admin else None,
        is_admin=current_user.is_admin
    )
    
    if not quote:
        flash(_("Quote not found"), "error")
        return redirect(url_for("quotes.list_quotes"))
    
    quote.calculate_totals()  # Ensure totals are up to date
    
    # Get all comments (both internal and client-facing)
    comments = Comment.get_quote_comments(quote_id, include_replies=True, include_internal=True)

    return render_template("quotes/view.html", quote=quote, comments=comments)


@quotes_bp.route("/quotes/<int:quote_id>/edit", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def edit_quote(quote_id):
    """Edit an quote"""
    from sqlalchemy.orm import joinedload
    
    quote = Quote.query.options(
        joinedload(Quote.client),
        joinedload(Quote.items)
    ).filter_by(id=quote_id).first_or_404()

    # Only allow editing draft quotes
    if quote.status != "draft":
        flash(_("Only draft quotes can be edited"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        tax_rate = request.form.get("tax_rate", "0").strip()
        currency_code = request.form.get("currency_code", "EUR").strip()
        valid_until = request.form.get("valid_until", "").strip()
        notes = request.form.get("notes", "").strip()
        terms = request.form.get("terms", "").strip()
        payment_terms = request.form.get("payment_terms", "").strip()
        visible_to_client = request.form.get("visible_to_client") == "on"

        # Discount fields
        discount_type = request.form.get("discount_type", "").strip()
        discount_amount = request.form.get("discount_amount", "").strip()
        discount_reason = request.form.get("discount_reason", "").strip()
        coupon_code = request.form.get("coupon_code", "").strip()

        try:
            tax_rate = Decimal(tax_rate) if tax_rate else Decimal("0")
            if tax_rate < 0 or tax_rate > 100:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_("Invalid tax rate format"), "error")
            return render_template("quotes/edit.html", quote=quote, clients=Client.get_active_clients())

        # Validate discount fields
        discount_amount_decimal = None
        if discount_type and discount_amount:
            try:
                discount_amount_decimal = Decimal(discount_amount)
                if discount_type == "percentage":
                    if discount_amount_decimal < 0 or discount_amount_decimal > 100:
                        raise InvalidOperation
                elif discount_type == "fixed":
                    if discount_amount_decimal < 0:
                        raise InvalidOperation
                else:
                    discount_type = None  # Invalid type, ignore discount
            except (InvalidOperation, ValueError):
                flash(_("Invalid discount amount format"), "error")
                return render_template("quotes/edit.html", quote=quote, clients=Client.get_active_clients())

        # Parse valid_until date
        valid_until_date = None
        if valid_until:
            try:
                valid_until_date = datetime.strptime(valid_until, "%Y-%m-%d").date()
            except ValueError:
                flash(_("Invalid date format for valid until"), "error")
                return render_template("quotes/edit.html", quote=quote, clients=Client.get_active_clients())

        # Update quote
        quote.title = title
        quote.description = description.strip() if description else None
        quote.tax_rate = tax_rate
        quote.currency_code = currency_code
        quote.valid_until = valid_until_date
        quote.notes = notes.strip() if notes else None
        quote.terms = terms.strip() if terms else None
        quote.payment_terms = payment_terms.strip() if payment_terms else None
        quote.visible_to_client = visible_to_client

        # Update discount fields
        quote.discount_type = discount_type if discount_type else None
        quote.discount_amount = discount_amount_decimal if discount_amount_decimal else None
        quote.discount_reason = discount_reason.strip() if discount_reason else None
        quote.coupon_code = coupon_code.upper().strip() if coupon_code else None

        # Update line items
        item_ids = request.form.getlist("item_id[]")
        item_descriptions = request.form.getlist("item_description[]")
        item_quantities = request.form.getlist("item_quantity[]")
        item_prices = request.form.getlist("item_price[]")
        item_units = request.form.getlist("item_unit[]")

        # Delete items not in the form
        existing_item_ids = {int(id) for id in item_ids if id}
        for item in quote.items:
            if item.id not in existing_item_ids:
                db.session.delete(item)

        # Update or create items
        item_stock_ids = request.form.getlist("item_stock_item_id[]")
        item_warehouse_ids = request.form.getlist("item_warehouse_id[]")

        # Pad lists to match length
        while len(item_stock_ids) < len(item_ids):
            item_stock_ids.append("")
        while len(item_warehouse_ids) < len(item_ids):
            item_warehouse_ids.append("")

        for item_id, desc, qty, price, unit, stock_id, wh_id in zip(
            item_ids, item_descriptions, item_quantities, item_prices, item_units, item_stock_ids, item_warehouse_ids
        ):
            if desc.strip():
                try:
                    stock_item_id = int(stock_id) if stock_id and stock_id.strip() else None
                    warehouse_id = int(wh_id) if wh_id and wh_id.strip() else None

                    if item_id:
                        # Update existing item
                        item = QuoteItem.query.get(item_id)
                        if item and item.quote_id == quote.id:
                            item.description = desc.strip()
                            item.quantity = Decimal(qty) if qty else Decimal("1")
                            item.unit_price = Decimal(price) if price else Decimal("0")
                            item.total_amount = item.quantity * item.unit_price
                            item.unit = unit.strip() if unit else None
                            item.stock_item_id = stock_item_id
                            item.warehouse_id = warehouse_id
                            item.is_stock_item = stock_item_id is not None
                    else:
                        # Create new item
                        item = QuoteItem(
                            quote_id=quote.id,
                            description=desc.strip(),
                            quantity=Decimal(qty) if qty else Decimal("1"),
                            unit_price=Decimal(price) if price else Decimal("0"),
                            unit=unit.strip() if unit else None,
                            stock_item_id=stock_item_id,
                            warehouse_id=warehouse_id,
                        )
                        db.session.add(item)
                except (ValueError, InvalidOperation):
                    pass  # Skip invalid items

        quote.calculate_totals()

        if not safe_commit("edit_quote", {"quote_id": quote_id}):
            flash(_("Could not update quote due to a database error. Please check server logs."), "error")
            from app.models import StockItem, Warehouse
            import json

            stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()
            warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
            stock_items_json = json.dumps(
                [
                    {
                        "id": item.id,
                        "sku": item.sku,
                        "name": item.name,
                        "default_price": float(item.default_price) if item.default_price else None,
                        "unit": item.unit or "pcs",
                        "description": item.name,
                    }
                    for item in stock_items
                ]
            )
            warehouses_json = json.dumps([{"id": wh.id, "code": wh.code, "name": wh.name} for wh in warehouses])
            return render_template(
                "quotes/edit.html",
                quote=quote,
                clients=Client.get_active_clients(),
                stock_items=stock_items,
                warehouses=warehouses,
                stock_items_json=stock_items_json,
                warehouses_json=warehouses_json,
            )

        log_event("quote.updated", user_id=current_user.id, quote_id=quote.id, quote_title=title)
        track_event(current_user.id, "quote.updated", {"quote_id": quote.id, "quote_title": title})

        flash(_("Quote updated successfully"), "success")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    from app.models import StockItem, Warehouse
    import json

    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    stock_items_json = json.dumps(
        [
            {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "default_price": float(item.default_price) if item.default_price else None,
                "unit": item.unit or "pcs",
                "description": item.name,
            }
            for item in stock_items
        ]
    )
    warehouses_json = json.dumps([{"id": wh.id, "code": wh.code, "name": wh.name} for wh in warehouses])
    return render_template(
        "quotes/edit.html",
        quote=quote,
        clients=Client.get_active_clients(),
        stock_items=stock_items,
        warehouses=warehouses,
        stock_items_json=stock_items_json,
        warehouses_json=warehouses_json,
    )


@quotes_bp.route("/quotes/<int:quote_id>/send", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def send_quote(quote_id):
    """Send an quote to the client"""
    quote = Quote.query.get_or_404(quote_id)

    if not quote.can_be_sent:
        if quote.requires_approval and quote.approval_status != "approved":
            flash(_("Quote must be approved before it can be sent"), "error")
        else:
            flash(_("Only draft quotes can be sent"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    try:
        quote.send()
    except ValueError as e:
        flash(_("Cannot send quote: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Reserve stock for quote items if enabled
    from app.models import StockReservation
    import os

    auto_reserve_on_send = os.getenv("INVENTORY_AUTO_RESERVE_ON_QUOTE_SENT", "false").lower() == "true"
    if auto_reserve_on_send:
        for item in quote.items:
            if item.is_stock_item and item.stock_item_id and item.warehouse_id:
                try:
                    expires_in_days = get_setting("INVENTORY_QUOTE_RESERVATION_EXPIRY_DAYS", 30)
                    StockReservation.create_reservation(
                        stock_item_id=item.stock_item_id,
                        warehouse_id=item.warehouse_id,
                        quantity=item.quantity,
                        reservation_type="quote",
                        reservation_id=quote.id,
                        reserved_by=current_user.id,
                        expires_in_days=expires_in_days,
                    )
                except ValueError as e:
                    flash(
                        _(
                            "Warning: Could not reserve stock for item %(item)s: %(error)s",
                            item=item.description,
                            error=str(e),
                        ),
                        "warning",
                    )

    if not safe_commit("send_quote", {"quote_id": quote_id}):
        flash(_("Could not send quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Send notifications
    from app.utils.email import send_quote_sent_notification
    from app.models import User

    # Notify quote creator
    if quote.creator and quote.creator.email:
        send_quote_sent_notification(quote, quote.creator)

    # Notify admins
    admins = User.query.filter_by(role="admin", is_active=True).all()
    for admin in admins:
        if admin.id != quote.creator_id and admin.email:
            send_quote_sent_notification(quote, admin)

    log_event("quote.sent", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title)
    track_event(current_user.id, "quote.sent", {"quote_id": quote.id, "quote_title": quote.title})

    flash(_("Quote sent successfully"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/accept", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("accept_quotes")
def accept_quote(quote_id):
    """Accept an quote and create a project"""
    quote = Quote.query.get_or_404(quote_id)

    if not quote.can_be_accepted:
        flash(_("This quote cannot be accepted"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if request.method == "POST":
        # Create project from quote
        project_name = request.form.get("project_name", quote.title).strip()
        if not project_name:
            project_name = quote.title

        # Calculate totals to get budget amount
        quote.calculate_totals()
        budget_amount = quote.total_amount

        # Create project
        project = Project(
            name=project_name,
            client_id=quote.client_id,
            description=quote.description,
            billable=True,
            budget_amount=budget_amount,
            quote_id=quote.id,
            status="active",
        )

        db.session.add(project)

        # Accept the quote
        try:
            db.session.flush()  # Get project ID
            quote.accept(current_user.id, project.id)
        except ValueError as e:
            flash(_("Could not accept quote: %(error)s", error=str(e)), "error")
            db.session.rollback()
            return redirect(url_for("quotes.view_quote", quote_id=quote_id))

        # Reserve stock for quote items when accepted (if not already reserved)
        from app.models import StockReservation
        import os

        for item in quote.items:
            if item.is_stock_item and item.stock_item_id and item.warehouse_id:
                # Check if reservation already exists
                existing = StockReservation.query.filter_by(
                    stock_item_id=item.stock_item_id,
                    warehouse_id=item.warehouse_id,
                    reservation_type="quote",
                    reservation_id=quote.id,
                    status="reserved",
                ).first()

                if not existing:
                    try:
                        expires_in_days = int(os.getenv("INVENTORY_QUOTE_RESERVATION_EXPIRY_DAYS", "30"))
                        StockReservation.create_reservation(
                            stock_item_id=item.stock_item_id,
                            warehouse_id=item.warehouse_id,
                            quantity=item.quantity,
                            reservation_type="quote",
                            reservation_id=quote.id,
                            reserved_by=current_user.id,
                            expires_in_days=expires_in_days,
                        )
                    except ValueError as e:
                        flash(
                            _(
                                "Warning: Could not reserve stock for item %(item)s: %(error)s",
                                item=item.description,
                                error=str(e),
                            ),
                            "warning",
                        )

        if not safe_commit("accept_quote", {"quote_id": quote_id, "project_id": project.id}):
            flash(_("Could not accept quote due to a database error. Please check server logs."), "error")
            return redirect(url_for("quotes.view_quote", quote_id=quote_id))

        # Send notifications
        from app.utils.email import send_quote_accepted_notification
        from app.models import User

        # Notify quote creator
        if quote.creator and quote.creator.email:
            send_quote_accepted_notification(quote, quote.creator)

        # Notify admins
        admins = User.query.filter_by(role="admin", is_active=True).all()
        for admin in admins:
            if admin.id != quote.creator_id and admin.email:
                send_quote_accepted_notification(quote, admin)

        log_event(
            "quote.accepted", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title, project_id=project.id
        )
        track_event(
            current_user.id,
            "quote.accepted",
            {"quote_id": quote.id, "quote_title": quote.title, "project_id": project.id},
        )

        flash(_("Quote accepted and project created successfully"), "success")
        return redirect(url_for("projects.view_project", project_id=project.id))

    return render_template("quotes/accept.html", quote=quote)


@quotes_bp.route("/quotes/<int:quote_id>/reject", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def reject_quote(quote_id):
    """Reject an quote"""
    quote = Quote.query.get_or_404(quote_id)

    if quote.status not in ["sent", "draft"]:
        flash(_("This quote cannot be rejected"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    try:
        quote.reject()
    except ValueError as e:
        flash(_("Could not reject quote: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not safe_commit("reject_quote", {"quote_id": quote_id}):
        flash(_("Could not reject quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    log_event("quote.rejected", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title)
    track_event(current_user.id, "quote.rejected", {"quote_id": quote.id, "quote_title": quote.title})

    flash(_("Quote rejected"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("delete_quotes")
def delete_quote(quote_id):
    """Delete an quote"""
    quote = Quote.query.get_or_404(quote_id)

    # Only allow deleting draft or rejected quotes
    if quote.status not in ["draft", "rejected"]:
        flash(_("Only draft or rejected quotes can be deleted"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    quote_title = quote.title
    db.session.delete(quote)

    if not safe_commit("delete_quote", {"quote_id": quote_id}):
        flash(_("Could not delete quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    log_event("quote.deleted", user_id=current_user.id, quote_id=quote_id, quote_title=quote_title)
    track_event(current_user.id, "quote.deleted", {"quote_id": quote_id, "quote_title": quote_title})

    flash(_("Quote deleted successfully"), "success")
    return redirect(url_for("quotes.list_quotes"))


@quotes_bp.route("/quotes/<int:quote_id>/attachments/upload", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def upload_attachment(quote_id):
    """Upload an attachment to a quote"""
    from werkzeug.utils import secure_filename
    from flask import current_app
    import os
    from datetime import datetime

    quote = Quote.query.get_or_404(quote_id)

    # Check permissions
    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to upload attachments to this quote"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # File upload configuration
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "txt", "xls", "xlsx", "zip", "rar"}
    UPLOAD_FOLDER = "uploads/quote_attachments"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if "file" not in request.files:
        flash(_("No file provided"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    file = request.files["file"]
    if file.filename == "":
        flash(_("No file selected"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not allowed_file(file.filename):
        flash(_("File type not allowed"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        flash(_("File size exceeds maximum allowed size (10 MB)"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Save file
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{quote_id}_{timestamp}_{original_filename}"

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Get file info
    mime_type = file.content_type or "application/octet-stream"
    description = request.form.get("description", "").strip() or None
    is_visible_to_client = request.form.get("is_visible_to_client", "false").lower() == "true"

    # Create attachment record
    attachment = QuoteAttachment(
        quote_id=quote_id,
        filename=filename,
        original_filename=original_filename,
        file_path=os.path.join(UPLOAD_FOLDER, filename),
        file_size=file_size,
        uploaded_by=current_user.id,
        mime_type=mime_type,
        description=description,
        is_visible_to_client=is_visible_to_client,
    )

    db.session.add(attachment)

    if not safe_commit("upload_quote_attachment", {"quote_id": quote_id, "attachment_id": attachment.id}):
        flash(_("Could not upload attachment due to a database error. Please check server logs."), "error")
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    log_event(
        "quote.attachment.uploaded",
        user_id=current_user.id,
        quote_id=quote_id,
        attachment_id=attachment.id,
        filename=original_filename,
    )
    track_event(
        current_user.id,
        "quote.attachment.uploaded",
        {"quote_id": quote_id, "attachment_id": attachment.id, "filename": original_filename},
    )

    flash(_("Attachment uploaded successfully"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/attachments/<int:attachment_id>/download")
@login_required
def download_attachment(attachment_id):
    """Download a quote attachment"""
    from flask import send_file, current_app
    import os

    attachment = QuoteAttachment.query.get_or_404(attachment_id)
    quote = attachment.quote

    # Check permissions
    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to download this attachment"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote.id))

    # Build file path
    file_path = os.path.join(current_app.root_path, "..", attachment.file_path)

    if not os.path.exists(file_path):
        flash(_("File not found"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote.id))

    return send_file(
        file_path, as_attachment=True, download_name=attachment.original_filename, mimetype=attachment.mime_type
    )


@quotes_bp.route("/quotes/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def delete_attachment(attachment_id):
    """Delete a quote attachment"""
    from flask import current_app
    import os

    attachment = QuoteAttachment.query.get_or_404(attachment_id)
    quote = attachment.quote

    # Check permissions
    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to delete this attachment"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote.id))

    # Delete file
    file_path = os.path.join(current_app.root_path, "..", attachment.file_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Failed to delete attachment file: {e}")

    # Delete database record
    attachment_id_for_log = attachment.id
    quote_id = quote.id
    db.session.delete(attachment)

    if not safe_commit("delete_quote_attachment", {"attachment_id": attachment_id_for_log}):
        flash(_("Could not delete attachment due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    log_event(
        "quote.attachment.deleted", user_id=current_user.id, quote_id=quote_id, attachment_id=attachment_id_for_log
    )
    track_event(
        current_user.id, "quote.attachment.deleted", {"quote_id": quote_id, "attachment_id": attachment_id_for_log}
    )

    flash(_("Attachment deleted successfully"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/request-approval", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def request_approval(quote_id):
    """Request approval for a quote"""
    quote = Quote.query.get_or_404(quote_id)

    # Check permissions
    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to request approval for this quote"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not quote.requires_approval:
        flash(_("This quote does not require approval"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    try:
        quote.request_approval()
    except ValueError as e:
        flash(_("Cannot request approval: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not safe_commit("request_quote_approval", {"quote_id": quote_id}):
        flash(_("Could not request approval due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Send notification to approvers
    from app.utils.email import send_quote_approval_request_notification
    from app.models import User

    # Notify admins (default approvers)
    admins = User.query.filter_by(role="admin", is_active=True).all()
    for admin in admins:
        if admin.email:
            send_quote_approval_request_notification(quote, admin)

    log_event("quote.approval.requested", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title)
    track_event(current_user.id, "quote.approval.requested", {"quote_id": quote.id, "quote_title": quote.title})

    flash(_("Approval requested successfully"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/approve", methods=["POST"])
@login_required
@admin_or_permission_required("approve_quotes")
def approve_quote(quote_id):
    """Approve a quote"""
    quote = Quote.query.get_or_404(quote_id)

    if not quote.requires_approval:
        flash(_("This quote does not require approval"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if quote.approval_status != "pending":
        flash(_("This quote is not pending approval"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    notes = request.form.get("notes", "").strip() or None

    try:
        quote.approve(current_user.id, notes)
    except ValueError as e:
        flash(_("Cannot approve quote: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not safe_commit("approve_quote", {"quote_id": quote_id}):
        flash(_("Could not approve quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Send notification to quote creator
    from app.utils.email import send_quote_approved_notification

    if quote.creator and quote.creator.email:
        send_quote_approved_notification(quote, quote.creator)

    log_event("quote.approved", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title)
    track_event(current_user.id, "quote.approved", {"quote_id": quote.id, "quote_title": quote.title})

    flash(_("Quote approved successfully"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/reject-approval", methods=["POST"])
@login_required
@admin_or_permission_required("approve_quotes")
def reject_approval(quote_id):
    """Reject a quote in approval workflow"""
    quote = Quote.query.get_or_404(quote_id)

    if not quote.requires_approval:
        flash(_("This quote does not require approval"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if quote.approval_status != "pending":
        flash(_("This quote is not pending approval"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash(_("Rejection reason is required"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    try:
        quote.reject_approval(current_user.id, reason)
    except ValueError as e:
        flash(_("Cannot reject quote: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    if not safe_commit("reject_quote_approval", {"quote_id": quote_id}):
        flash(_("Could not reject quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    # Send notification to quote creator
    from app.utils.email import send_quote_approval_rejected_notification

    if quote.creator and quote.creator.email:
        send_quote_approval_rejected_notification(quote, quote.creator)

    log_event("quote.approval.rejected", user_id=current_user.id, quote_id=quote.id, quote_title=quote.title)
    track_event(current_user.id, "quote.approval.rejected", {"quote_id": quote.id, "quote_title": quote.title})

    flash(_("Quote approval rejected"), "success")
    return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/templates")
@login_required
def list_templates():
    """List all quote templates"""
    templates = QuoteTemplate.get_user_templates(current_user.id, include_public=True)
    return render_template("quotes/templates.html", templates=templates)


@quotes_bp.route("/quotes/templates/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("create_quotes")
def create_template():
    """Create a new quote template"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash(_("Template name is required"), "error")
            return render_template("quotes/template_form.html")

        # Get template settings
        default_tax_rate = request.form.get("default_tax_rate", "0").strip()
        default_currency_code = request.form.get("default_currency_code", "EUR").strip()
        default_payment_terms = request.form.get("default_payment_terms", "").strip() or None
        default_terms = request.form.get("default_terms", "").strip() or None
        default_valid_until_days = request.form.get("default_valid_until_days", type=int) or 30
        default_requires_approval = request.form.get("default_requires_approval", "false").lower() == "true"
        default_approval_level = request.form.get("default_approval_level", type=int) or 1
        is_public = request.form.get("is_public", "false").lower() == "true"

        try:
            default_tax_rate = Decimal(default_tax_rate) if default_tax_rate else Decimal("0")
        except (ValueError, InvalidOperation):
            default_tax_rate = Decimal("0")

        # Get default items
        item_descriptions = request.form.getlist("item_description[]")
        item_quantities = request.form.getlist("item_quantity[]")
        item_prices = request.form.getlist("item_price[]")
        item_units = request.form.getlist("item_unit[]")

        default_items = []
        for desc, qty, price, unit in zip(item_descriptions, item_quantities, item_prices, item_units):
            if desc.strip():
                default_items.append(
                    {
                        "description": desc.strip(),
                        "quantity": float(qty) if qty else 1,
                        "unit_price": float(price) if price else 0,
                        "unit": unit.strip() if unit else None,
                    }
                )

        # Create template
        template = QuoteTemplate(
            name=name,
            created_by=current_user.id,
            description=description,
            default_tax_rate=default_tax_rate,
            default_currency_code=default_currency_code,
            default_payment_terms=default_payment_terms,
            default_terms=default_terms,
            default_valid_until_days=default_valid_until_days,
            default_requires_approval=default_requires_approval,
            default_approval_level=default_approval_level,
            is_public=is_public,
        )
        template.items_list = default_items if default_items else None

        db.session.add(template)

        if not safe_commit("create_quote_template", {"template_id": template.id}):
            flash(_("Could not create template due to a database error. Please check server logs."), "error")
            return render_template("quotes/template_form.html")

        log_event("quote.template.created", user_id=current_user.id, template_id=template.id, template_name=name)
        track_event(current_user.id, "quote.template.created", {"template_id": template.id, "template_name": name})

        flash(_("Template created successfully"), "success")
        return redirect(url_for("quotes.list_templates"))

    return render_template("quotes/template_form.html")


@quotes_bp.route("/quotes/templates/<int:template_id>/save-from-quote", methods=["POST"])
@login_required
@admin_or_permission_required("create_quotes")
def save_template_from_quote(template_id):
    """Save current quote as a template"""
    quote = Quote.query.get_or_404(quote_id)

    # Check permissions
    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to create a template from this quote"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    name = request.form.get("name", "").strip()
    if not name:
        flash(_("Template name is required"), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    description = request.form.get("description", "").strip() or None
    is_public = request.form.get("is_public", "false").lower() == "true"

    # Extract items
    default_items = []
    for item in quote.items:
        default_items.append(
            {
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "unit": item.unit,
            }
        )

    # Create template
    template = QuoteTemplate(
        name=name,
        created_by=current_user.id,
        description=description,
        default_tax_rate=quote.tax_rate,
        default_currency_code=quote.currency_code,
        default_payment_terms=quote.payment_terms,
        default_terms=quote.terms,
        default_valid_until_days=30,  # Default
        default_requires_approval=quote.requires_approval,
        default_approval_level=quote.approval_level or 1,
        is_public=is_public,
    )
    template.items_list = default_items if default_items else None

    db.session.add(template)

    if not safe_commit("save_quote_template", {"template_id": template.id, "quote_id": quote_id}):
        flash(_("Could not save template due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))

    log_event("quote.template.saved_from_quote", user_id=current_user.id, template_id=template.id, quote_id=quote_id)
    track_event(current_user.id, "quote.template.saved_from_quote", {"template_id": template.id, "quote_id": quote_id})

    flash(_("Template saved successfully"), "success")
    return redirect(url_for("quotes.list_templates"))


@quotes_bp.route("/quotes/<int:quote_id>/export-pdf", methods=["GET"])
@login_required
def export_quote_pdf(quote_id):
    """Export quote as PDF"""
    quote = Quote.query.get_or_404(quote_id)

    if not current_user.is_admin and quote.created_by != current_user.id:
        flash(_("You do not have permission to export this quote"), "error")
        return redirect(request.referrer or url_for("quotes.list_quotes"))

    # Get page size from query parameter, default to A4
    page_size = request.args.get("size", "A4")

    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size not in valid_sizes:
        page_size = "A4"

    try:
        from app.utils.pdf_generator import QuotePDFGenerator
        from app.models import Settings
        import io
        from flask import send_file

        settings = Settings.get_settings()
        pdf_generator = QuotePDFGenerator(quote, settings=settings, page_size=page_size)
        pdf_bytes = pdf_generator.generate_pdf()
        filename = f"quote_{quote.quote_number}_{page_size}.pdf"
        return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename)
    except ImportError:
        # Fallback if QuotePDFGenerator doesn't exist yet
        from app.utils.pdf_generator_fallback import QuotePDFGeneratorFallback
        from app.models import Settings
        import io
        from flask import send_file

        settings = Settings.get_settings()
        pdf_generator = QuotePDFGeneratorFallback(quote, settings=settings)
        pdf_bytes = pdf_generator.generate_pdf()
        filename = f"quote_{quote.quote_number}_{page_size}.pdf"
        return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error generating quote PDF: {e}", exc_info=True)
        flash(_("Error generating PDF: %(error)s", error=str(e)), "error")
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/send-email", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def send_quote_email(quote_id):
    """Send quote via email"""
    quote = Quote.query.get_or_404(quote_id)

    # Get recipient email from request
    recipient_email = (
        request.form.get("recipient_email", "").strip() or request.json.get("recipient_email", "").strip()
        if request.is_json
        else ""
    )

    if not recipient_email:
        # Try to use quote client email
        if quote.client and quote.client.email:
            recipient_email = quote.client.email

    if not recipient_email:
        return jsonify({"error": _("Recipient email address is required")}), 400

    # Get custom message if provided
    custom_message = request.form.get("custom_message", "").strip() or (
        request.json.get("custom_message", "").strip() if request.is_json else ""
    )

    try:
        from app.utils.email import send_quote_email

        success, result, message = send_quote_email(
            quote=quote,
            recipient_email=recipient_email,
            sender_user=current_user,
            custom_message=custom_message if custom_message else None,
        )

        if success:
            flash(_("Quote sent successfully to %(email)s", email=recipient_email), "success")
            log_event(
                "quote.emailed",
                user_id=current_user.id,
                quote_id=quote.id,
                quote_title=quote.title,
                recipient_email=recipient_email,
            )
            track_event(
                current_user.id,
                "quote.emailed",
                {"quote_id": quote.id, "quote_title": quote.title, "recipient_email": recipient_email},
            )
            if request.is_json:
                return jsonify({"success": True, "message": message})
            return redirect(url_for("quotes.view_quote", quote_id=quote_id))
        else:
            flash(_("Failed to send quote: %(error)s", error=message), "error")
            if request.is_json:
                return jsonify({"error": message}), 400
            return redirect(url_for("quotes.view_quote", quote_id=quote_id))
    except Exception as e:
        current_app.logger.error(f"Error sending quote email: {e}", exc_info=True)
        flash(_("Error sending email: %(error)s", error=str(e)), "error")
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        return redirect(url_for("quotes.view_quote", quote_id=quote_id))


@quotes_bp.route("/quotes/<int:quote_id>/duplicate")
@login_required
@admin_or_permission_required("create_quotes")
def duplicate_quote(quote_id):
    """Duplicate an existing quote"""
    from datetime import timedelta
    from app.utils.timezone import local_now

    original_quote = Quote.query.get_or_404(quote_id)

    # Check access permissions
    if not current_user.is_admin and original_quote.created_by != current_user.id:
        flash(_("You do not have permission to duplicate this quote"), "error")
        return redirect(url_for("quotes.list_quotes"))

    # Generate new quote number
    new_quote_number = Quote.generate_quote_number()

    # Calculate new valid_until date (30 days from now, or extend original if it exists)
    if original_quote.valid_until:
        new_valid_until = local_now().date() + timedelta(days=30)
    else:
        new_valid_until = None

    # Create new quote
    new_quote = Quote(
        quote_number=new_quote_number,
        client_id=original_quote.client_id,
        title=original_quote.title,
        description=original_quote.description,
        status="draft",  # Always start as draft
        valid_until=new_valid_until,
        notes=original_quote.notes,
        terms=original_quote.terms,
        payment_terms=original_quote.payment_terms,
        created_by=current_user.id,
        visible_to_client=original_quote.visible_to_client,
        template_id=original_quote.template_id,
        currency_code=original_quote.currency_code,
        tax_rate=original_quote.tax_rate,
        discount_type=original_quote.discount_type,
        discount_amount=original_quote.discount_amount,
        discount_reason=original_quote.discount_reason,
        coupon_code=original_quote.coupon_code,
    )

    db.session.add(new_quote)
    if not safe_commit(
        "duplicate_quote_create", {"source_quote_id": original_quote.id, "new_quote_number": new_quote_number}
    ):
        flash(_("Could not duplicate quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.list_quotes"))

    # Duplicate quote items
    for original_item in original_quote.items:
        new_item = QuoteItem(
            quote_id=new_quote.id,
            description=original_item.description,
            quantity=original_item.quantity,
            unit_price=original_item.unit_price,
            unit=original_item.unit,
        )
        db.session.add(new_item)

    # Calculate totals
    new_quote.calculate_totals()
    if not safe_commit("duplicate_quote_finalize", {"quote_id": new_quote.id}):
        flash(_("Could not finalize duplicated quote due to a database error. Please check server logs."), "error")
        return redirect(url_for("quotes.list_quotes"))

    flash(_("Quote %(quote_number)s created as duplicate", quote_number=new_quote_number), "success")
    log_event(
        "quote.duplicated",
        user_id=current_user.id,
        quote_id=new_quote.id,
        original_quote_id=original_quote.id,
        quote_title=new_quote.title,
    )
    track_event(
        current_user.id,
        "quote.duplicated",
        {"quote_id": new_quote.id, "original_quote_id": original_quote.id, "quote_title": new_quote.title},
    )
    return redirect(url_for("quotes.edit_quote", quote_id=new_quote.id))


@quotes_bp.route("/quotes/bulk_action", methods=["POST"])
@login_required
@admin_or_permission_required("edit_quotes")
def bulk_action():
    """Perform bulk actions on selected quotes"""
    action = request.form.get("action")
    quote_ids = request.form.getlist("quote_ids[]")

    if not action or not quote_ids:
        flash(_("Please select an action and at least one quote"), "error")
        return redirect(url_for("quotes.list_quotes"))

    try:
        quote_ids = [int(qid) for qid in quote_ids]
    except ValueError:
        flash(_("Invalid quote IDs"), "error")
        return redirect(url_for("quotes.list_quotes"))

    # Get quotes (with permission check)
    quotes = Quote.query.filter(Quote.id.in_(quote_ids)).all()
    if not current_user.is_admin:
        quotes = [q for q in quotes if q.created_by == current_user.id]

    if not quotes:
        flash(_("No quotes found or you do not have permission"), "error")
        return redirect(url_for("quotes.list_quotes"))

    success_count = 0
    error_count = 0

    if action == "duplicate":
        from datetime import timedelta
        from app.utils.timezone import local_now

        for quote in quotes:
            try:
                new_quote_number = Quote.generate_quote_number()
                new_valid_until = local_now().date() + timedelta(days=30) if quote.valid_until else None

                new_quote = Quote(
                    quote_number=new_quote_number,
                    client_id=quote.client_id,
                    title=quote.title,
                    description=quote.description,
                    status="draft",
                    valid_until=new_valid_until,
                    notes=quote.notes,
                    terms=quote.terms,
                    payment_terms=quote.payment_terms,
                    created_by=current_user.id,
                    visible_to_client=quote.visible_to_client,
                    template_id=quote.template_id,
                    currency_code=quote.currency_code,
                    tax_rate=quote.tax_rate,
                    discount_type=quote.discount_type,
                    discount_amount=quote.discount_amount,
                    discount_reason=quote.discount_reason,
                    coupon_code=quote.coupon_code,
                    approval_status="not_required",
                )
                db.session.add(new_quote)
                db.session.flush()

                # Duplicate items
                for item in quote.items:
                    new_item = QuoteItem(
                        quote_id=new_quote.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        unit=item.unit,
                    )
                    db.session.add(new_item)

                new_quote.calculate_totals()
                success_count += 1
            except Exception as e:
                current_app.logger.error(f"Error duplicating quote {quote.id}: {e}")
                error_count += 1

        if safe_commit("bulk_duplicate_quotes", {"count": success_count}):
            flash(_("Duplicated %(count)d quote(s)", count=success_count), "success")
            if error_count > 0:
                flash(_("Failed to duplicate %(count)d quote(s)", count=error_count), "error")
        else:
            flash(_("Error duplicating quotes"), "error")

    elif action == "mark_sent":
        for quote in quotes:
            try:
                if quote.status == "draft" and quote.approval_status != "pending":
                    quote.send()
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                current_app.logger.error(f"Error marking quote {quote.id} as sent: {e}")
                error_count += 1

        if safe_commit("bulk_mark_sent", {"count": success_count}):
            flash(_("Marked %(count)d quote(s) as sent", count=success_count), "success")
            if error_count > 0:
                flash(_("Could not mark %(count)d quote(s) as sent", count=error_count), "error")
        else:
            flash(_("Error updating quotes"), "error")

    elif action == "delete":
        for quote in quotes:
            try:
                # Check if quote can be deleted
                if quote.status in ["draft", "rejected", "expired"]:
                    db.session.delete(quote)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                current_app.logger.error(f"Error deleting quote {quote.id}: {e}")
                error_count += 1

        if safe_commit("bulk_delete_quotes", {"count": success_count}):
            flash(_("Deleted %(count)d quote(s)", count=success_count), "success")
            if error_count > 0:
                flash(_("Could not delete %(count)d quote(s) (may be in use)", count=error_count), "error")
        else:
            flash(_("Error deleting quotes"), "error")

    else:
        flash(_("Invalid action"), "error")

    return redirect(url_for("quotes.list_quotes"))
