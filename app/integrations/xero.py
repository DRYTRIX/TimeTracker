"""
Xero integration connector.
Sync invoices, expenses, and payments with Xero.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os
import base64
import logging

logger = logging.getLogger(__name__)


class XeroConnector(BaseConnector):
    """Xero integration connector."""

    display_name = "Xero"
    description = "Sync invoices, expenses, and payments with Xero"
    icon = "xero"

    BASE_URL = "https://api.xero.com"

    @property
    def provider_name(self) -> str:
        return "xero"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Xero OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("xero")
        client_id = creds.get("client_id") or os.getenv("XERO_CLIENT_ID")

        if not client_id:
            raise ValueError("XERO_CLIENT_ID not configured")

        scopes = [
            "accounting.transactions",
            "accounting.contacts",
            "accounting.settings",
            "offline_access"
        ]

        auth_url = "https://login.xero.com/identity/connect/authorize"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state or "",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("xero")
        client_id = creds.get("client_id") or os.getenv("XERO_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("XERO_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Xero OAuth credentials not configured")

        token_url = "https://identity.xero.com/connect/token"

        # Xero requires Basic Auth for token exchange
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri
            }
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Get tenant info
        tenant_info = {}
        if "access_token" in data:
            try:
                tenants_response = requests.get(
                    f"{self.BASE_URL}/connections",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                if tenants_response.status_code == 200:
                    tenants = tenants_response.json()
                    if tenants:
                        tenant_info = {
                            "tenantId": tenants[0].get("tenantId"),
                            "tenantName": tenants[0].get("tenantName"),
                        }
            except Exception:
                pass

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope"),
            "extra_data": tenant_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("xero")
        client_id = creds.get("client_id") or os.getenv("XERO_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("XERO_CLIENT_SECRET")

        token_url = "https://identity.xero.com/connect/token"

        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token
            }
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Update credentials
        self.credentials.access_token = data.get("access_token")
        if "refresh_token" in data:
            self.credentials.refresh_token = data.get("refresh_token")
        if expires_at:
            self.credentials.expires_at = expires_at
        from app.utils.db import safe_commit
        safe_commit("refresh_xero_token", {"integration_id": self.integration.id})

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Xero."""
        try:
            tenant_id = self.integration.config.get("tenant_id") if self.integration else None
            if not tenant_id:
                # Try to get from extra_data
                if self.credentials and self.credentials.extra_data:
                    tenant_id = self.credentials.extra_data.get("tenantId")

            if not tenant_id:
                return {"success": False, "message": "Xero tenant not configured"}

            organisation_info = self._api_request(
                "GET",
                f"/api.xro/2.0/Organisation",
                self.get_access_token(),
                tenant_id
            )

            if organisation_info:
                org_name = organisation_info.get("Organisations", [{}])[0].get("Name", "Unknown")
                return {
                    "success": True,
                    "message": f"Connected to Xero organisation: {org_name}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to retrieve organisation information"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def _api_request(self, method: str, endpoint: str, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Make API request to Xero"""
        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Xero-tenant-id": tenant_id
        }

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, timeout=10, json={})
            else:
                response = requests.request(method, url, headers=headers, timeout=10)

            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Xero API request failed: {e}")
            return None

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync invoices and expenses with Xero"""
        from app.models import Invoice, Expense
        from app import db

        try:
            tenant_id = self.integration.config.get("tenant_id")
            if not tenant_id:
                if self.credentials and self.credentials.extra_data:
                    tenant_id = self.credentials.extra_data.get("tenantId")
            
            if not tenant_id:
                return {"success": False, "message": "Xero tenant not configured"}

            access_token = self.get_access_token()
            synced_count = 0
            errors = []

            # Sync invoices (create as invoices in Xero)
            if sync_type == "full" or sync_type == "invoices":
                invoices = Invoice.query.filter(
                    Invoice.status.in_(["sent", "paid"]),
                    Invoice.created_at >= datetime.utcnow() - timedelta(days=90)
                ).all()

                for invoice in invoices:
                    try:
                        xero_invoice = self._create_xero_invoice(invoice, access_token, tenant_id)
                        if xero_invoice:
                            # Store Xero ID in invoice metadata
                            if not hasattr(invoice, 'metadata') or not invoice.metadata:
                                invoice.metadata = {}
                            invoice.metadata['xero_invoice_id'] = xero_invoice.get("Invoices", [{}])[0].get("InvoiceID")
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing invoice {invoice.id}: {str(e)}")

            # Sync expenses (create as expenses in Xero)
            if sync_type == "full" or sync_type == "expenses":
                expenses = Expense.query.filter(
                    Expense.date >= datetime.utcnow().date() - timedelta(days=90)
                ).all()

                for expense in expenses:
                    try:
                        xero_expense = self._create_xero_expense(expense, access_token, tenant_id)
                        if xero_expense:
                            if not hasattr(expense, 'metadata') or not expense.metadata:
                                expense.metadata = {}
                            expense.metadata['xero_expense_id'] = xero_expense.get("Expenses", [{}])[0].get("ExpenseID")
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing expense {expense.id}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}"
            }

    def _create_xero_invoice(self, invoice, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Create invoice in Xero"""
        # Build Xero invoice structure
        xero_invoice = {
            "Type": "ACCREC",
            "Contact": {
                "Name": invoice.client.name if invoice.client else "Unknown"
            },
            "Date": invoice.date.strftime("%Y-%m-%d") if invoice.date else datetime.utcnow().strftime("%Y-%m-%d"),
            "DueDate": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else datetime.utcnow().strftime("%Y-%m-%d"),
            "LineItems": []
        }

        # Add invoice items
        for item in invoice.items:
            xero_invoice["LineItems"].append({
                "Description": item.description,
                "Quantity": float(item.quantity),
                "UnitAmount": float(item.unit_price),
                "LineAmount": float(item.quantity * item.unit_price),
            })

        endpoint = "/api.xro/2.0/Invoices"
        return self._api_request("POST", endpoint, access_token, tenant_id)

    def _create_xero_expense(self, expense, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Create expense in Xero"""
        # Build Xero expense structure
        xero_expense = {
            "Date": expense.date.strftime("%Y-%m-%d") if expense.date else datetime.utcnow().strftime("%Y-%m-%d"),
            "Contact": {
                "Name": expense.vendor or "Unknown"
            },
            "LineItems": [{
                "Description": expense.description or "Expense",
                "Quantity": 1.0,
                "UnitAmount": float(expense.amount),
                "LineAmount": float(expense.amount),
            }]
        }

        endpoint = "/api.xro/2.0/Expenses"
        return self._api_request("POST", endpoint, access_token, tenant_id)

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "tenant_id",
                    "type": "string",
                    "label": "Tenant ID",
                    "description": "Xero organisation tenant ID"
                },
                {
                    "name": "sync_invoices",
                    "type": "boolean",
                    "label": "Sync Invoices",
                    "default": True
                },
                {
                    "name": "sync_expenses",
                    "type": "boolean",
                    "label": "Sync Expenses",
                    "default": True
                }
            ],
            "required": ["tenant_id"]
        }

