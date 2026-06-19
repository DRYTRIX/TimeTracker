"""
Routes for payment gateway management and payment processing.
"""

from decimal import Decimal

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.models import Invoice
from app.services.checkout_service import CheckoutService
from app.services.payment_gateway_service import PaymentGatewayService
from app.utils.module_helpers import module_enabled
from app.utils.permissions import admin_or_permission_required

payment_gateways_bp = Blueprint("payment_gateways", __name__)


@payment_gateways_bp.route("/payment-gateways")
@login_required
@module_enabled("payment_gateways")
@admin_or_permission_required("manage_payment_gateways")
def list_gateways():
    """List payment gateways"""
    from app.models import PaymentGateway

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
                "sandbox": is_test_mode,
            }

        service = PaymentGatewayService()
        result = service.create_gateway(name=name, provider=provider, config=config, is_test_mode=is_test_mode)

        if result["success"]:
            flash(_("Payment gateway created successfully."), "success")
            return redirect(url_for("payment_gateways.list_gateways"))
        flash(result["message"], "error")

    return render_template("payment_gateways/create.html")


@payment_gateways_bp.route("/invoices/<int:invoice_id>/pay", methods=["GET", "POST"])
@login_required
@module_enabled("payment_gateways")
def pay_invoice(invoice_id):
    """Pay an invoice (staff)"""
    invoice = Invoice.query.get_or_404(invoice_id)
    checkout = CheckoutService()
    gateway = checkout.get_checkout_gateway()

    if not gateway:
        flash(_("No payment gateway configured. Please contact an administrator."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    if request.method == "POST":
        result = checkout.start_checkout(
            invoice,
            success_endpoint="payment_gateways.payment_success",
            cancel_endpoint="invoices.view_invoice",
        )
        if result.get("success"):
            return redirect(result["url"])
        flash(result.get("message") or _("Payment failed"), "error")

    return render_template("payment_gateways/pay.html", invoice=invoice, gateway=gateway)


@payment_gateways_bp.route("/payment-gateways/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook"""
    gateway = PaymentGatewayService().get_active_gateway(provider="stripe")
    if not gateway:
        return jsonify({"error": "Gateway not found"}), 404

    result = CheckoutService().complete_webhook(gateway, request.data, dict(request.headers))
    status = result.get("status", 500 if not result.get("success") else 200)
    if not result.get("success"):
        return jsonify({"error": result.get("message")}), status
    return jsonify({"status": "success"}), status


@payment_gateways_bp.route("/payment-gateways/paypal/webhook", methods=["POST"])
def paypal_webhook():
    """Handle PayPal webhook"""
    gateway = PaymentGatewayService().get_active_gateway(provider="paypal")
    if not gateway:
        return jsonify({"error": "Gateway not found"}), 404

    result = CheckoutService().complete_webhook(gateway, request.data, dict(request.headers))
    status = result.get("status", 500 if not result.get("success") else 200)
    if not result.get("success"):
        return jsonify({"error": result.get("message")}), status
    return jsonify({"status": "success"}), status


@payment_gateways_bp.route("/payment-gateways/payment-success/<int:invoice_id>")
@login_required
@module_enabled("payment_gateways")
def payment_success(invoice_id):
    """Payment success page"""
    flash(_("Payment processed successfully."), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
