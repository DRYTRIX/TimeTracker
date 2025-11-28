"""
Routes for payment gateway management and payment processing.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.models import PaymentGateway, Invoice, PaymentTransaction
from app.services.payment_gateway_service import PaymentGatewayService
from app.utils.stripe_integration import StripeIntegration
from app.utils.permissions import admin_or_permission_required
from decimal import Decimal
import json
import os

payment_gateways_bp = Blueprint("payment_gateways", __name__)


@payment_gateways_bp.route("/payment-gateways")
@login_required
@admin_or_permission_required("admin_access")
def list_gateways():
    """List payment gateways"""
    gateways = PaymentGateway.query.all()
    return render_template("payment_gateways/list.html", gateways=gateways)


@payment_gateways_bp.route("/payment-gateways/create", methods=["GET", "POST"])
@login_required
@admin_or_permission_required("admin_access")
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

    config = json.loads(gateway.config) if isinstance(gateway.config, str) else gateway.config
    webhook_secret = config.get("webhook_secret") or os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        return jsonify({"error": "Webhook secret not configured"}), 500

    stripe_integration = StripeIntegration(gateway.config.get("api_key"))
    event = stripe_integration.verify_webhook(payload, sig_header, webhook_secret)

    if not event:
        return jsonify({"error": "Invalid signature"}), 400

    # Handle event
    service = PaymentGatewayService()

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        transaction_id = payment_intent["id"]
        invoice_id = int(payment_intent["metadata"].get("invoice_id", 0))

        if invoice_id:
            amount = Decimal(str(payment_intent["amount"])) / 100
            service.update_transaction_status(
                transaction_id=transaction_id, status="completed", gateway_response=payment_intent
            )

    return jsonify({"status": "success"})


@payment_gateways_bp.route("/payment-gateways/payment-success/<int:invoice_id>")
@login_required
def payment_success(invoice_id):
    """Payment success page"""
    invoice = Invoice.query.get_or_404(invoice_id)
    flash(_("Payment processed successfully."), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
