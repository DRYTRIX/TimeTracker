"""
Routes for payment gateway management and payment processing.
"""

import os
from decimal import Decimal

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models import Invoice, PaymentGateway, PaymentTransaction
from app.services.payment_gateway_service import PaymentGatewayService
from app.utils.module_helpers import module_enabled
from app.utils.permissions import admin_or_permission_required
from app.utils.stripe_integration import StripeIntegration

payment_gateways_bp = Blueprint("payment_gateways", __name__)


@payment_gateways_bp.route("/payment-gateways")
@login_required
@module_enabled("payment_gateways")
@admin_or_permission_required("manage_payment_gateways")
def list_gateways():
    """List payment gateways"""
    gateways = PaymentGateway.query.all()
    return render_template("payment_gateways/list.html", gateways=gateways)


@payment_gateways_bp.route("/payment-gateways/create", methods=["GET", "POST"])
@login_required
@module_enabled("payment_gateways")
@admin_or_permission_required("manage_payment_gateways")
def create_gateway():
    """Create a payment gateway"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        provider = request.form.get("provider", "").strip()
        is_test_mode = request.form.get("is_test_mode", "false").lower() == "true"

        # Get config based on provider
        config = {}
        if provider == "stripe":
            config = {
                "api_key": request.form.get("api_key", "").strip(),
                "publishable_key": request.form.get("publishable_key", "").strip(),
                "webhook_secret": request.form.get("webhook_secret", "").strip(),
            }
        elif provider == "paypal":
            config = {
                "client_id": request.form.get("client_id", "").strip(),
                "client_secret": request.form.get("client_secret", "").strip(),
            }

        service = PaymentGatewayService()
        result = service.create_gateway(name=name, provider=provider, config=config, is_test_mode=is_test_mode)

        if result["success"]:
            flash(_("Payment gateway created successfully."), "success")
            return redirect(url_for("payment_gateways.list_gateways"))
        else:
            flash(result["message"], "error")

    return render_template("payment_gateways/create.html")


@payment_gateways_bp.route("/invoices/<int:invoice_id>/pay", methods=["GET", "POST"])
@login_required
@module_enabled("payment_gateways")
def pay_invoice(invoice_id):
    """Pay an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Get active payment gateway
    service = PaymentGatewayService()
    gateway = service.get_active_gateway(provider="stripe")

    if not gateway:
        flash(_("No payment gateway configured. Please contact an administrator."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    if request.method == "POST":
        # Process payment
        amount = Decimal(str(invoice.total_amount))

        # For Stripe, create payment intent
        if gateway.provider == "stripe":
            # Get API key from config
            import json

            config = json.loads(gateway.config) if isinstance(gateway.config, str) else gateway.config
            api_key = config.get("api_key") or os.getenv("STRIPE_API_KEY")

            if not api_key:
                flash(_("Stripe API key not configured."), "error")
                return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

            stripe_integration = StripeIntegration(api_key)

            # Create checkout session
            success_url = request.url_root.rstrip("/") + url_for(
                "payment_gateways.payment_success", invoice_id=invoice_id
            )
            cancel_url = request.url_root.rstrip("/") + url_for("invoices.view_invoice", invoice_id=invoice_id)

            result = stripe_integration.create_checkout_session(
                invoice_id=invoice_id,
                amount=amount,
                currency=invoice.currency_code,
                success_url=success_url,
                cancel_url=cancel_url,
                description=f"Invoice {invoice.invoice_number}",
            )

            if result["success"]:
                return redirect(result["url"])
            else:
                flash(result["message"], "error")
        else:
            flash(_("Payment gateway not yet supported."), "error")

    return render_template("payment_gateways/pay.html", invoice=invoice, gateway=gateway)


@payment_gateways_bp.route("/payment-gateways/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook"""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    # Get webhook secret
    gateway = PaymentGatewayService().get_active_gateway(provider="stripe")
    if not gateway:
        return jsonify({"error": "Gateway not found"}), 404

    import json

    config = json.loads(gateway.config) if isinstance(gateway.config, str) else (gateway.config or {})
    webhook_secret = (config.get("webhook_secret") or os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    api_key = (config.get("api_key") or os.getenv("STRIPE_API_KEY") or "").strip()

    if not webhook_secret:
        return jsonify({"error": "Webhook secret not configured"}), 500

    if not api_key:
        return jsonify({"error": "Stripe API key not configured"}), 500

    stripe_integration = StripeIntegration(api_key)
    event = stripe_integration.verify_webhook(payload, sig_header, webhook_secret)

    if not event:
        return jsonify({"error": "Invalid signature"}), 400

    # Handle event
    service = PaymentGatewayService()

    event_type = event.get("type")
    data_obj = (event.get("data") or {}).get("object") or {}

    def _parse_invoice_id(obj) -> int:
        try:
            meta = obj.get("metadata") or {}
            return int(meta.get("invoice_id") or 0)
        except Exception:
            return 0

    def _get_or_create_transaction(transaction_id: str, invoice_id: int, amount: Decimal, currency: str, response):
        tx = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
        if tx:
            return tx
        tx = PaymentTransaction(
            invoice_id=invoice_id,
            gateway_id=gateway.id,
            transaction_id=transaction_id,
            amount=amount,
            currency=(currency or "EUR").upper(),
            status="processing",
            payment_method="card",
            gateway_response=response,
        )
        return tx

    if event_type in ("payment_intent.succeeded", "checkout.session.completed"):
        invoice_id = _parse_invoice_id(data_obj)
        transaction_id = (
            data_obj.get("payment_intent") if event_type == "checkout.session.completed" else data_obj.get("id")
        ) or ""
        if not invoice_id or not transaction_id:
            return jsonify({"status": "ignored"}), 200

        # Stripe amounts are in cents.
        amount_cents = data_obj.get("amount_received") or data_obj.get("amount_total") or data_obj.get("amount") or 0
        try:
            amount = (Decimal(str(amount_cents)) / 100) if amount_cents else Decimal("0")
        except Exception:
            amount = Decimal("0")
        currency = (data_obj.get("currency") or "EUR").upper()

        tx = PaymentTransaction.query.filter_by(transaction_id=transaction_id).first()
        if not tx:
            tx = PaymentTransaction(
                invoice_id=invoice_id,
                gateway_id=gateway.id,
                transaction_id=transaction_id,
                amount=amount,
                currency=currency,
                status="processing",
                payment_method="card",
                gateway_response=data_obj,
            )
            db.session.add(tx)

        # Update status idempotently (service only applies invoice changes on first completion).
        service.update_transaction_status(transaction_id=transaction_id, status="completed", gateway_response=data_obj)

    return jsonify({"status": "success"})


@payment_gateways_bp.route("/payment-gateways/payment-success/<int:invoice_id>")
@login_required
@module_enabled("payment_gateways")
def payment_success(invoice_id):
    """Payment success page"""
    invoice = Invoice.query.get_or_404(invoice_id)
    flash(_("Payment processed successfully."), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
