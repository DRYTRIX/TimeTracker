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

        scopes = ["com.intuit.quickbooks.accounting", "com.intuit.quickbooks.payment"]

        params = {
            "client_id": client_id,
            "scope": " ".join(scopes),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "state": state or "",
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
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
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
                    "GET", f"/v3/company/{realm_id}/companyinfo/{realm_id}", data.get("access_token"), realm_id
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
            "extra_data": {"company_name": company_info.get("CompanyName", ""), "company_id": data.get("realmId")},
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
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
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
        self.credentials.save()

        return {"access_token": data.get("access_token"), "expires_at": expires_at.isoformat() if expires_at else None}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to QuickBooks."""
        try:
            realm_id = self.integration.config.get("realm_id") if self.integration else None
            if not realm_id:
                return {"success": False, "message": "QuickBooks company not configured"}

            company_info = self._api_request(
                "GET", f"/v3/company/{realm_id}/companyinfo/{realm_id}", self.get_access_token(), realm_id
            )

            if company_info:
                company_name = company_info.get("CompanyInfo", {}).get("CompanyName", "Unknown")
                return {"success": True, "message": f"Connected to QuickBooks company: {company_name}"}
            else:
                return {"success": False, "message": "Failed to retrieve company information"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def _api_request(self, method: str, endpoint: str, access_token: str, realm_id: str, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to QuickBooks"""
        base_url = self.get_base_url()
        url = f"{base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if realm_id:
            headers["realmId"] = realm_id

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, timeout=30, json=json_data or {})
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, timeout=30, json=json_data or {})
            else:
                response = requests.request(method, url, headers=headers, timeout=30, json=json_data)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"QuickBooks API request timeout: {method} {endpoint}")
            raise ValueError("QuickBooks API request timed out. Please try again.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"QuickBooks API connection error: {e}")
            raise ValueError(f"Failed to connect to QuickBooks API: {str(e)}")
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            if e.response:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("fault", {}).get("error", [{}])[0].get("detail", "")
                    if not error_detail:
                        error_detail = error_data.get("fault", {}).get("error", [{}])[0].get("message", "")
                except Exception:
                    error_detail = e.response.text[:200] if e.response.text else ""
            
            error_msg = f"QuickBooks API error ({e.response.status_code}): {error_detail or str(e)}"
            logger.error(f"QuickBooks API request failed: {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"QuickBooks API request failed: {e}", exc_info=True)
            raise ValueError(f"QuickBooks API request failed: {str(e)}")

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync invoices and expenses with QuickBooks"""
        from app.models import Invoice, Expense
        from app import db

        try:
            realm_id = self.integration.config.get("realm_id")
            if not realm_id:
                return {"success": False, "message": "QuickBooks company not configured"}

            access_token = self.get_access_token()
            if not access_token:
                return {"success": False, "message": "No access token available. Please reconnect the integration."}

            synced_count = 0
            errors = []

            # Sync invoices (create as invoices in QuickBooks)
            if sync_type == "full" or sync_type == "invoices":
                try:
                    invoices = Invoice.query.filter(
                        Invoice.status.in_(["sent", "paid"]), Invoice.created_at >= datetime.utcnow() - timedelta(days=90)
                    ).all()

                    for invoice in invoices:
                        try:
                            # Skip if already synced (has QuickBooks ID)
                            if hasattr(invoice, "metadata") and invoice.metadata and invoice.metadata.get("quickbooks_id"):
                                continue
                            
                            qb_invoice = self._create_quickbooks_invoice(invoice, access_token, realm_id)
                            if qb_invoice:
                                # Store QuickBooks ID in invoice metadata
                                if not hasattr(invoice, "metadata") or not invoice.metadata:
                                    invoice.metadata = {}
                                invoice.metadata["quickbooks_id"] = qb_invoice.get("Id")
                                synced_count += 1
                        except ValueError as e:
                            # Validation errors - log but continue
                            error_msg = f"Invoice {invoice.id}: {str(e)}"
                            errors.append(error_msg)
                            logger.warning(error_msg)
                        except requests.exceptions.HTTPError as e:
                            # API errors - log with details
                            error_msg = f"Invoice {invoice.id}: QuickBooks API error - {e.response.status_code}: {e.response.text[:200] if e.response else str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg, exc_info=True)
                        except Exception as e:
                            # Other errors
                            error_msg = f"Invoice {invoice.id}: {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg, exc_info=True)
                except Exception as e:
                    error_msg = f"Error fetching invoices: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Sync expenses (create as expenses in QuickBooks)
            if sync_type == "full" or sync_type == "expenses":
                try:
                    expenses = Expense.query.filter(Expense.date >= datetime.utcnow().date() - timedelta(days=90)).all()

                    for expense in expenses:
                        try:
                            # Skip if already synced
                            if hasattr(expense, "metadata") and expense.metadata and expense.metadata.get("quickbooks_id"):
                                continue
                            
                            qb_expense = self._create_quickbooks_expense(expense, access_token, realm_id)
                            if qb_expense:
                                if not hasattr(expense, "metadata") or not expense.metadata:
                                    expense.metadata = {}
                                expense.metadata["quickbooks_id"] = qb_expense.get("Id")
                                synced_count += 1
                        except ValueError as e:
                            # Validation errors
                            error_msg = f"Expense {expense.id}: {str(e)}"
                            errors.append(error_msg)
                            logger.warning(error_msg)
                        except requests.exceptions.HTTPError as e:
                            # API errors
                            error_msg = f"Expense {expense.id}: QuickBooks API error - {e.response.status_code}: {e.response.text[:200] if e.response else str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg, exc_info=True)
                        except Exception as e:
                            # Other errors
                            error_msg = f"Expense {expense.id}: {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg, exc_info=True)
                except Exception as e:
                    error_msg = f"Error fetching expenses: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_msg = f"Database error during sync: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                return {"success": False, "message": error_msg, "synced_count": synced_count, "errors": errors}

            if errors:
                return {
                    "success": True,
                    "synced_count": synced_count,
                    "errors": errors,
                    "message": f"Sync completed with {len(errors)} error(s). Synced {synced_count} items."
                }
            
            return {"success": True, "synced_count": synced_count, "errors": errors, "message": f"Successfully synced {synced_count} items."}

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during QuickBooks sync: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "message": error_msg}

    def _create_quickbooks_invoice(self, invoice, access_token: str, realm_id: str) -> Optional[Dict]:
        """Create invoice in QuickBooks"""
        # Get customer mapping from integration config or invoice metadata
        customer_mapping = self.integration.config.get("customer_mappings", {}) if self.integration else {}
        item_mapping = self.integration.config.get("item_mappings", {}) if self.integration else {}
        
        # Try to get QuickBooks customer ID from mapping or metadata
        customer_qb_id = None
        if invoice.client_id:
            # Check mapping first
            customer_qb_id = customer_mapping.get(str(invoice.client_id))
            # Fallback to invoice metadata
            if not customer_qb_id and hasattr(invoice, "metadata") and invoice.metadata:
                customer_qb_id = invoice.metadata.get("quickbooks_customer_id")
        
        # If no mapping found, try to find customer by name in QuickBooks
        if not customer_qb_id and invoice.client_id:
            try:
                customer_name = invoice.client.name if invoice.client else None
                if customer_name:
                    # Query QuickBooks for customer by DisplayName
                    # QuickBooks query syntax: SELECT * FROM Customer WHERE DisplayName = 'CustomerName'
                    # URL encode the query parameter
                    from urllib.parse import quote
                    # Escape single quotes for SQL (replace ' with '')
                    escaped_name = customer_name.replace("'", "''")
                    query = f"SELECT * FROM Customer WHERE DisplayName = '{escaped_name}'"
                    query_url = f"/v3/company/{realm_id}/query?query={quote(query)}"
                    
                    customers_response = self._api_request(
                        "GET",
                        query_url,
                        access_token,
                        realm_id
                    )
                    
                    if customers_response and "QueryResponse" in customers_response:
                        customers = customers_response["QueryResponse"].get("Customer", [])
                        if customers:
                            # Handle both single customer and list of customers
                            if isinstance(customers, list):
                                if len(customers) > 0:
                                    customer_qb_id = customers[0].get("Id")
                            else:
                                customer_qb_id = customers.get("Id")
                            
                            if customer_qb_id:
                                # Auto-save mapping for future use
                                if not self.integration.config:
                                    self.integration.config = {}
                                if "customer_mappings" not in self.integration.config:
                                    self.integration.config["customer_mappings"] = {}
                                self.integration.config["customer_mappings"][str(invoice.client_id)] = customer_qb_id
                                logger.info(f"Auto-mapped client {invoice.client_id} to QuickBooks customer {customer_qb_id}")
                    else:
                        logger.warning(f"Customer '{customer_name}' not found in QuickBooks. Please configure customer mapping.")
            except Exception as e:
                logger.error(f"Error looking up QuickBooks customer: {e}", exc_info=True)
        
        # If still no customer ID, we cannot create the invoice
        if not customer_qb_id:
            error_msg = f"Customer mapping not found for client {invoice.client_id}. Cannot create QuickBooks invoice."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Build QuickBooks invoice structure
        qb_invoice = {
            "CustomerRef": {"value": customer_qb_id},
            "Line": []
        }

        # Add invoice items
        for item in invoice.items:
            try:
                # Try to get QuickBooks item ID from mapping
                item_qb_id = item_mapping.get(str(item.id))
                if not item_qb_id and isinstance(item_mapping.get(item.description), dict):
                    item_qb_id = item_mapping.get(item.description, {}).get("id")
                
                item_qb_name = item.description or "Service"
                
                # If no mapping, try to find item by name in QuickBooks
                if not item_qb_id:
                    try:
                        # Query QuickBooks for item by Name
                        from urllib.parse import quote
                        # Escape single quotes for SQL (replace ' with '')
                        escaped_name = item_qb_name.replace("'", "''")
                        query = f"SELECT * FROM Item WHERE Name = '{escaped_name}'"
                        query_url = f"/v3/company/{realm_id}/query?query={quote(query)}"
                        
                        items_response = self._api_request(
                            "GET",
                            query_url,
                            access_token,
                            realm_id
                        )
                        
                        if items_response and "QueryResponse" in items_response:
                            items = items_response["QueryResponse"].get("Item", [])
                            if items:
                                # Handle both single item and list of items
                                if isinstance(items, list):
                                    if len(items) > 0:
                                        item_qb_id = items[0].get("Id")
                                else:
                                    item_qb_id = items.get("Id")
                                
                                if item_qb_id:
                                    # Auto-save mapping for future use
                                    if "item_mappings" not in self.integration.config:
                                        self.integration.config["item_mappings"] = {}
                                    self.integration.config["item_mappings"][str(item.id)] = item_qb_id
                                    logger.info(f"Auto-mapped invoice item {item.id} to QuickBooks item {item_qb_id}")
                    except Exception as e:
                        logger.warning(f"Error looking up QuickBooks item '{item_qb_name}': {e}")
                
                # Build line item
                line_item = {
                    "Amount": float(item.quantity * item.unit_price),
                    "DetailType": "SalesItemLineDetail",
                    "SalesItemLineDetail": {
                        "Qty": float(item.quantity),
                        "UnitPrice": float(item.unit_price),
                    },
                }
                
                if item_qb_id:
                    line_item["SalesItemLineDetail"]["ItemRef"] = {
                        "value": item_qb_id,
                        "name": item_qb_name,
                    }
                else:
                    # Use description as item name (QuickBooks will use or create item)
                    line_item["SalesItemLineDetail"]["ItemRef"] = {
                        "name": item_qb_name,
                    }
                    logger.warning(f"Item mapping not found for invoice item {item.id}. Using description as item name.")
                
                qb_invoice["Line"].append(line_item)
            except Exception as e:
                logger.error(f"Error processing invoice item {item.id}: {e}", exc_info=True)
                # Continue with other items instead of failing completely
                continue
        
        # Validate invoice has at least one line item
        if not qb_invoice["Line"]:
            error_msg = "Invoice has no valid line items"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Add invoice date and due date
        if invoice.created_at:
            qb_invoice["TxnDate"] = invoice.created_at.strftime("%Y-%m-%d")
        if invoice.due_date:
            qb_invoice["DueDate"] = invoice.due_date.strftime("%Y-%m-%d")
        
        endpoint = f"/v3/company/{realm_id}/invoice"
        result = self._api_request("POST", endpoint, access_token, realm_id, json_data=qb_invoice)
        
        if not result:
            raise ValueError("Failed to create invoice in QuickBooks - no response from API")
        
        # Validate response
        if "Invoice" not in result:
            raise ValueError(f"Invalid response from QuickBooks API: {result}")
        
        return result

    def _create_quickbooks_expense(self, expense, access_token: str, realm_id: str) -> Optional[Dict]:
        """Create expense in QuickBooks"""
        # Get account mapping from integration config
        account_mapping = self.integration.config.get("account_mappings", {}) if self.integration else {}
        default_expense_account = self.integration.config.get("default_expense_account_id") if self.integration else None
        
        # Try to get account ID from expense category mapping or use default
        account_id = default_expense_account
        if expense.category_id:
            account_id = account_mapping.get(str(expense.category_id), default_expense_account)
        elif hasattr(expense, "metadata") and expense.metadata:
            account_id = expense.metadata.get("quickbooks_account_id", default_expense_account)
        
        # If no account ID found, try to find or use default expense account
        if not account_id:
            try:
                # Query for default expense accounts
                from urllib.parse import quote
                query = "SELECT * FROM Account WHERE AccountType = 'Expense' AND Active = true MAXRESULTS 1"
                query_url = f"/v3/company/{realm_id}/query?query={quote(query)}"
                
                accounts_response = self._api_request(
                    "GET",
                    query_url,
                    access_token,
                    realm_id
                )
                
                if accounts_response and "QueryResponse" in accounts_response:
                    accounts = accounts_response["QueryResponse"].get("Account", [])
                    if accounts:
                        if isinstance(accounts, list):
                            if len(accounts) > 0:
                                account_id = accounts[0].get("Id")
                        else:
                            account_id = accounts.get("Id")
                
                if not account_id:
                    # Fallback to a common expense account ID
                    account_id = "1"
                    logger.warning("No expense account found, using default account ID 1")
            except Exception as e:
                logger.error(f"Error looking up QuickBooks expense account: {e}", exc_info=True)
                # Use fallback
                account_id = account_id or "1"
        
        # Build QuickBooks expense structure
        qb_expense = {
            "PaymentType": "Cash",
            "AccountRef": {"value": account_id},
            "Line": [
                {
                    "Amount": float(expense.amount),
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "AccountBasedExpenseLineDetail": {"AccountRef": {"value": account_id}},
                }
            ],
        }
        
        # Add vendor if available
        if expense.vendor:
            qb_expense["EntityRef"] = {"name": expense.vendor}
        
        # Add expense date
        if expense.date:
            qb_expense["TxnDate"] = expense.date.strftime("%Y-%m-%d")
        
        # Add memo/description
        if expense.description:
            qb_expense["Line"][0]["Description"] = expense.description

        endpoint = f"/v3/company/{realm_id}/purchase"
        result = self._api_request("POST", endpoint, access_token, realm_id, json_data=qb_expense)
        
        if not result:
            raise ValueError("Failed to create expense in QuickBooks - no response from API")
        
        # Validate response
        if "Purchase" not in result:
            raise ValueError(f"Invalid response from QuickBooks API: {result}")
        
        return result

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "realm_id",
                    "type": "string",
                    "label": "Company ID (Realm ID)",
                    "description": "QuickBooks company ID (realm ID)",
                },
                {
                    "name": "use_sandbox",
                    "type": "boolean",
                    "label": "Use Sandbox",
                    "default": True,
                    "description": "Use QuickBooks sandbox environment for testing",
                },
                {"name": "sync_invoices", "type": "boolean", "label": "Sync Invoices", "default": True},
                {"name": "sync_expenses", "type": "boolean", "label": "Sync Expenses", "default": True},
                {
                    "name": "default_expense_account_id",
                    "type": "string",
                    "label": "Default Expense Account ID",
                    "description": "QuickBooks account ID to use for expenses when no mapping is configured",
                    "default": "1",
                },
                {
                    "name": "customer_mappings",
                    "type": "json",
                    "label": "Customer Mappings",
                    "description": "JSON mapping of TimeTracker client IDs to QuickBooks customer IDs (e.g., {\"1\": \"qb_customer_id_123\"})",
                },
                {
                    "name": "item_mappings",
                    "type": "json",
                    "label": "Item Mappings",
                    "description": "JSON mapping of TimeTracker invoice items to QuickBooks items",
                },
                {
                    "name": "account_mappings",
                    "type": "json",
                    "label": "Account Mappings",
                    "description": "JSON mapping of TimeTracker expense category IDs to QuickBooks account IDs",
                },
            ],
            "required": ["realm_id"],
        }
