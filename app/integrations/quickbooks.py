"""
QuickBooks integration connector.
Sync invoices, expenses, and payments with QuickBooks Online.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os
import base64
import logging

logger = logging.getLogger(__name__)


class QuickBooksConnector(BaseConnector):
    """QuickBooks Online integration connector."""

    display_name = "QuickBooks Online"
    description = "Sync invoices, expenses, and payments with QuickBooks"
    icon = "quickbooks"

    BASE_URL = "https://sandbox-quickbooks.api.intuit.com"  # Sandbox
    PRODUCTION_URL = "https://quickbooks.api.intuit.com"  # Production

    @property
    def provider_name(self) -> str:
        return "quickbooks"

    def get_base_url(self):
        """Get base URL based on environment"""
        use_sandbox = self.integration.config.get("use_sandbox", True) if self.integration else True
        return self.BASE_URL if use_sandbox else self.PRODUCTION_URL

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get QuickBooks OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("quickbooks")
        client_id = creds.get("client_id") or os.getenv("QUICKBOOKS_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("QUICKBOOKS_CLIENT_SECRET")

        if not client_id:
            raise ValueError("QUICKBOOKS_CLIENT_ID not configured")

        auth_url = "https://appcenter.intuit.com/connect/oauth2"

        scopes = [
            "com.intuit.quickbooks.accounting",
            "com.intuit.quickbooks.payment"
        ]

        params = {
            "client_id": client_id,
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "state": state or ""
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("quickbooks")
        client_id = creds.get("client_id") or os.getenv("QUICKBOOKS_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("QUICKBOOKS_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("QuickBooks OAuth credentials not configured")

        token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

        # QuickBooks requires Basic Auth for token exchange
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
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

        # Get company info
        company_info = {}
        if "access_token" in data and "realmId" in data:
            try:
                realm_id = data["realmId"]
                company_response = self._api_request(
                    "GET",
                    f"/v3/company/{realm_id}/companyinfo/{realm_id}",
                    data.get("access_token"),
                    realm_id
                )
                if company_response:
                    company_info = company_response.get("CompanyInfo", {})
            except Exception:
                pass

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": "Bearer",
            "realm_id": data.get("realmId"),  # QuickBooks company ID
            "extra_data": {
                "company_name": company_info.get("CompanyName", ""),
                "company_id": data.get("realmId")
            }
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings
        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("quickbooks")
        client_id = creds.get("client_id") or os.getenv("QUICKBOOKS_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("QUICKBOOKS_CLIENT_SECRET")

        token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
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
        self.credentials.save()

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to QuickBooks."""
        try:
            realm_id = self.integration.config.get("realm_id") if self.integration else None
            if not realm_id:
                return {"success": False, "message": "QuickBooks company not configured"}

            company_info = self._api_request(
                "GET",
                f"/v3/company/{realm_id}/companyinfo/{realm_id}",
                self.get_access_token(),
                realm_id
            )

            if company_info:
                company_name = company_info.get("CompanyInfo", {}).get("CompanyName", "Unknown")
                return {
                    "success": True,
                    "message": f"Connected to QuickBooks company: {company_name}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to retrieve company information"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def _api_request(self, method: str, endpoint: str, access_token: str, realm_id: str) -> Optional[Dict]:
        """Make API request to QuickBooks"""
        base_url = self.get_base_url()
        url = f"{base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        if realm_id:
            headers["realmId"] = realm_id

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
            logger.error(f"QuickBooks API request failed: {e}")
            return None

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync invoices and expenses with QuickBooks"""
        from app.models import Invoice, Expense
        from app import db

        try:
            realm_id = self.integration.config.get("realm_id")
            if not realm_id:
                return {"success": False, "message": "QuickBooks company not configured"}

            access_token = self.get_access_token()
            synced_count = 0
            errors = []

            # Sync invoices (create as invoices in QuickBooks)
            if sync_type == "full" or sync_type == "invoices":
                invoices = Invoice.query.filter(
                    Invoice.status.in_(["sent", "paid"]),
                    Invoice.created_at >= datetime.utcnow() - timedelta(days=90)
                ).all()

                for invoice in invoices:
                    try:
                        qb_invoice = self._create_quickbooks_invoice(invoice, access_token, realm_id)
                        if qb_invoice:
                            # Store QuickBooks ID in invoice metadata
                            if not hasattr(invoice, 'metadata') or not invoice.metadata:
                                invoice.metadata = {}
                            invoice.metadata['quickbooks_id'] = qb_invoice.get("Id")
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing invoice {invoice.id}: {str(e)}")

            # Sync expenses (create as expenses in QuickBooks)
            if sync_type == "full" or sync_type == "expenses":
                expenses = Expense.query.filter(
                    Expense.date >= datetime.utcnow().date() - timedelta(days=90)
                ).all()

                for expense in expenses:
                    try:
                        qb_expense = self._create_quickbooks_expense(expense, access_token, realm_id)
                        if qb_expense:
                            if not hasattr(expense, 'metadata') or not expense.metadata:
                                expense.metadata = {}
                            expense.metadata['quickbooks_id'] = qb_expense.get("Id")
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

    def _create_quickbooks_invoice(self, invoice, access_token: str, realm_id: str) -> Optional[Dict]:
        """Create invoice in QuickBooks"""
        # Build QuickBooks invoice structure
        qb_invoice = {
            "Line": []
        }

        # Add invoice items
        for item in invoice.items:
            qb_invoice["Line"].append({
                "Amount": float(item.quantity * item.unit_price),
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "ItemRef": {
                        "value": "1",  # Would need to map to actual QuickBooks item
                        "name": item.description
                    },
                    "Qty": float(item.quantity),
                    "UnitPrice": float(item.unit_price)
                }
            })

        # Add customer reference (would need customer mapping)
        # qb_invoice["CustomerRef"] = {"value": customer_qb_id}

        endpoint = f"/v3/company/{realm_id}/invoice"
        return self._api_request("POST", endpoint, access_token, realm_id)

    def _create_quickbooks_expense(self, expense, access_token: str, realm_id: str) -> Optional[Dict]:
        """Create expense in QuickBooks"""
        # Build QuickBooks expense structure
        qb_expense = {
            "PaymentType": "Cash",
            "AccountRef": {
                "value": "1"  # Would need account mapping
            },
            "Line": [{
                "Amount": float(expense.amount),
                "DetailType": "AccountBasedExpenseLineDetail",
                "AccountBasedExpenseLineDetail": {
                    "AccountRef": {
                        "value": "1"  # Expense account
                    }
                }
            }]
        }

        endpoint = f"/v3/company/{realm_id}/purchase"
        return self._api_request("POST", endpoint, access_token, realm_id)

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "realm_id",
                    "type": "string",
                    "label": "Company ID (Realm ID)",
                    "description": "QuickBooks company ID (realm ID)"
                },
                {
                    "name": "use_sandbox",
                    "type": "boolean",
                    "label": "Use Sandbox",
                    "default": True,
                    "description": "Use QuickBooks sandbox environment for testing"
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
            "required": ["realm_id"]
        }

