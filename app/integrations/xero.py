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

        scopes = ["accounting.transactions", "accounting.contacts", "accounting.settings", "offline_access"]

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
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        response = requests.post(
            token_url,
            headers={"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
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
                    f"{self.BASE_URL}/connections", headers={"Authorization": f"Bearer {data['access_token']}"}
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
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        response = requests.post(
            token_url,
            headers={"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": self.credentials.refresh_token},
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
                "GET", f"/api.xro/2.0/Organisation", self.get_access_token(), tenant_id
            )

            if organisation_info:
                org_name = organisation_info.get("Organisations", [{}])[0].get("Name", "Unknown")
                return {"success": True, "message": f"Connected to Xero organisation: {org_name}"}
            else:
                return {"success": False, "message": "Failed to retrieve organisation information"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def _api_request(self, method: str, endpoint: str, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Make API request to Xero"""
        url = f"{self.BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Xero-tenant-id": tenant_id,
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
                    Invoice.status.in_(["sent", "paid"]), Invoice.created_at >= datetime.utcnow() - timedelta(days=90)
                ).all()

                for invoice in invoices:
                    try:
                        xero_invoice = self._create_xero_invoice(invoice, access_token, tenant_id)
                        if xero_invoice:
                            # Store Xero ID in invoice metadata
                            if not hasattr(invoice, "metadata") or not invoice.metadata:
                                invoice.metadata = {}
                            invoice.metadata["xero_invoice_id"] = xero_invoice.get("Invoices", [{}])[0].get("InvoiceID")
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing invoice {invoice.id}: {str(e)}")

            # Sync expenses (create as expenses in Xero)
            if sync_type == "full" or sync_type == "expenses":
                expenses = Expense.query.filter(Expense.date >= datetime.utcnow().date() - timedelta(days=90)).all()

                for expense in expenses:
                    try:
                        xero_expense = self._create_xero_expense(expense, access_token, tenant_id)
                        if xero_expense:
                            if not hasattr(expense, "metadata") or not expense.metadata:
                                expense.metadata = {}
                            expense.metadata["xero_expense_id"] = xero_expense.get("Expenses", [{}])[0].get("ExpenseID")
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing expense {expense.id}: {str(e)}")

            db.session.commit()

            return {"success": True, "synced_count": synced_count, "errors": errors}

        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def _create_xero_invoice(self, invoice, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Create invoice in Xero"""
        # Get customer mapping from integration config or invoice metadata
        contact_mapping = self.integration.config.get("contact_mappings", {}) if self.integration else {}
        item_mapping = self.integration.config.get("item_mappings", {}) if self.integration else {}
        
        # Try to get Xero contact ID from mapping or metadata
        contact_id = None
        contact_name = invoice.client.name if invoice.client else "Unknown"
        
        if invoice.client_id:
            # Check mapping first
            contact_id = contact_mapping.get(str(invoice.client_id))
            # Fallback to invoice metadata
            if not contact_id and hasattr(invoice, "metadata") and invoice.metadata:
                contact_id = invoice.metadata.get("xero_contact_id")
        
        # Build Xero invoice structure
        xero_invoice = {
            "Type": "ACCREC",
            "Date": invoice.date.strftime("%Y-%m-%d") if invoice.date else datetime.utcnow().strftime("%Y-%m-%d"),
            "DueDate": (
                invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else datetime.utcnow().strftime("%Y-%m-%d")
            ),
            "LineItems": [],
        }
        
        # Add contact - use ID if available, otherwise use name
        if contact_id:
            xero_invoice["Contact"] = {"ContactID": contact_id}
        else:
            xero_invoice["Contact"] = {"Name": contact_name}
            logger.warning(f"Contact mapping not found for client {invoice.client_id}. Using name: {contact_name}")

        # Add invoice items
        for item in invoice.items:
            # Try to get Xero item code from mapping
            item_code = item_mapping.get(str(item.id)) or item_mapping.get(item.description, {}).get("code")
            
            line_item = {
                "Description": item.description,
                "Quantity": float(item.quantity),
                "UnitAmount": float(item.unit_price),
                "LineAmount": float(item.quantity * item.unit_price),
            }
            
            # Add item code if available
            if item_code:
                line_item["ItemCode"] = item_code
            
            xero_invoice["LineItems"].append(line_item)

        endpoint = "/api.xro/2.0/Invoices"
        return self._api_request("POST", endpoint, access_token, tenant_id)

    def _create_xero_expense(self, expense, access_token: str, tenant_id: str) -> Optional[Dict]:
        """Create expense in Xero"""
        # Get account mapping from integration config
        account_mapping = self.integration.config.get("account_mappings", {}) if self.integration else {}
        default_expense_account = self.integration.config.get("default_expense_account_code", "200") if self.integration else "200"
        
        # Try to get account code from expense category mapping or use default
        account_code = default_expense_account
        if expense.category_id:
            account_code = account_mapping.get(str(expense.category_id), default_expense_account)
        elif hasattr(expense, "metadata") and expense.metadata:
            account_code = expense.metadata.get("xero_account_code", default_expense_account)
        
        # Build Xero expense structure
        xero_expense = {
            "Date": expense.date.strftime("%Y-%m-%d") if expense.date else datetime.utcnow().strftime("%Y-%m-%d"),
            "Contact": {"Name": expense.vendor or "Unknown"},
            "LineItems": [
                {
                    "Description": expense.description or "Expense",
                    "Quantity": 1.0,
                    "UnitAmount": float(expense.amount),
                    "LineAmount": float(expense.amount),
                    "AccountCode": account_code,
                }
            ],
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
                    "required": True,
                    "placeholder": "tenant-uuid-123",
                    "description": "Xero organisation tenant ID",
                    "help": "Find your tenant ID in Xero after connecting. It's automatically set during OAuth.",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "xero_to_timetracker", "label": "Xero → TimeTracker (Import only)"},
                        {"value": "timetracker_to_xero", "label": "TimeTracker → Xero (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "timetracker_to_xero",
                    "description": "Choose how data flows between Xero and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "invoices", "label": "Invoices"},
                        {"value": "expenses", "label": "Expenses"},
                        {"value": "payments", "label": "Payments"},
                        {"value": "contacts", "label": "Contacts"},
                    ],
                    "default": ["invoices", "expenses"],
                    "description": "Select which items to synchronize",
                },
                {"name": "sync_invoices", "type": "boolean", "label": "Sync Invoices", "default": True, "description": "Enable invoice synchronization"},
                {"name": "sync_expenses", "type": "boolean", "label": "Sync Expenses", "default": True, "description": "Enable expense synchronization"},
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when invoices or expenses are created/updated",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
                {
                    "name": "default_expense_account_code",
                    "type": "string",
                    "label": "Default Expense Account Code",
                    "required": False,
                    "default": "200",
                    "description": "Xero account code to use for expenses when no mapping is configured",
                    "help": "Find account codes in Xero Chart of Accounts",
                },
                {
                    "name": "contact_mappings",
                    "type": "json",
                    "label": "Contact Mappings",
                    "required": False,
                    "placeholder": '{"1": "contact-uuid-123", "2": "contact-uuid-456"}',
                    "description": "JSON mapping of TimeTracker client IDs to Xero Contact IDs",
                    "help": "Map your TimeTracker clients to Xero contacts. Format: {\"timetracker_client_id\": \"xero_contact_id\"}",
                },
                {
                    "name": "item_mappings",
                    "type": "json",
                    "label": "Item Mappings",
                    "required": False,
                    "placeholder": '{"service_1": "item_code_123"}',
                    "description": "JSON mapping of TimeTracker invoice items to Xero item codes",
                    "help": "Map your TimeTracker services/products to Xero items",
                },
                {
                    "name": "account_mappings",
                    "type": "json",
                    "label": "Account Mappings",
                    "required": False,
                    "placeholder": '{"expense_category_1": "account_code_200"}',
                    "description": "JSON mapping of TimeTracker expense category IDs to Xero account codes",
                    "help": "Map your TimeTracker expense categories to Xero accounts",
                },
            ],
            "required": ["tenant_id"],
            "sections": [
                {
                    "title": "Connection Settings",
                    "description": "Configure your Xero connection",
                    "fields": ["tenant_id"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "sync_invoices", "sync_expenses", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Data Mapping",
                    "description": "Map TimeTracker data to Xero",
                    "fields": ["default_expense_account_code", "contact_mappings", "item_mappings", "account_mappings"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "timetracker_to_xero",
                "sync_items": ["invoices", "expenses"],
            },
        }
